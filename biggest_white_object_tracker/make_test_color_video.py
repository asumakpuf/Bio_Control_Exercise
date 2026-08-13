from pathlib import Path

import numpy as np
import cv2


def draw_blob(frame: np.ndarray, center_x: int, center_y: int) -> None:
    tracked_color = (80, 112, 32)
    points = np.array(
        [
            [center_x - 90, center_y - 35],
            [center_x - 35, center_y - 95],
            [center_x + 80, center_y - 65],
            [center_x + 110, center_y + 25],
            [center_x + 35, center_y + 95],
            [center_x - 105, center_y + 55],
        ],
        dtype=np.int32,
    )
    cv2.fillPoly(frame, [points], tracked_color)
    cv2.circle(frame, (center_x - 30, center_y - 30), 48, tracked_color, -1)
    cv2.circle(frame, (center_x + 45, center_y + 35), 55, tracked_color, -1)


def make_frame(index: int, frame_count: int, width: int, height: int) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    progress = index / max(1, frame_count - 1)
    center_x = int(130 + progress * 380)
    center_y = int(240 + 65 * np.sin(progress * np.pi * 2))

    draw_blob(frame, center_x, center_y)
    cv2.circle(frame, (95, 95), 35, (230, 230, 230), -1)
    cv2.rectangle(frame, (70, 360), (145, 430), (0, 0, 255), -1)
    return frame


def main() -> None:
    output_dir = Path("examples")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "moving_lab_color_blob.avi"

    width, height = 640, 480
    fps = 20.0
    frame_count = 120
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
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
