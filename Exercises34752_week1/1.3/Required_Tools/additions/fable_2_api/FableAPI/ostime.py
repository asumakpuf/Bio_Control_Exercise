import time
import sys, os

class OSTime():
    @staticmethod
    def getOSTime():
        if sys.platform == 'win32':
            return time.perf_counter()
            #return time.clock()
            #return time.time()
        else:
            return time.time()
