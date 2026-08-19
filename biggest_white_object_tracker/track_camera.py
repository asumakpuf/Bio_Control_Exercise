from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

import cv2

from color_object_model import LargestColorObjectModel
from detect_biggest_white_object import draw_annotation


DEFAULT_BLUE_LOW = [0, 140, 112]
DEFAULT_BLUE_HIGH = [136, 147, 125]
DEFAULT_YELLOW_LOW = [30, 104, 127]
DEFAULT_YELLOW_HIGH = [54, 108, 138]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Track the largest blue and yellow LAB color targets in a camera feed or video file."
    )
    parser.add_argument("--video", type=Path, help="Video file to process. If omitted, the script uses the camera.")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index used when --video is omitted. Default: 0")
    parser.add_argument("--min-area", type=float, default=100.0, help="Ignore objects smaller than this pixel area. Default: 100")
    parser.add_argument("--blue-label-id", type=int, default=0, help="Label id for the blue target. Default: 0")
    parser.add_argument("--yellow-label-id", type=int, default=1, help="Label id for the yellow target. Default: 1")
    parser.add_argument("--blue-low", type=int, nargs=3, default=DEFAULT_BLUE_LOW, metavar=("L", "A", "B"))
    parser.add_argument("--blue-high", type=int, nargs=3, default=DEFAULT_BLUE_HIGH, metavar=("L", "A", "B"))
    parser.add_argument("--yellow-low", type=int, nargs=3, default=DEFAULT_YELLOW_LOW, metavar=("L", "A", "B"))
    parser.add_argument("--yellow-high", type=int, nargs=3, default=DEFAULT_YELLOW_HIGH, metavar=("L", "A", "B"))
    parser.add_argument(
        "--blue-min-area",
        type=float,
        default=None,
        help="Minimum area for the blue target. Default: same as --min-area",
    )
    parser.add_argument(
        "--yellow-min-area",
        type=float,
        default=None,
        help="Minimum area for the yellow target. Default: same as --min-area",
    )
    parser.add_argument(
        "--format",
        choices=("json", "normalized", "pixels"),
        default="pixels",
        help="Coordinate print format. Default: pixels",
    )
    parser.add_argument("--print-every", type=int, default=1, help="Print every N detected frames. Default: 1")
    parser.add_argument("--no-display", action="store_true", help="Do not open the live preview window.")
    parser.add_argument(
        "--browser-display",
        action="store_true",
        help="Show the annotated camera feed in a local browser page instead of an OpenCV window.",
    )
    parser.add_argument("--browser-host", default="127.0.0.1", help="Host for --browser-display. Default: 127.0.0.1")
    parser.add_argument("--browser-port", type=int, default=8000, help="Port for --browser-display. Default: 8000")
    parser.add_argument("--output-video", type=Path, help="Optional path for saving the annotated video.")
    parser.add_argument("--max-frames", type=int, help="Stop after this many frames. Useful for quick video tests.")
    parser.add_argument("--width", type=int, help="Requested camera frame width.")
    parser.add_argument("--height", type=int, help="Requested camera frame height.")
    return parser.parse_args()


def format_coordinates(output_format: str, frame_number: int, timestamp: float, target: str, detection) -> str:
    if output_format == "normalized":
        return f"frame={frame_number} time={timestamp:.3f} target={target} {detection.normalized_line}"

    if output_format == "json":
        x_center, y_center = detection.center
        normalized_width, normalized_height = detection.normalized[2:]
        payload = {
            "frame": frame_number,
            "time": round(timestamp, 3),
            "target": target,
            "label_id": detection.label_id,
            "bbox_xywh_pixels": detection.box,
            "center_pixels": [round(x_center, 1), round(y_center, 1)],
            "bbox_normalized": [round(value, 6) for value in detection.normalized],
            "area": round(detection.area, 1),
            "image_size": [detection.image_width, detection.image_height],
            "width_normalized": round(normalized_width, 6),
            "height_normalized": round(normalized_height, 6),
        }
        return json.dumps(payload)

    return f"frame={frame_number} time={timestamp:.3f} target={target} {detection.pixels_line}"


def open_capture(args: argparse.Namespace) -> cv2.VideoCapture:
    if args.video:
        capture = cv2.VideoCapture(str(args.video))
        if not capture.isOpened():
            raise RuntimeError(f"Could not open video file: {args.video}")
        return capture

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise RuntimeError(f"Could not open camera index {args.camera}")
    return capture


def make_video_writer(output_video: Optional[Path], first_frame, capture: cv2.VideoCapture) -> Optional[cv2.VideoWriter]:
    if output_video is None:
        return None

    output_video.parent.mkdir(parents=True, exist_ok=True)
    height, width = first_frame.shape[:2]
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write output video: {output_video}")
    return writer


def display_delay_ms(is_video_file: bool) -> int:
    return 1 if not is_video_file else 30


def show_preview(window_name: str, frame, wait_ms: int) -> tuple[bool, int]:
    try:
        cv2.imshow(window_name, frame)
        return True, cv2.waitKey(wait_ms) & 0xFF
    except cv2.error:
        print(
            "Display disabled: this OpenCV build does not support cv2.imshow(). "
            "Tracking will continue in terminal-only mode. Use --output-video to save annotated frames.",
            flush=True,
        )
        return False, -1


def close_preview_windows() -> None:
    try:
        cv2.destroyAllWindows()
    except cv2.error:
        pass


def boxes_intersect(first_box: tuple[int, int, int, int], second_box: tuple[int, int, int, int]) -> bool:
    first_x, first_y, first_width, first_height = first_box
    second_x, second_y, second_width, second_height = second_box
    return (
        first_x < second_x + second_width
        and first_x + first_width > second_x
        and first_y < second_y + second_height
        and first_y + first_height > second_y
    )


def box_line_side(box: tuple[int, int, int, int], line_y: int) -> int:
    _, y, _, height = box
    if y + height < line_y:
        return -1
    if y > line_y:
        return 1
    return 0


def draw_yellow_center_line(frame, yellow_detection) -> int:
    _, y_center = yellow_detection.center
    line_y = int(round(y_center))
    frame_height, frame_width = frame.shape[:2]
    cv2.line(frame, (0, line_y), (frame_width - 1, line_y), (0, 255, 255), 2)
    cv2.putText(
        frame,
        "yellow line",
        (8, max(18, line_y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return line_y


def add_event_message(messages: list[dict], text: str, now: float, duration_seconds: float = 2.0) -> None:
    messages.append({"text": text, "expires_at": now + duration_seconds})


def draw_event_messages(frame, messages: list[dict], now: float) -> list[dict]:
    active_messages = [message for message in messages if message["expires_at"] > now]
    if not active_messages:
        return active_messages

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.75
    thickness = 2
    margin = 8
    line_height = 30
    text_width = max(cv2.getTextSize(message["text"], font, scale, thickness)[0][0] for message in active_messages)
    box_height = margin * 2 + line_height * len(active_messages)
    cv2.rectangle(frame, (10, 10), (10 + text_width + margin * 2, 10 + box_height), (0, 0, 0), -1)

    for index, message in enumerate(active_messages):
        y = 10 + margin + 22 + index * line_height
        cv2.putText(frame, message["text"], (10 + margin, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return active_messages


class BrowserPreview:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.condition = threading.Condition()
        self.latest_jpeg = None
        self.sequence = 0
        self.stopped = False
        self.server = None
        self.thread = None

    @property
    def url(self) -> str:
        if self.server is None:
            return f"http://{self.host}:{self.port}/"
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/"

    def start(self) -> None:
        handler = self._make_handler()
        self.server = ThreadingHTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def update(self, frame) -> None:
        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return
        with self.condition:
            self.latest_jpeg = buffer.tobytes()
            self.sequence += 1
            self.condition.notify_all()

    def stop(self) -> None:
        with self.condition:
            self.stopped = True
            self.condition.notify_all()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()

    def _make_handler(self):
        preview = self

        class PreviewHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    self._serve_index()
                elif self.path == "/stream.mjpg":
                    self._serve_stream()
                else:
                    self.send_error(404)

            def _serve_index(self):
                body = b"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Object tracker</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: sans-serif; }
    header { padding: 10px 14px; background: #202020; }
    img { display: block; max-width: 100vw; max-height: calc(100vh - 44px); margin: 0 auto; }
  </style>
</head>
<body>
  <header>Blue target: blue box | Yellow target: yellow box</header>
  <img src="/stream.mjpg" alt="Live annotated camera feed">
</body>
</html>
"""
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _serve_stream(self):
                self.send_response(200)
                self.send_header("Age", "0")
                self.send_header("Cache-Control", "no-cache, private")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()

                last_sequence = -1
                while True:
                    with preview.condition:
                        preview.condition.wait_for(
                            lambda: preview.stopped
                            or (preview.latest_jpeg is not None and preview.sequence != last_sequence)
                        )
                        if preview.stopped:
                            break
                        jpeg = preview.latest_jpeg
                        last_sequence = preview.sequence

                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError, socket.error):
                        break

        return PreviewHandler


def start_browser_preview(host: str, port: int) -> BrowserPreview:
    last_error = None
    candidate_ports = [port] if port == 0 else range(port, port + 11)
    for candidate_port in candidate_ports:
        preview = BrowserPreview(host, candidate_port)
        try:
            preview.start()
            return preview
        except OSError as exc:
            last_error = exc
    raise RuntimeError(f"Could not start browser preview on {host}:{port}: {last_error}")


def main() -> None:
    args = parse_args()
    if args.print_every < 1:
        raise ValueError("--print-every must be at least 1")
    if args.max_frames is not None and args.max_frames < 1:
        raise ValueError("--max-frames must be at least 1")

    blue_model = LargestColorObjectModel(
        args.blue_low,
        args.blue_high,
        args.blue_min_area if args.blue_min_area is not None else args.min_area,
        args.blue_label_id,
    )
    yellow_model = LargestColorObjectModel(
        args.yellow_low,
        args.yellow_high,
        args.yellow_min_area if args.yellow_min_area is not None else args.min_area,
        args.yellow_label_id,
    )
    targets = [
        ("blue", blue_model, (255, 0, 0)),
        ("yellow", yellow_model, (0, 255, 255)),
    ]

    capture = open_capture(args)
    if args.width:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if args.height:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    print("Tracking targets: blue and yellow", flush=True)
    print(f"Blue LAB range: low={args.blue_low} high={args.blue_high}", flush=True)
    print(f"Yellow LAB range: low={args.yellow_low} high={args.yellow_high}", flush=True)

    frame_number = 0
    detected_count = 0
    writer = None
    wait_ms = display_delay_ms(args.video is not None)
    window_name = "Largest object tracker"
    browser_preview = None
    previous_blue_line_side = None
    blue_was_on_line = False
    boxes_were_colliding = False
    line_crossing_count = 0
    collision_count = 0
    event_messages = []
    if args.browser_display:
        browser_preview = start_browser_preview(args.browser_host, args.browser_port)
        print(f"Open camera preview: {browser_preview.url}", flush=True)
    display_enabled = not args.no_display and browser_preview is None

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            frame_number += 1
            preview = frame.copy()
            detections = []
            detections_by_name = {}

            for target_name, model, box_color in targets:
                detection = model.detect(frame)
                if detection is None:
                    continue
                detections.append((target_name, detection))
                detections_by_name[target_name] = detection
                preview = draw_annotation(
                    preview,
                    detection.box,
                    detection.normalized,
                    detection.area,
                    detection.label_id,
                    label=target_name,
                    box_color=box_color,
                )

            blue_detection = detections_by_name.get("blue")
            yellow_detection = detections_by_name.get("yellow")
            now = time.time()

            if yellow_detection is not None:
                line_y = draw_yellow_center_line(preview, yellow_detection)

                if blue_detection is not None:
                    blue_side = box_line_side(blue_detection.box, line_y)
                    blue_is_on_line = blue_side == 0
                    crossed_line = (
                        (blue_is_on_line and not blue_was_on_line)
                        or (
                            previous_blue_line_side is not None
                            and blue_side != 0
                            and previous_blue_line_side != 0
                            and blue_side != previous_blue_line_side
                        )
                    )
                    if crossed_line:
                        line_crossing_count += 1
                        text = f"Blue crossed yellow line #{line_crossing_count}"
                        add_event_message(event_messages, text, now)
                        print(f"frame={frame_number} {text}", flush=True)

                    previous_blue_line_side = blue_side
                    blue_was_on_line = blue_is_on_line
                else:
                    blue_was_on_line = False
            else:
                previous_blue_line_side = None
                blue_was_on_line = False

            if blue_detection is not None and yellow_detection is not None:
                boxes_are_colliding = boxes_intersect(blue_detection.box, yellow_detection.box)
                if boxes_are_colliding and not boxes_were_colliding:
                    collision_count += 1
                    text = f"Blue/yellow collision #{collision_count}"
                    add_event_message(event_messages, text, now)
                    print(f"frame={frame_number} {text}", flush=True)
                boxes_were_colliding = boxes_are_colliding
            else:
                boxes_were_colliding = False

            event_messages = draw_event_messages(preview, event_messages, now)

            if detections:
                detected_count += 1
                if detected_count % args.print_every == 0:
                    for target_name, detection in detections:
                        print(format_coordinates(args.format, frame_number, now, target_name, detection), flush=True)
            elif detected_count % args.print_every == 0:
                print(f"frame={frame_number} No object found", flush=True)

            if writer is None:
                writer = make_video_writer(args.output_video, preview, capture)
            if writer is not None:
                writer.write(preview)

            if browser_preview is not None:
                browser_preview.update(preview)

            if display_enabled:
                display_enabled, key = show_preview(window_name, preview, wait_ms)
                if not display_enabled and browser_preview is None:
                    browser_preview = start_browser_preview(args.browser_host, args.browser_port)
                    browser_preview.update(preview)
                    print(f"Open camera preview: {browser_preview.url}", flush=True)
                if key == 27:
                    break

            if args.max_frames is not None and frame_number >= args.max_frames:
                break
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if display_enabled:
            close_preview_windows()
        if browser_preview is not None:
            browser_preview.stop()


if __name__ == "__main__":
    main()
