'''
Created on 17/01/2016

@author: djchr
'''
import os, sys
from threading import Thread, Event
#import pyaudio
import wave
import numpy as np
CHUNK = 1024

class FableBeep(Thread):
    def __init__(self, frequency, duration):
        Thread.__init__(self)
        self.frequency = frequency
        self.duration = duration
        self._stopper = Event()

    def run(self):
        frequency = self.frequency
        duration = self.duration
        self._stopper.clear()
        fs = 44100
        # audio = (np.sin(2*np.pi*np.arange(fs*duration)*frequency/fs)).astype(np.float32)
        # p = pyaudio.PyAudio()
        # # open stream based on the wave object which has been input.
        # stream = p.open(format=pyaudio.paFloat32,
        #                 channels = 1,
        #                 rate = fs,
        #                 output = True)
        # # read data (based on the chunk size)
        # data = audio[0:CHUNK]
        # nchunks = 0 # number of chunks processed
        # # play stream (looping from beginning of file to the end)
        # while not self._stopper.is_set():
        #     if len(data) > 0:
        #         # writing to the stream is what *actually* plays the sound.
        #         stream.write(data.tostring())
        #         nchunks = nchunks+1
        #         data = audio[nchunks*CHUNK:nchunks*CHUNK+CHUNK]
        #     else:
        #         stream.stop_stream()
        #         stream.close()
        #         p.terminate()
        #         self.stop()

    def stop(self):
        self._stopper.set()

class FableSound(Thread):
    def __init__(self, soundfilename):
        Thread.__init__(self)
        self.soundfilename = soundfilename
        self._stopper = Event()

    def run(self):
        # soundfilename = self.soundfilename
        self._stopper.clear()
        # # open the file for reading.
        # wf = wave.open(soundfilename, 'rb')
        # # create an audio object
        # p = pyaudio.PyAudio()
        # # open stream based on the wave object which has been input.
        # stream = p.open(format =
        #                 p.get_format_from_width(wf.getsampwidth()),
        #                 channels = wf.getnchannels(),
        #                 rate = wf.getframerate(),
        #                 output = True)
        # # read data (based on the chunk size)
        # data = wf.readframes(CHUNK)
        # # play stream (looping from beginning of file to the end)
        # while not self._stopper.is_set():
        #     if len(data) > 0:
        #         # writing to the stream is what *actually* plays the sound.
        #         stream.write(data)
        #         data = wf.readframes(CHUNK)
        #     else:
        #         stream.stop_stream()
        #         stream.close()
        #         p.terminate()
        #         self.stop()

    def stop(self):
        self._stopper.set()
