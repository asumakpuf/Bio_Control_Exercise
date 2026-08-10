from __future__ import print_function
import serial, time, threading, traceback
import serial.tools.list_ports
import sys, glob, math
from threading import Thread, current_thread

from .ostime import OSTime
from serial.tools.list_ports_common import ListPortInfo
#from click.termui import pause
from .moduleState import ModuleState
from .DEFINES import ModuleTypes

class Statistics():
    dongleWakeup = 0
    dongleBytesDropped = 0
    radioPackagesSentOk = 0
    radioPackagesSentErr = 0
    radioPackagesReceiveOk = 0
    radioPackagesReceiveErr = 0
    def toString(self):
        statStr = "dongleWakeup ="+str(self.dongleWakeup)+"\n"
        statStr += "dongleBytesDropped ="+str(self.dongleBytesDropped)+"\n"
        statStr += "radioPackagesSentOk ="+str(self.radioPackagesSentOk)+"\n"
        statStr += "radioPackagesSentErr ="+str(self.radioPackagesSentErr)+"\n"
        statStr += "radioPackagesReceiveOk ="+str(self.radioPackagesReceiveOk)+"\n"
        statStr += "radioPackagesReceiveErr ="+str(self.radioPackagesReceiveErr)+"\n"
        return statStr



class Dongle():
    def __init__(self):
        self.ser = None
        self.stat = Statistics
        self.lock = threading.Lock()
        self.autoconnectThread = None
        pass

    def connect(self, portNr):
        self.lock.acquire()
        try:#actual BAUD rate on arduino 368 @8MHz => 8*10^6/(8*(8+1)) = 111111 (instead of 115200)
            time_out = 0.015
            if sys.platform == 'linux':
                portList = glob.glob ('/dev/tty[A-Za-z]*')
                print('Linux implementation - tested!')
                if type(portNr) is str:
                    port = portNr
                else:
                    port = portList[portNr]
                self.ser = serial.Serial(port, 500000, timeout = time_out, write_timeout = time_out)
                # FIX: It turns out that Linux-kernel sends some bytes every single time a usb2serial port is
                #      connected. One of this bytes is the char 'x' which make the DONGLE to enter to terminal-mode.
                #      In order to deal with this issue, it is necessary to exit from terminal-mode - that's what
                #      the next lines do...
                self.ser.write(bytes([0x65, 0]))
                self.ser.flush()
                self.ser.read(2)
            elif sys.platform == 'win32':
                self.ser = serial.Serial(portNr, 500000, timeout = time_out, write_timeout = time_out)
            elif sys.platform == 'cygwin':
                portList = glob.glob ('/dev/tty[A-Za-z]*')
                if type(portNr) is str:
                    port = portNr
                else:
                    port = portList[portNr]
                self.ser = serial.Serial(port, 500000, timeout = time_out, write_timeout = time_out)
            elif sys.platform == 'darwin':
                portList = glob.glob('/dev/tty.*')
                print('MAC implementation - tested!')
                if type(portNr) is str:
                    port = portNr
                else:
                    port = portList[portNr]
                self.ser = serial.Serial(port, 500000, timeout = time_out, write_timeout = time_out)

            #HERE is the PROBLEM WHEN TRYING TO LOAD THE MODULE
            res, state = ModuleState.load(self.ser)
            print("dongle connect: " +  str(res))
            if res:
                print(state['type'], end='')
                if not state['type'] == 'Dongle':
                    self.lock.release()
                    return False
            self.lock.release()
            return self.ping()
        except Exception: # serial.SerialException eller ValueError
            if not self.ser == None:
                self.ser.close()
            self.ser = None
            self.lock.release()
            print("Connection Exception ", sys.exc_info())
            return False

    class DongleConnectThread(threading.Thread):
        def __init__(self, dongle, period = 1):
            threading.Thread.__init__(self)
            self._dongle = dongle
            self._period = period
            self._connected = False
            self.pause = False

        def reconnect(self):
            self._connected = False

        def isConnected(self):
            return self._connected

        def setPause(self, pause):
            self.pause = pause

        def run(self):
            while True:
                try:
                    time.sleep(self._period)
                    if not self._connected and not self.pause:
                        if self._autoconnect():
                            self._connected = True

                except Exception:
                    print("Exception in autoconnect thread! ", traceback.print_exc())

        def _autoconnect(self):
            #print("Trying to autoconnect dongle")
            if self._dongle.ping() == True:
                print("Dongle already connected")
                return True

            self._dongle.close() # close open port if any
            ports = sorted(serial.tools.list_ports.comports())

            fableDevs = 0
            for port, name, hwid in ports:
                print('PORT: {}, NAME: {}, HWID: {}'.format(port, name, hwid))
                if ('VID:PID=03EB:FABE' in hwid) or ("Fable " in name):
                    fableDevs+=1
                    print("Trying to connect", port, "", end='')
                    res = self._dongle.connect(port)
                    if res == True:
                        if self._dongle.ping() == True:
                            print("...success")
                            return True
                    print("...failure")
                    self._dongle.close()
            if fableDevs == 0:
                print('Trying to connect - No devices found')
            return False

    def autoconnectStart(self):
        if self.autoconnectThread == None:
            self.autoconnectThread= self.DongleConnectThread(self, period = 1)
            self.autoconnectThread.setName('Dongle Connect Thread')
            self.autoconnectThread.daemon = True
            self.autoconnectThread.start()
        else:
            self.autoconnectThread.reconnect()

    def isConnected(self):
        if self.autoconnectThread == None:
            return False
        return self.autoconnectThread.isConnected()

    def pauseAutoConnect(self, pause):
        self.autoconnectThread.setPause(pause)

    def _isACK(self,reply):
        return (len(reply) != 0 and reply[0]==ord('A'))

    def _isSerialReady(self):
        if self.ser == None:
            return False
        try:
            self.ser.inWaiting()
            self.ser.write([])
            self.ser.read(size=0)
        except Exception:
            print("Dongle not ready! ", sys.exc_info())
            return False
        return True

    def wakeup(self):
        #if self.ser == None: return False
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.stat.dongleWakeup += 1
        for i in range(10):
            self.ser.write(bytes([0xff]))
        self.ser.flush()
        time.sleep(0.1)
        self.ser.read(self.ser.inWaiting())
        self.lock.release()
        return self.ping()

    def checkConnection(self, returnPing=True):
        if not self._isSerialReady():
            self.autoconnectStart()
            return False
        if returnPing:
            return self.ping()
        else:
            return True

    def getState(self, size):
        if not self._isSerialReady(): return False, None
        self.lock.acquire()
        if not self.ser.inWaiting() == 0:
            print("Dropping ", self.ser.inWaiting())
            self.ser.read(self.ser.inWaiting())
        try:
            self.ser.write(bytes([0xf8, size, 0]))
            self.ser.flush()
            reply = self.ser.read(size)
            self.lock.release()
            if len(reply) == size:
                return True, reply
        except serial.serialutil.SerialTimeoutException:
            print(" Write failure - resetting dongle2", current_thread())
            self.lock.release()
            self.close()
            self.checkConnection()
        return False, None

    def setState(self, data, index): # NOT SAFE/SECURE!!! HACKERS DELIGHT
        if not self._isSerialReady(): return False
        self.lock.acquire()
        if not self.ser.inWaiting() == 0:
            print("Dropping ", self.ser.inWaiting())
            self.ser.read(self.ser.inWaiting())
        try:
            buffer = []
            buffer.append(0xf9)
            buffer.append(0x0f)
            buffer.append(0xab)
            buffer.append(0x1e)
            buffer.append(len(data))
            buffer.append(index)
            for val in data:
                buffer.append(val)
            self.ser.write(bytes(buffer))
            self.ser.flush()
            reply = self.ser.read(1)
            self.lock.release()
            return self._isACK(reply)
        except serial.serialutil.SerialTimeoutException:
            print(" Write failure - resetting dongle3", current_thread())
            self.lock.release()
            self.close()
            self.checkConnection()
        return False

    def ping(self):
        if not self._isSerialReady():
            #print(' Dongle not ready')
            return False
        self.lock.acquire()
        if self.ser == None:
            self.lock.release()
            self.close()
            self.checkConnection()
            return False
        cTime = OSTime.getOSTime()
        try:
            if self.ser.inWaiting() != 0:
                print("Ping, throw away=", self.ser.read(self.ser.inWaiting()))
            self.ser.write(bytes([0xff]))
            self.ser.flush()
            reply = self.ser.read(1)
        except serial.serialutil.SerialTimeoutException:
            #print(" Write failure - resetting dongle4", current_thread())
            self.lock.release()
            self.close()
            self.checkConnection()
            return False
        except Exception:
            #print(" Ping  failure", current_thread())
            traceback.print_exc(file=sys.stdout)
            self.lock.release()
            self.close()
            self.checkConnection()
            return False
        lag = 1000*(OSTime.getOSTime()-cTime)
        if lag > 5:
            pass
            #print("Dongle seems slow (%s ms), change latency timer to 1 ms in devicemanager..." % int(lag))
        self.lock.release()
        return self._isACK(reply)

    def setLed(self,val):
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.ser.write(bytes([0xfb]))
        self.ser.write(bytes([val]))
        self.ser.flush()
        reply = self.ser.read(1)
        self.lock.release()
        return self._isACK(reply)

    def setRGBLed(self,r,g,b):
        cTime = OSTime.getOSTime()
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.ser.write(bytes([0xfa, r, g, b]))
        self.ser.flush()
        reply = self.ser.read(1)
        #print("rgb reply=", reply, "time = ",1000*(OSTime.getOSTime()-cTime))
        self.lock.release()
        return self._isACK(reply)

    def scanForModules(self):
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.ser.write(bytes([0xf4]))
        self.ser.flush()
        time.sleep(0.2)
        print("self.ser.inWaiting()=",self.ser.inWaiting())
        reply = self.ser.read(self.ser.inWaiting())
        print(reply)
        for x in reply:
            print(x)
        self.lock.release()

    def setDongleBuzzer(self, tone):
        if not self._isSerialReady(): return False
        tone = int(tone)
        b0 = int(tone & 0xff)
        b1 = int((tone >> 8) & 0xff)
        self.lock.acquire()
        self.ser.write(bytes([0xf9]))
        self.ser.write(bytes([b1]))
        self.ser.write(bytes([b0]))
        self.ser.flush()
        reply = self.ser.read(1)
        res = self._isACK(reply)
        self.lock.release()
        return res

    def getDongleTime(self):
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.ser.write(bytes([0xf8]))
        self.ser.flush()
        reply = self.ser.read(1)
        if (not self._isACK(reply)):
            self.lock.release()
            return -1
        b = self.ser.read(4)
        res = b[0] + (b[1]<<8) + (b[2]<<16) + (b[3]<<24)
        self.lock.release()
        return res

    def stopDongle(self):
        if not self._isSerialReady(): return False
        self.lock.acquire()
        self.ser.write(bytes([0xf7]))
        self.ser.flush()
        reply = self.ser.read(1)
        res = self._isACK(reply)
        self.lock.release()
        return res

#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

    def writeRadioPacket(self, data):
        if not self._isSerialReady(): return False
        self.lock.acquire()
        if not self.ser.inWaiting() == 0:
            self.stat.dongleBytesDropped += self.ser.inWaiting()
            print("Help!!!, throw away=", self.ser.read(self.ser.inWaiting()))
        buffer = []
        buffer.append(0xfe)
        buffer.append(len(data))
        for b in data:
            buffer.append(b)
        self.ser.write(bytes(buffer))
        self.ser.flush()
        reply = self.ser.read(1)
        success = self._isACK(reply)
        if (success):
            self.stat.radioPackagesSentOk += 1
        else:
            self.stat.radioPackagesSentErr += 1
            if not self.ser.inWaiting() == 0:
                self.stat.dongleBytesDropped += self.ser.inWaiting()
                data = self.ser.read(self.ser.inWaiting())
                print("Help!!!, throw away=", data)
                if len(data) != 0 and data[len(data) - 1] == ord('A'):
                    success = True
        self.lock.release()
        return success


#    def writeRadioPacket(self, data):
#        if not self._isSerialReady(): return False
#        self.lock.acquire()
#        if not self.ser.inWaiting() == 0:
#            self.stat.dongleBytesDropped += self.ser.inWaiting()
#            print("Warning: Data dropped before writing radio packet:", self.ser.read(self.ser.inWaiting()))
#        buffer = []
#        buffer.append(0xfe)
#        buffer.append(len(data))
#        for b in data:
#            buffer.append(b)
#        cTime = OSTime.getOSTime()
#        #print("writeRadioPacket data: ", [hex(i) for i in buffer])
#        try:
#            self.ser.write(bytes(buffer))
#            self.ser.flush()
#            reply = self.ser.read(1)
#        except serial.serialutil.SerialTimeoutException:
#            print(" Write failure - resetting dongle1", current_thread())
#            self.lock.release()
#            self.close()
#            self.checkConnection()
#            return False
#
#
#        #print("Reply= ", reply, "2 time ", (time.clock()-now)*1000)
#        success = self._isACK(reply)
#        if (success):
#            self.stat.radioPackagesSentOk +=1
#        else:
#            self.stat.radioPackagesSentErr +=1
#            #print('While writing radio packet, reply not A?', reply, 'inWaiting=', self.ser.inWaiting())
#            if reply == ord('#'): #if got another packet during write, then try to clean it up
#                if self.ser.inWaiting() > 0:
#                    try:
#                        length = self.ser.read(1)
#                        if self.ser.inWaiting() >= length:
#                            self.ser.read(length) #throw away packet
#                            res = self.ser.read(1)
#                            if res == True:
#                                success = True #the write radio packet was send
#                    except serial.serialutil.SerialTimeoutException:
#                        pass
#
#            #if not self.ser.inWaiting() == 0:
#            #    self.stat.dongleBytesDropped += self.ser.inWaiting()
#            #    data = self.ser.read(self.ser.inWaiting())
#            #    print("Warning: Data dropped after writing radio packet:", data)
#            #    if len(data)!=0 and data[len(data)-1]==ord('A'):
#            #        success = True
#        self.lock.release()
#        return success


#######################################################################################################
#######################################################################################################
#######################################################################################################
#######################################################################################################

    def readPacket(self, nBytes, nTimeout=1):
        if not self._isSerialReady():
            return
        self.lock.acquire()
        for _ in range(nTimeout):
            packet = self.ser.read(nBytes)
            if len(packet) == nBytes: break

        if len(packet) == nBytes:
            self.stat.radioPackagesReceiveOk +=1
        else:
            self.stat.radioPackagesReceiveErr +=1
        self.lock.release()
        return packet

    def close(self):
        if self.ser == None: return
        self.lock.acquire()
        if self.ser == None: return
        self.ser.close()
        self.ser = None
        self.lock.release()

    def getStatistics(self):
        return self.stat
