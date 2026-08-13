from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the largest white object in a black-and-white image, draw a bounding box, and save normalized coordinates."
    )
    parser.add_argument("image", type=Path, help="Input black-and-white image")
    parser.add_argument(
        "--output",
        type=Path,
        help="Annotated image output path. Default: outputs/<name>_boxed.<ext>",
    )
    parser.add_argument(
        "--label-output",
        type=Path,
        help="Normalized label output path. Default: outputs/<name>.txt",
    )
    parser.add_argument("--threshold", type=int, default=127, help="Threshold for white pixels, from 0 to 255. Default: 127")
    parser.add_argument("--label-id", type=int, default=0, help="Label id to write in the normalized label file. Default: 0")
    parser.add_argument("--min-area", type=float, default=1.0, help="Ignore contours smaller than this pixel area. Default: 1")
    parser.add_argument("--invert", action="store_true", help="Detect black objects on a white background instead.")
    parser.add_argument("--verbose", action="store_true", help="Print image size, normalized label, and output paths.")
    return parser.parse_args()


def default_output_paths(image_path: Path) -> tuple[Path, Path]:
    output_dir = Path("outputs")
    output_image = output_dir / f"{image_path.stem}_boxed{image_path.suffix}"
    label_output = output_dir / f"{image_path.stem}.txt"
    return output_image, label_output


def load_image(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    if image.ndim == 2:
        gray = image
        display = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        display = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
    else:
        display = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return gray, display


def find_largest_white_box(
    gray: np.ndarray,
    threshold: int,
    min_area: float,
    invert: bool = False,
) -> tuple[int, int, int, int, float]:
    threshold_type = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, binary = cv2.threshold(gray, threshold, 255, threshold_type)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = [(contour, cv2.contourArea(contour)) for contour in contours if cv2.contourArea(contour) >= min_area]
    if not candidates:
        raise ValueError("No object found. Try lowering --threshold or --min-area.")

    largest_contour, area = max(candidates, key=lambda item: item[1])
    x, y, width, height = cv2.boundingRect(largest_contour)
    return x, y, width, height, area


def to_normalized_coordinates(
    box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[float, float, float, float]:
    x, y, width, height = box
    x_center = (x + width / 2) / image_width
    y_center = (y + height / 2) / image_height
    normalized_width = width / image_width
    normalized_height = height / image_height
    return x_center, y_center, normalized_width, normalized_height


def draw_annotation(
    image: np.ndarray,
    box: tuple[int, int, int, int],
    normalized: tuple[float, float, float, float],
    area: float,
    label_id: int = 0,
    label: Optional[str] = None,
    box_color: tuple[int, int, int] = (0, 255, 0),
    text_color: tuple[int, int, int] = (255, 255, 255),
    background_color: tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    annotated = image.copy()
    x, y, width, height = box
    cv2.rectangle(annotated, (x, y), (x + width, y + height), box_color, 2)

    prefix = f"{label} " if label else ""
    lines = [
        f"{prefix}id {label_id}",
        f"xywh px: {x} {y} {width} {height}",
        "norm: " + " ".join(f"{value:.6f}" for value in normalized),
        f"area: {area:.0f}",
    ]

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thickness = 1
    margin = 4
    line_height = 18
    text_width = max(cv2.getTextSize(line, font, scale, thickness)[0][0] for line in lines)
    text_height = line_height * len(lines) + margin * 2
    label_x = x
    label_y = max(0, y - text_height)

    cv2.rectangle(
        annotated,
        (label_x, label_y),
        (label_x + text_width + margin * 2, label_y + text_height),
        background_color,
        -1,
    )
    for index, line in enumerate(lines):
        baseline_y = label_y + margin + 14 + index * line_height
        cv2.putText(annotated, line, (label_x + margin, baseline_y), font, scale, text_color, thickness, cv2.LINE_AA)

    return annotated


def write_normalized_label(
    label_output: Path,
    label_id: int,
    normalized: tuple[float, float, float, float],
) -> None:
    label_output.parent.mkdir(parents=True, exist_ok=True)
    label = f"{label_id} " + " ".join(f"{value:.6f}" for value in normalized) + "\n"
    label_output.write_text(label, encoding="utf-8")


def main() -> None:
    args = parse_args()
    if not 0 <= args.threshold <= 255:
        raise ValueError("--threshold must be between 0 and 255")

    default_image_output, default_label_output = default_output_paths(args.image)
    output = args.output or default_image_output
    label_output = args.label_output or default_label_output

    gray, display = load_image(args.image)
    image_height, image_width = gray.shape[:2]
    x, y, width, height, area = find_largest_white_box(gray, args.threshold, args.min_area, args.invert)
    box = (x, y, width, height)
    normalized = to_normalized_coordinates(box, image_width, image_height)
    annotated = draw_annotation(display, box, normalized, area, args.label_id)

    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), annotated):
        raise RuntimeError(f"Could not write output image: {output}")
    write_normalized_label(label_output, args.label_id, normalized)

    if args.verbose:
        print(f"image_size: {image_width}x{image_height}")
        print(f"bbox_xywh_pixels: {box}")
        print(f"normalized_label: {args.label_id} " + " ".join(f"{value:.6f}" for value in normalized))
        print(f"annotated_image: {output}")
        print(f"label_file: {label_output}")


if __name__ == "__main__":
    main()
