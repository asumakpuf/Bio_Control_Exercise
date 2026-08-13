from __future__ import annotations

from dataclasses import dataclass

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
    label_id: int = 0

    @property
    def box(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    @property
    def normalized(self) -> tuple[float, float, float, float]:
        return to_normalized_coordinates(self.box, self.image_width, self.image_height)

    def pixels_line(self) -> str:
        return f"{self.x} {self.y} {self.width} {self.height}"

    def normalized_line(self) -> str:
        x_center, y_center, width, height = self.normalized
        return (
            f"{self.label_id} "
            f"{x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
        )


class LargestColorObjectModel:
    def __init__(
        self,
        low_lab: np.ndarray,
        high_lab: np.ndarray,
        min_area: float = 100.0,
        label_id: int = 0,
    ) -> None:
        self.low_lab = self._validate_bound(low_lab, "low_lab")
        self.high_lab = self._validate_bound(high_lab, "high_lab")
        self.min_area = min_area
        self.label_id = label_id

    def mask(self, frame: np.ndarray) -> np.ndarray:
        lab_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        mask = cv2.inRange(lab_frame, self.low_lab, self.high_lab)

        kernel = np.ones((5, 5), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def detect(self, frame: np.ndarray) -> Detection | None:
        mask = self.mask(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [
            (contour, cv2.contourArea(contour))
            for contour in contours
            if cv2.contourArea(contour) >= self.min_area
        ]
        if not candidates:
            return None

        largest_contour, area = max(candidates, key=lambda item: item[1])
        x, y, width, height = cv2.boundingRect(largest_contour)
        image_height, image_width = frame.shape[:2]
        return Detection(
            x=x,
            y=y,
            width=width,
            height=height,
            area=area,
            image_width=image_width,
            image_height=image_height,
            label_id=self.label_id,
        )

    @staticmethod
    def _validate_bound(value: np.ndarray, name: str) -> np.ndarray:
        array = np.asarray(value, dtype=np.uint8)
        if array.shape != (3,):
            raise ValueError(f"{name} must contain exactly three LAB values")
        return array
