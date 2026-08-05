import cv2
import numpy as np
import argparse
from operator import xor

def callback(value):
    pass

def setup_trackbars(range_filter):
    cv2.namedWindow("Trackbars", 0)

    for i in ["MIN", "MAX"]:
        v = 0 if i == "MIN" else 255
        for j in range_filter:
            cv2.createTrackbar("%s_%s" % (j, i), "Trackbars", v, 255, callback)

def get_trackbar_values(range_filter):
    values = []
    for i in ["MIN", "MAX"]:
        for j in range_filter:
            v = cv2.getTrackbarPos("%s_%s" % (j, i), "Trackbars")
            values.append(v)

    return values

def colorpicker():
    range_filter = "LAB"

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print('colorpicker() -> Cannot open camera')
        exit(0)
    camera.set(3,640)
    camera.set(4,480)
    setup_trackbars(range_filter)

    while True:
        ret, image = camera.read()
        if not ret:
            print('colorpicker() -> Cannot read frame - ending execution...')
            break
        
        frame_to_thresh = cv2.cvtColor(image, cv2.COLOR_BGR2LAB) # LAB

        v1_min, v2_min, v3_min, v1_max, v2_max, v3_max = get_trackbar_values(range_filter)
        thresh = cv2.inRange(frame_to_thresh, (v1_min, v2_min, v3_min), (v1_max, v2_max, v3_max))

        image = cv2.flip(image, 1)
        cv2.imshow("Original", image)

        thresh = cv2.flip(thresh, 1)
        cv2.imshow("Thresh", thresh)

        k = cv2.waitKey(100) & 0xFF
        if k == 27: #ESC key
            break

    camera.release()
    # There are a few peculiarities with the GUI in OpenCV. The destroyImage call fails to close a 
    # window (atleast under Linux, where the default backend was Gtk+ until 2.1.0) unless waitKey 
    # was called to pump the events. Adding a waitKey(1) call right after destroyWindow may work.
    # Even so, closing is not guaranteed; the the waitKey function is only intercepted if a window 
    # has focus, and so if the window didn't have focus at the time you invoked destroyWindow, 
    # chances are it'll stay visible till the next destroyWindow call.
    cv2.destroyAllWindows()
    for i in range (1,5):
        cv2.waitKey(1)

    return np.array([v1_min, v2_min, v3_min]), np.array([v1_max, v2_max, v3_max])

# USAGE: You need to specify a filter and "only one" image source
# python ColorPicker.py --filter RGB --image /path/image.png
# or
# python ColorPicker.py --filter HSV --webcam
if __name__ == '__main__':
    colorpicker()
