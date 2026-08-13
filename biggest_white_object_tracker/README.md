# Biggest Object Tracker

Small OpenCV project that tracks the largest object matching either a color range or a black-and-white threshold, draws a bounding box around it, and prints coordinates.

Normalized format:

```text
label_id x_center y_center width height
```

The four coordinate values are normalized to the image size, so they are between `0` and `1`.

## Setup

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Track Your Color on the Laptop Camera

This uses the LAB range from your calibration:

```python
low_green = [76, 45, 0]
high_green = [121, 112, 153]
```

Run the live camera tracker:

```bash
python track_color_camera.py
```

It opens camera `0`, shows the live stream, draws a bounding box around the largest matching object, and prints:

```text
x y width height
```

Press `q` or `Esc` to stop.

If your laptop camera is not camera `0`, try:

```bash
python track_color_camera.py --camera 1
```

Show the threshold mask next to the camera feed:

```bash
python track_color_camera.py --show-mask
```

Use different LAB values:

```bash
python track_color_camera.py --low-lab 76,45,0 --high-lab 121,112,153
```

Ignore small noise:

```bash
python track_color_camera.py --min-area 1000
```

## Test Color Tracking on a Video

Generate the included color test video:

```bash
python make_test_color_video.py
```

Visualize it with the bounding box:

```bash
python track_color_camera.py --video examples/moving_lab_color_blob.avi
```

Run without a preview window:

```bash
python track_color_camera.py --video examples/moving_lab_color_blob.avi --no-display
```

## Run on an Image

```bash
python detect_biggest_white_object.py path/to/image.png
```

By default this prints pixel coordinates:

```text
x y width height
```

Example:

```text
250 95 311 221
```

It also writes:

```text
outputs/image_boxed.png
outputs/image.txt
```

The `.txt` file contains one normalized annotation line for the largest white object.

## Track Black-and-White Camera or Video

Run the live camera tracker:

```bash
python track_camera.py
```

It opens camera `0`, draws the largest detected white object, and prints only pixel coordinates:

```text
x y width height
```

Example output:

```text
250 95 311 221
252 96 309 220
```

Press `q` or `Esc` to stop.

Run on a video file:

```bash
python track_camera.py --video examples/moving_irregular_blob.mp4 --no-display
```

Visualize the video while it runs:

```bash
python track_camera.py --video examples/moving_irregular_blob.mp4
```

Save an annotated video:

```bash
python track_camera.py --video examples/moving_irregular_blob.mp4 --output-video outputs/boxed_video.mp4 --no-display
```

Print normalized coordinates instead:

```bash
python track_camera.py --format normalized
```

Print JSON if you need the full message:

```bash
python track_camera.py --format json
```

Useful options:

```bash
python track_camera.py --camera 1
python track_camera.py --threshold 180 --min-area 500
python track_camera.py --invert
python track_camera.py --no-display
python track_camera.py --video examples/moving_irregular_blob.mp4 --max-frames 20
```

## Demo

The `examples/` folder contains a few black-and-white images you can test with:

```bash
python detect_biggest_white_object.py examples/test_shapes.png
python detect_biggest_white_object.py examples/tall_object.png
python detect_biggest_white_object.py examples/noisy_objects.png
python detect_biggest_white_object.py examples/touching_border.png
python detect_biggest_white_object.py examples/irregular_polygon.png
python detect_biggest_white_object.py examples/lumpy_blob.png
python detect_biggest_white_object.py examples/crescent_with_holes.png
```

Regenerate the example images:

```bash
python make_test_image.py
```

Generate the black-and-white example test video:

```bash
python make_test_video.py
```

## Example Model

Use the tracker model directly from Python:

```python
import cv2
from white_object_model import LargestWhiteObjectModel

frame = cv2.imread("examples/irregular_polygon.png")
model = LargestWhiteObjectModel(threshold=127, min_area=100)
detection = model.detect(frame)

if detection is not None:
    print(detection.pixels_line())
```

Run the included example:

```bash
python example_model_usage.py
```

## Options

```bash
python detect_biggest_white_object.py image.png --threshold 180 --label-id 0
python detect_biggest_white_object.py image.png --output boxed.png --label-output label.txt
python detect_biggest_white_object.py image.png --min-area 100
python detect_biggest_white_object.py image.png --verbose
```

Use `--invert` if your object is black and the background is white.
