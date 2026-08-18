from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class ObjectCoordinates:
    box: tuple[int, int, int, int]
    center: tuple[float, float]
    normalized_box: tuple[float, float, float, float]
    area: float
    image_size: tuple[int, int]
    label_id: int


def get_target_bounding_box_coordinates(frame: np.ndarray, target_model) -> Optional[ObjectCoordinates]:
    """Return the target bounding-box coordinates, or None when the target is not visible."""
    detection = target_model.detect(frame)
    return _coordinates_from_detection(detection)


def get_object_coordinates(frame: np.ndarray, object_model) -> Optional[ObjectCoordinates]:
    """Return the tracked object's coordinates, or None when the object is not visible."""
    detection = object_model.detect(frame)
    return _coordinates_from_detection(detection)


def _coordinates_from_detection(detection) -> Optional[ObjectCoordinates]:
    if detection is None:
        return None

    return ObjectCoordinates(
        box=detection.box,
        center=detection.center,
        normalized_box=detection.normalized,
        area=detection.area,
        image_size=(detection.image_width, detection.image_height),
        label_id=detection.label_id,
    )
