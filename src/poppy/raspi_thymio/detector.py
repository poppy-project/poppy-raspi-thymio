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
import signal
from pathlib import Path

import click

from .control import Control

FRAME_DIR = Path("/run/ucia")
OUT_FIFO = Path("/run/ucia/detection.fifo")


@click.command(name="ucia-detector")
@click.option(
    "--freq",
    help="Capture frequency (Hz)",
    default=2,
    show_default=True,
    type=click.FLOAT,
)
@click.option(
    "--fifo",
    help="Output named pipe",
    default=OUT_FIFO,
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--frame-dir",
    help="Output frame directory",
    default=FRAME_DIR,
    show_default=True,
    type=click.Path(path_type=Path, exists=False),
)
@click.option("--verbose/--quiet", default=False, help="YOLO verbose")
@click.option(
    "--loglevel",
    help="Logging level",
    default="DEBUG",
    show_default=True,
    type=click.STRING,
)
def main(freq: float, fifo: Path, frame_dir: Path, verbose: bool, loglevel: str):
    """
    Continuously capture an image and detect objects using YOLO.
    Send JSON records to a FIFO and record image frames in files.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.DEBUG)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logging.info("Setting loglevel to %s = %s", loglevel, str(loglevel_int))

    frame_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    if not fifo.is_fifo:
        os.mkfifo(fifo)
        logging.info("Made FIFO %s", fifo)
    fifo_fd = open(fifo, "w")

    control = Control(
        fifo_fd=fifo_fd,
        frame_dir=frame_dir,
        freq_hz=freq,
    )
    control.start()  # run forever in foreground


if __name__ == "__main__":
    main()
