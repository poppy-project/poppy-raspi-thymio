# -*- coding: utf-8 -*-

"""
Things that can be detected
"""

import colorsys
import logging
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Tuple

import numpy as np


class Kind(Enum):
    Ball = 0
    Cube = 1
    Star = 2


@dataclass
class Thing:
    """
    A thing that has been detected somewhere.
    """

    kind: Kind
    xyxy: np.ndarray
    color: Tuple = (0, 0, 0)
    confidence: float = 0.0
    best: bool = False

    @cached_property
    def center(self):
        """Center coordinates."""
        return np.array(
            ((self.xyxy[0] + self.xyxy[2]) // 2, (self.xyxy[1] + self.xyxy[3]) // 2)
        )

    @property
    def label(self) -> str:
        """Thing text label."""
        return f"{self.kind.name} {self.confidence:3.2f}"

    def __str__(self) -> str:
        return self.label
