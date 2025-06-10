# -*- coding: utf-8 -*-

"""
Video frame handling.
"""

import logging
from functools import cached_property
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from find_system_fonts_filename import FindSystemFontsFilenameException  # type: ignore
from find_system_fonts_filename import get_system_fonts_filename  # type: ignore
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import poppy.raspi_thymio.colors as colors

logger = logging.getLogger(__name__)

Mcenter = np.array([[0.5, 0, 0.5, 0], [0, 0.5, 0, 0.5]])


class Frame:
    """
    Stream of video frames.
    """

    frame_size = (640, 640)
    hough_width = 320
    mask_poly = np.array([[0, 28], [4, 20], [26, 20], [30, 28]]) * hough_width // 30
    mask = cv2.fillPoly(
        np.zeros((hough_width, hough_width)), [mask_poly], (255, 255, 255)
    )
    _camera = None

    try:
        font_file = next(
            (f for f in get_system_fonts_filename() if Path(f).name == "Arial.ttf"),
            None,
        )
    except FindSystemFontsFilenameException:
        font_file = None
    font = (
        ImageFont.truetype(font_file, 12)
        if font_file
        else ImageFont.load_default(size=12)
    )

    def __init__(self, out_dir: Path | None = None) -> None:
        """
        Instantiate video frame stream, logging frames to out_dir.
        """
        if out_dir:
            try:
                (Path(out_dir) / "touch").touch(exist_ok=True)
            except FileNotFoundError:
                logger.warn(
                    "Frame: can't write to %s, frame logging deactivated", str(out_dir)
                )
                out_dir = None
        self.out_dir = out_dir or Path("/tmp")
        logger.info(
            "Frame<%s>: init, will %s.",
            hex(id(self)),
            f"log frames to {str(out_dir)}" if out_dir else "not log frames",
        )
        logger.debug("Frame: using font %s", str(self.font))

    def get_frame(self, image_file: Path | None = None) -> None:
        """
        Get a video frame, from file if provided, else from camera.
        """
        if image_file:
            logger.debug("Frame: reading from %s", str(image_file))
            color = Image.open(image_file)
        else:
            logger.debug("Frame: reading from camera")
            color = self.camera().capture_image()
        self.color = color.resize(self.frame_size)

        with open(self.out_dir / "raw.jpeg", "wb") as f:
            self.color.save(f)
            logger.debug("Frame: wrote raw frame %s", f.name)

        # Invalidate cached properties
        try:
            del self.gray
            del self.xray
        except AttributeError:
            pass

    @cached_property
    def gray(self) -> Image.Image:
        """
        Return grayscale image.
        """
        return self.color.convert("L")

    @cached_property
    def xray(self) -> np.ndarray:
        """
        Return x-ray image.
        """
        blur = self.gray.resize((self.hough_width, self.hough_width)).filter(
            ImageFilter.GaussianBlur(4)
        )
        xray = cv2.Canny(np.array(blur), 30, 100)
        # xray = cv2.bitwise_and(xray, self.mask)

        cv2.imwrite(str(f_name := self.out_dir / "xray.jpeg"), xray)
        logger.debug("Frame: wrote xray frame %s", f_name)
        return xray

    def remap_gray(self, coord: np.ndarray) -> np.ndarray:
        """Remap coord to gray dimensions."""
        return coord

    def remap_xray(self, coord: np.ndarray) -> np.ndarray:
        """Remap coord to x-ray dimensions."""
        return (coord * self.frame_size[0] / self.hough_width).astype(int)

    def center_color(self, center) -> Tuple[int, int, int]:
        """Mean object color around the center."""
        cx, cy = center

        rgb = (
            np.array(self.color)[(cy - 7):(cy + 7), (cx - 7):(cx + 7)]
            .mean(axis=0)
            .mean(axis=0)
            .astype(int)
        )
        # logger.debug(
        #     "*** midpoint color (%d,%d) = %s im %s", cx, cy, str(rgb), str(self.color)
        # )
        return rgb

    def center_color_xyxy(self, xyxy) -> np.ndarray:
        """
        Center coordinates of a box.
        """
        return self.center_color((Mcenter @ xyxy).astype(int))

    def decorate(self, things=None, lanes=None) -> None:
        """
        Destructively decorate video frame with the detected boxes and lanes.
        """
        draw = ImageDraw.Draw(self.color, "RGBA")
        bg_col = colors.BR_YELLOW
        fg_col = colors.BLACK
        td_col = colors.BR_GRAY
        ln_col = colors.BR_CYAN

        for thing in things or []:
            x1, y1, x2, y2 = thing.xyxy
            y1, y2 = sorted((y1, y2))

            # Bounding box
            draw.rectangle([(x1, y1), (x2, y2)], outline=bg_col, width=2)
            h, w = (m := self.font.getmask(thing.label).getbbox())[3] + 2, m[2] + 1
            draw.rectangle(((x1, y1 - h - 2), (x1 + w, y1 - 1)), fill=bg_col)
            draw.text((x1 + 1, y1 - h - 2), thing.label, font=self.font, fill=fg_col)

            # Target
            if thing.target:
                cx, cy = thing.center
                draw.line([cx, cy - 8, cx, cy + 8], width=1, fill=td_col)
                draw.line([cx - 8, cy, cx + 8, cy], width=1, fill=td_col)

        for lane in lanes or []:
            x1, y1, x2, y2 = lane.xyxy
            y1, y2 = sorted((y1, y2))
            cx, cy = lane.center
            draw.line([x1, y1, x2, y2], width=1, fill=ln_col)
            # endpts = [*(lane.center - (12, 18)), *(lane.center + (12, 12))]
            draw.pieslice(
                [cx - 12, cy - 18, cx + 12, cy + 12], start=50, end=130, fill=ln_col
            )

        with open(self.out_dir / "frame.jpeg", "wb") as f:
            self.color.save(f)
            logger.debug("Frame: wrote frame %s", f.name)

    @classmethod
    def camera(cls):
        """
        Get the Pi camera, instantiate only once even if shared by multiple
        video streams.
        """

        # Conditionally import optional dependency picamera2
        try:
            from picamera2 import Picamera2  # type: ignore[import-not-found]
        except ImportError:
            logger.warn("Camera: optional dependency Picamera2 missing, no camera")
            cls._camera = False
            return None

        if not cls._camera and cls._camera is not False:
            cls._camera = Picamera2()
            cls._camera.preview_configuration.main.size = cls.frame_size
            cls._camera.preview_configuration.main.format = "RGB888"
            cls._camera.preview_configuration.align()
            cls._camera.configure("preview")
            cls._camera.start()
            logger.info("Camera %s", str(cls._camera))

        return cls._camera

    def __str__(self) -> str:
        return f"{self}"
