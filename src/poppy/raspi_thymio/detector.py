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
    "--fifo",
    help="Detector output named pipe",
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
@click.option(
    "--remote-fifo",
    help="Remote output named pipe",
    default=REMOTE_FIFO,
    show_default=True,
    type=click.Path(path_type=Path),
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
    fifo: Path,
    frame_dir: Path,
    remote_fifo: Path,
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

    for f in [fifo, remote_fifo]:
        if not f.is_fifo:
            os.mkfifo(fifo)

    thymio = Thymio(start=True)

    remote = Remote(
        fifo_fd=open(remote_fifo, "w+"),
        thymio=thymio,
    )
    remote.start()  # Run forever in background.

    control = Control(
        fifo_fd=open(fifo, mode="a"),
        frame_dir=frame_dir,
        freq_hz=freq,
        thymio=thymio,
    )
    control.start()  # Run forever in foreground.


if __name__ == "__main__":
    main()
