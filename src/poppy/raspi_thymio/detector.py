"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mpoppy_raspi_thymio` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``poppy_raspi_thymio.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``poppy_raspi_thymio.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import logging
import os
import zmq
from pathlib import Path

import click

from .control import Control
from .remote import Remote
from .thymio import Thymio

logger = logging.getLogger(__name__)

FRAME_DIR = Path("/run/ucia")
OUT_FIFO = Path("/run/ucia/detection.fifo")
REMOTE_FIFO = Path("/run/ucia/remote.fifo")


@click.command(name="ucia-detector")
@click.option(
    "--freq",
    help="Capture frequency (Hz)",
    default=2,
    show_default=True,
    type=click.FLOAT,
)
@click.option(
    "--frame-dir",
    help="Output frame directory",
    default=FRAME_DIR,
    show_default=True,
    type=click.Path(path_type=Path, exists=False),
)
@click.option(
    "--zmq-address",
    help="Address for zmq",
    default="tcp://localhost:5556",
    show_default=True,
    type=click.STRING,
)
@click.option("--verbose/--quiet", default=False, help="YOLO verbose")
@click.option(
    "--loglevel",
    help="Logging level",
    default="DEBUG",
    show_default=True,
    type=click.STRING,
)
def main(
    freq: float,
    frame_dir: Path,
    zmq_address: str,
    verbose: bool,
    loglevel: str,
):
    """
    Continuously capture an image and detect objects using YOLO.
    Send JSON records to a FIFO and record image frames in files.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.DEBUG)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logger.info("Setting loglevel to %s = %s", loglevel, str(loglevel_int))
    logger.propagate = False

    frame_dir.mkdir(mode=0o775, parents=True, exist_ok=True)

    context = zmq.Context()

    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind("tcp://*:5557")
    logging.info("Open PUB zmq %s", pub_socket)

    sub_socket = context.socket(zmq.SUB)
    sub_socket.bind("tcp://*:5556")
    sub_socket.setsockopt(zmq.SUBSCRIBE, b'')
    logging.info("Open SUB zmq %s", sub_socket)

    thymio = Thymio(start=True)

    remote = Remote(
        zmq_socket=sub_socket,
        thymio=thymio,
    )
    remote.start()  # Run forever in background.

    control = Control(
        zmq_socket=pub_socket,
        frame_dir=frame_dir,
        freq_hz=freq,
        thymio=thymio,
    )
    control.start()  # Run forever in foreground.


if __name__ == "__main__":
    main()
