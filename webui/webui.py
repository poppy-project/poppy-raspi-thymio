######################################
#   Jean-Luc.Charles@mailo.com
#   2024/12/16 - v1.1
######################################

import logging
import os
import signal
from time import sleep

from flask import Flask, Response

app = Flask(__name__)


def generate_frames():
    """Get frames from /run/ucia to stream to client."""

    previous = None
    
    while True:
        # Sleep
        sleep(0.200)

        # Send frame to video stream.
        with open("/run/ucia/frame.jpeg", "rb") as file:
            frame = file.read()
            if frame and frame != previous:
                previous = frame
                yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


@app.route("/video")
def video_feed():
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/halt")
def halt():
    logging.warning("Shutting down the RPi4...")
    os.system("shutdown -h now")


@app.route("/quit")
def quit():
    logging.warning("Quit required...")
    os.kill(os.getpid(), 9)
    sys.exit(0)


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    # Logging
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)
    logging.debug("Setting loglevel to %s", "DEBUG")

    # Run the web interface
    app.run(host="0.0.0.0", port=5000, threaded=True)
