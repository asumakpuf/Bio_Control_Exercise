'''
Created on 28/08/2014

@author: djchr
'''
import sys
import os, sys, traceback
if sys.platform == 'win32':
    import pywintypes
    import win32event
    import win32com.directsound.directsound as directsound
    import numpy as np

    class BufferDescriptor(object):
        def __init__(self, milliseconds=100):
            
            wfxFormat = pywintypes.WAVEFORMATEX()
            wfxFormat.wFormatTag = pywintypes.WAVE_FORMAT_PCM
            wfxFormat.nChannels = 2
            wfxFormat.nSamplesPerSec = 44100
            wfxFormat.nAvgBytesPerSec = 176400
            wfxFormat.nBlockAlign = 4
            wfxFormat.wBitsPerSample = 16
            
            self.format = wfxFormat
            self.size = 4*int((44100*milliseconds)/1000.)
            self.milliseconds = milliseconds
            self.shape = (self.size//4, 2)
            self.dtype = np.int16
            self.Fs = 44100


    class DirectSoundRecorder():
        def __init__(self, descriptor):
            d = directsound.DirectSoundCaptureCreate(None, None)
            sdesc = directsound.DSCBUFFERDESC()
            sdesc.dwBufferBytes = descriptor.size
            sdesc.lpwfxFormat = descriptor.format
            _buffer = d.CreateCaptureBuffer(sdesc)
            event = win32event.CreateEvent(None, 0, 0, None)
            notify = _buffer.QueryInterface(directsound.IID_IDirectSoundNotify)
            notify.SetNotificationPositions((directsound.DSBPN_OFFSETSTOP, event))
            self.device = d
            self.sdesc = sdesc
            self.descriptor = descriptor
            self.buffer = _buffer
            self.event = event
            self.notify = notify
            self.timeout = 2 * descriptor.milliseconds / 1000.
               
        def record(self):
            self.buffer.Start(0)
            win32event.WaitForSingleObject(self.event, -1)
            data = self.buffer.Update(0, self.descriptor.size)
            array = np.frombuffer(data, dtype=self.descriptor.dtype).reshape(self.descriptor.shape)
            return array

    class Microphone():
        initialized = False
        description = None
        recorder = None
        
        @staticmethod
        def getRMS(milliseconds = 100):
            try:
                
                if not Microphone.initialized: 
                    Microphone.desc = BufferDescriptor(milliseconds)    
                    Microphone.recorder = DirectSoundRecorder(Microphone.desc)
                    Microphone.initialized = True
                data = Microphone.recorder.record()
            
                cleft = data[:,0]
                rms=0
                for i in range(len(cleft)):
                    x = float(cleft[i])
                    rms += x**2  
                rms = int(np.sqrt(rms/len(cleft)))
                return rms
            except Exception:
                print("Microphone Exception ", sys.exc_info())
                traceback.print_exc(file=sys.stdout)
                
                Microphone.initialized = False #reinitialize the microphone (e.g. if default mic has changed)
                return 0
else:
    #import pyaudio
    import wave
    import audioop
    import numpy as np
    class Microphone():
        @staticmethod
        def getRMS(milliseconds = 100):
            # FORMAT = pyaudio.paInt16
            # CHANNELS = 1
            # RATE = 44100
            # CHUNK = 1024
            # milliseconds = milliseconds/1000
            # audio = pyaudio.PyAudio()

            # # start Recording
            # stream = audio.open(format=FORMAT, channels=CHANNELS,
            #                 rate=RATE, input=True,
            #                 frames_per_buffer=CHUNK)
            # data = stream.read(CHUNK*2)
            
            # rms = audioop.rms(data, 2)

            # # stop Recording
            # stream.stop_stream()
            # stream.close()
            # audio.terminate()

            rms = 0
            return rms
    

if __name__ == '__main__':    
    for i in range(100):
        x = Microphone.getRMS(milliseconds=50)
        print("Mic RMS=", x)
