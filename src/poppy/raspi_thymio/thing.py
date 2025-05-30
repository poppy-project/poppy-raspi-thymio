# -*- coding: utf-8 -*-

"""
Things that can be detected.
"""

import logging
import os
from enum import IntEnum
from pathlib import Path
from typing import List, Tuple

import numpy as np
from ultralytics import YOLO

from .detectable import Detectable, DetectableList
from .frame import Frame
from .self_type import Self


class ThingKind(IntEnum):
    Parking = 0   # V3 native 0
    Zebra = 1     # V3 native 14
    Stop = 2      # V3 native 12
    Balle = 3     # V3 native 1
    Cube = 4      # V3 native 3
    Cylindre = 5  # V3 native 4
    Hexagone = 6  # V3 native 5
    Home = 7      # V3 native 6
    Etoile = 8    # V3 native 11
    Triangle = 9  # V3 native 13
    Cible = 10    # V3 native 2
    Nid = 11      # V3 native 10
    Gauche = 12   # V3 native 7
    Droite = 13   # V3 native 8
    Voie = 14     # V3 native 9
    Other = 15


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
        return f"{self.kind.name} {self.kind} {self.confidence:3.2f}"

    def event(self) -> List[List[int]]:
        """
        Format single thing as Thymio event.
        """
        f = self.format()
        return [f.get(i, 0) for i in ["conf", "color", "az", "el"]]

    def __str__(self) -> str:
        # return self.label
        return f"{self.label}{self.center}={self.azel}{'!' if self.target else ''}"


class ThingList(DetectableList[Thing]):
    """
    List of detected things.
    """

    # YOLO parameters are class attributes.
    minconfidence = 0.6
    maxdetect = 15
    yolo_version = os.environ.get("UCIA_YOLO_VERSION", "v8n")
    yolo_epochs = os.environ.get("UCIA_YOLO_EPOCHS", 300)
    yolo_batch = os.environ.get("UCIA_YOLO_BATCH", 30)
    yolo_weights = (
        Path(os.environ.get("UCIA_MODELS", "."))
        / "YOLO-trained-V3"
        / f"UCIA-II-YOLO{yolo_version}"
        / f"batch-{int(yolo_batch):02d}_epo-{int(yolo_epochs):03d}"
        / "weights/best_ncnn_model"
    )
    logging.info("Loading YOLO model %s", yolo_weights)
    yolo = YOLO(yolo_weights, task="detect", verbose=False)
    logging.info("Loaded YOLO model")

    kind_remap = [0, 3, 10, 4, 5, 6, 7, 12, 13, 14, 11, 8, 2, 9, 1]

    @classmethod
    def detect(cls, frame: Frame) -> Self:
        """
        Factory method to detect things in an image.
        """
        if not cls.yolo:
            return cls([])

        # YOLO detection
        results = cls.yolo.predict(
            frame.gray,
            imgsz=frame.frame_size[0],
            classes=[e.value for e in ThingKind],
            conf=cls.minconfidence,
            max_det=cls.maxdetect,
            verbose=False,
        )
        boxes = results[0].boxes
        logging.debug("Thing Detect: detect %d boxes", len(boxes))

        # Interpret YOLO results as Things.
        def find_features(frame, boxes):
            """Interpret YOLO results as Things."""

            for class_id, confidence, xyxy in zip(
                (ThingKind(int(i)) for i in boxes.cls), boxes.conf, boxes.xyxy
            ):
                # label = f"{class_id.name} {confidence:3.2f}"
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
                    kind=ThingKind(cls.kind_remap[class_id]),
                    confidence=confidence,
                )
                thing.color = frame.center_color(thing.center)

                # Yield thing.
                logging.debug("Yielding %s", str(thing))
                yield thing

        # Return list of things.
        return cls(find_features(frame, boxes))

    def event(self) -> List[List[int]]:
        """
        Format things as Thymio event.
        """
        best = {
            k: obj.event()
            for k in ThingKind
            for obj in self
            if obj.kind == k and obj.target
        }
        return [
            i
            for k in ThingKind
            for i in best.get(k, [0, 0, 0, 0])
            if k < ThingKind.Other
        ]

    def __str__(self) -> str:
        return f"ThingList<{hex(id(self))}({', '.join(str(t) for t in self)})>"
