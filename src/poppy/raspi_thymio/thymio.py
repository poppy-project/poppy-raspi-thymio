# -*- coding: utf-8 -*-

"""
Communication with a Thymio robot.
"""

import logging
from importlib.resources import as_file, files

from tdmclient import ClientAsync, aw


class Thymio:
    """
    Manage a connection to a Thymio.
    """

    def __init__(self, start: bool = True):
        self.client = None
        self.node = None
        if start:
            self.get_node()
            self.start()

    def get_node(self) -> None:
        """
        Start communication with a Thymio.
        """
        if not self.client:
            self.client = ClientAsync()

        self.node = aw(self.client.wait_for_node())

    def start(self) -> None:
        """
        Register events and program with a Thymio.
        """
        if self.node:
            aw(self.node.lock())
            aw(
                self.node.register_events(
                    [("camera.detect", 5), ("camera.thing", 60), ("camera.best", 12), ("camera.lane", 3)]
                )
            )
            aw(self.node.set_scratchpad(self.aseba_program()))
            if (r := aw(self.node.compile(self.aseba_program()))) is None:
                self.run()
            else:
                logging.warning("CAN'T RUN AESL: error %d", r)
        else:
            logging.warning("Init_thymio: NO NODE")

    def run(self) -> None:
        """
        Run program on a Thymio.
        """
        if self.node:
            aw(self.node.lock())
            aw(self.node.run())
            logging.info("RUNNING AESL")

    def events(self, events: dict) -> None:
        """
        Send event to Thymio.
        """
        logging.info("Thymio send event %s", str(events))
        if self.node:
            aw(self.node.lock())
            aw(self.node.send_events(events))

    def variables(self, assignments: dict) -> None:
        """
        Assign variables on Thymio.
        """
        for var, values in assignments.items():
            logging.info("Thymio set variable %s", str(var))
            if self.node:
                aw(self.node.lock())
                aw(self.node.set_variables(assignments))

    def aseba_program(self) -> str:
        """Aesl program."""
        resource = files("poppy.raspi_thymio.aesl").joinpath("poppy-raspi-thymio.aesl")
        with as_file(resource) as aesl, open(aesl, mode="r", encoding="UTF-8") as file:
            aseba_program = file.read()

        return aseba_program
