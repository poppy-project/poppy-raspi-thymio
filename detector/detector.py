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
from itertools import combinations
from pathlib import Path
from typing import List, Tuple

import click
import cv2
import numpy as np
from collections import deque
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from tdmclient import ClientAsync, aw
from ultralytics import YOLO

# Constants

CAPTURE_SIZE = (640, 640)
FRAME_DIR = Path("/run/ucia")
OUT_FIFO = Path("/run/ucia/detection.fifo")

FONT = ImageFont.truetype("/home/ucia/.config/Ultralytics/Arial.ttf", 12)

# Hough line detection downsampled image size
HOUGH_W = 320
# Hough parameters rho, theta, threshold; min pts, max gap; iterations
HOUGH = (2, np.pi / 90, 15, 15, 25, 8)
# Mask background beyond 20 cm and close foreground
HOUGH_MASK = np.array([[0, 28], [4, 20], [26, 20], [30, 28]]) * HOUGH_W // 30

# Smoothing of lane lines
BINS_NUM = 12
BINS_EDGES = CAPTURE_SIZE[0] / float(BINS_NUM) * np.array(range(BINS_NUM))

BLUR = 4

# See https://personal.sron.nl/~pault/ for color schemes for color-blind users
BR_BLUE = (68, 119, 170, 255)
BR_CYAN = (102, 204, 238, 255)
BR_GREEN = (34, 136, 51, 255)
BR_YELLOW = (204, 187, 68, 255)
BR_RED = (238, 102, 119, 255)
BR_PURPLE = (170, 51, 119, 255)
BR_GRAY = (187, 187, 187, 255)

WHITE = (255, 255, 255, 250)
BLACK = (0, 0, 0, 250)

# Feature colors

EDGE = BR_BLUE
LANE = BR_CYAN
BEST = BR_GRAY


class Class:
    """Shape class names and colors."""

    def __init__(self, name, color, box, label):
        self.name = name
        self.color = color
        self.box = box
        self.label = label


shape = [
    Class("Ball", BR_YELLOW, BR_YELLOW, BLACK),
    Class("Cube", BR_YELLOW, BR_YELLOW, BLACK),
    Class("Star", BR_YELLOW, BR_YELLOW, BLACK),
]


# Detector thread


class Detector(threading.Thread):
    """
    Continuously capture an image and detect objects.
    Send JSON records to a FIFO.
    Store image frames in files.
    """

    def __init__(
        self,
        camera,
        yolo,
        fifo,
        frame_dir=FRAME_DIR,
        thymio=None,
        freq_hz=60,
        minconf=0.6,
        maxdetect=6,
    ):
        threading.Thread.__init__(self)
        self.sleep_event = threading.Event()
        self.wait_sec = 1.0 / freq_hz
        self.daemon = False
        self.camera = camera
        self.yolo = yolo
        self.fifo = fifo
        self.frame_dir = frame_dir
        self.thymio = thymio
        self.minconfidence = minconf
        self.maxdetect = maxdetect
        self.lines = deque(maxlen=6)
        self.mask = None
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
        with open(self.frame_dir / "raw.jpeg", "wb") as f:
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

        # Detect lanes
        xray = gray.resize((HOUGH_W, HOUGH_W)).filter(ImageFilter.GaussianBlur(BLUR))
        with open(self.frame_dir / "xray.jpeg", "wb") as f:
            xray.save(f)
            logging.debug("Detect_one: wrote xray frame %s", f.name)

        if self.mask is None:
            self.mask = np.zeros_like(np.array(xray))
            cv2.fillPoly(self.mask, [HOUGH_MASK], (255, 255, 255))

        xcan = cv2.Canny(np.array(xray), 30, 100)
        xcan = cv2.bitwise_and(xcan, self.mask)
        cv2.imwrite(f_name := self.frame_dir / "xcan.jpeg", xcan)
        logging.debug("Detect_one: wrote xcan frame %s", f_name)
        lines = [
            cv2.HoughLinesP(
                xcan,
                *HOUGH[0:3],
                np.array([]),
                minLineLength=HOUGH[3],
                maxLineGap=HOUGH[4],
            )
            * (CAPTURE_SIZE[0] / HOUGH_W)
            for i in range(HOUGH[5])
        ]
        sample = np.concatenate(lines)
        combo = self.add_lines(lines=sample)
        logging.debug("Detect_one: combo lines \n%s", str(combo))

        best_lanes = self.choose_best_lane(lines=combo, image=gray)
        logging.info("Best lanes %s", best_lanes)

        # Send camera best object event
        best_objects = self.choose_best_objects(objects)
        self.thymio.events({"camera.best": self.best_objects(best_objects)})

        # Send camera best lane events
        for lane in best_lanes:
            cx, cy, x1, y1, x2, y2, slope, *_ = lane
            az = int(cx / 0.32) - 1000
            el = int((600 - cy) * 1.9)
            sl = 100 - sorted((0, int(slope * 100), 100))[1]
            self.thymio.events({"camera.lane": [az, el, sl]})

        # Write decorated frame.
        with open(self.frame_dir / "frame.jpeg", "wb") as f:
            self.decorate(
                color, boxes=boxes, lines=combo, lanes=best_lanes, best=best_objects
            ).save(f)
            logging.debug("Detect_one: wrote frame %s", f.name)

    def add_lines(self, lines):
        """Add new lines to moving average."""

        def analyze_lines(lines):
            """Analyze Hough lines."""
            midpt = [lines[:, :, [0, 2]].mean(axis=2), lines[:, :, [1, 3]].mean(axis=2)]
            # slope = abs(lines[:, :, 3] - lines[:, :, 1]) / (
            #     abs(lines[:, :, 2] - lines[:, :, 1]) + 0.00001
            # )
            slope = np.arctan2(
                lines[:, 0, 2] - lines[:, 0, 0], lines[:, 0, 3] - lines[:, 0, 1]
            ) / (np.pi / 2)

            ln_av = np.reshape(np.c_[lines[:, 0, :], *midpt, slope], (-1, 1, 7))
            ln_av = ln_av[ln_av[:, 0, 4].argsort()]  # sort by midpoint X
            return ln_av

        info = analyze_lines(lines)

        if len(self.lines) < 2:
            concat = analyze_lines(lines)
            self.lines.extend([concat[:, :, :4]])
        else:
            concat = analyze_lines(np.concatenate(list(self.lines) + [lines]))
            self.lines.extend([analyze_lines(lines)[:, :, :4]])

        # Filter to choose mostly vertical lines
        vertical = concat[abs(concat[:, :, 5]) > 0.3].reshape(-1, 1, 7)

        # Make historical consensus lines by binning X
        dig = np.digitize(vertical[:, 0, 4], BINS_EDGES)

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
            x1, y1, x2, y2 = (coords := xyxy.numpy().astype(int))
            if (
                (slope := abs(np.arctan2(y2 - y1, x2 - x1)) - 0.785) > 0.15
                or abs(x2 - x1) < 20
                or abs(y2 - y1) < 20
            ):
                logging.debug(
                    "Ignoring misshaped (%g > 0.15) %d %g %d,%d %d,%d",
                    slope,
                    class_id,
                    confidence,
                    *coords,
                )
                continue
            rgb = self.midpoint_color(x1, y1, x2, y2, image)
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

    def choose_best_objects(self, objects):
        """
        Select best object of each class.
        """
        best = {}
        for obj in objects:
            if (c := obj["class"]) not in best or best[c]["conf"] < obj["conf"]:
                best[c] = obj
        return [best.get(c) for c in range(3)]

    def best_objects(self, objects) -> List[int]:
        """
        Select best object of each class.
        """
        return [
            (obj.get(i, 0) if obj else 0)
            for obj in objects
            for i in ["conf", "color", "az", "el"]
        ]
        # for obj in objects:
        #     if (c := obj["class"]) not in best or best[c][1] < obj["conf"]:
        #         best[c] = [obj[i] for i in ["conf", "color", "az", "el"]]
        # return [best.get(c, (0, 0, 0, 0))[x] for c in range(3) for x in range(4)]

    def choose_best_lane(self, lines, image) -> List[Tuple[int, int]] | None:
        """
        Select best lane from lines.
        Assume lines are sorted by midpoint (column 4).
        """
        d = lines.astype(int)[:, 0, [4, 5]]
        comp = {
            (i, j): ((d[i, 0] + d[j, 0]) // 2, (d[i, 1] + d[j, 1]) // 2, slope)
            for i, j in combinations(range(d.shape[0]), r=2)
            if abs(d[i, 0] - d[j, 0]) < 150
            if self.midpoint_color(d[i, 0], d[i, 1], d[j, 0], d[j, 1], image) < 100
            # if (slope := abs(d[i, 1] - d[j, 1]) / abs(d[i, 0] - d[j, 0] + 0.0001)) < 1.0
            if abs(slope := np.arctan2(d[j, 1] - d[i, 1], d[j, 0] - d[i, 0])) < 0.78
        }
        logging.debug("*** comparison %s", str(comp))

        candidates = sorted(
            [
                (*c[:2], d[ab[0], 0], d[ab[0], 1], d[ab[1], 0], d[ab[1], 1], c[2])
                for ab, c in comp.items()
            ],
            key=lambda v: v[6],
        )
        logging.debug("*** candidates %s", str(candidates))

        return candidates[: min(2, len(candidates))]

    def decorate(self, image, boxes, lines, lanes, best):
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
            draw.rectangle(
                ((x1, y1 - 1), (x1 + w, y1 - h - 2)), fill=shape[class_id].color
            )
            draw.text(
                (x1 + 1, y1 - h - 2), label, font=FONT, fill=shape[class_id].label
            )

        for obj in best:
            if not obj:
                continue
            x1, y1, x2, y2 = obj.get("xyxy", (-1, -1, -1, -1))
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            draw.line([cx, cy - 8, cx, cy + 8], width=1, fill=BEST)
            draw.line([cx - 8, cy, cx + 8, cy], width=1, fill=BEST)

        for line in lines:
            for x1, y1, x2, y2 in line[:, :4]:
                slope = abs(y2 - y1) / float(abs(x2 - x1)) if abs(x2 - x1) > 10 else 50
                if slope > 0.66:
                    draw.line([x1, y1, x2, y2], width=1, fill=EDGE)
                    a, b = (x1 + x2) // 2, (y1 + y2) // 2
                    draw.ellipse([a - 3, b - 3, a + 3, b + 3], fill=EDGE)

        for cx, cy, x1, y1, x2, y2, *_ in lanes:
            # draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=LANE)
            draw.line([x1, y1, x2, y2], width=1, fill=EDGE)
            draw.pieslice(
                [cx - 12, cy - 18, cx + 12, cy + 12], start=50, end=130, fill=LANE
            )

        return image

    @staticmethod
    def midpoint_color(x1, y1, x2, y2, image):
        """Mean object color around the center."""
        cx, cy = int(x1 + x2) // 2, int(y1 + y2) // 2

        rgb = (
            np.array(image)[cy - 7 : cy + 7, cx - 7 : cx + 7]
            .mean(axis=0)
            .mean(axis=0)
            .astype(int)
        )
        logging.debug(
            "*** midpoint color (%d,%d) = %s im %s", cx, cy, str(rgb), str(image)
        )
        return rgb

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
            aw(
                self.node.register_events(
                    [("camera.detect", 5), ("camera.best", 12), ("camera.lane", 3)]
                )
            )
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

var vin = 200
var vout = 200
var slow
var turn
var target = 1
var state = 0
var scan_phase = 0
var seen = 0
var wait_state

call math.fill(camera.best, 0)

onevent camera.best
camera.best[0:11] = event.args[0:11]

onevent camera.detect
camera.detect[5] = 50 + (((camera.detect[5] % 10) + 1) % 7)
call leds.temperature(0, 4 - abs((camera.detect[5] % 10) % 7 - 3))
camera.detect[0:4] = event.args[0:4]

# Heartbeat

onevent temperature
if camera.detect[5] / 10 < 1 then
        call leds.temperature(3, 0)
else
        camera.detect[5] = camera.detect[5] - 10
end

# State machine

onevent acc
	leds.circle = [0,0,0,0,0,0,0,0]
	leds.circle[state] = 16
	# State dispatch
	if  state == 0 then
		callsub rosa_0_stop
	end
	if  state == 1 then
		callsub rosa_1_orient
	end
	if  state == 2 then
		callsub rosa_2_pursue
	end
	if  state == 4 then
		callsub rosa_4_return
	end
	if  state == 5 then
		callsub rosa_5_scan
	end

#Targets = [0, 93, 3, -885, 62,   1, 83, 2, 731, 554,   2, 86, 3, 151, 392]
#call math.fill(camera.best, 0)

sub rosa_0_stop
	state = 0
	seen = 0
	leds.top = [32,0,0]
	motor.left.target = 0
	motor.right.target = 0

sub rosa_1_orient
	state = 1
	if abs(camera.best[target * 4 + 3]) < 20 then
		state = 2
		return
	end
	vout = 200
	vin = -vout
	timer.period[1] = abs(camera.best[target * 4 + 3] / 2)
	callsub start_turn

sub rosa_2_pursue
	state = 2
	leds.top = [0,32,0]
	vout = 120
	# Check for success
	if seen > 3 and (camera.best[target * 4 + 1] < 10 or camera.best[target * 4 + 4] < 10) then
		state = 4
		return
	end
	# Otherwise continue pursuit
	seen = seen + 1
	slow = ((3 * (camera.best[target * 4 + 4]-60)) + 400) / 20
	vout = vout * slow / 100
	turn = 100 - abs(camera.best[target * 4 + 3]) / 10
	vin = (vout * turn) / 100
	callsub start_turn

sub start_turn
	if  camera.best[target * 4 + 3] >= 0 then
		motor.left.target = vout
		motor.right.target = vin
	else
		motor.left.target = vin
		motor.right.target = vout
	end

sub rosa_4_return
	state = 4
	seen = 0
    callsub flip

sub flip
	leds.top = [0,32,10]
	motor.left.target = -400
	motor.right.target = 400
	timer.period[1] = 1250

sub rosa_5_scan
	state = 5
	seen = 0
	leds.top = [0,0,10]
	scan_phase = (scan_phase + 1) % 4
	if  scan_phase == 1 or scan_phase == 2 then
		motor.left.target = -10
		motor.right.target = 10
	else
		motor.left.target = 10
		motor.right.target = -10
	end
	timer.period[1] = 3500

# Buttons and tap

onevent button.center
	target = 1
	state = 0
	callsub rosa_0_stop

onevent button.forward
	state = 1

onevent button.left
	target = 0

onevent button.right
	target = 2

onevent button.backward
	state = 0
	callsub flip

onevent tap
	callsub rosa_0_stop

# Motion timer and proximity sensors

onevent prox
	# Manual success
	if  prox.horizontal[5] > 1200 then
		state = 4
	end

	# Success and Emergency stop
	if  prox.ground.delta[0] < 600 or prox.ground.delta[1] < 600 then
		leds.bottom.left = [30,0,30]
		leds.bottom.right = [30,0,30]
		motor.left.target = -100
		motor.right.target = -100
		timer.period[1] = 500
		state = 0
	end

onevent timer1
	motor.left.target = 0
	motor.right.target = 0
	timer.period[1] = 0
	if  state == 7 then
		state = wait_state
	end
	if  state == 1 then
		wait_state = state
		state = 7
		timer.period[0] = 1200
	end
	if  state == 4 then
		motor.left.target = 100
		motor.right.target = 100
		wait_state = 0
		state = 7
	end
	if  state == 5 then
		callsub rosa_5_scan
	end

onevent timer0
	timer.period[0] = 0
	if  state == 7 then
		state = wait_state
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
    type=click.Path(path_type=Path, exists=False),
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

    frame_dir.mkdir(mode=0o775, parents=True, exist_ok=True)

    if not fifo.is_fifo:
        os.mkfifo(fifo)
        logging.info("Made FIFO %s", fifo)
    fifo_fd = open(fifo, "w")

    detector = Detector(
        camera=camera,
        yolo=yolo,
        fifo=fifo_fd,
        frame_dir=frame_dir,
        thymio=thymio,
        freq_hz=freq,
    )
    detector.start()  # run forever in foreground


if __name__ == "__main__":
    main()
