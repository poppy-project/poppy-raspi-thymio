# -*- coding: utf-8 -*-

"""
Aesl program data.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class AeslData:
    """
    Aesl program data.
    """

    def __init__(self, path: Path, name: str = None, meta: dict = None):
        self.path = path
        self.program = str(path.name)
        self.meta = meta or self.load_meta(path)
        self.name = name or self.meta.get("name", self.clean(path))
        logger.info("Aesl program data for %s = %s", self.name, self)

    def load_meta(self, path: Path) -> dict:
        logger.debug("Aesl program meta: searching for %s", path.with_suffix(".json").name)
        if (meta_file := path.with_suffix(".json")).exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                try:
                    meta = json.load(f)
                    logger.debug("Aesl program meta for %s: found %s", path.name, meta)
                    return meta
                except json.decoder.JSONDecodeError:
                    pass  # fall through to default return
        return dict()

    @staticmethod
    def clean(x: Path):
        return re.sub(r"^[0-9]+-", "", x.stem).replace("_", " ")

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return (
            f'AeslData(path=Path("{self.path}"), name="{self.name}", meta={self.meta})'
        )
