######################################
#   Jean-Luc.Charles@mailo.com
#   2024/12/16 - v1.1
######################################

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

font1 = ImageFont.truetype("/home/ucia/.config/Ultralytics/Arial.ttf", 12)
font2 = ImageFont.truetype("/home/ucia/.config/Ultralytics/Arial.ttf", 14)

class_name = ("Ball", "Cube", "Star")
main_color = ("red", "green", "blue")
class_color = ((80, 145, 255, 250), (240, 150, 100, 250), (255, 255, 255, 250))
box_color = ((80, 145, 255, 150), (240, 150, 100, 150), (255, 255, 255, 150))
label_color = ((255, 255, 255, 250), (0, 0, 0, 250), (0, 0, 0, 250))
label_width = (47, 56, 48)


# Detector thread


class Detector(threading.Thread):
    """
    Continuously capture an image and detect objects.
    Send JSON records to a FIFO.
    Store image frames in files.
    """

    def __init__(
        self, camera, detector, fifo, thymio=None, freq_hz=60, minconf=0.6, maxdetect=6
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.wait_sec = 60.0 / freq_hz
        self.daemon = False
        self.camera = camera
        self.detector = detector
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
        results = self.detector.predict(
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
        self.thymio_event({"cambest": self.best_objects(objects)})

        # Write decorated frame.
        with open(FRAME_DIR / "frame.jpeg", "wb") as f:
            self.decorate(color, boxes).save(f)
            logging.debug("Detect_one: wrote frame %s", f.name)

    def find_objects(self, image, boxes):
        """
        Interpret results as objects.
        """
        for (
            class_id,
            confidence,
            xyxy,
        ) in zip((int(i) for i in boxes.cls), boxes.conf, boxes.xyxy):
            name = class_name[class_id]
            label = f"{name} {confidence:3.2f}"
            # The bounding box coordinates:
            x1, y1, x2, y2 = xyxy.numpy().astype(int)
            # object center coordinates:
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
            self.thymio_event(
                {"camera": [obj[i] for i in ["class", "conf", "color", "az", "el"]]}
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
        for (
            class_id,
            confidence,
            xyxy,
        ) in zip((int(i) for i in boxes.cls), boxes.conf, boxes.xyxy):
            name = class_name[class_id]
            label = f"{name} {confidence:3.2f}"
            x1, y1, x2, y2 = xyxy.numpy().astype(int)

            draw.rectangle([(x1, y1), (x2, y2)], outline=box_color[class_id], width=2)
            draw.rectangle(
                ((x1, y1), (x1 + label_width[class_id], y1 - 11)),
                fill=class_color[class_id],
            )
            draw.text((x1, y1 - 12), label, font=font1, fill=label_color[class_id])

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

    def thymio_event(self, events: dict):
        """
        Send event to Thymio.
        """
        logging.info("Thymio send event %s", str(events))
        if self.thymio:
            aw(self.thymio.lock())
            aw(self.thymio.send_events(events))


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


def init_detector(yolo_version="v8n", batch=2, epochs=100):
    """
    Instantiate the YOLO detector.
    """
    weights = (
        Path("YOLO-trained-V2")
        / f"UCIA-YOLO{yolo_version}"
        / f"batch-{batch:02d}_epo-{epochs:03d}/weights/best_ncnn_model"
    )
    model = YOLO(weights, task="detect")
    logging.info("Detector model %s: %s", str(weights), str(model))

    return model


# Aesl program.

aseba_program = r"""var cam[6] = [0, 0, 0, 0, 0, 0]                                                                                                                          
var cambest[12]
var i

onevent camera
cam[5] = 3 - (3 * (cam[5] % 2))
call leds.temperature(cam[5], 3 - cam[5])
cam[0:4] = event.args[0:4]

onevent cambest
cambest[0:11] = event.args[0:11]
"""


def init_thymio():
    """
    Instantiate a connection to a Thymio.
    """
    client = ClientAsync()
    node = aw(client.wait_for_node())
    if node:
        aw(node.lock())
        aw(node.register_events([("camera", 5), ("cambest", 12)]))
        aw(node.set_scratchpad(aseba_program))
        if (r := aw(node.compile(aseba_program))) is None:
            logging.info("RUNNING AESL")
            aw(node.run())
        else:
            logging.warning("CAN'T RUN AESL: error %d", r)
    else:
        logging.warning("Init_thymio: NO NODE")
    return node


# Main event.


@click.command()
@click.option("--freq", help="Capture frequency (Hz)", default=15, type=click.FLOAT)
@click.option(
    "--fifo",
    default=OUT_FIFO,
    help="Output named pipe",
    type=click.Path(path_type=Path),
)
@click.option(
    "--frame-dir",
    default=FRAME_DIR,
    help="Output frame directory",
    type=click.Path(path_type=Path, exists=True),
)
@click.option("--loglevel", default="INFO", help="Logging level", type=click.STRING)
def main(freq: float, fifo: Path, frame_dir: Path, loglevel: str):
    """
    Continuously capture an image and detect objects using YOLO.
    Send JSON records to a FIFO and record image frames in files.
    """
    loglevel_int = getattr(logging, loglevel.upper(), logging.INFO)
    logging.basicConfig(format="%(asctime)s %(message)s", level=loglevel_int)
    logging.debug("Setting loglevel to %s", "DEBUG")

    camera = init_camera()
    detector = init_detector()
    thymio = init_thymio()

    if not fifo.is_fifo:
        os.mkfifo(fifo)
        logging.info("Made FIFO %s", fifo)
    fifo_fd = open(fifo, "w")

    detector = Detector(camera, detector, fifo_fd, thymio, freq)
    detector.start()  # run forever in foreground


if __name__ == "__main__":
    main()
