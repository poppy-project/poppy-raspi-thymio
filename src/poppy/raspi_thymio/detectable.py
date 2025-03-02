# -*- coding: utf-8 -*-

"""
Base class for features that can be detected
"""

import colorsys
import logging
import sys
from dataclasses import dataclass
from enum import Enum, IntEnum
from functools import cached_property, total_ordering
from itertools import chain, groupby
from pathlib import Path
from typing import List, Tuple

import numpy as np

from .frame import Frame
from .self_type import Self

Mcenter = np.array([[0.5, 0, 0.5, 0], [0, 0.5, 0, 0.5]])
DetectableKind = IntEnum("Kind", ("Default", "Other"))


@total_ordering
class Detectable:
    """
    Any feature that can be detected.
    """

    def __init__(
        self,
        xyxy: np.ndarray,
        kind: Enum = DetectableKind.Default,
        color: Tuple = (255, 255, 255),
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

    @cached_property
    def center(self) -> np.ndarray:
        """
        Center coordinates.
        """
        return (Mcenter @ self.xyxy).astype(int)

    @cached_property
    def azel(self) -> Tuple[int, int]:
        """
        Azimuth, elevation.
        """
        az = int(self.center[0] / 0.32) - 1000
        el = int((600 - self.center[1]) * 1.9)
        return az, el

    def same_as(self: Self, other: Self) -> bool:
        """
        Decide whether other is the same feature as this one.
        """
        cen_diff = self.center - other.center
        cen_ssq = np.dot(cen_diff.T, cen_diff)

        col_diff = (
            colorsys.rgb_to_hls(*self.color)[0] - colorsys.rgb_to_hls(*other.color)[0]
        )
        logging.debug(
            "Check same %s@%s %s@%s: cen_ssq %g col_diff %g",
            str(self.color),
            str(self.center),
            str(other.color),
            str(other.center),
            cen_ssq,
            col_diff,
        )

        return self.kind == other.kind and cen_ssq <= 100 and abs(col_diff) <= 0.1

    def __lt__(self, other) -> bool:
        """Order by kind then by confidence."""
        return (self.kind.value - self.confidence) < (
            other.kind.value - other.confidence
        )

    def __eq__(self, other) -> bool:
        """Order by kind then by confidence."""
        return (self.kind.value == other.kind.value) and (
            self.confidence == other.confidence
        )

    def __str__(self) -> str:
        return f"{self.center[0]} {self.confidence:3.2f}"


class DetectableList(List[Detectable]):
    """
    List of detectable features.
    """

    def refresh(self: Self, frame: Frame) -> None:
        """
        Detect new features, refresh TTL.
        """
        update = self.detect(frame)
        self.merge(update)

    @classmethod
    def detect(cls, frame: Frame) -> Self:
        """
        Factory method to detect features in an image.
        Should be overridden in derived class.
        """
        return cls([])

    def merge(self: Self, update: Self) -> None:
        """
        Detect new features, refresh TTL.
        """
        logging.debug("Detectable: Merge into [%s]", ",".join(str(i) for i in self))
        logging.debug(
            "Detectable: w/ update [%s]", ",".join(str(i) for i in sorted(update))
        )
        pool = {k: list(g) for k, g in groupby(sorted(update), key=lambda x: x.kind)}
        logging.debug(
            "Detectable: w/ pool(%s): %s",
            ",".join(str(i) for i in pool.keys()),
            " ".join(f"[{str(i)}] = ({str(x)})" for i, x in pool.items()),
        )
        for i, feature in enumerate(self):
            if feature.ttl < 1:
                logging.debug("Detectable: dropping %s ttl < 1", str(feature))
                del self[i]
                continue
            feature.ttl -= 1
            for j, candidate in enumerate(pool[feature.kind]):
                logging.debug("Detectable: eval %s", str(feature))
                if feature.same_as(candidate):
                    logging.debug(
                        "Detectable: %s same feature %s", str(feature), str(candidate)
                    )
                    self[i] = candidate
                    del pool[feature.kind][j]
                    continue
                else:
                    logging.debug(
                        "Detectable: %s not same %s", str(feature), str(candidate)
                    )
        logging.debug(
            "Detectable: appending %s", " ".join(str(v) for v in pool.values())
        )
        self.extend(chain.from_iterable(pool.values()))

    def update_targets(self: Self) -> None:
        """
        For each kind, choose new target if needed.
        """
        features = sorted(self, key=lambda d: d.kind)
        for k, grp in groupby(features, key=lambda d: d.kind):
            subset = list(grp)
            # logging.debug("Update: subset %s", str(DetectableList(subset)))
            if not any(f.target for f in subset):
                by_conf = sorted(subset, key=lambda f: f.confidence, reverse=True)
                if by_conf and (best := by_conf[0]):
                    best.target = True
                    logging.debug("Update: %s is target", str(best))

    def format(self):
        """Format for JSON conversion."""
        features = sorted(self, key=lambda d: float(d.kind) - d.confidence)
        result = [
            {
                "class": int(f.kind),
                "conf": int(f.confidence * 100),
                "color": int(colorsys.rgb_to_hls(*f.color)[0] * 12.0),
                "az": azel[0],
                "el": azel[1],
                "xyxy": f.xyxy.tolist(),
                "rgb": f.color.tolist(),
                "name": f.kind.name,
                "label": f.label,
            }
            for f in features
            for azel in [f.azel]
        ]
        return result

    def __str__(self) -> str:
        return f"DetectableList<{hex(id(self))}({ ', '.join(str(t) for t in self) })>"
