# -*- coding: utf-8 -*-

"""
Things that can be detected
"""

import colorsys
import logging
from enum import Enum
from pathlib import Path
from typing import Tuple

import numpy as np


class Kind(Enum):
    Ball = 0
    Cube = 1
    Star = 2


class Thing:
    """
    A thing that has been detected somewhere.
    """

    def __init__(
        self,
        kind: Kind,
        xyxy: np.ndarray,
        color: Tuple = (0, 0, 0),
        confidence: float = 0.0,
        best: bool = False,
    ) -> None:
        """
        A Thing has a class, a position, and a confidence.
        """
        self.kind = kind
        self.confidence = confidence
        self.xyxy = xyxy
        self.center = np.array(((xyxy[0] + xyxy[2]) // 2, (xyxy[1] + xyxy[3]) // 2))
        self.color = color

    @property
    def label(self) -> str:
        """Thing text label."""
        return f"{self.kind.name} {self.confidence:3.2f}"

    def __str__(self) -> str:
        return self.label
