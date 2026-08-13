from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2
import numpy as np

from color_object_model import Detection, LargestColorObjectModel
from detect_biggest_white_object import draw_annotation
from track_camera import display_delay_ms, make_video_writer, open_capture


DEFAULT_LOW_LAB = np.array([76, 45, 0], dtype=np.uint8)
DEFAULT_HIGH_LAB = np.array([121, 112, 153], dtype=np.uint8)


def parse_lab_bound(value: str) -> np.ndarray:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("Expected three comma-separated values")

    try:
        values = [int(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("LAB values must be integers") from exc

    if any(number < 0 or number > 255 for number in values):
        raise argparse.ArgumentTypeError("LAB values must be between 0 and 255")

    return np.array(values, dtype=np.uint8)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Track the largest object in a live camera feed or video using a LAB "
            "color range."
        )
    )
    parser.add_argument(
        "--video",
        type=Path,
        help="Video file to process. If omitted, the script uses the camera.",
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera device index used when --video is omitted. Default: 0",
    )
    parser.add_argument(
        "--low-lab",
        type=parse_lab_bound,
        default=DEFAULT_LOW_LAB,
        help="Lower LAB threshold as L,A,B. Default: 76,45,0",
    )
    parser.add_argument(
        "--high-lab",
        type=parse_lab_bound,
        default=DEFAULT_HIGH_LAB,
        help="Upper LAB threshold as L,A,B. Default: 121,112,153",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=300.0,
        help="Ignore objects smaller than this pixel area. Default: 300",
    )
    parser.add_argument(
        "--label-id",
        type=int,
        default=0,
        help="Label id included in normalized output. Default: 0",
    )
    parser.add_argument(
        "--format",
        choices=("json", "normalized", "pixels"),
        default="pixels",
        help="Coordinate print format. Default: pixels",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=1,
        help="Print every N detected frames. Default: 1",
    )
    parser.add_argument(
        "--show-mask",
        action="store_true",
        help="Show the threshold mask next to the camera image.",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Do not open the live preview window.",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        help="Optional path for saving the annotated video.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="Stop after this many frames. Useful for quick video tests.",
    )
    parser.add_argument(
        "--width",
        type=int,
        help="Requested camera frame width.",
    )
    parser.add_argument(
        "--height",
        type=int,
        help="Requested camera frame height.",
    )
    return parser.parse_args()


def format_coordinates(
    output_format: str,
    frame_number: int,
    timestamp: float,
    detection: Detection,
) -> str:
    if output_format == "normalized":
        return detection.normalized_line()

    if output_format == "pixels":
        return detection.pixels_line()

    x_center, y_center, normalized_width, normalized_height = detection.normalized
    return json.dumps(
        {
            "frame": frame_number,
            "time": round(timestamp, 3),
            "label_id": detection.label_id,
            "bbox_xywh_pixels": {
                "x": detection.x,
                "y": detection.y,
                "width": detection.width,
                "height": detection.height,
            },
            "bbox_normalized": {
                "x_center": round(x_center, 6),
                "y_center": round(y_center, 6),
                "width": round(normalized_width, 6),
                "height": round(normalized_height, 6),
            },
            "area": round(detection.area, 2),
            "image_size": {
                "width": detection.image_width,
                "height": detection.image_height,
            },
        }
    )


def make_preview(
    frame: np.ndarray,
    model: LargestColorObjectModel,
    detection: Detection | None,
    show_mask: bool,
) -> np.ndarray:
    if detection is None:
        preview = frame.copy()
        cv2.putText(
            preview,
            "No object found",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    else:
        preview = draw_annotation(
            frame,
            detection.box,
            detection.normalized,
            detection.area,
        )
        cv2.circle(preview, detection.center, 5, (0, 0, 255), -1)

    if not show_mask:
        return preview

    mask_bgr = cv2.cvtColor(model.mask(frame), cv2.COLOR_GRAY2BGR)
    return np.hstack((preview, mask_bgr))


def main() -> None:
    args = parse_args()
    if args.print_every < 1:
        raise ValueError("--print-every must be at least 1")
    if args.max_frames is not None and args.max_frames < 1:
        raise ValueError("--max-frames must be at least 1")

    capture = open_capture(args)
    if not args.video and args.width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if not args.video and args.height:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    model = LargestColorObjectModel(
        low_lab=args.low_lab,
        high_lab=args.high_lab,
        min_area=args.min_area,
        label_id=args.label_id,
    )

    frame_number = 0
    detected_count = 0
    writer = None
    wait_ms = display_delay_ms(capture, args.video is not None)
    window_name = "Largest color object tracker"

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            frame_number += 1
            timestamp = time.time()
            detection = model.detect(frame)
            preview = make_preview(frame, model, detection, args.show_mask)

            if writer is None:
                writer = make_video_writer(args.output_video, capture, preview)

            if detection is not None:
                detected_count += 1
                if detected_count % args.print_every == 0:
                    print(
                        format_coordinates(
                            output_format=args.format,
                            frame_number=frame_number,
                            timestamp=timestamp,
                            detection=detection,
                        ),
                        flush=True,
                    )

            if writer is not None:
                writer.write(preview)

            if not args.no_display:
                cv2.imshow(window_name, preview)
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (ord("q"), 27):
                    break

            if args.max_frames is not None and frame_number >= args.max_frames:
                break
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if not args.no_display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
