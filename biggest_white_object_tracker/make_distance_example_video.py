from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a simple two-object line-crossing example video.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/distance_crossing_example.mp4"),
        help="Output video path. Default: outputs/distance_crossing_example.mp4",
    )
    parser.add_argument("--width", type=int, default=640, help="Frame width. Default: 640")
    parser.add_argument("--height", type=int, default=480, help="Frame height. Default: 480")
    parser.add_argument("--fps", type=float, default=20.0, help="Output FPS. Default: 20")
    return parser.parse_args()


def lab_to_bgr(lab: tuple[int, int, int]) -> tuple[int, int, int]:
    pixel = np.uint8([[lab]])
    return tuple(int(value) for value in cv2.cvtColor(pixel, cv2.COLOR_LAB2BGR)[0, 0])


def write_example_video(output: Path, width: int, height: int, fps: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write output video: {output}")

    blue_bgr = lab_to_bgr((150, 98, 60))
    yellow_bgr = lab_to_bgr((90, 108, 158))
    positions = list(range(60, 340, 7)) + list(range(340, 60, -7))
    for frame_index, object_y in enumerate(positions):
        frame = np.full((height, width, 3), 32, dtype=np.uint8)

        phase = frame_index / max(1, len(positions) - 1)
        target_x = int(280 + 90 * math.sin(2 * math.pi * phase))
        target_y = int(220 + 45 * math.sin(4 * math.pi * phase + math.pi / 5))
        target_top_left = (target_x, target_y)
        target_bottom_right = (target_x + 80, target_y + 40)

        cv2.rectangle(frame, target_top_left, target_bottom_right, yellow_bgr, -1)
        cv2.rectangle(frame, (80, object_y), (150, object_y + 60), blue_bgr, -1)

        cv2.putText(
            frame,
            f"frame {frame_index + 1}",
            (18, height - 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
        writer.write(frame)

    writer.release()


def main() -> None:
    args = parse_args()
    write_example_video(args.output, args.width, args.height, args.fps)
    print(f"example_video: {args.output}")


if __name__ == "__main__":
    main()
