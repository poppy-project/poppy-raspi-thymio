# -*- coding: utf-8 -*-

"""
Control loop.
"""

import json
import logging
import threading
import zmq
from pathlib import Path

from .frame import Frame
from .thing import ThingKind, ThingList
from .thymio import Thymio

logger = logging.getLogger(__name__)

# Control thread


class Control(threading.Thread):
    """
    Continuously capture an image and detect objects.
    Send JSON records to a FIFO.
    Store image frames in files.
    """

    def __init__(
        self,
        zmq_socket,
        frame_dir: Path,
        freq_hz=60,
        detectables=[ThingList()],
        thymio=None,
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.daemon = False

        self.zmq_socket = zmq_socket

        self.frame_dir = frame_dir
        self.wait_sec = 1.0 / freq_hz

        self.frame = Frame(out_dir=frame_dir)
        self.thymio = thymio if thymio else Thymio(start=True)

        # self.things = ThingList()
        # self.lanes = LaneList()
        self.detectables = detectables

        logger.info("Control loop fires every %g sec", self.wait_sec)

        # Instantiate camera.
        camera = self.frame.camera()
        logger.info("Control frame uses camera %s", camera)

    def run(self):
        """
        Run recurring thread.
        """
        logger.debug("Control thread run")
        while True:
            self.sleep_event.clear()
            self.sleep_event.wait(self.wait_sec)
            logger.debug("Detector thread wakeup")
            threading.Thread(target=self.detect_one).start()

    def detect_one(self):
        """
        Capture one frame and detect objects.
        """
        self.frame.get_frame()
        for objects in self.detectables:
            objects.refresh(self.frame)
        # self.things.refresh(self.frame)
        # self.lanes.refresh(self.frame)

        for objects in self.detectables:
            objects.update_targets()
        # self.things.update_targets()
        # self.lanes.update_targets()

        # things = ThingList.detect(self.frame)
        # logger.info("Detect found %d things", len(things))

        # lanes = LaneList.detect(self.frame)
        # logger.info("Detect found %d lanes", len(things))

        # Write detected objects.
        # for objects in self.things, self.lanes:
        for objects in self.detectables:
            output = json.dumps(objects.format())
            self.zmq_socket.send_string(f"detection {output}")
            logging.debug("Detect: wrote zmq (%s) %s", self.zmq_socket, output)

        # Write decorated frame.
        # self.frame.decorate(self.things, self.lanes)
        self.frame.decorate(*self.detectables)

        # Send Thymio events.
        for objects in self.detectables:
            name = type(objects[0] if objects else objects).__name__.lower()
            self.thymio.events({f"camera.{name}": (e := objects.event())})
            logger.debug(f"Send event camera.{name} %s", str(e))

        # self.thymio.events({"camera.lane": (e := self.lanes.event())})
        # logger.debug("Send event camera.lane %s", str(e))

        for objects in self.detectables:
            for thing in objects:
                v = thing.event()  # conf color az el
                self.thymio.events({"camera.detect": (e := [int(thing.kind), *v])})
                logger.debug("Send event camera.detect %s", str(e))
                self.thymio.variables({"camera.detect": e})
                logger.debug("Set variable camera.detect %s", str(e))

        # Send Thymio variables.
        values = [0] * (4 * (len(ThingKind) - 1))
        for objects in self.detectables:
            for thing in objects:
                v = thing.event()  # conf color az el
                base = thing.kind * 4
                values[base : (base + len(v))] = v
        self.thymio.variables({"camera.thing": values})
        logger.debug("Set variable camera.thing %s", str(e))
