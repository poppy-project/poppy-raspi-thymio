# -*- coding: utf-8 -*-

"""
Remote loop.
"""

import json
import logging
import threading
from pathlib import Path

from .thymio import Thymio

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
        # self.wait_sec = 1.0 / freq_hz

        self.thymio = thymio

        logging.info("Remote loop fires depending on FIFO %s", self.fifo_fd.name)

    def run(self):
        """
        Run recurring thread.
        """
        logging.debug("Control thread run")
        for line in self.fifo_fd:
            try:
                message = json.loads(line)
            except JSONDecodeError(e):
                logging.warn("Ignoring mangled JSON message: %s", e)
                continue  # Skip to next message

            if "button" in message.keys():
                try:
                    rc5 = int(message["button"])
                except ValueError:
                    logging.warn("Ignoring invalid button %s: %s", rc5, e)
                    continue  # Skip to next message
                self.button(rc5)
            elif (program := message.get("program", None)) is not None:
                self.program(program)
            else:
                logging.warn("Ignoring invalid JSON message: %s", message)

    def button(self, button):
        """
        Handle a button event.
        """
        logging.info("Button event from remote %s", button)
        # self.thymio.events({"command": (e := [button])})
        logging.debug("Send event command [%s]", button)

    def program(self, program: str):
        """
        Handle a button event.
        """
        logging.info("Program event from remote %s", program)
