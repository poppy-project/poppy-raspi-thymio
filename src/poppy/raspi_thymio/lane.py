# -*- coding: utf-8 -*-

"""
Lanes that can be followed
"""

import colorsys
import logging
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Tuple

import numpy as np


@dataclass
class Lane:
    """
    A lane that can be followed.
    """

    xyxy: np.ndarray
    color: Tuple = (None, None, None)
    confidence: float = 1.0
    best: bool = False

    @cached_property
    def center(self):
        """Center coordinates."""
        return np.array(
            ((self.xyxy[0] + self.xyxy[2]) // 2, (self.xyxy[1] + self.xyxy[3]) // 2)
        )

    def __str__(self) -> str:
        return f"Lane {self.center[0]} {self.confidence:3.2f}"
