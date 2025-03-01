# -*- coding: utf-8 -*-

"""
Things that can be detected
"""

import colorsys
import logging
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from pathlib import Path
from typing import List, Tuple

import numpy as np
from ultralytics import YOLO

from .detectable import Detectable, DetectableList
from .frame import Frame
from .self_type import Self


class ThingKind(IntEnum):
    Ball = 0
    Cube = 1
    Star = 2
    Other = 9


class Thing(Detectable):
    """
    A thing that has been detected somewhere.
    """

    def __init__(
        self,
        xyxy: np.ndarray,
        kind: ThingKind = ThingKind.Other,
        color: Tuple = (0, 0, 0),
        confidence: float = 1.0,
        target: bool = False,
        ttl: int = 3,
    ) -> None:
        self.xyxy = xyxy
        self.kind = kind
        self.color = color
        self.confidence = confidence
        self.target = target
        self.ttl = ttl

    @property
    def label(self) -> str:
        """Thing text label."""
        return f"{self.kind.name} {self.confidence:3.2f}"

    def __str__(self) -> str:
        # return self.label
        return f"{self.label}{self.center}={self.azel}{'!!' if self.target else ''}"


class ThingList(DetectableList[Thing]):
    """
    List of detected things.
    """

    # YOLO parameters are class attributes.
    minconfidence = 0.6
    maxdetect = 6
    yolo = None

    @classmethod
    def detect(cls, frame: Frame) -> Self:
        """
        Factory method to detect features in an image.
        Should be overridden in derived class.
        """
        if not ThingList.yolo:
            return cls([])

        # YOLO detection
        results = ThingList.yolo.predict(
            frame.gray,
            imgsz=frame.frame_size[0],
            classes=[e.value for e in ThingKind],
            conf=ThingList.minconfidence,
            max_det=ThingList.maxdetect,
        )
        boxes = results[0].boxes
        logging.debug("Thing Detect: detect %d boxes", len(boxes))

        # Interpret YOLO results as Things.
        def find_features(frame, boxes):
            """Interpret YOLO results as Things."""

            for class_id, confidence, xyxy in zip(
                (ThingKind(int(i)) for i in boxes.cls), boxes.conf, boxes.xyxy
            ):
                label = f"{class_id.name} {confidence:3.2f}"
                # Bounding box and center
                x1, y1, x2, y2 = (coords := xyxy.numpy().astype(int))
                if (
                    (slope := abs(np.arctan2(y2 - y1, x2 - x1)) - 0.785) > 0.15
                    or abs(x2 - x1) < 20
                    or abs(y2 - y1) < 20
                ):
                    logging.debug(
                        "Ignoring misshaped (%g > 0.15) %s %g %d,%d %d,%d",
                        slope,
                        class_id.name,
                        confidence,
                        *coords,
                    )
                    continue

                thing = Thing(
                    xyxy=np.array((x1, y2, x2, y1)),
                    kind=class_id,
                    confidence=confidence,
                )
                thing.color = frame.center_color(thing.center)

                # Yield thing.
                logging.debug("Yielding %s", str(thing))
                yield thing

        # Return list of things.
        return cls(find_features(frame, boxes))

    def __str__(self) -> str:
        return f"ThingList<{hex(id(self))}({ ", ".join(str(t) for t in self) })>"
