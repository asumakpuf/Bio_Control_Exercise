from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from detect_biggest_white_object import find_largest_white_box, to_normalized_coordinates


@dataclass(frozen=True)
class Detection:
    x: int
    y: int
    width: int
    height: int
    area: float
    image_width: int
    image_height: int
    label_id: int = 0

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    @property
    def normalized(self) -> tuple[float, float, float, float]:
        return to_normalized_coordinates(self.box, self.image_width, self.image_height)

    @property
    def pixels_line(self) -> str:
        x_center, y_center = self.center
        return f"{self.label_id} {self.x} {self.y} {self.width} {self.height} {x_center:.1f} {y_center:.1f} {self.area:.0f}"

    @property
    def normalized_line(self) -> str:
        return f"{self.label_id} " + " ".join(f"{value:.6f}" for value in self.normalized)


class LargestWhiteObjectModel:
    def __init__(self, threshold: int = 127, min_area: float = 100.0, invert: bool = False, label_id: int = 0) -> None:
        if not 0 <= threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")
        self.threshold = threshold
        self.min_area = min_area
        self.invert = invert
        self.label_id = label_id

    def detect(self, frame: np.ndarray) -> Optional[Detection]:
        gray = self._to_gray(frame)
        image_height, image_width = gray.shape[:2]
        try:
            x, y, width, height, area = find_largest_white_box(gray, self.threshold, self.min_area, self.invert)
        except ValueError:
            return None
        return Detection(x, y, width, height, area, image_width, image_height, self.label_id)

    @staticmethod
    def _to_gray(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            return frame
        if frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
