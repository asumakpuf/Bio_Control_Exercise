from pathlib import Path

import cv2

from white_object_model import LargestWhiteObjectModel


def main() -> None:
    image_path = Path("examples/irregular_polygon.png")
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise FileNotFoundError(f"Could not read {image_path}")

    model = LargestWhiteObjectModel(threshold=127, min_area=100)
    detection = model.detect(frame)
    if detection is None:
        print("no object")
        return

    print(detection.pixels_line())


if __name__ == "__main__":
    main()
