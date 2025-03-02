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
