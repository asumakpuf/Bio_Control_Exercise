from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import cv2

from detect_biggest_white_object import (
    draw_annotation,
)
from white_object_model import Detection, LargestWhiteObjectModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Track the largest white object in a camera feed or video file and "
            "continuously print bounding-box coordinates."
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
        "--threshold",
        type=int,
        default=127,
        help="Threshold for white pixels, from 0 to 255. Default: 127",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=100.0,
        help="Ignore objects smaller than this pixel area. Default: 100",
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help="Track black objects on a white background instead.",
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
    payload = {
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
    return json.dumps(payload)


def open_capture(args: argparse.Namespace) -> cv2.VideoCapture:
    source = str(args.video) if args.video else args.camera
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        if args.video:
            raise RuntimeError(f"Could not open video file: {args.video}")
        raise RuntimeError(f"Could not open camera index {args.camera}")
    return capture


def make_video_writer(
    output_video: Path | None,
    capture: cv2.VideoCapture,
    first_frame: cv2.typing.MatLike,
) -> cv2.VideoWriter | None:
    if output_video is None:
        return None

    output_video.parent.mkdir(parents=True, exist_ok=True)
    height, width = first_frame.shape[:2]
    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write output video: {output_video}")
    return writer


def display_delay_ms(capture: cv2.VideoCapture, is_video_file: bool) -> int:
    if not is_video_file:
        return 1

    fps = capture.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    return max(1, int(1000 / fps))


def main() -> None:
    args = parse_args()
    if not 0 <= args.threshold <= 255:
        raise ValueError("--threshold must be between 0 and 255")
    if args.print_every < 1:
        raise ValueError("--print-every must be at least 1")

    if args.max_frames is not None and args.max_frames < 1:
        raise ValueError("--max-frames must be at least 1")

    capture = open_capture(args)

    if not args.video and args.width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if not args.video and args.height:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    model = LargestWhiteObjectModel(
        threshold=args.threshold,
        min_area=args.min_area,
        invert=args.invert,
        label_id=args.label_id,
    )
    frame_number = 0
    detected_count = 0
    writer = None
    wait_ms = display_delay_ms(capture, args.video is not None)
    window_name = "Largest white object tracker"

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            frame_number += 1
            timestamp = time.time()
            if writer is None:
                writer = make_video_writer(args.output_video, capture, frame)

            detection = model.detect(frame)
            if detection is not None:
                preview = draw_annotation(
                    frame,
                    detection.box,
                    detection.normalized,
                    detection.area,
                )
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
            else:
                preview = frame
                if not args.no_display:
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
