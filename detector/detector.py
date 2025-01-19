#!/bin/env python

# Inria 2025-01-18: David James Sherman <david.sherman@inria.fr>
#
# Inspired by detect_camera-3 2024-12-16 - v1.1
# by Jean-Luc Charles <Jean-Luc.Charles@mailo.com>

import json
import logging
import os
import signal
import threading
from pathlib import Path

import click
import cv2
import numpy as np
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFont
from tdmclient import ClientAsync, aw
from ultralytics import YOLO

# Constants

CAPTURE_SIZE = (640, 640)
FRAME_DIR = Path("/run/ucia")
OUT_FIFO = Path("/run/ucia/detection.fifo")

FONT = ImageFont.truetype("/home/ucia/.config/Ultralytics/Arial.ttf", 12)


# Shape class names and colors


class Class:
    def __init__(self, name, color, box, label):
        self.name = name
        self.color = color
        self.box = box
        self.label = label


shape = [
    Class("Ball", (80, 145, 255, 250), (80, 145, 255, 150), (255, 255, 255, 250)),
    Class("Cube", (240, 150, 100, 250), (240, 150, 100, 150), (0, 0, 0, 250)),
    Class("Star", (255, 255, 255, 250), (255, 255, 255, 150), (0, 0, 0, 250)),
]

# Detector thread


class Detector(threading.Thread):
    """
    Continuously capture an image and detect objects.
    Send JSON records to a FIFO.
    Store image frames in files.
    """

    def __init__(
        self, camera, yolo, fifo, thymio=None, freq_hz=60, minconf=0.6, maxdetect=6
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.wait_sec = 1.0 / freq_hz
        self.daemon = False
        self.camera = camera
        self.yolo = yolo
        self.fifo = fifo
        self.thymio = thymio
        self.minconfidence = minconf
        self.maxdetect = maxdetect
        logging.info("Detector fires every %g sec", self.wait_sec)

    def run(self):
        """Run recurring thread."""
        logging.debug("Detector thread run")
        while True:
            self.sleep_event.clear()
            self.sleep_event.wait(self.wait_sec)
            logging.debug("Detector thread wakeup")
            threading.Thread(target=self.detect_one).start()

    # Detection

    def detect_one(self):
        """
        Capture one frame and detect objects.
        """
        # Capture frame.
        color = self.camera.capture_image().resize(CAPTURE_SIZE)
        gray = color.convert("L")
        with open(FRAME_DIR / "raw.jpeg", "wb") as f:
            color.save(f)
            logging.info("Detect_one: wrote raw frame %s", f.name)

        # Detect objects
        results = self.yolo.predict(
            gray,
            imgsz=CAPTURE_SIZE[0],
            classes=[0, 1, 2],
            conf=self.minconfidence,
            max_det=self.maxdetect,
        )
        boxes = results[0].boxes
        logging.info("Detect_one: detect %d boxes", len(boxes))
        objects = list(self.find_objects(color, boxes))
        logging.info("Detect_one: found %d objects", len(objects))

        # Write detected objects
        for obj in objects:
            output = json.dumps(obj)
            bytes = self.fifo.write(f"{output}\n")
            self.fifo.flush()
            logging.debug(
                "Detect_one: wrote (%d) to %s %s", bytes, self.fifo.name, output
            )

        # Send camera best event
        self.thymio.events({"camera.best": self.best_objects(objects)})

        # Write decorated frame.
        with open(FRAME_DIR / "frame.jpeg", "wb") as f:
            self.decorate(color, boxes).save(f)
            logging.debug("Detect_one: wrote frame %s", f.name)

    def find_objects(self, image, boxes):
        """
        Interpret results as objects.
        """
        for class_id, confidence, xyxy in zip(
            (int(i) for i in boxes.cls), boxes.conf, boxes.xyxy
        ):
            name = shape[class_id].name
            label = f"{name} {confidence:3.2f}"
            # Bounding box and center
            x1, y1, x2, y2 = xyxy.numpy().astype(int)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            # mean object color around the center:
            rgb = (
                np.array(image)[cy - 7 : cy + 7, cx - 7 : cx + +7]
                .mean(axis=0)
                .mean(axis=0)
                .astype(int)
            )
            hue = self.rgb_to_hue(rgb)
            obj = {
                "class": class_id,
                "conf": int(100 * confidence),
                "color": (int(hue / 30.0) + 12) % 12,
                "az": int((x1 + x2) / 2 / 0.32) - 1000,
                "el": int((600 - (y1 + y2) / 2) * 1.9),
                "xyxy": [int(i) for i in (x1, y2, x2, y1)],
                "rgb": rgb.tolist(),
                "name": name,
                "label": label,
            }

            # Inform Thymio
            self.thymio.events(
                {
                    "camera.detect": [
                        obj[i] for i in ["class", "conf", "color", "az", "el"]
                    ]
                }
            )

            # Yield object
            logging.debug("Yielding %s", str(obj))
            yield obj

    def best_objects(self, objects):
        """
        Select best object of each class.
        """
        best = {}
        for obj in objects:
            if (c := obj["class"]) not in best or best[c][1] < obj["conf"]:
                best[c] = [obj[i] for i in ["conf", "color", "az", "el"]]
        return [best.get(c, (0, 0, 0, 0))[x] for c in range(3) for x in range(4)]

    def decorate(self, image, boxes):
        """
        Destructively dcorate an image with the detected boxes.
        """
        draw = ImageDraw.Draw(image, "RGBA")
        for class_id, confidence, xyxy in zip(
            (int(i) for i in boxes.cls), boxes.conf, boxes.xyxy
        ):
            label = f"{shape[class_id].name} {confidence:3.2f}"
            x1, y1, x2, y2 = xyxy.numpy().astype(int)

            draw.rectangle([(x1, y1), (x2, y2)], outline=shape[class_id].box, width=2)
            h, w = (m := FONT.getmask(label).getbbox())[3] + 2, m[2] + 1
            #                sum([*FONT.getmetrics(), (m := FONT.getmask(label).getbbox())[3]]),
            draw.rectangle(
                ((x1, y1 - 1), (x1 + w, y1 - h - 2)), fill=shape[class_id].color
            )
            draw.text(
                (x1 + 1, y1 - h - 2), label, font=FONT, fill=shape[class_id].label
            )

        return image

    @staticmethod
    def rgb_to_hue(rgb):
        """Convert RGB color to a hue."""  # array([116, 110,  81])
        colmin, colmax = min(rgb), max(rgb)
        if colmax == colmin:
            return 0
        if rgb[0] == colmax:
            return 60.0 * (0.0 + (rgb[1] - rgb[2]) / (colmax - colmin))
        elif rgb[1] == colmax:
            return 60.0 * (2.0 + (rgb[2] - rgb[0]) / (colmax - colmin))
        return 60.0 * (4.0 + (rgb[0] - rgb[1]) / (colmax - colmin))


# Thymio class


class Thymio:
    """
    Manage a connection to a Thymio.
    """

    def __init__(self):
        self.client = ClientAsync()
        self.node = aw(self.client.wait_for_node())
        if self.node:
            aw(self.node.lock())
            aw(self.node.register_events([("camera.detect", 5), ("camera.best", 12)]))
            aw(self.node.set_scratchpad(self.aseba_program()))
            if (r := aw(self.node.compile(self.aseba_program()))) is None:
                logging.info("RUNNING AESL")
                aw(self.node.run())
            else:
                logging.warning("CAN'T RUN AESL: error %d", r)
        else:
            logging.warning("Init_thymio: NO NODE")

    def events(self, events: dict):
        """
        Send event to Thymio.
        """
        logging.info("Thymio send event %s", str(events))
        if self.node:
            aw(self.node.lock())
            aw(self.node.send_events(events))

    def aseba_program(self):
        """Aesl program."""
        aseba_program = r"""var camera.detect[6] = [0, 0, 0, 0, 0, 50]
var camera.best[12]

onevent camera.best
camera.best[0:11] = event.args[0:11]

onevent camera.detect
camera.detect[5] = 50 + (((camera.detect[5] % 10) + 1) % 7)
call leds.temperature(0, 4 - abs((camera.detect[5] % 10) % 7 - 3))
camera.detect[0:4] = event.args[0:4]

onevent temperature
if camera.detect[5] / 10 < 1 then
        call leds.temperature(3, 0)
else
        camera.detect[5] = camera.detect[5] - 10
end
        """
        return aseba_program.lstrip(" ")


# Initializations


def init_camera():
    """
    Instantiate the Pi Camera.
    """
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = CAPTURE_SIZE
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()
    logging.info("Camera %s", str(picam2))

    return picam2


def init_yolo(yolo_version="v8n", batch=2, epochs=100, verbose=False):
    """
    Instantiate the YOLO predictor.
    """
    weights = (
        Path("YOLO-trained-V2")
        / f"UCIA-YOLO{yolo_version}"
        / f"batch-{batch:02d}_epo-{epochs:03d}/weights/best_ncnn_model"
    )
    model = YOLO(weights, task="detect", verbose=verbose)
    logging.info("Yolo model %s: %s", str(weights), str(model))

    return model


# Main event.


@click.command()
@click.option(
    "--freq",
    help="Capture frequency (Hz)",
    default=2,
    show_default=True,
    type=click.FLOAT,
)
@click.option(
    "--fifo",
    help="Output named pipe",
    default=OUT_FIFO,
    show_default=True,
    type=click.Path(path_type=Path),
)
@click.option(
    "--frame-dir",
    help="Output frame directory",
    default=FRAME_DIR,
    show_default=True,
    type=click.Path(path_type=Path, exists=True),
)
@click.option("--verbose/--quiet", default=False, help="YOLO verbose")
@click.option(
    "--loglevel",
    help="Logging level",
    default="INFO",
    show_default=True,
    type=click.STRING,
)
def main(freq: float, fifo: Path, frame_dir: Path, verbose: bool, loglevel: str):
    """
    Continuously capture an image and detect objects using YOLO.
    Send JSON records to a FIFO and record image frames in files.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.INFO)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logging.info("Setting loglevel to %s", loglevel)

    camera = init_camera()
    yolo = init_yolo(verbose=verbose)
    thymio = Thymio()

    if not fifo.is_fifo:
        os.mkfifo(fifo)
        logging.info("Made FIFO %s", fifo)
    fifo_fd = open(fifo, "w")

    detector = Detector(camera, yolo, fifo_fd, thymio, freq)
    detector.start()  # run forever in foreground


if __name__ == "__main__":
    main()
