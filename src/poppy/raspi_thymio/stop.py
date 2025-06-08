"""
Command-line app to stop the Thymio.
"""

import logging
import os
from pathlib import Path

import click
from tdmclient import ClientAsync, aw

from .thymio import Thymio


@click.command(name="thymio-stop")
@click.option("--verbose/--quiet", default=False, help="Verbosity")
@click.option(
    "--loglevel",
    help="Logging level",
    default="DEBUG",
    show_default=True,
    type=click.STRING,
)
def main(verbose: bool, loglevel: str):
    """
    Stop the Thymio.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.DEBUG)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logging.info("Setting loglevel to %s = %s", loglevel, str(loglevel_int))

    thymio = Thymio(start=False)
    thymio.get_node()
    if thymio.node:
        aw(thymio.node.lock())
        if (r := aw(thymio.node.compile("call _poweroff()"))) is None:
            thymio.run()
        else:
            logging.warning("CAN'T RUN AESL: error %d", r)
    else:
        logging.warning("Init_thymio: NO NODE")


if __name__ == "__main__":
    main()
