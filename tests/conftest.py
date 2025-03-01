"""Common fixtures and steps."""

# import subprocess
# from pathlib import Path
# from typing import List
import logging
from pathlib import Path

import pytest
from ultralytics import YOLO

from poppy.raspi_thymio.thing import ThingList


@pytest.fixture(scope="session", autouse=True)
def tdm():
    pass
    # proc = subprocess.Popen(...)
    # request.addfinalizer(proc.kill)


weights = (
    Path("/Users/sherman/work/poppy-rosa/UCIA_ObjectDetection/YOLO-trained-V2")
    / f"UCIA-YOLOv8n"
    / f"batch-02_epo-100/weights/best_ncnn_model"
)
ThingList.yolo = YOLO(weights, task="detect", verbose=True)
logging.info("Yolo model %s: %s", str(weights), str(ThingList.yolo))
