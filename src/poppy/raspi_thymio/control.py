# -*- coding: utf-8 -*-

"""
Control loop.
"""

import json
import logging
import signal
import threading
from pathlib import Path
from typing import Tuple

from .frame import Frame
from .lane import Lane, LaneKind, LaneList
from .thing import Thing, ThingKind, ThingList
from .thymio import Thymio

# Control thread


class Control(threading.Thread):
    """
    Continuously capture an image and detect objects.
    Send JSON records to a FIFO.
    Store image frames in files.
    """

    def __init__(
        self,
        fifo_fd: Path,
        frame_dir: Path,
        freq_hz=60,
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.daemon = False

        self.fifo_fd = fifo_fd
        self.frame_dir = frame_dir
        self.wait_sec = 1.0 / freq_hz

        self.frame = Frame(out_dir=frame_dir)
        self.thymio = Thymio(start=True)

        self.things = ThingList()
        self.lanes = LaneList()

        logging.info("Control loop fires every %g sec", self.wait_sec)

    def run(self):
        """
        Run recurring thread.
        """
        logging.debug("Control thread run")
        while True:
            self.sleep_event.clear()
            self.sleep_event.wait(self.wait_sec)
            logging.debug("Detector thread wakeup")
            threading.Thread(target=self.detect_one).start()

    def detect_one(self):
        """
        Capture one frame and detect objects.
        """
        self.frame.get_frame()
        self.things.refresh(self.frame)
        self.lanes.refresh(self.frame)

        self.things.update_targets()
        self.lanes.update_targets()
        
        # things = ThingList.detect(self.frame)
        # logging.info("Detect found %d things", len(things))

        # lanes = LaneList.detect(self.frame)
        # logging.info("Detect found %d lanes", len(things))

        # Write detected objects.
        for objects in self.things, self.lanes:
            output = json.dumps(objects.format())
            bytes = self.fifo_fd.write(f"{output}\n")
            self.fifo_fd.flush()
            logging.debug(
                "Detect: wrote fifo %s (%d) %s", self.fifo_fd.name, bytes, output
            )

        # Write decorated frame.
        self.frame.decorate(self.things, self.lanes)

        # Send Thymio events.
        self.thymio.events({"camera.best": (e := self.things.event())})
        logging.debug("Send event camera.best %s", str(e))

        self.thymio.events({"camera.lane": (e := self.lanes.event())})
        logging.debug("Send event camera.lane %s", str(e))

        for thing in self.things:
            v = thing.event()  # conf color az el
            self.thymio.events({"camera.detect": (e := [int(thing.kind), *v])})
            logging.debug("Send event camera.detect %s", str(e))
