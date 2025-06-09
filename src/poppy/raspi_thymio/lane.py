# -*- coding: utf-8 -*-

"""
Lanes that can be followed
"""

import colorsys
import logging
from collections import deque
from enum import IntEnum
from itertools import combinations
from typing import List, Tuple

import cv2
import numpy as np

from .detectable import Detectable, DetectableList
from .frame import Frame
from .self_type import Self


class LaneKind(IntEnum):
    Center = 0
    Other = 9


class Lane(Detectable):
    """
    A lane that can be followed.
    """

    def __init__(
        self,
        xyxy: np.ndarray,
        kind: LaneKind = LaneKind.Other,
        color: Tuple = (0, 0, 0),
        confidence: float = 0.5,
        target: bool = False,
        ttl: int = 3,
        slope: float = 0.0,
    ) -> None:
        self.xyxy = xyxy
        self.kind = kind
        self.color = color
        self.confidence = confidence
        self.target = target
        self.ttl = ttl
        self.slope = slope

    @property
    def label(self) -> str:
        """Lane text label."""
        return f"{self.azel[0]}"

    def format(self):
        """Format for JSON conversion."""
        result = super().format()
        result["slope"] = self.slope
        return result

    def event(self) -> List[List[int]]:
        """
        Format single thing as Thymio event.
        """
        f = self.format()
        vec = [f.get(i, 0) for i in ["az", "el", "slope"]]
        vec[2] = int(vec[2] * 100)
        return vec

    def __str__(self) -> str:
        return self.label


class LaneList(DetectableList[Lane]):
    """
    List of detected lanes.
    """

    # Hough parameters rho, theta, threshold; min pts, max gap; iterations
    hough_params = [2, np.pi / 90, 15]
    minlen, maxgap = 15, 25
    hough_iter = 8

    # Shared history of past lines
    lines = deque(maxlen=6)

    # Smoothing of lane lines
    bins_edges = 640 / 12.0 * np.array(range(12))

    @classmethod
    def detect(cls, frame: Frame) -> Self:
        """
        Factory method to detect lanes in an image.
        """
        lines = [
            cv2.HoughLinesP(
                frame.xray,
                *cls.hough_params,
                np.array([]),
                minLineLength=cls.minlen,
                maxLineGap=cls.maxgap,
            )
            * (frame.frame_size[0] / frame.hough_width)
            for i in range(cls.hough_iter)
        ]
        sample = np.concatenate(lines)
        combo = cls.add_lines(lines=sample)
        logger.debug("Detect_one: combo lines \n%s", str(combo))

        best_lanes = cls.choose_best_lane(lines=combo, frame=frame)
        logger.info("Best lanes %s", best_lanes)

        return cls(
            Lane(xyxy=np.array(line[2:6]), kind=LaneKind.Center, slope=line[6])
            for line in best_lanes
        )

    @classmethod
    def add_lines(cls, lines):
        """Add new lines to moving average."""

        # info = cls.analyze_lines(lines)

        # Combine new lines with history.
        if len(cls.lines) < 2:
            concat = cls.analyze_lines(lines)
            cls.lines.extend([concat[:, :, :4]])
        else:
            concat = cls.analyze_lines(np.concatenate(list(cls.lines) + [lines]))
            cls.lines.extend([cls.analyze_lines(lines)[:, :, :4]])

        # Filter to choose mostly vertical lines
        vertical = concat[abs(concat[:, :, 5]) > 0.3].reshape(-1, 1, 7)

        # Make historical consensus lines by binning X
        dig = np.digitize(vertical[:, 0, 4], cls.bins_edges)

        subset = (bc := np.bincount(dig)) > 0
        consensus = np.concatenate(
            [
                (np.bincount(dig, vertical[:, 0, i])[subset] / bc[subset]).reshape(
                    -1, 1, 1
                )
                for i in range(vertical.shape[2])
            ],
            axis=2,
        )

        return consensus

    @staticmethod
    def analyze_lines(lines):
        """Analyze Hough lines."""
        midpt = [lines[:, :, [0, 2]].mean(axis=2), lines[:, :, [1, 3]].mean(axis=2)]
        slope = np.arctan2(
            lines[:, 0, 2] - lines[:, 0, 0], lines[:, 0, 3] - lines[:, 0, 1]
        ) / (np.pi / 2)

        ln_av = np.reshape(np.c_[lines[:, 0, :], *midpt, slope], (-1, 1, 7))
        ln_av = ln_av[ln_av[:, 0, 4].argsort()]  # sort by midpoint X
        return ln_av

    @classmethod
    def choose_best_lane(cls, lines, frame) -> List[Tuple[int, int]] | None:
        """
        Select best lane from lines.
        Assume lines are sorted by midpoint (column 4).
        """
        d = lines.astype(int)[:, 0, [4, 5]]
        comp = {
            (i, j): ((d[i, 0] + d[j, 0]) // 2, (d[i, 1] + d[j, 1]) // 2, slope)
            for i, j in combinations(range(d.shape[0]), r=2)
            if abs(d[i, 0] - d[j, 0]) < 150
            if colorsys.rgb_to_hls(
                *frame.center_color_xyxy((d[i, 0], d[i, 1], d[j, 0], d[j, 1]))
            )[0]
            < 100
            if abs(slope := np.arctan2(d[j, 1] - d[i, 1], d[j, 0] - d[i, 0])) < 0.78
        }
        # logger.debug("*** comparison %s", str(comp))

        candidates = sorted(
            [
                (*c[:2], d[ab[0], 0], d[ab[0], 1], d[ab[1], 0], d[ab[1], 1], c[2])
                for ab, c in comp.items()
            ],
            key=lambda v: v[6],
        )
        # logger.debug("*** candidates %s", str(candidates))

        return candidates[: min(2, len(candidates))]

    def event(self) -> List[List[int]]:
        """
        Format lanes as Thymio event.
        """
        best = {
            k: obj.event()
            for k in LaneKind
            for obj in self
            if obj.kind == k and obj.target
        }
        return [i for k in LaneKind for i in best.get(k, [0, 0, 0]) if k < 9]

    def __str__(self) -> str:
        return f"LaneList<{hex(id(self))}({', '.join(str(t) for t in self)})>"
