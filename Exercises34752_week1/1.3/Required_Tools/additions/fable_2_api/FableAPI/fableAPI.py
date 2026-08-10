import time
import sys, os
import math
import threading
import random
import psutil

from .moduleXMLHandler import ModuleXMLHandler
from .dongle import Dongle
from .sound import FableSound,FableBeep
from .microphone import Microphone
from .ostime import OSTime
from .dongleManager import DongleManager
from .jointManager import JointManager
from .faceManager import FaceManager
from .spinManager import SpinManager
from .firmwareUpdater import FirmwareUpdate
from .tools import Tools
from .runtime import FableRuntime
from .DEFINES import ControlState, Keys, ModuleTypes
from .moduleState import JointState, ModuleState, FaceState, SpinState

class FableAPI(): 
    state = ControlState.terminated
    crashReason = ''
    keys = []
    threadStop = []
    modID = 0
    logfile = None
    moduleInfo = []
    printData = ['<br><br/>']
    def __init__(self):
        self.dongle = Dongle()
        self.rtplot = None
        self.replyCache = dict()
        self.plotSeries = dict()
        self.dongleStatus = "Unknown"
        self.startup()
        self.timeOffset = 0
        self.moduleID = 0
        self.lock = threading.Lock()
        self.soundPlayer = None
        self.beepPlayers = [None]*10
        self.mic = Microphone()
        self.dongleManager = DongleManager(self, self.dongle)
        self.runtime = FableRuntime(self.dongle, self)
        self.runtime.daemon = True
        self.runtime.start()
        self.BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.SOUND_DIR = os.path.join(self.BASE_DIR, 'sounds')
        self.USER_DIR = os.path.expanduser('~')
        if sys.platform == 'win32':
            self.APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'Fable')
        else:
            self.APPDATA_DIR = os.path.join(self.USER_DIR, 'Fable')
        os.makedirs(self.APPDATA_DIR, exist_ok=True)
        self.DESKTOP_DIR = os.path.join(self.USER_DIR, 'Desktop')
        self.xmlHandler = ModuleXMLHandler(os.path.join(self.APPDATA_DIR, 'myModules.xml'))
        pass

    def testFunc(self):
        return "string from within FableAPI"

    @property
    def moduleID(self):
        return self.__moduleID

    @moduleID.setter
    def moduleID(self, ID):
        self.__moduleID = ID
        self.modID = ID
        return self.__moduleID

    @staticmethod
    def setControlState(newState):
        FableAPI.state = newState

    @staticmethod
    def getControlState():
        return FableAPI.state

    @staticmethod
    def getControlStatus():
        if FableAPI.state == ControlState.running:
            return "Running"
        elif FableAPI.state == ControlState.paused:
            return "Paused"
        elif FableAPI.state == ControlState.stopped:
            return "Stopping"
        elif FableAPI.state == ControlState.terminated:
            return "Stopped"
        elif FableAPI.state == ControlState.crashed:
            return "Crashed"
        return ""

    @staticmethod
    def getCrashReason():
        return FableAPI.crashReason

    @staticmethod
    def setCrashReason(reason):
        FableAPI.crashReason = reason

    @staticmethod
    def stopThread(name):
        if not name in FableAPI.threadStop:
            FableAPI.threadStop.append(name)

    @staticmethod
    def keyDownEvent(keyValue):
        keyValue = int(keyValue)
        if FableAPI.keys.count(keyValue) == 0:
            FableAPI.keys.append(keyValue)
        #print("Keys Pressed: ", FableAPI.keys)

    @staticmethod
    def keyUpEvent(keyValue):
        keyValue = int(keyValue)
        if FableAPI.keys.count(keyValue) > 0:
            FableAPI.keys.remove(keyValue)
        #print("Keys Pressed: ", FableAPI.keys)

    def updateModuleInfoList(self):
        #print("Searching for modules")
        modulesFound = dict()
        delayMs = 100
        self._genericModuleSetMethod([255, 255, 239, delayMs], ack=False) # random delayed ping id
        cTime = OSTime.getOSTime()
        while (delayMs+10) > 1000*(OSTime.getOSTime()-cTime):
            packet = self.dongle.readPacket(5)
            if packet != None and len(packet)==5:
                if packet[0] == ord('#') and packet[1] == 3 and packet[4] == ord('A'):
                    mType = packet[2]
                    mID = packet[3]
                    self.sawModule(mType, mID)
                    modulesFound[ModuleTypes.toString(mType)+str(mID)] = [mType, mID]
        #           print(" found module id=", mID, "of type",ModuleTypes.toString(mType), "delay=", 1000*(time.clock()-cTime), "ms ")

        newModuleInfo = []
        for mkey in modulesFound:
            mType = modulesFound[mkey][0]
            mID = modulesFound[mkey][1]
            batLevel = self.getModuleBatteryLevel(mID)
            batLevel = round(batLevel,0)
            quality = self.getConnectionQuality(mID)
            status = self.getStatus(mID)
            statusStr = ''


            #newModuleInfo.append([mID, mType, ModuleTypes.toString(mType), str(batLevel), str(quality)])
            newModuleInfo.append([mID, mType, ModuleTypes.toString(mType), str(batLevel), statusStr])

        for m1 in self.moduleInfo:
            found = False
            for m2 in newModuleInfo:
                if (m1[0] == m2[0]) and (m1[1] == m2[1]):
                    found = True
            if not found: #m1 has disappeared
                print("Module ", m1[0],ModuleTypes.toString(m1[1]), " has disappeared")
                #if self.pingModule(m1[0], moduleType=m1[1]): #really gone?
                #    batLevel = self.getModuleBatteryLevel(m1[0])
                #    newModuleInfo.append([m1[0], m1[1], ModuleTypes.toString(m1[1]), str(round(batLevel,3))])
                #else:
                #    print("Module ", m1[0],ModuleTypes.toString(m1[1]), " has disappeared")

        self.moduleInfo = newModuleInfo
        self.moduleInfo.sort()

    def getModuleList(self):
        newModuleInfo = []
        for sID in self.runtime.getActiveModuleIDs():
            mType = self.getModuleType(sID)
            if mType == ModuleTypes.JOINT:
                batLevel = str(round(self.getBattery(sID), 0))+'%'
                quality = round(self.getConnectionQuality(sID), 0)
                status = self.getStatus(sID)
                statusStr = ''
                if status == JointState.STATUS_BOOT:
                    statusStr = 'Resetting'
                    batLevel = '-'
                elif status == JointState.STATUS_READY:
                    statusStr = 'Ready'
                    if quality < 50:
                        statusStr = 'Poor Radio'
                elif status == JointState.STATUS_LOAD_ERROR:
                    statusStr = 'Overload 1'
                elif status == JointState.STATUS_DIST_ERROR:
                    statusStr = 'Overload 2'
                elif status == JointState.STATUS_LOW_BATTERY:
                    statusStr = 'Low Battery'
                elif status == JointState.STATUS_RUNNING:
                    statusStr = 'Running'
                elif status == JointState.STATUS_LOCKED:
                    statusStr = 'Locked'
                    batLevel = '-'
                newModuleInfo.append([sID, mType, ModuleTypes.toString(mType), str(batLevel), statusStr])
            elif mType == ModuleTypes.FACE:
                batLevel = "" #str(round(self.getBattery(sID), 0))+'%'
                quality = 100 # round(self.getConnectionQuality(sID), 0)
                status = FaceState.STATUS_READY # self.getStatus(sID)
                statusStr = ''
                if status == FaceState.STATUS_READY:
                    statusStr = 'Ready'
                    if quality < 50:
                        statusStr = 'Poor Radio'
                elif status == FaceState.STATUS_RUNNING:
                    statusStr = 'Running'
                newModuleInfo.append(["", mType, ModuleTypes.toString(mType), str(batLevel), statusStr])
            else:
                print("Module type ", mType, " not supported.")
            self.sawModule(mType, sID)
        self.moduleInfo = newModuleInfo
        return self.moduleInfo

    def getModuleIDs(self):
        return self.runtime.getActiveModuleIDs()

    def sawModule(self, mType, mID):
        self.xmlHandler.seenModule(str(mID), ModuleTypes.toString(mType))
        #self.runtime.seenModule(mID, mType)

    def clearModulesList(self):
        for module in self.xmlHandler.getAllModulesSeen():
            moduleID = module[0]
            moduleType = module[1]
            self.xmlHandler.removeModule(moduleID, moduleType)
        self.xmlHandler.saveModules()

    def getRescentModuleList(self, n=100, moduleTypes = ["any"]):
        return self.xmlHandler.getResentModules(n, moduleTypes)

    def updateDongleStatus(self):
        if self.checkDongleConnection():
            self.dongleStatus ="OK"
        else:
            self.dongleStatus ="Not Connected"

    def getDongleStatus(self):
        if self.dongleStatus == "OK":
            if self.dongle.checkConnection(returnPing=False):
                return self.dongleStatus
        self.updateDongleStatus()
        return self.dongleStatus

    def isCurrentThreadTerminated(self):
        return threading.current_thread().getName() in FableAPI.threadStop

    def bootstrap(self):
        time.sleep(0.001) #yield thread for 1 ms bad idea?
        if not threading.current_thread().getName() is 'CodeThread': return
        if self.isCurrentThreadTerminated():
            print("Stop this thread! ", threading.current_thread().getName())
            FableAPI.threadStop.remove(threading.current_thread().getName())
            raise Exception('Thread Terminated','')
        if FableAPI.state == ControlState.running:
            return
        if FableAPI.state == ControlState.paused:
            print("Sleeping")
            sleepTime = OSTime.getOSTime()
            while FableAPI.state == ControlState.paused:
                time.sleep(0.1)
            self.startTime = self.startTime + (OSTime.getOSTime() - sleepTime)
            print("waken up!")
        if FableAPI.state == ControlState.stopped:
            print("Terminating now ", threading.current_thread().getName() )
            self.terminate()
            print("Bye bye")
            sys.exit(0)

    def terminate(self):
        if not self.logfile == None:
            self.logfile.close()
            self.logfile = None
        if not self.rtplot == None:
            self.rtplot.reset()
            #self.rtplot = None
        if self.beepPlayers != [None]*10:
            for beepPlayer in self.beepPlayers:
                beepPlayer.stop()
                beepPlayer.join()
        if self.soundPlayer != None:
            self.soundPlayer.stop()
            self.soundPlayer.join()
        self.plotSeries = dict()
        self.runtime.terminate()
        #self.dongle.writeRadioPacket([255, 255, 246]) #stop all modules in this channel - bad if more groups on same channel
        self.dongle.stopDongle()
        FableAPI.state = ControlState.terminated

    def startup(self):
        self.startTime = OSTime.getOSTime()
        self.printData = ['<br><br/>']

    def handleResult(self, res):
        if res == False:
            self.dongle.autoconnectStart()

    def setup(self, defaultPort= None, blocking=False):
        if defaultPort!= None and self.dongle.connect(defaultPort):
            print("Connected to dongle on port = ", defaultPort)
            return True
        self.dongle.autoconnectStart()
        while blocking and not self.dongle.isConnected():
            self.sleep(0.1)
        print("setup done")
        return True

    def writeRadioPacket(self,packet):
        res = self.dongle.writeRadioPacket(packet)
        self.bootstrap()
        self.handleResult(res)
        return res

    def pyplot(self, data):
        self.bootstrap()
        from realTimePlot import RealTimePlot
        if self.rtplot == None: # or not self.rtplot.isAlive():
            self.rtplot = RealTimePlot()
            self.rtplot.start()
            while not self.rtplot.isReady():
                time.sleep(0.001)
            self.rtplot.setAxesLabels("x","y")
        if self.rtplot.isAlive():
            self.rtplot.appendY(data, 100)
        else:
            print("Warning: Plot is not alive...")

    def _findOptimalPlotIndex(self, data):
        deltaT= []
        for i in range(1, len(data)):
            deltaT.append(data[i][0]-data[i-1][0])
        minDeltaT = min(deltaT)
        index = deltaT.index(minDeltaT)+1
        return index


    def plotDataAppend(self, data, label='1', windowSize = 50, windowTime = 2.5):
        self.bootstrap()
        if not type(data) in [int, float]: return
        if not label in self.plotSeries:
            self.plotSeries[label] = []
        self.plotSeries[label].append([self.getTime(),round(data,3)])
        if len(self.plotSeries[label]) > windowSize:
            if (self.plotSeries[label][-1][0]-self.plotSeries[label][0][0]) > windowTime:
                del self.plotSeries[label][0]
            if len(self.plotSeries[label]) > windowSize:
                index = self._findOptimalPlotIndex(self.plotSeries[label])
                del self.plotSeries[label][index]

    def plotDataGet(self, label='1',doBootstrap=True):
        if doBootstrap: self.bootstrap()
        if not label in self.plotSeries:
            return []
        return self.plotSeries[label]

    def getPrintData(self):
        data =''
        for line in self.printData:
            data+=line
        if FableAPI.state == ControlState.crashed:
            data='Error in code: <br><br/>'
            data+=FableAPI.getCrashReason()

        return str(data)

    def getStatistics(self):
        return self.dongle.getStatistics()

    def speedLoadConvert(self, value):
        if value > 1023: #CW direction
            value = value - 1023
            sign = 1
        else:
            sign = -1
        return Tools.crop(-100, 100, sign*value/10.23)

    def _genericModuleSetMethod(self, radioPacket, ack = True, nTimeout = 1):
        startTime = OSTime.getOSTime()
        self.bootstrap()
        self.lock.acquire()
        res = self.dongle.writeRadioPacket(radioPacket)
        self.handleResult(res)
        if res == False:
            self.lock.release()
            return False
        if ack:
            packet = self.dongle.readPacket(5, nTimeout)
            self.lock.release()
            if not len(packet) == 5:
                return False
            if packet[0] != ord('#'):
                return False
            if packet[1] != 3:
                return False
            if packet[4] != ord('A'):
                return False
            senderType = packet[2]
            senderID = packet[3]
            self.sawModule(senderType, senderID)
            return True;
        else:
            #deltaTime = OSTime.getOSTime()-startTime
            #print("deltaTime =", 1000*deltaTime)
            self.lock.release()
            return True

    def _genericModuleGetMethod(self, radioPacket, nBytesReturn, nTimeout= 1):
        self.bootstrap()
        self.lock.acquire()
        res = self.dongle.writeRadioPacket(radioPacket)
        self.handleResult(res)
        if res == False:
            self.lock.release()
            print("Error: Write")
            return []
        packet = self.dongle.readPacket(nBytesReturn+4, nTimeout)
        if not len(packet) == (nBytesReturn+4):
            print("Error: Read 1 len=", len(packet))
            self.lock.release()
            return []
        if not  packet[0] == ord('#'):
            print("Error: Read 2")
            self.lock.release()
            return []
        self.lock.release()
        #TODO: check if packet is from correct Module
       # print(packet, "===> ", packet[4:nBytesReturn+4])
        return packet[4:nBytesReturn+4]

    def _genericModuleGetInt16Method(self, radioPacket, signed = False, nTimeout= 1):
        res = self._genericModuleGetMethod(radioPacket, 2, nTimeout)
        #print(res)
        #print(str(int(res[0])), str(int(res[1])))
        if not len(res) == 2:
            return [False, 0] # return something else here?
        return [True, Tools.toInt16(res[0], res[1], signed)]

    def _genericModuleGetInt32Method(self, radioPacket, signed = False, nTimeout= 1):
        res = self._genericModuleGetMethod(radioPacket, 4, nTimeout)
        if not len(res) == 4:
            return [False, 0] # return something else here?
        return [True, Tools.toInt32(res[0], res[1], res[2], res[3], signed)]

    def _genericModuleGetArrayMethod(self, radioPacket, nValues, signed = False, nTimeout= 1):
        res = self._genericModuleGetMethod(radioPacket, nValues, nTimeout)
        if not len(res) == nValues:
            return [False, 0] # return something else here?
        value = [True, res]
        return value

    def _getModuleIntValue(self, packet, limits, default, nBits, useCache = True, signed = False, nTimeout= 1):
        #TODO: experiment with different cache models: e.g. linear fit, bootstrapped, etc.
        if nBits == 16:
            [success, value] = self._genericModuleGetInt16Method(packet, signed, nTimeout)
        elif nBits == 32:
            [success, value] = self._genericModuleGetInt32Method(packet, signed, nTimeout)
        else:
            raise ValueError("Only 16 and 32 bits can be used!")
        key = str(packet)
        error = False
        if not success:
            #print("Communication Error")
            error = True
        elif value > limits[1] or value < limits[0]:
            #print("Out of Range Error value =", value)
            error = True

        if error:
            if key in self.replyCache and useCache:
                #print("using cache ",value, "=>", self.replyCache[key])
                value = self.replyCache[key]
            else:
                value = default
        else:
            self.replyCache[key] = value
        return value

    def getModuleSID(self, radioID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID)
        return m.getSID()


    def discoverModules(self):
        #print("discover modules!")
        if not self.dongle.isConnected(): return
        #self.dongleManager.syncState()
        delayMs = 25
        self._genericModuleSetMethod([255, 255, 238, delayMs], ack=False) # random delayed ping id
        cTime = OSTime.getOSTime()
        found = 0
        while (delayMs+100) > 1000*(OSTime.getOSTime()-cTime):
            packet = self.dongle.readPacket(10)
            if packet != None and len(packet)==10:
                #print([hex(i) for i in packet])
                #print('dt=',1000*(OSTime.getOSTime()-cTime),'ms')
                #print("got packet", packet[5], packet[5] == 238, 'from', chr(packet[6]) + chr(packet[7]) + chr(packet[8]) + chr(packet[9]))
                found+=1
                #NOTE packet format: 0: packet begin char, 1: , 4: , 5:
                if packet[0] == ord('#') and packet[1] == 8 and packet[4] == ord('A') and packet[5] == 238:
                    moduleType = packet[2] #
                    radioID = packet[3] #
                    #print('type', moduleType,' radioID', radioID)
                    serialID = chr(packet[6]) + chr(packet[7]) + chr(packet[8]) + chr(packet[9]) #
                    self.runtime.seenModule(serialID, moduleType, radioID)
                    #print(" found module sID=",serialID," rID=", radioID, "of type",ModuleTypes.toString(moduleType), "delay=", 1000*(time.clock()-cTime), "ms ")
            elif packet != None:
                pass
                #print("got wrong packet")
                #print([hex(i) for i in packet])
        #print('found = ', found)
        return self.getModuleIDs()

    def sleep(self, wtime):
        while True:
            self.bootstrap()
            if wtime < 0.1:
                time.sleep(wtime)
                return
            else:
                time.sleep(0.1)
                wtime -= 0.1

    def getMicrophoneRMS(self, millisecondes = 50):
        from .microphone import Microphone as mic
        return mic.getRMS(millisecondes)

    def pingModule(self, moduleID):
        return self._genericModuleSetMethod([255, moduleID, 255])

    def getConnectionQuality(self, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID)
        quality = m.getConnectionQuality()
        return quality

    def getStatus(self, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID)
        status = m.getStatus()
        return status

    def pingDongle(self):
        self.bootstrap()
        return self.dongle.ping()

    def checkDongleConnection(self):
        self.bootstrap()
        return self.dongle.checkConnection()

    def measureDonglePingLag(self):
        self.bootstrap()
        cTime = OSTime.getOSTime()
        n = 100
        for _ in range(n):
            self.pingDongle()
        return 1000*(OSTime.getOSTime() - cTime)/n

    def getDongleTime(self):
        self.bootstrap()
        return self.dongle.getDongleTime()

#################################################################################################
#                                FABLE API FUNCITONS                                            #
#################################################################################################

    def speak(self, phrase, laungage= 'en', pitch = 1.4):
        self.bootstrap()
        from speak import Speak
        print("speaking now")
        Speak.speak(phrase, laungage, pitch)

    def getSoundLevel(self, millisecondes = 50):
        self.bootstrap()
        micVal = self.getMicrophoneRMS(millisecondes) #TODO: make it non blocking
        if micVal > 20000:
            micVal = 20000
        return micVal/200

    def playBeep(self, frequency, duration, channel):
        self.bootstrap()
        if channel < 10 and channel >= 0:
            beepPlayer = FableBeep(frequency, duration)
            self.beepPlayers[channel] = beepPlayer
            beepPlayer.start()
        else:
            print("Channel ", channel, " invalid.")

    def plot(self, data, label, windowSize = 50, windowTime = 2.5):
        self.bootstrap()
        self.plotDataAppend(data, label, windowSize, windowTime)

    def isPressed(self, keyType):
        self.bootstrap()
        return FableAPI.keys.count(keyType) > 0

    def playSound(self, filename):
        self.bootstrap()
        filename = os.path.join(self.SOUND_DIR, filename)
        if os.path.exists(filename):
            self.bootstrap()
            if self.soundPlayer != None:
                self.soundPlayer.stop()
                self.soundPlayer.join()
            self.soundPlayer = FableSound(filename)
            self.soundPlayer.start()
        else:
            print(filename + ' does not exist!')

    def getTime(self):
        self.bootstrap()
        return OSTime.getOSTime() - self.startTime

    def wait(self, wtime):
        self.sleep(wtime)

    def output(self, *args):
        self.bootstrap()
        string =''
        for data in args:
            string += str(data) + ' '
        string += '<br><br/>'
        self.printData.append(string)
        nLines = len(self.printData)
        if nLines > 100: #TODO: this function is a hack coupled closely to the GUI, clean it up!
            self.printData = self.printData[nLines-100:]

    def log(self, data, filename = 'log.csv'):
        self.bootstrap()
        if data == None: return
        if self.logfile == None:
            try:
                self.logfile = open(os.path.join(self.DESKTOP_DIR, filename), 'w')
                self.logfile.write('sep=;\n')
            except: #In some international cases Desktop is called someting different
                print(sys.exc_info()[0])
                self.logfile = open(os.path.join(self.USER_DIR, filename), 'w')
                self.logfile.write('sep=;\n')
                return

        if type(data) is list:
            lineData = data
        else:
            lineData= [data]
        for element in lineData:
            if type(element) is float:
                self.logfile.write(str(round(element,3)).replace(".", ",")+'; ')
            else:
                self.logfile.write(str(element)+';')
        self.logfile.write('\n')
        self.logfile.flush()

    def setName(self, name, moduleID):
        data = [ModuleTypes.ANY, moduleID, 252] # use sync state command
        charName = [ord(c) for c in name]
        if len(charName) > 10:
            charName = charName[0:10]
        charName = charName + (10-len(charName))*[0]
        for i in range(len(charName)):
            data.append(14+i) # for reading: 0x80|(14+i)
            data.append(charName[i])
        return self._genericModuleSetMethod(data)

    def getName(self, moduleID):
        return "NULL"

    def setColor(self, color, moduleID):
        self.bootstrap()
        r = math.floor(color[0]/8)
        g = math.floor(color[1]/8)
        b = math.floor(color[2]/8)
        if moduleID is 'Dongle':
            res = self.dongleManager.setColorRGB(r,g,b) #TODO: Not thread safe
            self.handleResult(res)
            return res
        else:
            m = self.runtime.getModule(moduleID)
            return m.setRGBLed(r,g,b)

    def getModuleType(self, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID)
        return m.getType()

    def getBattery(self, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID)
        batteryLevel = m.getBatteryLevel()
        if m.getType() == ModuleTypes.JOINT:
            if batteryLevel>4000: return 100 #longer life if limited to 4150 (see http://batteryuniversity.com/learn/article/how_to_prolong_lithium_based_batteries)
            if batteryLevel<3500: return 0
            batteryLevel = 100*(batteryLevel-3500)/(4000-3500)
        elif m.getType() == ModuleTypes.FACE:
            batteryLevel = batteryLevel*100
        return batteryLevel


#methods for joint modules
    def setPos(self, posX, posY, moduleID): # 0 - 100 percent speed is set on all motors
        self.bootstrap()
        res, posX, posY = Tools.toFiniteFloats(posX, posY)
        if not res: return False
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        res = m.setPos(posX, 0)
        res = m.setPos(posY, 1) and res
        return res

    def setSpeed(self, speedX, speedY, moduleID): # 0 - 100 percent speed is set on all motors
        self.bootstrap()
        res, speedX, speedY = Tools.toFiniteFloats(speedX, speedY)
        if not res: return False
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        res = m.setSpeed(speedX, 0)
        res = m.setSpeed(speedY, 1) and res
        return res

    def setTorque(self, torqueX, torqueY, moduleID):
        self.bootstrap()
        res, torqueX, torqueY = Tools.toFiniteFloats(torqueX, torqueY)
        if not res: return False
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        res = True
        if torqueX != 0:
            res = m.setTorqueLimit(abs(torqueX), 0) and res
            res = m.setPos(90*Tools.sign(torqueX), 0) and res
        else:
            res = m.setTorqueLimit(abs(torqueX), 0) and res  
        if torqueY != 0:
            res = m.setTorqueLimit(abs(torqueY), 1) and res
            res = m.setPos(90*Tools.sign(torqueY), 1) and res
        else:
            res = m.setTorqueLimit(abs(torqueY), 1) and res
        return res

    def setAccurate(self, accurateX, accurateY, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        marginX, marginY, slopeX, slopeY, punchX, punchY = 1, 1, 128, 128, 32, 32
        if accurateX == 'HIGH': marginX, slopeX, punchX = 0, 64, 64
        if accurateY == 'HIGH': marginY, slopeY, punchY = 0, 64, 64
        res = m.setComplianceMargin(marginX, 1, 0)
        res = m.setComplianceMargin(marginX, -1, 0) and res
        res = m.setComplianceSlope(slopeX, 1, 0)    and res
        res = m.setComplianceSlope(slopeX, -1, 0)   and res
        res = m.setPunch(punchX, 0)                 and res
        res = m.setComplianceMargin(marginY, 1, 1)  and res
        res = m.setComplianceMargin(marginY, -1, 1) and res
        res = m.setComplianceSlope(slopeY, 1, 1)    and res
        res = m.setComplianceSlope(slopeY, -1, 1)   and res
        res = m.setPunch(punchY, 1)                 and res
        return res

    def getPos(self, motorID, moduleID): #return -90 to 90 degrees for joint
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        pos = m.getPos(motorID)
        degrees = Tools.crop(-90, 90, (150.0*(pos-512.0))/512.0, returnType=float)
        return degrees

    def getSpeed(self, motorID, moduleID): #return -100 to 100 in percent
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        speed = m.getSpeed(motorID)
        return self.speedLoadConvert(speed)

    def getTorque(self, motorID, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        load = m.getLoad(motorID)
        return self.speedLoadConvert(load)

    def getMoving(self, motorID, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        moving = m.getMoving(motorID)
        return moving == 1

    def getVoltage(self, motorID, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        voltage = m.getVoltage(motorID)
        return voltage

    def getTemperature(self, motorID, moduleID):
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.JOINT)
        termperature = m.getTemperature(motorID)
        return termperature

# methods for Face module
    def setFaceEmotion(self, emotion):
        """Set the emotional state in the Face.

        Args:
            emotion(str,int): Emotional state, e.g. ``Happy`` or `1`.

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        res = m.setFaceEmotion(emotion)
        return res

    def setFaceFocus(self, focusX, focusY, focusZ):
        """Set the focus point, i.e where the eyes of the Face are looking.

        Args:
            focusX(float): Distance in meters.
            focusY(float): Distance in meters.
            focusZ(float): Distance in meters.

        Note:
            Coordinate base defined as follows::

                +--------------------------+
                |   +------------------+   |
                |   |         Z        |   |
                | O |         |        | | |
                |   |        X·-- Y    |   |
                |   +------------------+   |
                +--------------------------+

            In which origo is in the screen center, that is (width/2, height/2).
            X is the distance orthogonal to the screen surface.
            Y is the distance along the screen 'height' (portrait mode).
            Z is the distance along the screen 'width' (portrait mode).

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        res = m.setFaceFocus(focusX, 'X')
        res = m.setFaceFocus(focusY, 'Y') and res
        res = m.setFaceFocus(focusZ, 'Z') and res
        return res

    def getFaceEmotion(self):
        """Get the emotional state of the Face.

        Returns:
            int: Emotional state, e.g. ``1``.

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        emotion = m.getFaceEmotion()
        return emotion

    def getFaceFocus(self, direction):
        """Get the focus point of the Face (where the eyes are looking).

        Args:
            direction(str):

        Returns:
            float: Distance in meters in given direction.

        Note:
            Coordinate base defined as follows::

                +--------------------------+
                |   +------------------+   |
                |   |         Z        |   |
                | O |         |        | | |
                |   |        X·-- Y    |   |
                |   +------------------+   |
                +--------------------------+

            In which origo is in the screen center, that is (width/2, height/2).
            X is the distance orthogonal to the screen surface.
            Y is the distance along the screen 'height' (portrait mode).
            Z is the distance along the screen 'width' (portrait mode).

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        dist = m.getFaceFocus(direction)
        return dist

    def getFaceOrientation(self):
        """Get the orientation of the Face device.

        Interfaces directly with the Unity `DeviceOrientation<https://docs.unity3d.com/ScriptReference/DeviceOrientation.html>`_

        Note:
            Possible return values are
                * Unknown
                * Portrait
                * PortraitUpsideDown
                * LandscapeLeft
                * LandscapeRight
                * FaceUp
                * FaceDown

        Returns:
            str: Orientation e.g. ``'FaceUp'``.

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        ori = m.getFaceOrientation()
        return ori

    def getFaceCompass(self):
        """Get the heading direction of the Face device.

        Interfaces directly with the Unity `Compass.magneticHeading<https://docs.unity3d.com/ScriptReference/Compass-magneticHeading.html>`_

        Returns:
            float: Heading in degrees e.g. `247.6`.

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        heading = m.getFaceCompass()
        return heading

    def getFaceAcceleration(self, direction):
        """Get the acceleration X, Y or Z of the device (face).

        Interfaces directly with the Unity `Input.acceleration<https://docs.unity3d.com/ScriptReference/Input-acceleration.html>`_

        Args:
            direction(str,int): Valid directions are 'X', 'Y' or 'Z'.

        Returns:
            float: Acceleration in meters per second e.g. `5.124`.

        """
        self.bootstrap()
        m = self.runtime.getModule('FACE', ModuleTypes.FACE)
        acc = m.getFaceAcceleration(direction)
        return acc

#################################################################################################################################
#                                                  FABLE SPIN MODULE FUNCTIONS                                                  #
#################################################################################################################################
    def spinResetEncoder(self, motorID, moduleID):
        """Resets the enconder of a motor on the Spin module.

        :param str motorID: ID of the motor to target. Either 'A' or 'B'.
        :param str moduleID: ID of the targeted Spin.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)

        if motorID in ['BOTH', 'both']:
            m.resetEncoder('A')
            m.resetEncoder('B')
        else:                
            m.resetEncoder(motorID)


    def setSpinSpeed(self, speedA, speedB, moduleID):
        """Sets the speed on the two motors of a specified Spin module.

        The speed values must be a percentage (between 0 and 100). Any values outside
        the boundary is discarded.
        
        :param float speedA: Percent representing the speed on motor A.
        :param float speedB: Percent representing the speed on motor A.
        :param str moduleID: ID of the target Spin.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        
        m.relaxLifting(0)
        m.relaxLifting(1)

        res = m.setSpeed(speedA, 0)
        res = m.setSpeed(speedB, 1) and res
        return res


    def setSpinStopPos(self, stopPosA, stopPosB, moduleID):
        """__PRIVATE__
        Sets the stop position of a specified motor on the Spin module.

        :param float stopPosA: 
        :param float stopPosB:
        :param str moduleID: ID of the target Spin.
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.setStopPos(stopPosA, 0)
        res = m.setStopPos(stopPosB, 1) and res
        return res
    
    
    def setSpinMotorRotation(self, posA, posB, moduleID): #  degrees angle is set on all motors
        """__PRIVATE__
        Sets angular rotation of a specified connector (motor) on the Spin module.
        
        :param float posA: Angle, in degrees, to move on connector A.
        :param float posB: Angle, in degrees, to move on connector B.
        :param str moduleID: ID of the target Spin.
        :returns: None
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.setPos(posA, 0)
        res = m.setPos(posB, 1) and res
        return res

    
    def setSpinDriveDistance(self, distance, radius, moduleID):
        """__PRIVATE__
        Makes the Spin module drive a certain distance depending the spin radius.

        :param float distance: Distance to drive in a straight line in meters.
        :param float radius: Spin radius needed to calculate angles to turn, in centimeter.
        :param str moduleID: ID of the target Spin.
        :returns: None
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        rotations = int(distance/(radius/100)*180/math.pi*2)
        res = m.setPos(-rotations, 0)
        res = m.setPos(rotations, 1) and res
        return res

    
    def setSpinHeadlight(self, mode, moduleID, intensity = 0):
        """__PRIVATE__
        Changes the flashlight intensity on a Spin module.
        
        :param str mode: Whether the lights should turn ``on``, ``off``, ``toggle`` or set to a ``percentage``.
        :param float intensity: Intensity value of flashlight, between 0 and 100.
        :param str moduleID: ID of the target Spin.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)

        if (mode == 'on'):
            intensity = 50
        elif (mode == 'off'):
            intensity = 0
        elif (mode == 'toggle'):
            current = m.getHeadlight()
            if (current > 0):
                intensity = 0
            else:
                intensity = 50

        res = m.setHeadlight(intensity)
        return res

    
    def setSpinIrMsg(self, message, moduleID):
        """Sends predefined messages via infrared communication from a Spin module.

        Use together with api.getSpinIrMsg on a different Spin module.

        :param int message: Number between 0 and 255 that will be sent via infrared.
        :param str moduleID: ID of the target Spin.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        m.setIrMessage(message)

    
    def getSpinIrMsg(self, moduleID):
        """Reads the most recent received IR message on the Spin module.

        Use together with api.setSpinIrMsg on a different Spin module.

        :param str moduleID: ID of the target Spin.
        :returns: The last received infrared message on the targetted Spin.
        :rtype: int
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getIrRecentMessage()

    
    def getSpinMotorAngle(self, motorID, moduleID): 
        """Reads the angle of a specified motor from the Spin module.
        
        :param str motorID: ID of the motor to target. Either 'A' or 'B'.
        :param str moduleID: ID of the target Spin.
        :returns: Relative angle in degrees.
        :rtype: float
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getAngle(motorID)

    
    def getSpinMotorSpeed(self, motorID, moduleID): 
        """Reads the speed of a specified motor from the Spin module.
        
        :param str motorID: ID of the motor to target. Either 'A' or 'B'.
        :param str moduleID: ID of the targetted Spin.
        :returns: The speed of the targetted Spin.
        :rtype: float
        """
        self.bootstrap()
        
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getSpeed(motorID)


    def getSpinTorque(self, motorID, moduleID):
        """Reads the torque value of a motor from the Spin module.

        Motors can turn in two directions, hence the torque will be between
        -1 Nm and 1 Nm depending on the direction.
        
        :param str motorID: ID of a Spin's motor. Either 'A' or 'B'.
        :param str moduleID: ID of target Spin.
        :returns: Newton-meter value of torque of the target motor.
        :rtype: float
        """
        # Check for invalid moduleID

        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getTorque(motorID)


    def getSpinSensorAmbient(self, mode, moduleID):
        """__PRIVATE__
        Reads the ambient light sensor from the Spin module.
        
        It measures the ambient light by computing the average of the three color sensors readings.
        
        :param str moduleID: ID of the target Spin.
        :param str mode: Either 'directed' or 'ambient'.
        :returns: The directed or ambient light.
        :rtype: float
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        cval0 = m.getSensorC(mode, 1)
        cval1 = m.getSensorC(mode, 2)
        cval2 = m.getSensorC(mode, 3)
        return (cval0 + cval1 + cval2)/3 # return average

    
    def getSpinLight(self, mode, sensorID, moduleID):
        """Reads the light measure from a specified sensor on the Spin module.

        :param str mode: Either 'ambient' or 'directed'
        :param int sensorID: ID of the color sensor. Either '1', '2' or '3'.
        :param str moduleID: ID of the target Spin.
        :returns: value of the Clear (ambient) color from the sensors.
        :rtype: float
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.getSensorC(mode, sensorID)

        return res

    
    def getSpinSensorColor(self, sensorID, moduleID): 
        """Reads the RGB values of one of the three color sensors from the Spin module.
        
        :param int sensorID: ID of the color sensor. Either '1', '2' or '3'.
        :param str moduleID: ID of the target Spin.
        :returns: RGB values of the color sensed mapped between the range 0-100.
        :rtype: float[]
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        rval = m.getSensorR(sensorID)
        gval = m.getSensorG(sensorID)
        bval = m.getSensorB(sensorID)
        #mapping rgb values to range 0-100.
        rval = Tools.mapNumber(rval, 0, 255, 0, 100)
        gval = Tools.mapNumber(gval, 0, 255, 0, 100)
        bval = Tools.mapNumber(bval, 0, 255, 0, 100)

        rgbval = [rval, gval, bval]
        print('color', rgbval)
        #print("clear {}: red {}: green {}: blue {}".format(cval,rval,gval,bval))
        return rgbval

    
    def getSpinProximitySensor(self, sensorID, moduleID): 
        """"Reads the averaged distance (proximity) from a specified sensor on the Spin module.
        
        The Spin module sensor have a minimum and maximum active range for proximity
        detection. The minimum detectable distance is 3cm, and the maximum detectable
        distance is 15cm.
        
        :param int sensorID: ID of the color sensor. Either '1', '2' or '3'.
        :param str moduleID: ID of the target Spin.
        :returns: proximity value sensed in percentage, between 0 and 100.
        :rtype: float
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.getSensorP(sensorID)
        res = Tools.crop(0, 100, res, returnType=float)

        return res

    
    def spinObstacleDetected(self, proxi_perc, moduleID):
        """Detects if an object is within a specified specified range of the proximity sensor.

        All 3 sensors are checked. If one sensor detects an obstacle within range,
        detection is set to True.

        :param float proxi_perc: Percentual range of proximity sensor.
        :param str moduleID: ID of the target Spin. 
        :returns: whether or not an object is detected within range.
        :rtyep: bool
        """
        self.bootstrap()

        # store the 3 sensor readings in a list, each value 0 to 100
        sensor_res = [0, 0, 0]
        for sensor_ID in range(1, 4):
            li_idx = sensor_ID - 1
            
            #check each sensor and store the reading in the list
            sensor_data = self.getSpinProximitySensor(sensor_ID, moduleID)
            sensor_res[li_idx] = sensor_data

        sensor_res = min(sensor_res)
        if (proxi_perc <= round(sensor_res)):
            return True
        return False

    
    def getSpinSensorReading(self, measure, sensorID, moduleID):
        """Reads the measurement from a specified sensor on the Spin module.

        :param str measure: The measure to read from the sensor. Either 'proximity', 'color', 'ambientLight' or 'directedLight'.

        :param int sensorID: ID of the color sensor. Either '1', '2' or '3'.
        :param str moduleID: ID of the target Spin.
        :returns: the measure reading.
        :rtype: float
        """
        self.bootstrap()

        if (measure == 'proximity'):    
            return self.getSpinProximitySensor(sensorID, moduleID) 

        elif (measure == 'color'):
            # returns [r,g,b]
            return self.getSpinSensorColor(sensorID, moduleID)
        elif (measure == 'ambientLight'):
            # returns int value of light intensity in the room, tuning needed
            return self.getSpinLight('ambient', sensorID, moduleID)
        elif (measure == 'directedLight'):
            # returns int value of light intensity that is directed to the sensor, tuning needed
            return self.getSpinLight('directed', sensorID, moduleID)


    def getRawLightSensor(self, sensorID, moduleID):
        """__PRIVATE__
        Reads ambient light from the Spin module.
        This is the raw value of the sensor (firmware), without the mapping.

        :param int sensorID: ID of target sensor.
        :param str moduleID: ID of the target Spin.
        :returns: raw reading of ambient light.
        :rtype: int
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.getSensorC('ambient', sensorID, raw=True)

        return int(res)


    def getSpinIsColorFound(self, color, moduleID, threshold=32):
        """Computes the similarity between a given color and the 'color' sensed by the Spin
        module.

        :param int[] color: RGB values of color to detect.
        :param str moduleID: ID of the target Spin.
        :param int threshold: Value to assess similarity.
        :returns: whether or not the color is detected.
        :rtype: bool
        """
        # Turn on the headlights - strongly optional.... NOT.
        self.setSpinHeadlight('on', moduleID)
        # Clamp the target color when invoked from Python editor.
        self.__checkColorClamping(color)
        # Transformation to range 0 - 1..
        color[0] = color[0] / 100.0
        color[1] = color[1] / 100.0
        color[2] = color[2] / 100.0

        red = blue = green = yellow = magenta = cyan = False
        # Each color has been tweaked invidivually, requiring this conditional block.
        if (color == [1, 0, 0]):    #red
            red = True
            color = [0.8, 0, 0.3]
            threshold = 15
        if (color == [0, 1, 0]):    #green
            green = True
            color = [0.2, 0.6, 0]
            threshold = 27
        if (color == [0, 0, 1]):    #blue
            blue = True
            color = [0, 0, 1]
            threshold = 21
        if (color == [1, 1, 0]):    #yellow
            yellow = True
            color = [0.6, 0.4, 0]    #yellow value to improve performance.
            threshold = 15
        if (color == [1, 0, 1]):
            magenta = True
            color = [0.58, 0, 0.35]
            threshold = 15
        if (color == [0, 1, 1]):    #cyan
            cyan = True
            color = [0, 0.47, 0.47]   #cyan value to improve performance.
            threshold = 10
        
        # Read directed and ambient light if target color is white or black.
        if (color == [1, 1, 1] or color == [0, 0, 0]):
            directed_light = self.getSpinLight('directed', 2, moduleID)
            ambient_light = self.getSpinLight('ambient', 2, moduleID)
        # Read the color using sensor 2.
        sensorColor = self.getSpinSensorColor(2, moduleID)
        # Transform to range 0 - 1.
        sensorColor[0] = sensorColor[0] / 100.0
        sensorColor[1] = sensorColor[1] / 100.0 
        sensorColor[2] = sensorColor[2] / 100.0
        
        # White and Black detection.
        if (color == [1, 1, 1] or color == [0, 0, 0]):
            # Compute ratios between the components.
            ratio_rg = abs(sensorColor[0] - sensorColor[1])
            ratio_gb = abs(sensorColor[1] - sensorColor[2])
            ratio_rb = abs(sensorColor[0] - sensorColor[2])
            # Estimate the probability of the sense color being black by checking
            # if its components have similar values.
            probably_black = (ratio_rg <= 0.15 and ratio_gb <= 0.15 and ratio_rb <= 0.15)
            probably_black = probably_black and (sensorColor[0] < 0.41 and 
                                                 sensorColor[1] < 0.41 and 
                                                 sensorColor[2] < 0.41)
            probably_white = (ratio_rg <= 0.2 and ratio_gb <= 0.2 and ratio_rb <= 0.2)
            if (color == [1, 1, 1]):    #white
                # Use directed light for white detection.
                if ambient_light >= 10 and probably_white:
                    return True
            else:                       #black                
                # Use everything to assess black dominance.
                if (ambient_light < 5 and probably_black):
                    return True
        else:
            # Transformation from RGB to Standard RGB space.
            color1_rgb = sRGBColor(color[0], color[1], color[2])
            color2_rgb = sRGBColor(sensorColor[0], sensorColor[1], sensorColor[2])
            # Convert to Lab Color Space.
            color1_lab = convert_color(color1_rgb, LabColor)
            # Convert to Lab Color Space.
            color2_lab = convert_color(color2_rgb, LabColor)
            # Compute the color difference.
            delta_e = delta_e_cie2000(color1_lab, color2_lab)
            
            # Hack for Red
            if (red):
                if (delta_e < threshold and sensorColor[1] < 0.25):
                    return True
                else:
                    return False

            # Hack for Blue
            if (blue):
                if (delta_e < threshold and sensorColor[1] < 0.37):
                    return True
                else:
                    return False
            
            # Hack for Magenta.
            if (magenta):
                if (delta_e < threshold):
                    return True
                else:
                    return False

            # Hack for Cyan.
            if (cyan):
                if (delta_e < threshold and sensorColor[2] > 0.40):
                    return True
                else:
                    return False
            
            # Color similarity.
            if (delta_e < threshold):
                return True

        return False


    def getSpinColorDelta(self, color, moduleID):
        """__PRIVATE__
        Computes color similarity between target and sensed color from the Spin module.

        :param int[] color: RGB values of color to detect.
        :param str moduleID: ID of the target Spin.
        :returns: similarity score.
        :rtype: double
        """
        self.setSpinHeadlight('on', moduleID)
        # Normalization.
        color[0] = color[0] / 100.0
        color[1] = color[1] / 100.0
        color[2] = color[2] / 100.0
        # Read the color using sensor 2.
        sensorColor = self.getSpinSensorColor(2, moduleID)
        # Normalization.
        sensorColor[0] = sensorColor[0] / 100.0
        sensorColor[1] = sensorColor[1] / 100.0 
        sensorColor[2] = sensorColor[2] / 100.0
        
        color1_rgb = sRGBColor(color[0], color[1], color[2])
        color2_rgb = sRGBColor(sensorColor[0], sensorColor[1], sensorColor[2])
        # Convert from RGB to Lab Color Space
        color1_lab = convert_color(color1_rgb, LabColor)
        # Convert from RGB to Lab Color Space
        color2_lab = convert_color(color2_rgb, LabColor)
        # Compute the color difference
        delta_e = delta_e_cie2000(color1_lab, color2_lab)

        return delta_e


    def getSensorR(self, sensorID,  moduleID): 
        """__PRIVATE__
        Reads the R component of a color sensor from the Spin module.
        
        :param int sensorID: ID of the color sensor. Either ``1``, ``2`` or ``3``.
        :param str moduleID: ID of the target Spin.
        :returns: Red value from the sensor readings.
        :rtype: float
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        rval = m.getSensorR(sensorID)
        return rval


    def getSensorG(self, sensorID,  moduleID): 
        """__PRIVATE__
        Reads the G component of a color sensor from the Spin module.
        
        :param int sensorID: ID of the color sensor. Either ``1``, ``2`` or ``3``.
        :param str moduleID: ID of the target Spin.
        :returns: Green value from the sensor readings.
        :rtype: float
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        gval = m.getSensorG(sensorID)
        return gval

    
    def getSensorB(self, sensorID,  moduleID): 
        """__PRIVATE__
        Reads the B component of a color sensor from the Spin module.
        
        :param int sensorID: ID of the color sensor. Either ``1``, ``2`` or ``3``.
        :param str moduleID: ID of the target Spin.
        :returns: Blue value from the sensor readings.
        :rtype: float
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        bval = m.getSensorB(sensorID)
        return bval

    
    def sensorInitOn(self, sensorNr, moduleID): # this is a hack, it should be handled in firmware
        """__PRIVATE__
        Sets speed of a specified spin module
        
        Attributes:
            enable - init 1 or 0
            sensorNr - Sensor number 1,2 or 3
            moduleID   - ID of target spin
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.sensorInit(1,sensorNr)
        return res

    
    def sensorInitOff(self, sensorNr, moduleID): # this is a hack, it should be handled in firmware
        """__PRIVATE__
        Sets speed of a specified spin module
        
        Attributes:
            enable - init 1 or 0
            sensorNr - Sensor number 1,2 or 3
            moduleID   - ID of target spin
        """
        self.bootstrap()
        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        res = m.sensorInit(0,sensorNr)
        return res

    
    def areSpinMotorsMoving(self, motorCombo, moduleID):
        """Checks if a specified motor on the Spin module is moving.

        :param str motorCombo: The number of motors to check. The combinations are 'no', 'any' or 'both' motors, or 'A' - 'B' for a single target.

        :param str moduleID: ID of the target Spin.
        :returns: whether or not the target is moving.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)

        motorA_moving = (0 != m.getSpeed('A'))
        motorB_moving = (0 != m.getSpeed('B'))

        if (motorCombo == 'no'):
            if not motorA_moving and not motorB_moving:
                return True
        if (motorCombo == 'any'):
            if motorA_moving or motorB_moving:
                return True
        if (motorCombo == 'both'):
            if motorA_moving and motorB_moving:
                return True
        if (motorCombo == 'A'):
            if motorA_moving:
                return True
        if (motorCombo == 'B'):
            if motorB_moving:
                return True
        return False

    
    def spinTurn(self, angle, radius, radiusMetric, moduleID='', speed=64):
        """__PRIVATE__
        Drives the Spin module around the arc of a circle.

        The circle is drawn with the given radius. The Spin drives following the
        arc generated the given angle, at a given speed.

        [INSERT IMAGE HERE] Because this feature is hard to explain with words.

        :param float angle: ??
        :param float radius: ??
        :param str radius metric: The metric units (``cm``, ``mm``, ``in``, ``ft``).
        :param str moduleID: ID of the target Spin.
        :param float speed: Percentual value for the driving speed (between 0 and 100).
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)

        if (radiusMetric == "cm"):
            radius = radius * 10
        elif (radiusMetric == "mm"):
            radius = radius
        elif (radiusMetric == "in"):
            radius = radius * 25.4
        elif (radiusMetric == "ft"):
            radius = radius * 304.8

        if (radius > 6000):
             #If radius is bigger than 6 meters
            m.driveByMetric(angle, 'degrees', speed)
            
        elif (radius == 0):
            m.spinByMetric(angle, 'degrees', speed)
        else:
            m.rotateByTurn(angle, radius, speed)


    def spinLiftPos(self, angle, motor, speed=10, moduleID=''):
        """__PRIVATE__
        Turns a motor a specified angle, in lift mode, on the Spin module.

        Lift mode is ??????????.

        :param float angle: Turning angle for the motor.
        :param str motor: ID of the motor to target. Either ``1``-``0``, or A``-``B``.
        :param str moduleID: ID of the target Spin.
        :param float speed: Percentual value for the turning speed (between 0 and 100).
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        m.setSpeed(speed, motor)
        m.setPos(angle, motor)


    def spinReset(self, target, moduleID):
        """__PRIVATE__"""
        # can target motor A, B or both
        raise NotImplementedError()


    def setSpinSignal(self, signal_value, moduleID):
        """__PRIVATE__"""
        raise NotImplementedError()


    def spinByMetric(self, measure, metric, moduleID, speed=50):
        """Performs a spin action using a specified value and metric, at a set speed, on the Spin module.

        For example, if the measure value is 5, the behavior will change depending on the metric selected:
            - 'times' commands the Spin module to spin in its own axis 5 full rotations (1800 degrees).
            - 'degrees' commands the Spin module to spin in its own axis 5 degrees.
            - 'radians' commands the Spin module to spin in its own axis 5 radians (286.5 degrees).

        :param str measure: The value to use for spinning.
        :param str metric: Metric use to drive.Use 'times', 'degrees' or 'radians'.
        :param str moduleID: ID of the target Spin.
        :param float speed: Percentual value for the driving speed (between 0 and 100).
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        m.spinByMetric(measure, metric, speed=speed)


    def driveByMetric(self, distance, metric, moduleID, speed=50):
        """Drives the Spin module for a specified distance or by wheel spins.

        :param float distance:
        :param str metric: Metric use to drive. For distance, use 'm', 'cm', 'in' or 'ft'. Use 'times' or 'radians' to set the number of spins of the wheels (times for n full 360° spins or radians for a more precise spins).
        :param str moduleID: ID of the target Spin.
        :param float speed: Percentual value for the driving speed (between 0 and 100).
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        m.driveByMetric(distance, metric, speed=speed)


    def getGestureDetected(self, gesture, moduleID):
        """__PRIVATE__
        Checks if a specified gesture is detected on the Spin module.
        
        :param str gesture: Target action to detect. Either ``pull`` or ``push``.
        :param str moduleID: ID of the target Spin.
        :returns: whether or not the gesture is detected.
        :rtype: bool
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getGestureDetected(gesture)


    def getSpinSignal(self, moduleID):
        """__PRIVATE__"""
        raise NotImplementedError()


    def getSpinMotorMetric(self, metric, moduleID):
        """Reads a metric from a motor on the Spin module.

        :param str metric: The value of the metric. The available measures are
            - 'angleA' or 'angleB'
            - 'rotationA' or 'rotationB'
            - 'velocityA' or 'velocityB'
        
        :param str moduleID: ID of the target Spin.
        :returns: whether or not the gesture is detected.
        :rtype: bool
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)

        if (metric == 'angleA'):
            return m.getAngle(0)
        elif (metric == 'angleB'):
            return m.getAngle(1)
        elif (metric == 'rotationsA'):
            return (m.getAngle(0) / 360)
        elif (metric == 'rotationsB'):
            return (m.getAngle(1) / 360)
        elif (metric == 'velocityA'):
            #Read the speed and convert RPM to percentage
            return (m.getSpeed(0) * 100 / m.MAX_SPEED_RPM)
        elif (metric == 'velocityB'):
            #Read the speed and convert RPM to percentage
            return (m.getSpeed(1) * 100 / m.MAX_SPEED_RPM)
            
        return m.getAngle(0)


    def getColorDistance(self, color_one, color_two):
        """__PRIVATE__"""
        raise NotImplementedError()


    def getColorChannel(self, channel, color):
        """Gets the red, green or blue value of a color array.

        :param str channel: The channel which shall be retrieved. Possible values are:
        - 'R' for red
        - 'G' for green
        - 'B' for blue
        :param list color: The color array that will be used to retrieve a color value.
        :returns: The channel color value.
        :rtype: int:"""
        if not type(color) in [list]:
            return 0
        
        if (channel == 'R' and len(color) > 0):
            return color[0]
        elif (channel == 'G' and len(color) > 1):
            return color[1]
        elif (channel == 'B' and len(color) > 2):
            return color[2]

        return 0


    def turnByArc(self, radius, angle, moduleID):
        """__PRIVATE__"""
        pass


    def getSpinHasReachedTarget(self, motor, moduleID):
        """Checks if a motor on the Spin module has reached the target goal.

        :param str motor: ID of the motor to target. Either 'A' or 'B'.
        :param str moduleID: ID of the target Spin.
        :returns: whether or not the motor has reached its target.
        :rtype: bool
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.hasReachedTarget(motor)


    def getSpinOdometry(self, coordinate, moduleID):
        """__PRIVATE__
        Description?????

        :param str coordinate: ????
        :param str moduleID: ID of the target Spin.
        :returns: ????
        :rtype: ????
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        return m.getOdometry(coordinate)


    def resetSpinOdometry(self, moduleID):
        """__PRIVATE__
        Description?????

        :param str moduleID: ID of the target Spin.
        """
        self.bootstrap()

        m = self.runtime.getModule(moduleID, ModuleTypes.SPIN)
        m.resetOdometry()