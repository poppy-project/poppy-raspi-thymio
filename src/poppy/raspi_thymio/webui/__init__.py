######################################
#   Jean-Luc.Charles@mailo.com
#   2024/12/16 - v1.1
######################################

import json
import logging
import os
import signal
import subprocess
import zmq
from importlib.resources import as_file, files
from itertools import cycle
from pathlib import Path
from time import sleep

import click
from flask import Flask, Response, render_template
from flask.cli import FlaskGroup

from poppy.raspi_thymio import __version__ as poppy_version
from .aesl import AeslData

REMOTE_FIFO = Path("/run/ucia/remote.fifo")
CUR_FRAME = Path("/run/ucia/frame.jpeg")

app = Flask(__name__)
zmq_socket = None

RC5 = dict(
    ((j := i.split(":"))[0], int(j[1]))
    for i in (
        "PLUS:16 MINUS:17 GO:53 FORWARD:80 BACKWARD:81 LEFT:85 RIGHT:86 STOP:87"
        " N0:0 N1:1 N2:2 N3:3 N4:4 N5:5 N6:6 N7:7 N8:8 N9:9"
    ).split(" ")
)


def generate_frames():
    """Get frames from /run/ucia to stream to client."""

    static_resource = files("poppy.raspi_thymio.webui").joinpath("static")
    with as_file(static_resource) as static:
        fallback_frames = [
            (Path(static) / f"PM5544-{i}.jpg").read_bytes() for i in range(3)
        ]
    fallback = cycle([fallback_frames[int(tick / 4)] for tick in range(12)])

    previous = None
    while True:
        # Sleep
        sleep(0.200)

        # Send frame to video stream.
        try:
            frame = CUR_FRAME.read_bytes()
        except FileNotFoundError:
            frame = next(fallback)

        if len(frame) == 0:
            frame = previous or next(fallback)

        if frame and frame != previous:
            previous = frame
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


def write_zmq_event(event: dict):
    """Write event to ZMQ."""
    global zmq_socket
    output = json.dumps(event)
    zmq_socket.send_string(f"remote {output}")
    logging.debug("Webui: wrote zmq (%s) remote %s", zmq_socket, output)


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/video")
def video_feed():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/halt")
@app.route("/power/shutdown")
def halt():
    logging.warning(response := "Shutting down the RPi4.")
    write_zmq_event(response := {"program": "_poweroff.aesl"})
    sleep(5)
    logging.shutdown()
    subprocess.run(["sudo", "shutdown", "-fh", "now"])
    return response


@app.route("/button/<string:button>")
def button(button: str):
    """Button route sends control event."""
    rc5 = RC5.get(button, 99)
    logging.debug(f"Sending button event {button} = {rc5}.")
    write_zmq_event(response := {"button": rc5})
    return response


@app.route("/program/<string:aesl>")
def program(aesl: str):
    """Program route sends control event."""
    logging.debug(f"Sending program event {aesl}.")
    write_zmq_event(response := {"program": aesl})
    return response


@app.route("/power/restart")
def restart():
    logging.warning(response := "Restarting ucia-detector.")
    subprocess.run(["sudo", "systemctl", "restart", "ucia-detector"])
    return response


@app.route("/power/stopThymio")
def stopThymio():
    logging.warning(response := "Stopping the Thymio.")
    write_zmq_event(response := {"program": "_poweroff.aesl"})
    sleep(8)
    subprocess.run(["sudo", "systemctl", "stop", "ucia-detector"])
    return response


@app.route("/quit")
def quit():
    logging.warning("Stopping the Web UI.")
    os.kill(os.getpid(), 9)
    sys.exit(0)


@app.context_processor
def inject_aesl_programs():
    """Thymio programs."""
    rsrc = files("poppy.raspi_thymio.aesl")
    aesl_files = sorted(i for i in (rsrc / ".").glob("[a-zA-Z0-9]*.aesl"))
    return dict(aesl_programs=[AeslData(p) for p in aesl_files])


@app.context_processor
def inject_svg_assets():
    """Software version."""
    rsrc = files("poppy.raspi_thymio.webui.static")
    # return dict(svg_assets={p.name: p for p in (rsrc / ".").glob("*.svg")})
    return dict(svg_assets={p.name: 1 for p in (rsrc / ".").glob("*.svg")})


@app.context_processor
def inject_software_version():
    """Software version."""
    return dict(software_version=f"v{poppy_version}")


@click.group(cls=FlaskGroup, create_app=lambda: app)
@click.option("--verbose/--quiet", default=False, help="Verbosity")
@click.option(
    "--loglevel",
    help="Logging level",
    default="DEBUG",
    show_default=True,
    type=click.STRING,
)
def main(
    # zmq_address: Path,
    verbose: bool,
    loglevel: str,
):
    """
    Run the server for the Web UI.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.DEBUG)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logging.info("Setting loglevel to %s = %s", loglevel, str(loglevel_int))

    # Output zmq.
    global zmq_socket
    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_socket.connect("tcp://localhost:5556")
    logging.info("Open output zmq %s", zmq_socket)

    # Guard for running the Web UI as a script.
    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    main()
