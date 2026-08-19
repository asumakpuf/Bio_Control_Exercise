from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Optional, Protocol

import cv2

from color_object_model import LargestColorObjectModel
from detect_biggest_white_object import draw_annotation
from object_coordinates import ObjectCoordinates, get_object_coordinates, get_target_bounding_box_coordinates
from track_camera import (
    DEFAULT_BLUE_HIGH,
    DEFAULT_BLUE_LOW,
    DEFAULT_YELLOW_HIGH,
    DEFAULT_YELLOW_LOW,
    BrowserPreview,
    start_browser_preview,
)


class FrameCapture(Protocol):
    def read(self):
        ...

    def release(self) -> None:
        ...

    def get(self, prop_id: int) -> float:
        ...

    def set(self, prop_id: int, value: float) -> bool:
        ...


class RealSenseColorCapture:
    def __init__(self, serial: str = "", width: int = 640, height: int = 480, fps: int = 15) -> None:
        try:
            import numpy as np
            import pyrealsense2 as rs2
        except ImportError as exc:
            raise ImportError("Install the Intel RealSense Python SDK first: pip install pyrealsense2") from exc

        self._np = np
        self._rs2 = rs2
        self._fps = fps
        self._format_name = "rgb8"
        self._pipeline = rs2.pipeline()
        self._config = rs2.config()
        if serial:
            self._config.enable_device(serial)
        self._config.enable_stream(rs2.stream.color, width, height, rs2.format.rgb8, fps)
        self._pipeline.start(self._config)
        time.sleep(0.8)

    def read(self):
        try:
            frames = self._pipeline.wait_for_frames(1000)
        except RuntimeError:
            return False, None

        color_frame = frames.get_color_frame()
        if not color_frame:
            return False, None

        frame = self._np.asanyarray(color_frame.get_data())
        if self._format_name == "bgr8":
            return True, frame
        return True, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def release(self) -> None:
        self._pipeline.stop()

    def get(self, prop_id: int) -> float:
        if prop_id == cv2.CAP_PROP_FPS:
            return float(self._fps)
        return 0.0

    def set(self, prop_id: int, value: float) -> bool:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute the object-target distance when the object crosses the target center line."
    )
    parser.add_argument("--video", type=Path, help="Video file to process. If omitted, the script uses the camera.")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index used when --video is omitted. Default: 0")
    parser.add_argument("--realsense", action="store_true", help="Use the Intel RealSense color stream instead of a webcam.")
    parser.add_argument("--realsense-serial", default="", help="Optional RealSense serial number. Default: first device.")
    parser.add_argument("--realsense-fps", type=int, default=15, help="RealSense color stream FPS. Default: 15")
    parser.add_argument("--min-area", type=float, default=100.0, help="Ignore objects smaller than this pixel area. Default: 100")
    parser.add_argument("--object-low", type=int, nargs=3, default=DEFAULT_BLUE_LOW, metavar=("L", "A", "B"))
    parser.add_argument("--object-high", type=int, nargs=3, default=DEFAULT_BLUE_HIGH, metavar=("L", "A", "B"))
    parser.add_argument("--target-low", type=int, nargs=3, default=DEFAULT_YELLOW_LOW, metavar=("L", "A", "B"))
    parser.add_argument("--target-high", type=int, nargs=3, default=DEFAULT_YELLOW_HIGH, metavar=("L", "A", "B"))
    parser.add_argument("--object-label-id", type=int, default=0, help="Label id for the moving object. Default: 0")
    parser.add_argument("--target-label-id", type=int, default=1, help="Label id for the line target. Default: 1")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format. Default: text")
    parser.add_argument("--no-display", action="store_true", help="Do not open the annotated preview window.")
    parser.add_argument(
        "--browser-display",
        action="store_true",
        help="Show the annotated feed in a local browser page instead of an OpenCV window.",
    )
    parser.add_argument("--browser-host", default="127.0.0.1", help="Host for --browser-display. Default: 127.0.0.1")
    parser.add_argument("--browser-port", type=int, default=8000, help="Port for --browser-display. Default: 8000")
    parser.add_argument("--output-video", type=Path, help="Optional path for saving the annotated video.")
    parser.add_argument("--max-frames", type=int, help="Stop after this many frames. Useful for quick video tests.")
    parser.add_argument("--width", type=int, help="Requested camera frame width.")
    parser.add_argument("--height", type=int, help="Requested camera frame height.")
    parser.add_argument("--stop-after-first", action="store_true", help="Stop after the first line crossing.")
    parser.add_argument("--loop-video", action="store_true", help="Loop --video forever for live preview demos.")
    parser.add_argument(
        "--print-function-returns",
        action="store_true",
        help="Print the return values from the target and object coordinate functions.",
    )
    parser.add_argument(
        "--print-every",
        type=int,
        default=1,
        help="Print function returns every N frames when --print-function-returns is enabled. Default: 1",
    )
    return parser.parse_args()


def open_capture(args: argparse.Namespace) -> FrameCapture:
    if args.video and args.realsense:
        raise ValueError("Use either --video or --realsense, not both.")

    if args.video:
        capture = cv2.VideoCapture(str(args.video))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video file: {args.video}")
        return capture

    if args.realsense:
        width = args.width or 640
        height = args.height or 480
        return RealSenseColorCapture(args.realsense_serial, width, height, args.realsense_fps)

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera}")
    return capture


def make_video_writer(output_video: Optional[Path], first_frame, capture: FrameCapture) -> Optional[cv2.VideoWriter]:
    if output_video is None:
        return None

    output_video.parent.mkdir(parents=True, exist_ok=True)
    height, width = first_frame.shape[:2]
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    writer = cv2.VideoWriter(str(output_video), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write output video: {output_video}")
    return writer


def line_y_from_target(target_coordinates: ObjectCoordinates) -> int:
    _, y_center = target_coordinates.center
    return int(round(y_center))


def box_line_side(box: tuple[int, int, int, int], line_y: int) -> int:
    _, y, _, height = box
    if y + height < line_y:
        return -1
    if y > line_y:
        return 1
    return 0


def crossed_line(
    object_box: tuple[int, int, int, int],
    line_y: int,
    previous_side: Optional[int],
    was_on_line: bool,
) -> tuple[bool, int, bool]:
    side = box_line_side(object_box, line_y)
    is_on_line = side == 0
    crossed = (is_on_line and not was_on_line) or (
        previous_side is not None and side != 0 and previous_side != 0 and side != previous_side
    )
    return crossed, side, is_on_line


def center_distance(first: ObjectCoordinates, second: ObjectCoordinates) -> tuple[float, float]:
    first_x, first_y = first.center
    second_x, second_y = second.center
    distance_pixels = math.hypot(first_x - second_x, first_y - second_y)

    image_width, image_height = first.image_size
    normalized_dx = (first_x - second_x) / image_width
    normalized_dy = (first_y - second_y) / image_height
    distance_normalized = math.hypot(normalized_dx, normalized_dy)
    return distance_pixels, distance_normalized


def format_crossing(
    frame_number: int,
    crossing_count: int,
    object_coordinates: ObjectCoordinates,
    target_coordinates: ObjectCoordinates,
    distance_pixels: float,
    distance_normalized: float,
    output_format: str,
) -> str:
    if output_format == "json":
        payload = {
            "frame": frame_number,
            "crossing": crossing_count,
            "distance_pixels": round(distance_pixels, 3),
            "distance_normalized": round(distance_normalized, 6),
            "object_box_xywh_pixels": object_coordinates.box,
            "object_center_pixels": [round(value, 1) for value in object_coordinates.center],
            "target_box_xywh_pixels": target_coordinates.box,
            "target_center_pixels": [round(value, 1) for value in target_coordinates.center],
            "line_y_pixels": line_y_from_target(target_coordinates),
        }
        return json.dumps(payload)

    return (
        f"frame={frame_number} crossing={crossing_count} "
        f"distance_px={distance_pixels:.3f} distance_norm={distance_normalized:.6f} "
        f"object_center=({object_coordinates.center[0]:.1f}, {object_coordinates.center[1]:.1f}) "
        f"target_center=({target_coordinates.center[0]:.1f}, {target_coordinates.center[1]:.1f}) "
        f"object_box={object_coordinates.box} target_box={target_coordinates.box}"
    )


def format_function_return(name: str, coordinates: Optional[ObjectCoordinates]) -> str:
    if coordinates is None:
        return f"{name}=None"

    return (
        f"{name}=ObjectCoordinates("
        f"box={coordinates.box}, "
        f"center=({coordinates.center[0]:.1f}, {coordinates.center[1]:.1f}), "
        f"normalized_box=({coordinates.normalized_box[0]:.6f}, {coordinates.normalized_box[1]:.6f}, "
        f"{coordinates.normalized_box[2]:.6f}, {coordinates.normalized_box[3]:.6f}), "
        f"area={coordinates.area:.0f}, "
        f"image_size={coordinates.image_size}, "
        f"label_id={coordinates.label_id})"
    )


def draw_line(frame, target_coordinates: ObjectCoordinates) -> None:
    line_y = line_y_from_target(target_coordinates)
    _, frame_width = frame.shape[:2]
    cv2.line(frame, (0, line_y), (frame_width - 1, line_y), (0, 255, 255), 2)
    cv2.putText(
        frame,
        "target line",
        (8, max(18, line_y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )


def draw_distance(frame, distance_pixels: float, crossing_count: int) -> None:
    text = f"crossing {crossing_count}: {distance_pixels:.1f}px"
    cv2.rectangle(frame, (10, 10), (310, 46), (0, 0, 0), -1)
    cv2.putText(frame, text, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)


def draw_live_log(frame, log_lines: list[str]) -> None:
    if not log_lines:
        return

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.52
    thickness = 1
    margin = 8
    line_height = 22
    lines = log_lines[-5:]
    text_width = max(cv2.getTextSize(line, font, scale, thickness)[0][0] for line in lines)
    box_width = min(frame.shape[1] - 20, text_width + margin * 2)
    box_height = line_height * len(lines) + margin * 2

    cv2.rectangle(frame, (10, 10), (10 + box_width, 10 + box_height), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        y = 10 + margin + 15 + index * line_height
        cv2.putText(frame, line, (10 + margin, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


def maybe_start_browser_preview(args: argparse.Namespace) -> Optional[BrowserPreview]:
    if not args.browser_display:
        return None

    browser_preview = start_browser_preview(args.browser_host, args.browser_port)
    print(f"Open live preview: {browser_preview.url}", flush=True)
    return browser_preview


def main() -> None:
    args = parse_args()
    if args.max_frames is not None and args.max_frames < 1:
        raise ValueError("--max-frames must be at least 1")
    if args.print_every < 1:
        raise ValueError("--print-every must be at least 1")

    object_model = LargestColorObjectModel(args.object_low, args.object_high, args.min_area, args.object_label_id)
    target_model = LargestColorObjectModel(args.target_low, args.target_high, args.min_area, args.target_label_id)

    capture = open_capture(args)
    if args.width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if args.height:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    frame_number = 0
    crossing_count = 0
    previous_side = None
    was_on_line = False
    writer = None
    browser_preview = maybe_start_browser_preview(args)
    display_enabled = not args.no_display and browser_preview is None
    wait_ms = 30 if args.video else 1
    live_log = []

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                if args.video and args.loop_video:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    previous_side = None
                    was_on_line = False
                    continue
                break

            frame_number += 1
            preview = frame.copy()
            target_coordinates = get_target_bounding_box_coordinates(frame, target_model)
            object_coordinates = get_object_coordinates(frame, object_model)

            if args.print_function_returns and frame_number % args.print_every == 0:
                print(
                    f"frame={frame_number} "
                    f"{format_function_return('get_target_bounding_box_coordinates_return', target_coordinates)} "
                    f"{format_function_return('get_object_coordinates_return', object_coordinates)}",
                    flush=True,
                )

            if target_coordinates is not None:
                preview = draw_annotation(
                    preview,
                    target_coordinates.box,
                    target_coordinates.normalized_box,
                    target_coordinates.area,
                    target_coordinates.label_id,
                    label="target",
                    box_color=(0, 255, 255),
                )
                draw_line(preview, target_coordinates)

            if object_coordinates is not None:
                preview = draw_annotation(
                    preview,
                    object_coordinates.box,
                    object_coordinates.normalized_box,
                    object_coordinates.area,
                    object_coordinates.label_id,
                    label="object",
                    box_color=(255, 0, 0),
                )

            if target_coordinates is None or object_coordinates is None:
                previous_side = None
                was_on_line = False
            else:
                line_y = line_y_from_target(target_coordinates)
                crossed, previous_side, was_on_line = crossed_line(
                    object_coordinates.box,
                    line_y,
                    previous_side,
                    was_on_line,
                )
                if crossed:
                    crossing_count += 1
                    distance_pixels, distance_normalized = center_distance(object_coordinates, target_coordinates)
                    crossing_line = format_crossing(
                        frame_number,
                        crossing_count,
                        object_coordinates,
                        target_coordinates,
                        distance_pixels,
                        distance_normalized,
                        args.format,
                    )
                    print(crossing_line, flush=True)
                    live_log.append(
                        f"frame {frame_number} | crossing {crossing_count} | distance {distance_pixels:.1f}px"
                    )
                    draw_distance(preview, distance_pixels, crossing_count)
                    if args.stop_after_first:
                        if writer is None:
                            writer = make_video_writer(args.output_video, preview, capture)
                        if writer is not None:
                            writer.write(preview)
                        break

            if writer is None:
                writer = make_video_writer(args.output_video, preview, capture)
            draw_live_log(preview, live_log)
            if writer is not None:
                writer.write(preview)

            if browser_preview is not None:
                browser_preview.update(preview)
                if args.video:
                    time.sleep(wait_ms / 1000)

            if display_enabled:
                try:
                    cv2.imshow("Distance on line crossing", preview)
                    if cv2.waitKey(wait_ms) & 0xFF == 27:
                        break
                except cv2.error:
                    print("Display disabled: this OpenCV build does not support cv2.imshow().", flush=True)
                    display_enabled = False

            if args.max_frames is not None and frame_number >= args.max_frames:
                break
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if browser_preview is not None:
            browser_preview.stop()
        if display_enabled:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass


if __name__ == "__main__":
    main()
