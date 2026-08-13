from pathlib import Path

import cv2
import numpy as np


def draw_irregular_blob(frame: np.ndarray, center_x: int, center_y: int) -> None:
    points = np.array(
        [
            [center_x - 95, center_y - 20],
            [center_x - 55, center_y - 85],
            [center_x + 30, center_y - 72],
            [center_x + 105, center_y - 5],
            [center_x + 65, center_y + 74],
            [center_x - 45, center_y + 92],
            [center_x - 110, center_y + 42],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(frame, [points], 255)
    cv2.circle(frame, (center_x - 45, center_y - 35), 42, 255, -1)
    cv2.circle(frame, (center_x + 45, center_y + 25), 55, 255, -1)


def make_frame(index: int, frame_count: int, width: int, height: int) -> np.ndarray:
    frame = np.zeros((height, width), dtype=np.uint8)
    progress = index / max(1, frame_count - 1)
    center_x = int(130 + progress * 380)
    center_y = int(240 + 80 * np.sin(progress * np.pi * 2))

    draw_irregular_blob(frame, center_x, center_y)
    cv2.circle(frame, (95, 95), 35, 255, -1)
    cv2.rectangle(frame, (70, 360), (145, 430), 255, -1)
    return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)


def main() -> None:
    output_dir = Path("examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "moving_irregular_blob.mp4"

    width, height = 640, 480
    fps = 20.0
    frame_count = 120
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write video: {output_path}")

    try:
        for index in range(frame_count):
            writer.write(make_frame(index, frame_count, width, height))
    finally:
        writer.release()

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
