import cv2
import numpy as np
import time

def prepare_camera():
    return cv2.VideoCapture(0)

def capture_image(cam):
    ret, frame = cam.read()
    if not ret:
        raise IOError("Connection to camera failed. Maybe another program is using it?")
    return frame

def show_camera(cam, low_green=None, high_green=None):
    cv2.namedWindow("test")
    while True:
        frame = capture_image(cam)

        locate(frame, low_green, high_green)
        cv2.imshow("test", frame)

        k = cv2.waitKey(0) & 0xFF
        if k == 27: #ESC key
            break

    cam.release()
    cv2.destroyAllWindows()
    for i in range (1,5):
        cv2.waitKey(1)

def locate(img, low_green=None, high_green=None):
    LAB_frame = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

    if low_green is None:
        low_green = np.array([15, 55, 115])
    if high_green is None:
        high_green = np.array([240, 115, 205])
    green_mask = cv2.inRange(LAB_frame, low_green, high_green)

    contours, hierarchy = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) != 0:
        c = max(contours, key = cv2.contourArea)

        x,y,w,h = cv2.boundingRect(c)

        # draw the contour (in green)
        cv2.rectangle(img,(x,y),(x+w,y+h),(0, 0,255),2)
        cv2.circle(img, (round(x+w/2), round(y+h/2)), 5, (0, 0, 255), -1)
    else:
        x = None
        y = None

    return x, y

def camera_loop(cam, low_green=None, high_green=None, wait_time=1.0):
    def wrap(func):
        class CoordinateStore:
            def __init__(self):
                self.point = None

            def select_point(self,event,x,y,flags,param):
                    if event == cv2.EVENT_LBUTTONDBLCLK:
                        self.point = [x,y]

        def wrapped_f(*args):
            # Instantiate class to store clicked point coordinate
            coordinateStore1 = CoordinateStore()

            cv2.namedWindow("image_capture")
            cv2.setMouseCallback('image_capture', coordinateStore1.select_point)

            # Variable to hold the last time the value was returned to 
            last_return_time = time.time() - wait_time

            while True:
                frame = capture_image(cam)

                x, y = locate(frame, low_green, high_green)
                cv2.imshow("image_capture", frame)
                
                # Only run the function at a user-specified interval.
                if (time.time() - last_return_time) >= wait_time:
                    done = func(*args, x, y, coordinateStore1.point)
                    last_return_time += wait_time
                if done:
                    break

                k = cv2.waitKey(0) & 0xFF
                if k == 27: #ESC key
                    break

            cam.release()
            cv2.destroyAllWindows()
            for i in range (1,5):
                cv2.waitKey(1)

        return wrapped_f
    return wrap

if __name__ == '__main__':

    cam = prepare_camera()
    
    low_green = np.array([15, 56, 133])
    high_green = np.array([240, 98, 206])

    class TestClass:
        def __init__(self):
            self.i = 0

        @camera_loop(cam, low_green, high_green, 0.5)
        def go(self, x, y, clickpoint):
            print(self.i)
            if clickpoint is not None:
                print(clickpoint)
            if self.i > 1000:
                return True
            self.i += 1
            return False

    test = TestClass()
    test.go()
