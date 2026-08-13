from pathlib import Path

import cv2
import numpy as np


def write_image(output_path: Path, image: np.ndarray) -> None:
    cv2.imwrite(str(output_path), image)
    print(f"Wrote {output_path}")


def make_test_shapes() -> np.ndarray:
    image = np.zeros((420, 640), dtype=np.uint8)
    cv2.circle(image, (115, 105), 48, 255, -1)
    cv2.rectangle(image, (250, 95), (560, 315), 255, -1)
    cv2.rectangle(image, (60, 285), (170, 370), 255, -1)
    return image


def make_tall_object() -> np.ndarray:
    image = np.zeros((480, 640), dtype=np.uint8)
    cv2.rectangle(image, (80, 80), (170, 180), 255, -1)
    cv2.rectangle(image, (365, 50), (465, 415), 255, -1)
    cv2.circle(image, (190, 365), 55, 255, -1)
    return image


def make_noisy_objects() -> np.ndarray:
    image = np.zeros((480, 640), dtype=np.uint8)
    cv2.rectangle(image, (210, 130), (520, 345), 255, -1)
    cv2.circle(image, (90, 90), 35, 255, -1)
    cv2.rectangle(image, (45, 320), (130, 390), 255, -1)

    rng = np.random.default_rng(4)
    points = rng.integers(low=(0, 0), high=(640, 480), size=(120, 2))
    for x, y in points:
        image[y, x] = 255
    return image


def make_touching_border() -> np.ndarray:
    image = np.zeros((360, 640), dtype=np.uint8)
    cv2.rectangle(image, (0, 95), (250, 300), 255, -1)
    cv2.rectangle(image, (380, 70), (515, 190), 255, -1)
    cv2.circle(image, (535, 280), 42, 255, -1)
    return image


def make_irregular_polygon() -> np.ndarray:
    image = np.zeros((480, 640), dtype=np.uint8)
    largest = np.array(
        [
            [210, 95],
            [330, 55],
            [430, 105],
            [515, 195],
            [470, 330],
            [350, 385],
            [225, 335],
            [165, 220],
        ],
        dtype=np.int32,
    )
    smaller = np.array(
        [[60, 300], [135, 265], [190, 330], [150, 405], [75, 390]],
        dtype=np.int32,
    )
    cv2.fillPoly(image, [largest], 255)
    cv2.fillPoly(image, [smaller], 255)
    cv2.circle(image, (95, 105), 44, 255, -1)
    return image


def make_lumpy_blob() -> np.ndarray:
    image = np.zeros((480, 640), dtype=np.uint8)
    blob_centers = [
        (275, 220, 92),
        (350, 160, 82),
        (415, 240, 96),
        (330, 300, 86),
        (250, 310, 58),
    ]
    for x, y, radius in blob_centers:
        cv2.circle(image, (x, y), radius, 255, -1)

    cv2.ellipse(image, (100, 135), (70, 38), 25, 0, 360, 255, -1)
    cv2.rectangle(image, (70, 330), (175, 405), 255, -1)
    return image


def make_crescent_with_holes() -> np.ndarray:
    image = np.zeros((480, 640), dtype=np.uint8)
    cv2.ellipse(image, (340, 240), (185, 125), -18, 0, 360, 255, -1)
    cv2.ellipse(image, (395, 205), (155, 95), -18, 0, 360, 0, -1)
    cv2.circle(image, (305, 255), 24, 0, -1)
    cv2.circle(image, (250, 210), 18, 0, -1)

    cv2.fillPoly(
        image,
        [np.array([[70, 95], [150, 60], [205, 120], [175, 185], [90, 175]])],
        255,
    )
    cv2.circle(image, (115, 360), 48, 255, -1)
    return image


def main() -> None:
    output_dir = Path("examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = {
        "test_shapes.png": make_test_shapes(),
        "tall_object.png": make_tall_object(),
        "noisy_objects.png": make_noisy_objects(),
        "touching_border.png": make_touching_border(),
        "irregular_polygon.png": make_irregular_polygon(),
        "lumpy_blob.png": make_lumpy_blob(),
        "crescent_with_holes.png": make_crescent_with_holes(),
    }

    for filename, image in samples.items():
        write_image(output_dir / filename, image)


if __name__ == "__main__":
    main()
