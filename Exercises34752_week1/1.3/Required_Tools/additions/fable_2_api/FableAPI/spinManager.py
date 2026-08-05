from .tools import Tools
from .dongle import Dongle
from .ostime import OSTime
from .DEFINES import ControlState, Keys, ModuleTypes, SpinEvents
import time, sys, copy
import numpy as np
import math
from .moduleState import JointState, ModuleState, SpinState

class SpinManager():
    def __init__(self, moduleID, radioID, dongle, api, runtime):
        self.dongle              = dongle
        self.api                 = api
        self.runtime             = runtime
        self.isDummy             = False
        self.syncCounter         = 0
        self.lastSyncTime        = OSTime.getOSTime()
        self.lastSyncSendTime    = OSTime.getOSTime()
        self.syncErrorCount      = 0
        self.newerSeen           = True
        self.used                = False
        self.hasBeenReset        = False
        self.syncHistory         = []
        self.shouldTerminate = False
        self.AXLE                = 119    #mm from wheel to wheel // maybe 119
        # self.WHEEL_CIRCUMFERENCE = 345.57 #mm 2r*pi
        self.WHEEL_RADIUS        = 53.7     #mm. Was 55 before but the newest wheels are 55.
        self.MAX_SPEED_RPM       = 60     #max speed in RPM

        #TODO: Remove once gesture detection is implemented on firmware level
        self.distanceHistorySensor1 = []
        self.distanceHistorySensor2 = []
        self.distanceHistorySensor3 = []

        # Odometry data gets updated by drive, spin, turn
        self.odometry_data = []

        self.defaultState = {
                        # State Stored in EEPROM
                          'serialID' : {'val': moduleID, 'type': 'p', 'adr_list': [ModuleState.SERIAL_NUMBER_ADR_0, ModuleState.SERIAL_NUMBER_ADR_1, ModuleState.SERIAL_NUMBER_ADR_2, ModuleState.SERIAL_NUMBER_ADR_3], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'type' : {'val': ModuleTypes.SPIN, 'type': 'p', 'adr_list': [ModuleState.TYPE_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1 , 'lastWrite' : -1},
                          'firmwareVersion' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.FIRMWARE_VER_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'hardwareVersion' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.HARDWARE_VER_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'resetCount' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.RESET_COUNT_ADR_0, ModuleState.RESET_COUNT_ADR_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'onTime' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.ON_TIME_ADR_0, ModuleState.ON_TIME_ADR_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'radioChannel' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.RADIO_CHANNEL_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'radioID' : {'val': radioID, 'type': 'p', 'adr_list': [ModuleState.RADIO_ID_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'boothMode' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.BOOTH_MODE_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'name' : {'val': '', 'type': 'p', 'adr_list': [ModuleState.NAME_ADR_0, ModuleState.NAME_ADR_1, ModuleState.NAME_ADR_2, ModuleState.NAME_ADR_3, ModuleState.NAME_ADR_4, ModuleState.NAME_ADR_5, ModuleState.NAME_ADR_6, ModuleState.NAME_ADR_7, ModuleState.NAME_ADR_8, ModuleState.NAME_ADR_9, ModuleState.NAME_ADR_10, ModuleState.NAME_ADR_11, ModuleState.NAME_ADR_12, ModuleState.NAME_ADR_13, ModuleState.NAME_ADR_14, ModuleState.NAME_ADR_15, ModuleState.NAME_ADR_16, ModuleState.NAME_ADR_17, ModuleState.NAME_ADR_18, ModuleState.NAME_ADR_19 ], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                        # State of servo write paramters
                          'posA' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.A_GOAL_POS_0,SpinState.A_GOAL_POS_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'getPosA' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.A_CURRENT_POS_0,SpinState.A_CURRENT_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'speedA' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.A_GOAL_SPEED_0,SpinState.A_GOAL_SPEED_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'getSpeedA' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.A_CURRENT_SPEED_0,SpinState.A_CURRENT_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'stopPosA' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.A_GOAL_STOP_POS_0,SpinState.A_GOAL_STOP_POS_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'hasAchievedStopPosA' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.A_ACHIEVED_STOP_POS], 'sync': False, 'period' : 0.1, 'lastSync' : -1, 'lastWrite' : -1},
                          'resetEncA' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.A_RESET_ENCODER], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'getTorqueA' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.A_TORQUE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          
                          'posB' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.B_GOAL_POS_0,SpinState.B_GOAL_POS_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'getPosB' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.B_CURRENT_POS_0,SpinState.B_CURRENT_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'speedB' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.B_GOAL_SPEED_0,SpinState.B_GOAL_SPEED_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'stopPosB' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.B_GOAL_STOP_POS_0,SpinState.B_GOAL_STOP_POS_1], 'sync': False, 'period' : 0.5, 'lastSync' : -1, 'lastWrite' : -1},
                          'getSpeedB' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.B_CURRENT_SPEED_0,SpinState.B_CURRENT_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'hasAchievedStopPosB' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.B_ACHIEVED_STOP_POS], 'sync': False, 'period' : 0.1, 'lastSync' : -1, 'lastWrite' : -1},
                          'resetEncB' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.B_RESET_ENCODER], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'getTorqueB' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.B_TORQUE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},


                        # State of Sensor relatet parameters (Jesper)
                          'headlight' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.HEADLIGHT_INTENSITY], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensorInit1' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.SENSORINIT1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor1c' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR1C], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor1r' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR1R], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor1g' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR1G], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor1b' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR1B], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor1p' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR1P], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensorInit2' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.SENSORINIT2], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor2c' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR2C], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor2r' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR2R], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor2g' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR2G], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor2b' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR2B], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor2p' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR2P], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensorInit3' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.SENSORINIT3], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor3c' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR3C], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor3r' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR3R], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor3g' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR3G], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor3b' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR3B], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'sensor3p' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.SENSOR3P], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                          'irWrite' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.IR_WRITE], 'sync': False, 'period' : 0.1, 'lastSync' : -1, 'lastWrite' : -1},
                          'irRead' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.IR_READ], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                        # State of module paramters not in EEPROM
                          'ledRGB' : {'val': [0,0,0], 'type': 'w', 'adr_list': [SpinState.LED_R, SpinState.LED_G, SpinState.LED_B], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'batteryLevel' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.BATTERY_LEVEL_0, SpinState.BATTERY_LEVEL_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'vccLevel' : {'val': 0, 'type': 'r', 'adr_list': [SpinState.VCC_LEVEL_0, SpinState.VCC_LEVEL_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'charging' : {'val': False, 'type': 'r', 'adr_list': [SpinState.CHARGING], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'status' : {'val': 0, 'type': 'w', 'adr_list': [SpinState.SPIN_STATUS], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1}

        }
        self.softState = copy.deepcopy(self.defaultState)
        self.hardState = copy.deepcopy(self.defaultState)
        self.servoKeys = {'posA','posB','getPosA','getPosB','speedA','speedB','getSpeedA','getSpeedB','stopPosA','stopPosB','hasAchievedStopPosA','hasAchievedStopPosB','resetEncA','resetEncB'}
        # Set the initial AXLE constant based on the hardware version
        self.setAxleConst()

    def setAxleConst(self):
        """Set the initial AXLE constant based on the hardware version of the Spin.

        Additionally, if reading the hardware doesn't work the very first time,
        the method will try again 1 second later.
        """
        hw_version = self.getHardwareVersion()
        
        # # If the hardware version was not read correctly, try again in 1 second
        # if (hw_version == 0 or hw_version == '0'):
        #     t = Timer(1.0, self.setAxleConst, [], {})
        #     t.start()
        # else:
        #     print('Changing Spin AXLE constant to match hw version ', str(hw_version))
        #     if (hw_version == 1):
        #         self.AXLE = 119
        #     elif (hw_version == 2):
        #         self.AXLE = 119

    def getSyncErrorCount(self):
        return self.syncErrorCount

    def getLastSyncTime(self):
        return self.lastSyncTime

    def isSyncronized(self, key):
        return self.hardState[key]['val'] == self.softState[key]['val']

    def doWrite(self, key):
        if (self.softState[key]['type'] == 'w' and (not self.isSyncronized(key))):
            return True

        if (self.softState[key]['type'] == 'p' and (not self.isSyncronized(key))):
            return True
        return False

    def doRead(self, key):
        #Special case for hasReachedTarget
        if (key == 'hasAchievedStopPosA' and (self.doWrite('speedA') or self.doWrite('stopPosA'))):
            return False
        #Special case for hasReachedTarget
        if (key == 'hasAchievedStopPosB' and (self.doWrite('speedB') or self.doWrite('stopPosB'))):
            return False

        if (self.softState[key]['sync'] == True) or (self.api.state == ControlState.running and self.used and (key in SpinEvents.getKeysToTrack())):
            nextSyncTime = (self.softState[key]['lastSync'] + self.softState[key]['period'])
            if OSTime.getOSTime() >= nextSyncTime:
                return True
        return False

    def checkStateForceSync(self, key):
        """Tries to force a sync for some special keys (posA, posB, speedA, speedB, stopPosA, stopPosB).
            
        Checks if the soft state received the SAME instruction as before.
        Only forces the sync if the grace period (softState[key][period]) has passed.

        This reduces spam in a while-true loop, and further reduces the triggering of torque overload."""

        if (self.softState[key]['val'] == self.hardState[key]['val']):
            nextSyncTime = (self.softState[key]['lastWrite'] + self.softState[key]['period'])
            if (OSTime.getOSTime() >= nextSyncTime):
                self.hardState[key]['val'] = self.softState[key]['val'] - 1

    def sync(self):
        if self.shouldTerminate:
            res = self.dongle.writeRadioPacket([self.getType(), self.getRadioID(), 247])
            if res:
                self.softState = copy.deepcopy(self.defaultState)
                self.hardState = copy.deepcopy(self.defaultState)
                self.syncCounter = 0
                self.syncErrorCount = 0
                self.used = False
                self.shouldTerminate = False
                self.odometry_data = []
                # print('reset complete')
            return

        self.lastSyncTime = OSTime.getOSTime()
        radioID = self.softState['radioID']['val']
        if radioID == None:
            self.syncCounter = self.syncCounter + 1
            self.saveSyncHistory('error')
            return False
        headerData = [ModuleTypes.SPIN, radioID, 252] # use sync state command
        writeData = []
        readData = []
        writeKeys = []
        readKeys = []
        readAdrs = []
        # print('==============')
        for key, val in self.softState.items():
            value = self.softState[key]['val']
            adrs = self.softState[key]['adr_list']
            if len(headerData+writeData+readData) >= 26:
                break
                #print('Data packet is full!')
            #print(len(headerData+writeData+readData))
            if self.doWrite(key):
                # if key == 'speedA':    #to check a certain state
                #     print('sync speed')
                #     print(value)
                self.used = True
                writeKeys.append(key)
                #print(key)
                # if (key == 'ledRGB'):
                #     print('ledRGB', self.softState['ledRGB']['val'])
                if type(value) == str:
                    for i in range(len(value)):
                        writeData.append(adrs[i])
                        writeData.append(ord(value[i]))
                if type(value) == list:
                    for i in range(len(value)):
                        writeData.append(adrs[i])
                        writeData.append(value[i])
                if type(value) == int:
                    if len(adrs) == 1:
                        writeData.append(adrs[0])
                        writeData.append(value)
                    if len(adrs) == 2:
                        writeData.append(adrs[0])
                        writeData.append(Tools.low(value))
                        writeData.append(adrs[1])
                        writeData.append(Tools.high(value))
                self.softState[key]['lastWrite'] = OSTime.getOSTime()
            if self.doRead(key):
                if key in self.servoKeys:
                    self.used = True
                readKeys.append(key)
                # if (key not in ['batteryLevel', 'charging', 'sensor1p', 'sensor2p', 'sensor3p']):
                #     print(key)
                for adr in adrs:
                    readData.append(0x80|adr)
                    readAdrs.append(adr)
                self.softState[key]['lastSync'] = OSTime.getOSTime()

        data = headerData+writeData+readData
        # print('[',len(data),'/30] =>', data)
        # print("Package: ", [i for i in data])
        if len(data) != 3 or (self.lastSyncSendTime + 0.5) < OSTime.getOSTime() :
            self.lastSyncSendTime = OSTime.getOSTime()
            # print('[',len(data),'/30] =>', data)
            if len(data) > 30:
                print("Error: Must break up sync message now!")
                #TODO: add breakup code here...
            res, packet = self.sendSyncMessage(headerData, writeData, readData)
            if res:
                res = self.handleSyncReturnMessage(packet, readKeys, readAdrs)
                if res == False:
                    self.syncErrorCount = self.syncErrorCount + 1
                    return False
                for key in writeKeys:
                    self.hardState[key]['val'] = self.softState[key]['val']
                for key in readKeys:
                    self.softState[key]['val'] = self.hardState[key]['val']

                self.syncErrorCount = 0
                self.syncCounter = self.syncCounter + 1
                self.saveSyncHistory('ok')
                return True
            else:
                self.syncErrorCount = self.syncErrorCount + 1
                self.syncCounter = self.syncCounter + 1
                self.saveSyncHistory('error')
                return False

        self.syncCounter = self.syncCounter + 1
        self.saveSyncHistory('ignore')
        return True

    def saveSyncHistory(self, result):
        self.syncHistory.append(result)
        if len(self.syncHistory) > 100:
            self.syncHistory.pop(0)

    def getConnectionQuality(self):
        errorCount= self.syncHistory.count('error')
        okCount = self.syncHistory.count('ok')
        ignoreCount = self.syncHistory.count('ignore')
        syncQuality = 100
        if (errorCount+okCount) !=0:
            syncQuality = 100*okCount/(errorCount+okCount)
        #print('Quality =',syncQuality, "ok", okCount, "err", errorCount, 'ignore', ignoreCount)
        return syncQuality

    def restoreStateAfterReset(self):
        for key, val in self.softState.items():
            if self.softState[key]['lastWrite'] != -1 and key != 'status':
                #print('updating keys ', key,'->', self.softState[key]['val'])
                self.hardState[key]['val'] = 0
            #print(key)

    def isOwnedByAnotherDongle(self):
        return self.hardState['status']['val'] == SpinState.STATUS_LOCKED

    def handleSyncReturnMessage(self, packet, readKeys, readAdrs):
        index = 5
        status = self.hardState['status']['val']
        if status == SpinState.STATUS_LOCKED:
            if self.hasBeenReset == True:
                self.hasBeenReset = False
            return False

        if self.hasBeenReset == True:
            self.restoreStateAfterReset()
            self.hasBeenReset = False

        if len(readAdrs) != (len(packet)-5):
            print('Return packet does not match length required ', packet)
            return False

        for key in readKeys:
            adrs = self.softState[key]['adr_list']
            if len(adrs) == 1:
                self.hardState[key]['val'] = packet[index]
                index = index + 1
            if len(adrs) == 2:
                self.hardState[key]['val'] = packet[index]+255*packet[index+1]
                index = index + 2

            #TODO: Remove once gesture detection is implemented on firmware level
            if key in SpinEvents.getKeysToTrack():
                if key == 'sensor1p':
                    s1Value = self.hardState[key]['val']
                    if (s1Value != 0):
                        s1Value = Tools.crop(3, 15, (112 * (s1Value ** -0.642)), returnType=float)
                    self.distanceHistorySensor1.append(s1Value)
                    if (len(self.distanceHistorySensor1) > 500):
                        del self.distanceHistorySensor1[:400]
                elif key == 'sensor2p':
                    s2Value = self.hardState[key]['val']
                    if (s2Value != 0):
                        s1Value = Tools.crop(3, 15, (112 * (s2Value ** -0.642)), returnType=float)
                    self.distanceHistorySensor2.append(s2Value)
                    if (len(self.distanceHistorySensor2) > 500):
                        del self.distanceHistorySensor1[:400]
                elif key == 'sensor3p':
                    s3Value = self.hardState[key]['val']
                    if (s3Value != 0):
                        s3Value = Tools.crop(3, 15, (112 * (s3Value ** -0.642)), returnType=float)
                    self.distanceHistorySensor3.append(s3Value)
                    if (len(self.distanceHistorySensor3) > 500):
                        del self.distanceHistorySensor1[:400]

        return True

    def sendSyncMessage(self, headerData, writeData, readData):
        radioPacket = headerData+writeData+readData
        nReply = 5+len(readData)
        #self.api.bootstrap()
        #self.api.lock.acquire()
        tt = OSTime.getOSTime()
        res = self.dongle.writeRadioPacket(radioPacket)
        self.api.handleResult(res)
        if res == False:
            print(self.getSerialID()+": Failed writing sync packet")
            return False, []
        packet = self.dongle.readPacket(nReply, 1) #TODO: figure out why this extended delay is nessecary?
        #print(self.getSerialID()+": Lag = ", 1000*(OSTime.getOSTime()-tt), ' n =',nReply)
        if not len(packet) >= 5:
            #print(self.getSerialID()+": Return packet too short",len(packet))
            return False, packet
        status = packet[4]
        if packet[0] != ord('#'):
            print("packet !=#",packet[0])
            return False, packet
        senderType = packet[2]
        if senderType != ModuleTypes.SPIN:
            print("type != Spin!",packet[2])
            return False, packet
        senderID = packet[3]
        if senderID != self.getRadioID():
            print("sender RadioID not as expected while sync!",senderID, self.getRadioID())
            return False, packet
        if self.hardState['status']['val'] != status:
            #print('reset? old:', self.hardState['status']['val'], 'new:',status)
            self.hardState['status']['val'] = status
            if (status ==  SpinState.STATUS_READY) or (status ==  SpinState.STATUS_RUNNING):
                #print('Module has been reset', status)
                self.hasBeenReset = True
        if self.hardState['status']['val'] == SpinState.STATUS_BOOT:
            #print("module booting up!",senderID, self.getRadioID())
            return False, packet
        self.softState['status']['val'] = status
       # self.api.sawModule(senderType, senderID)
        #self.api.lock.release()
        return True, packet

    def seen(self):
        self.newerSeen = False
        self.saveSyncHistory('ok')

    def terminate(self):
        self.shouldTerminate = True

    def waitForSync(self):
        now = self.syncCounter
        pause = self.runtime.isPaused()
        if pause:
            self.runtime.restart()
        if self.newerSeen:
            return
        while (self.syncCounter - now) <= 1: # wait two sync periods to make sure the read value is updated
            self.api.bootstrap()
            if self.isOwnedByAnotherDongle():
                return
        #if pause: #cause a deadlock in some situations
        #    self.runtime.pause()

    def resetEncoder(self, motorID):
        key = "resetEncA" if motorID in [0, 'a', 'A'] else "resetEncB"
        if self.softState[key]['val'] == 0:
            self.softState[key]['val'] = 1
        else:
            self.softState[key]['val'] = 0
        self.checkStateForceSync(key)


    def relaxLifting(self, motorID):
        key = "resetEncA" if motorID in [0, 'a', 'A'] else "resetEncB"
        if self.softState[key]['val'] == 2:
            self.softState[key]['val'] = 3
        else:
            self.softState[key]['val'] = 2
        self.checkStateForceSync(key)


    def setPos(self, pos, motorID):
        if not type(pos) in [int, float, np.int64, np.float64]: return
        key = "posA" if motorID in [0, 'a', 'A'] else "posB"
        pos = Tools.crop(-32768,32767,pos,returnType=int) + 32768

        self.softState[key]['val'] = pos
        self.checkStateForceSync(key)

    def setSpeed(self, speed, motorID, isPercent=True):
        if not type(speed) in [int, float, np.int64, np.float64]: return
        key = "speedA" if motorID in [0, 'a', 'A'] else "speedB"

        #Convert speed from percentage to RPM
        if (isPercent):
            speed = Tools.crop(-100, 100, speed, returnType=float) * self.MAX_SPEED_RPM / 100
        # print('converted speed', speed)
        else:
            speed = Tools.crop(-60, 60, speed, returnType=float)

        speed = int(speed) + 32768

        self.softState[key]['val'] = speed
        self.checkStateForceSync(key)

    def setStopPos(self, angle, motorID):
        if not type(angle) in [int, float, np.int64, np.float64]: return
        key = "stopPosA" if motorID in [0, 'a', 'A'] else "stopPosB"
        angle = Tools.crop(-32768, 32767, angle, returnType=int) + 32768

        self.softState[key]['val'] = angle
        self.checkStateForceSync(key)
        if "stopPosA":
            self.softState['hasAchievedStopPosA']['val'] = 0
            self.hardState['hasAchievedStopPosA']['val'] = 0
        elif "stopPosB":
            self.softState['hasAchievedStopPosB']['val'] = 0
            self.hardState['hasAchievedStopPosB']['val'] = 0


    def setHeadlight(self, intensity):
        if not type(intensity) in [int,float]: return
        intensity = int(Tools.crop(0,100,intensity))
        self.softState["headlight"]['val'] = intensity

    def getHeadlight(self):
        return self.softState["headlight"]['val']        

    def clearStatus(self):
        self.softState["status"]['val'] = SpinState.STATUS_READY
        self.hardState["status"]['val'] = SpinState.STATUS_READY

    def getStatus(self):
        stat = self.hardState['status']['val']
        # if stat is SpinState.STATUS_LOW_BATTERY:
        #     self.hardState['status']['val'] = SpinState.STATUS_READY
        return stat

    def setRGBLed(self, r, g, b):
        # r = Tools.crop(0,255,2.55*r)
        # g = Tools.crop(0,255,2.55*g)
        # b = Tools.crop(0,255,2.55*b)
        self.softState["ledRGB"]['val'] = [r,g,b]

    def setRadioID(self, newRadioID):
        self.softState['radioID']['val'] = newRadioID

    def setSerialID(self, newSID):
        self.softState['serialID']['val'] = newSID

    def setIrMessage(self, msg):
        if not msg in range(0,256): return
        self.softState['irWrite']['val'] = msg
        # Force a difference between the two states in order to force a sync
        self.hardState['irWrite']['val'] = msg - 1

    def _read(self, key):
        if self.softState[key]['sync'] == False:
           self.softState[key]['sync'] = True
           self.waitForSync() # not read before, wait until true value is resent
        return self.softState[key]['val']

    def getChargingState(self):
        return self._read('charging')

    def getSpeed(self, motorID):
        if motorID in [0, 'a', 'A']: key = 'getSpeedA'
        elif motorID in [1, 'b', 'B']: key = 'getSpeedB'
        else: key = 'getSpeedA'
        return self._read(key)-32768+128

    def getAngle(self, motorID):
        if motorID in [0, 'a', 'A']: key = 'getPosA'
        elif motorID in [1, 'b', 'B']: key = 'getPosB'
        else: key = 'getPosA'

        angle = self._read(key)-32768+128

        if (self.isDummy and angle == -32640):
            angle = 0
            
        # print(angle)
        return angle

    def getTorque(self, motorID):
        if motorID in [0, 'a', 'A']: key = 'getTorqueA'
        elif motorID in [1, 'b', 'B']: key = 'getTorqueB'
        else: key = 'getTorqueA'
        tau = (self._read(key)-127)/128     # Newton-meter
        return tau


# Added for the apds-9960 color sensor (Jesper)
    def getSensorC(self, mode, sensorNr, raw=False):
        if sensorNr in [1]: key = 'sensor1c'
        elif sensorNr in [2]: key = 'sensor2c'
        else: key = 'sensor3c'
        cval = self._read(key)
        #print(cval)
        # Fit the sensor reading to a function that was mapped to our measurements (check Google Drive or ask Ivan)
        if (cval != 0 and mode == 'directed'):
            #cval = 0.814 + (0.792 * cval) - (0.00158 * (cval ** 2))
            # cval = -14.2 + (8.99 * cval) - (0.0697 * (cval ** 2))
            cval = Tools.mapNumber(cval, 0, 255, 0, 100)
            cval = Tools.crop(0, 100, cval, returnType=int)
        elif (cval != 0 and mode == 'ambient'):
            #-9.41 + 27 * math.log1p(cval)
            if not raw:
                cval = 2.21 + (0.631 * cval) + (215e-03 * (cval ** 2))
                cval = Tools.crop(0, 100, cval, returnType=int)

        # DO NOT crop the final value, as some methods use the raw sensor data!!!
        return cval

# Added for the apds-9960 color sensor (Jesper)
    def getSensorR(self, sensorNr):
        if sensorNr in [1]: key = 'sensor1r'
        elif sensorNr in [2]: key = 'sensor2r'
        else: key = 'sensor3r'
        rval = self._read(key)
#        print(rval)
        return rval

# Added for the apds-9960 color sensor (Jesper)
    def getSensorG(self, sensorNr):
        if sensorNr in [1]: key = 'sensor1g'
        elif sensorNr in [2]: key = 'sensor2g'
        else: key = 'sensor3g'
        gval = self._read(key)
#        print(gval)
        return gval

# Added for the apds-9960 color sensor (Jesper)
    def getSensorB(self, sensorNr):
        if sensorNr in [1]: key = 'sensor1b'
        elif sensorNr in [2]: key = 'sensor2b'
        else: key = 'sensor3b'
        bval = self._read(key)
#        print(bval)
        return bval

# Added for the apds-9960 color sensor (Jesper)
    def getSensorP(self, sensorNr):
        if sensorNr == 1: 
            key = 'sensor1p'
        elif sensorNr == 2: 
            key = 'sensor2p'
        else: 
            key = 'sensor3p'
        pval = self._read(key)
        #print(pval)
        # Fit the sensor reading to a function that was mapped to our measurements (check Google Drive or ask Ivan)
        # if (pval != 0):
        #     pval = 6162 * (pval ** -1.71)

        if (pval != 0):
            pval = -7.9336 * (101.81* (pval ** -0.676))+119
        # Multiply by 10 to convert from cm to mm
        # pval = pval * 10

        return pval

    def getIrRecentMessage(self):
        key = 'irRead'
        msg = self._read(key)
        return msg

    def getVoltage(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'voltageX'
        else: key = 'voltageY'
        return self._read(key)/10.0

    def getTemperature(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'temperatureX'
        else: key = 'temperatureY'
        return self._read(key) #returns in celcius

    def getRadioID(self):
        return self.softState["radioID"]['val']

    def getSerialID(self):
        return self.softState['serialID']['val']

    def getType(self):
        return ModuleTypes.SPIN

    def getBatteryLevel(self):
        # s = self.softState['batteryLevel']
        # if s['sync'] == False:
        #     s['sync']       = True      # start the synchronization
        #     s['lastSync']   = -100      # trigger an update ASAP
        #     s['period']     = 1.0       # update every periods seconds
        #     self.waitForSync()
        # return s['val']
        return self._read('batteryLevel')

    def getGestureDetected(self, gesture):
        num_of_values_to_check = 60
        num_of_values_to_classify_as_gesture = 55
        data = self.distanceHistorySensor2[-num_of_values_to_check:]
        # print(data)
        if (gesture == 'push'):
            counter = 0
            for i in range(1, len(data)):
                if data[i] >= data[i - 1]:
                    counter = counter + 1
                    if counter > num_of_values_to_classify_as_gesture:
                        return True
                # else:
                    # counter = 0
        elif (gesture == 'pull'):
            counter = 0
            for i in range(1, len(data)):
                if data[i] <= data[i - 1]:
                    counter = counter + 1
                    if counter > num_of_values_to_classify_as_gesture:
                        return True
                # else:
                    # counter = 0
        
        return False
    
    def spinByMetric(self, measure, metric, speed=50):
        speedA = speed
        speedB = speed

        # convert to angles
        if metric == 'times':
            angle = measure * 360
        elif metric == 'degrees':
            angle = measure
        elif metric == 'radians':
            angle = measure * 57.2958

        # adjust angle
        # Rd - diameter the robot draws >> 120 mm
        # Wd - wheel diameter           >> 110 mm
        # offset formula                >> angle = angle * (392.7272/360)
        angle = angle *  ((math.pi * self.AXLE / self.WHEEL_RADIUS) * (180.0 / math.pi)) / 360.0
        angle = angle + (np.sign(measure) * (5.5 * math.ceil(abs(measure) / 360.0)))
        

        # print('angle', angle)
        if measure < 0:
            speedA *= -1
            speedB *= -1
        
        if angle == 0:
            speedA = 0
            speedB = 0

        self.setSpeed(speed=speedA, motorID='A')
        self.setSpeed(speed=speedB, motorID='B')

        self.setStopPos(angle, motorID='A')
        self.setStopPos(angle, motorID='B')

    def driveByMetric(self, distance, metric, speed=50):
        # forward motion
        speedA = -speed
        speedB = speed

        # convert all to mm
        if metric == 'm':
            distance = distance * 1000
        elif metric == 'cm':
            distance = distance * 10
        elif metric == 'ft':
            distance = distance * 304.8
        elif metric == 'in':
            distance = distance * 25.4
        elif metric == 'times':
            distance = distance * 360
        elif metric == 'radians':
            distance = distance * 57.2958
        
        # calculate angles from distance
        angle = 360 * (abs(distance) / self.WHEEL_RADIUS / (2 * math.pi))
        # angle = distance
        
        if distance < 0:
            speedA *= -1
            speedB *= -1
            angle *= -1

        if angle == 0:
            speedA = 0
            speedB = 0

        self.setSpeed(speed=speedA, motorID='A')
        self.setSpeed(speed=speedB, motorID='B')

        self.setStopPos(-angle, motorID='A')
        self.setStopPos(angle, motorID='B')


    def hasReachedTarget(self, motorID):
        # if ((OSTime.getOSTime() < self.softState['hasAchievedStopPosA']['lastSync'] + 0.04)):
            # if (motorID != 'B'):
            # return False
            # print(OSTime.getOSTime(), self.softState['hasAchievedStopPosA']['lastSync'] + 0.04)
        
        # if ((OSTime.getOSTime() < self.softState['hasAchievedStopPosB']['lastSync'] + 0.04)):
            # if (motorID != 'A'):
            # print(OSTime.getOSTime())
            # return False

        # print('asdasda')
        
        hasReachedA = (1 == self._read('hasAchievedStopPosA'))
        hasReachedB = (1 == self._read('hasAchievedStopPosB'))
        #logger.info("lastSA: {}, lastSB: {}".format())
        # logger.info("A: {}, B: {}".format(hasReachedA, hasReachedB))

        self.softState['hasAchievedStopPosA']['val'] = 0
        self.softState['hasAchievedStopPosB']['val'] = 0
        self.hardState['hasAchievedStopPosA']['val'] = 0
        self.hardState['hasAchievedStopPosB']['val'] = 0

        if motorID == 'both':
            if hasReachedA and hasReachedB:
                return True
        if motorID == 'any':
            if hasReachedA or hasReachedB:
                return True
        if motorID == 'B':
            if hasReachedB:
                return True
        if motorID == 'A':
            if hasReachedA:
                return True
        return False
        
    def rotateByTurn(self, angle, radius, speed):
        speed = Tools.crop(-100, 100, speed) * self.MAX_SPEED_RPM / 100

        #convert angle from degrees to radians
        #only positive angles are valid
        theta = angle * math.pi / 180.0
        r = radius

        SL =  (r - (self.AXLE/2.0))*theta 
        SR =  (r + (self.AXLE/2.0))*theta 
        print("Theta={}, SL={}, SR={}, r={}, speed={}".format(theta, SL, SR, r, speed))
        
        #Calculate the speed for both wheels
        #Multiply the speed with the angle direction
        if (abs(SL) == abs(SR)):
            speedL = speed * np.sign(SL) 
            speedR = speed * np.sign(SR) 
        elif (abs(SL) > abs(SR)):
            speedL = speed * np.sign(SL) 
            speedR = speed * ((r + (self.AXLE)) / r) * np.sign(SR)
            # speedR = SR/SL*speed * np.sign(SR)
        else:
            speedR = speed * np.sign(SR) 
            speedL = speed * ((r - (self.AXLE)) / r) * np.sign(SL)
            # speedL = SL/SR*speed * np.sign(SL) 

        print("speedL={}, speedR={}".format(speedL, speedR))

        #Map SL and SR to motors A and B according to the radius sign
        #if (r > 0):
        stopAngle_A = -SL / (math.pi*self.WHEEL_RADIUS/180.0)
        stopAngle_B = SR / (math.pi*self.WHEEL_RADIUS/180.0)

        speedA = -speedL
        speedB = speedR

        if stopAngle_A == 0:
            speedA = 0
        if stopAngle_B == 0:
            speedB = 0

        #self.getOdometryXY(SL, SR, r)
        self.setSpeed(speed=speedA, motorID='A', isPercent=False)
        self.setSpeed(speed=speedB, motorID='B', isPercent=False)
        self.setStopPos(stopAngle_A, motorID='A')
        self.setStopPos(stopAngle_B, motorID='B')

        #print("speedA={}, speedB={}, stopangA={}, stopangB={}".format(speedA, speedB, stopAngle_A, stopAngle_B))


    def _compute_odometry_pos(self, angular_dist_A, angular_dist_B, theta):
        """theta in radians
        """
        sA = angular_dist_A
        sB = angular_dist_B

        s = (sA + sB) / 2
        theta = (sA - sB) / self.AXLE

        x = s * math.cos(theta)
        y = s * math.sin(theta)
        
        return x, y

    def getOdometry(self, coordinate):
        if coordinate == 'x':
            idx = 0
            key = 'getPosA'
            goal = 'stopPosA'
        else:
            idx = 1
            key = 'getPosB'
            goal = 'stopPosB'

        res = 0
        #print(self.odometry_data)
        for data in self.odometry_data[:-1]:
            temp_x, temp_y = self._compute_odometry_pos(data[0], data[1], data[2])
            
            if idx == 0:
                res += temp_x
            else:
                res += temp_y

        current_angle = self._read(key)-32768+128
        goal_pos      = self.hardState[goal]['val']-32768+128

        if(np.sign(goal_pos) == 1 and current_angle != 0 and current_angle < goal_pos):
            reached = current_angle / goal_pos * self.odometry_data[-1][idx]
            res += reached
        elif (np.sign(goal_pos) == -1 and current_angle != 0 and current_angle > goal_pos):
            reached = current_angle / goal_pos * self.odometry_data[-1][idx]
            res += reached
        else:
            temp_x, temp_y = self._compute_odometry_pos(self.odometry_data[-1][0], self.odometry_data[-1][1], self.odometry_data[-1][2])
            
            if idx == 0:
                res += temp_x
            else:
                res += temp_y

        #print(res)
        return res

    def resetOdometry(self):
        self.odometry_data = []

    def getRadioChannel(self):
        return self.hardState["radioChannel"]['val']

    def getFirmwareVersion(self):
        version = self._read("firmwareVersion")
        self.waitForSync()
        return version

    def getHardwareVersion(self):
        hw = self._read("hardwareVersion")
        self.waitForSync()

        if hw == 0 or hw == '0':
            return hw

        hw = hex(hw)
        hw = str(hw)[2:]
        hw_byte = bytes.fromhex(hw)
        module_hw = ord(hw_byte) - ord('0')

        return module_hw
