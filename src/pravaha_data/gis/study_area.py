from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any


ASSET_PATH = (
    Path(__file__).resolve().parent
    / "static"
    / "chandrabani_study_area.json"
)


@lru_cache(maxsize=1)
def load_chandrabani_study_area() -> dict[str, Any]:
    return json.loads(ASSET_PATH.read_text(encoding="utf-8"))


def study_area() -> dict[str, Any]:
    return load_chandrabani_study_area()["study_area"]


def study_area_bbox() -> dict[str, float]:
    bbox = study_area()["bounding_box"]
    return {
        "west": float(bbox["west"]),
        "south": float(bbox["south"]),
        "east": float(bbox["east"]),
        "north": float(bbox["north"]),
    }


def terrain_summary() -> dict[str, Any]:
    return load_chandrabani_study_area()["terrain"]


def layer(name: str) -> dict[str, Any]:
    return load_chandrabani_study_area()["layers"][name]


def source_manifest() -> list[dict[str, Any]]:
    return load_chandrabani_study_area()["sources"]


def validation_points() -> list[dict[str, Any]]:
    return load_chandrabani_study_area()["validation_points"]
