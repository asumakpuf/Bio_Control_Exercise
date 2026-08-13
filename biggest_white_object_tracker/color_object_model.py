from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Union

import cv2
import numpy as np

from detect_biggest_white_object import to_normalized_coordinates


@dataclass(frozen=True)
class Detection:
    x: int
    y: int
    width: int
    height: int
    area: float
    image_width: int
    image_height: int
    label_id: int = 1

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


class LargestColorObjectModel:
    def __init__(
        self,
        low_lab: Union[Sequence[int], np.ndarray],
        high_lab: Union[Sequence[int], np.ndarray],
        min_area: float = 100.0,
        label_id: int = 1,
    ) -> None:
        self.low_lab = self._validate_bound(low_lab, "low_lab")
        self.high_lab = self._validate_bound(high_lab, "high_lab")
        self.min_area = min_area
        self.label_id = label_id

    def mask(self, frame: np.ndarray) -> np.ndarray:
        lab_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        mask = cv2.inRange(lab_frame, self.low_lab, self.high_lab)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    def detect(self, frame: np.ndarray) -> Optional[Detection]:
        mask = self.mask(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [(contour, cv2.contourArea(contour)) for contour in contours if cv2.contourArea(contour) >= self.min_area]
        if not candidates:
            return None

        largest_contour, area = max(candidates, key=lambda item: item[1])
        x, y, width, height = cv2.boundingRect(largest_contour)
        image_height, image_width = frame.shape[:2]
        return Detection(x, y, width, height, area, image_width, image_height, self.label_id)

    @staticmethod
    def _validate_bound(value: Union[Sequence[int], np.ndarray], name: str) -> np.ndarray:
        array = np.asarray(value, dtype=np.uint8)
        if array.shape != (3,):
            raise ValueError(f"{name} must contain exactly three LAB values")
        return array
