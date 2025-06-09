# -*- coding: utf-8 -*-

"""
Remote loop.
"""

import json
import logging
import threading
from pathlib import Path

from .thymio import Thymio

logger = logging.getLogger(__name__)


# Remote thread

class Remote(threading.Thread):
    """
    Continuously watch FIFO for JSON remote control events.
    Send button events to Thymio.
    Use program events to change Thymio program.
    """

    def __init__(
        self,
        fifo_fd: Path,
        thymio: Thymio,
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.daemon = True

        self.fifo_fd = fifo_fd
        self.fifo_fd.truncate()
        # self.wait_sec = 1.0 / freq_hz

        self.thymio = thymio

        logger.info("Remote loop fires depending on FIFO %s", self.fifo_fd.name)

    def run(self):
        """
        Run recurring thread.
        """
        logger.debug("Remote thread run")
        for line in self.fifo_fd:
            try:
                message = json.loads(line)
            except JSONDecodeError(e):
                logger.warn("Remote: Ignoring mangled JSON message: %s", e)
                continue  # Skip to next message

            if "button" in message.keys():
                try:
                    rc5 = int(message["button"])
                except ValueError:
                    logger.warn("Remote: Ignoring invalid button %s: %s", rc5, e)
                    continue  # Skip to next message
                logger.info("Remote: button %d", rc5)
                self.button(rc5)
            elif (program := message.get("program", None)) is not None:
                logger.info("Remote: program %s", program)
                self.program(program)
            else:
                logger.warn("Remote: Ignoring invalid JSON message: %s", message)

    def button(self, button):
        """
        Handle a button event.
        """
        logger.info("Button event from remote %s", button)
        # self.thymio.events({"command": (e := [button])})
        logger.debug("Send event command [%s]", button)

    def program(self, program: str):
        """
        Handle a button event.
        """
        logger.info("Program event from remote %s", program)
