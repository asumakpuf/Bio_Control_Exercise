from .tools import Tools
from .dongle import Dongle
from .ostime import OSTime
from .DEFINES import ControlState, Keys, ModuleTypes
import time, sys, copy
from .moduleState import JointState, ModuleState

class JointManager():
    def __init__(self, moduleID, radioID, dongle, api, runtime):
        self.dongle = dongle
        self.api = api
        self.runtime = runtime
        self.syncCounter = 0
        self.lastSyncTime = OSTime.getOSTime()
        self.lastSyncSendTime = OSTime.getOSTime()
        self.syncErrorCount = 0
        self.newerSeen = True
        self.used = False
        self.hasBeenReset = False
        self.syncHistory = []
        self.defaultState = {
                        # State Stored in EEPROM
                          'serialID' : {'val': moduleID, 'type': 'p', 'adr_list': [ModuleState.SERIAL_NUMBER_ADR_0, ModuleState.SERIAL_NUMBER_ADR_1, ModuleState.SERIAL_NUMBER_ADR_2, ModuleState.SERIAL_NUMBER_ADR_3], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'type' : {'val': ModuleTypes.JOINT, 'type': 'p', 'adr_list': [ModuleState.TYPE_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1 , 'lastWrite' : -1},
                          'firmwareVersion' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.FIRMWARE_VER_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'hardwareVersion' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.HARDWARE_VER_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'resetCount' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.RESET_COUNT_ADR_0, ModuleState.RESET_COUNT_ADR_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'onTime' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.ON_TIME_ADR_0, ModuleState.ON_TIME_ADR_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'radioChannel' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.RADIO_CHANNEL_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'radioID' : {'val': radioID, 'type': 'p', 'adr_list': [ModuleState.RADIO_ID_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'boothMode' : {'val': 0, 'type': 'p', 'adr_list': [ModuleState.BOOTH_MODE_ADR], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'name' : {'val': '', 'type': 'p', 'adr_list': [ModuleState.NAME_ADR_0, ModuleState.NAME_ADR_1, ModuleState.NAME_ADR_2, ModuleState.NAME_ADR_3, ModuleState.NAME_ADR_4, ModuleState.NAME_ADR_5, ModuleState.NAME_ADR_6, ModuleState.NAME_ADR_7, ModuleState.NAME_ADR_8, ModuleState.NAME_ADR_9, ModuleState.NAME_ADR_10, ModuleState.NAME_ADR_11, ModuleState.NAME_ADR_12, ModuleState.NAME_ADR_13, ModuleState.NAME_ADR_14, ModuleState.NAME_ADR_15, ModuleState.NAME_ADR_16, ModuleState.NAME_ADR_17, ModuleState.NAME_ADR_18, ModuleState.NAME_ADR_19 ], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                        # State of servo write paramters
                          'posX' : {'val': 0, 'type': 'w', 'adr_list': [JointState.X_GOAL_POS_0, JointState.X_GOAL_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'posY' : {'val': 0, 'type': 'w', 'adr_list': [JointState.Y_GOAL_POS_0, JointState.Y_GOAL_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'speedX' : {'val': 0, 'type': 'w', 'adr_list': [JointState.X_MOVING_SPEED_0, JointState.X_MOVING_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'speedY' : {'val': 0, 'type': 'w', 'adr_list': [JointState.Y_MOVING_SPEED_0, JointState.Y_MOVING_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'torqueLimitX' : {'val': -1, 'type': 'w', 'adr_list': [JointState.X_TORQUE_LIMIT_0, JointState.X_TORQUE_LIMIT_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'torqueLimitY' : {'val': -1, 'type': 'w', 'adr_list': [JointState.Y_TORQUE_LIMIT_0, JointState.Y_TORQUE_LIMIT_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CWComplianceMarginX' : {'val': -1, 'type': 'w', 'adr_list': [JointState.X_CW_COMPLIANCE_MARGIN], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CWComplianceMarginY' : {'val': -1, 'type': 'w', 'adr_list': [JointState.Y_CW_COMPLIANCE_MARGIN], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CCWComplianceMarginX' : {'val': -1, 'type': 'w', 'adr_list': [JointState.X_CCW_COMPLIANCE_MARGIN], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CCWComplianceMarginY' : {'val': -1, 'type': 'w', 'adr_list': [JointState.Y_CCW_COMPLIANCE_MARGIN], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CWComplianceSlopeX' : {'val': -1, 'type': 'w', 'adr_list': [JointState.X_CW_COMPLIANCE_SLOPE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CWComplianceSlopeY' : {'val': -1, 'type': 'w', 'adr_list': [JointState.Y_CW_COMPLIANCE_SLOPE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CCWComplianceSlopeX' : {'val': -1, 'type': 'w', 'adr_list': [JointState.X_CCW_COMPLIANCE_SLOPE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'CCWComplianceSlopeY' : {'val': -1, 'type': 'w', 'adr_list': [JointState.Y_CCW_COMPLIANCE_SLOPE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'punchX' : {'val': 0, 'type': 'w', 'adr_list': [JointState.X_PUNCH_0, JointState.X_PUNCH_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'punchY' : {'val': 0, 'type': 'w', 'adr_list': [JointState.Y_PUNCH_0, JointState.Y_PUNCH_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'torqueEnableX' : {'val': 0, 'type': 'w', 'adr_list': [JointState.X_TORQUE_ENABLE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'torqueEnableY' : {'val': 0, 'type': 'w', 'adr_list': [JointState.Y_TORQUE_ENABLE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                        # State of servo read paramters
                          'currentPosX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_CURRENT_POS_0, JointState.X_CURRENT_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentPosY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_CURRENT_POS_0, JointState.Y_CURRENT_POS_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentSpeedX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_SPEED_0, JointState.X_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentSpeedY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_SPEED_0, JointState.Y_SPEED_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentLoadX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_LOAD_0, JointState.X_LOAD_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentLoadY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_LOAD_0, JointState.Y_LOAD_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentMovingX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_MOVING], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentMovingY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_MOVING], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'voltageX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_VOLTAGE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'voltageY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_VOLTAGE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'temperatureX' : {'val': 0, 'type': 'r', 'adr_list': [JointState.X_TEMPERATURE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'temperatureY' : {'val': 0, 'type': 'r', 'adr_list': [JointState.Y_TEMPERATURE], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},

                        # State of module paramters not in EEPROM
                          'ledRGB' : {'val': [0,0,0], 'type': 'w', 'adr_list': [JointState.LED_R, JointState.LED_G, JointState.LED_B], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'batteryLevel' : {'val': 0, 'type': 'r', 'adr_list': [JointState.BATTERY_LEVEL_0, JointState.BATTERY_LEVEL_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'vccLevel' : {'val': 0, 'type': 'r', 'adr_list': [JointState.VCC_LEVEL_0, JointState.VCC_LEVEL_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'currentFlow' : {'val': 0, 'type': 'r', 'adr_list': [JointState.CURRENT_FLOW_0, JointState.CURRENT_FLOW_1], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'charging' : {'val': False, 'type': 'r', 'adr_list': [JointState.CHARGING], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1},
                          'status' : {'val': 0, 'type': 'w', 'adr_list': [JointState.JOINT_STATUS], 'sync': False, 'period' : 0, 'lastSync' : -1, 'lastWrite' : -1}

        }
        self.softState = copy.deepcopy(self.defaultState)
        self.hardState = copy.deepcopy(self.defaultState)
        self.servoKeys = {'posX','posY','speedX','speedY','torqueLimitX','torqueLimitY','CWComplianceMarginX','CWComplianceMarginY','CCWComplianceMarginX', 'CCWComplianceMarginY','CWComplianceSlopeX',
'CWComplianceSlopeY','CCWComplianceSlopeX','CCWComplianceSlopeY','punchX','punchY','torqueEnableX','torqueEnableY','currentPosX','currentPosY','currentSpeedX', 'currentSpeedY',
'currentLoadX', 'currentLoadY','currentMovingX','currentMovingY','voltageX','voltageY','temperatureX','temperatureY'}

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
        if self.softState[key]['sync'] == True:
            nextSyncTime = (self.softState[key]['lastSync'] + self.softState[key]['period'])
            if OSTime.getOSTime() >= nextSyncTime:
                return True
        return False

    def sync(self):
        self.lastSyncTime = OSTime.getOSTime()
        radioID = self.softState['radioID']['val']
        if radioID == None:
            self.syncCounter = self.syncCounter + 1
            self.saveSyncHistory('error')
            return False
        headerData = [ModuleTypes.JOINT, radioID, 252] # use sync state command
        writeData = []
        readData = []
        writeKeys = []
        readKeys = []
        readAdrs = []
        for key, val in self.softState.items():
            value = self.softState[key]['val']
            adrs = self.softState[key]['adr_list']
            if len(headerData+writeData+readData) >= 26:
                break
                #print('Data packet is full!')
            #print(len(headerData+writeData+readData))
            if self.doWrite(key):
                self.used = True
                writeKeys.append(key)
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
                for adr in adrs:
                    readData.append(0x80|adr)
                    readAdrs.append(adr)
                self.softState[key]['lastSync'] = OSTime.getOSTime()

        data = headerData+writeData+readData
        if len(data) != 3 or (self.lastSyncSendTime + 0.5) < OSTime.getOSTime() :
            self.lastSyncSendTime = OSTime.getOSTime()
            #print('[',len(data),'/30] =>', data)
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
        #ignoreCount = self.syncHistory.count('ignore')
        self.syncHistory.count('ignore')
        syncQuality = 100
        if (errorCount+okCount) !=0:
            syncQuality = 100*okCount/(errorCount+okCount)
        #print('Quality =',syncQuality, "ok", okCount, "err", errorCount, 'ignore', ignoreCount)
        return syncQuality

    def restoreStateAfterReset(self):
        for key, val in self.softState.items():
            if self.softState[key]['lastWrite'] != -1 and not key is 'status':
                #print('updating keys ', key,'->', self.softState[key]['val'])
                self.hardState[key]['val'] = 0 
            #print(key)
    
    def isOwnedByAnotherDongle(self):
        return self.hardState['status']['val'] == JointState.STATUS_LOCKED 
    
    def handleSyncReturnMessage(self, packet, readKeys, readAdrs):
        index = 5
        status = self.hardState['status']['val']
        if status == JointState.STATUS_LOCKED:
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
        return True

    def sendSyncMessage(self, headerData, writeData, readData):
        radioPacket = headerData+writeData+readData
        nReply = 5+len(readData)
        #self.api.bootstrap()
        #self.api.lock.acquire()
        #tt = OSTime.getOSTime()
        res = self.dongle.writeRadioPacket(radioPacket)
        self.api.handleResult(res)
        if res == False:
            print(self.getSerialID()+": Failed writing sync packet")
            return False, []
        packet = self.dongle.readPacket(nReply, 1) #TODO: figure out why this extended delay is nessecary?
        #print(self.getSerialID()+": Lag = ", 1000*(OSTime.getOSTime()-tt), ' n =',nReply)
        #print('Joint',self.getSerialID(),'delay: ', round(1000*(OSTime.getOSTime()-tt), 0), 'ms',len(packet))
        if not len(packet) >= 5:
            #print(self.getSerialID()+": Return packet too short",len(packet))
            return False, packet
        status = packet[4]
        if packet[0] != ord('#'):
            print("packet !=#",packet[0])
            return False, packet
        senderType = packet[2]
        if senderType != ModuleTypes.JOINT:
            print("type != Joint!",packet[2])
            return False, packet
        senderID = packet[3]
        if senderID != self.getRadioID():
            print("sender RadioID not as expected while sync!",senderID, self.getRadioID())
            return False, packet
        if self.hardState['status']['val'] != status:
            #print('reset? old:', self.hardState['status']['val'], 'new:',status)
            self.hardState['status']['val'] = status
            if (status ==  JointState.STATUS_READY) or (status ==  JointState.STATUS_RUNNING):
                #print('Module has been reset', status)
                self.hasBeenReset = True
        if self.hardState['status']['val'] == JointState.STATUS_BOOT:
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
        if self.used:
            self.dongle.writeRadioPacket([self.getType(), self.getRadioID(), 246])
        self.softState = copy.deepcopy(self.defaultState)
        self.hardState = copy.deepcopy(self.defaultState)
        self.syncCounter = 0
        self.syncErrorCount = 0
        self.used = False

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

    def setPos(self, pos, motorID):
        if not type(pos) in [int, float]: return -1
        key = "posX" if motorID in [0, 'x', 'X'] else "posY"
        val = 3.41333333*pos+512
        self.softState[key]['val'] = int(round(val, 0))
        return 0
        #time.sleep(0.001)
        #val = (1024*(Tools.crop(-90, 90, pos, returnType=float)+150))/300
        #self.softState[key]['val'] = int(round(val, 0))
        
    def setSpeed(self, speed, motorID):
        if not type(speed) in [int, float]: return -1
        key = "speedX" if motorID in [0, 'x', 'X'] else "speedY"
        # Speed Limit is set to 1-500 of a maximum 1023
        self.softState[key]['val'] = int(5*Tools.crop(1, 100, speed)) # speed =0  equals unlimited speed
        return 0
    
    def setTorqueLimit(self, torqueLimit, motorID):
        if not type(torqueLimit) in [int, float]: return -1
        key = "torqueLimitX" if motorID in [0, 'x', 'X'] else "torqueLimitY"
        # scale torque in range 1-900 (0 will be overwritten)
        self.softState[key]['val'] = int(Tools.crop(1, 600, 6*torqueLimit))
        # Torque limit is set to 800 of a maximum 1023
        return 0
            
    def setComplianceMargin(self, complianceMargin, direc, motorID):
        if not type(complianceMargin) in [int, float]: return
        key = "CWComplianceMargin" if direc > 0 else "CCWComplianceMargin"
        key = key + "X" if motorID in [0, 'x', 'X'] else key +"Y"
        self.softState[key]['val'] = int(Tools.crop(0, 255, complianceMargin))

    def setComplianceSlope(self, complianceSlope, direc, motorID):
        if not type(complianceSlope) in [int, float]: return
        key = "CWComplianceSlope" if direc > 0 else "CCWComplianceSlope"
        key = key + "X" if motorID in [0, 'x', 'X'] else key +"Y"
        self.softState[key]['val'] = int(Tools.crop(0, 255, complianceSlope))

    def setPunch(self, punch, motorID):
        if not type(punch) in [int, float]: return
        key = "punchX" if motorID in [0, 'x', 'X'] else "punchY"
        self.softState[key]['val'] = int(Tools.crop(32, 1024, punch))

    def setTorqueEnable(self, torqueEnable, motorID):
        if not type(torqueEnable) in [bool, int]: return
        key = "torqueEnableX" if motorID in [0, 'x', 'X'] else "torqueEnableY"
        self.softState[key]['val'] = bool(torqueEnable)

    def clearStatus(self):
        self.softState["status"]['val'] = JointState.STATUS_READY
    
    def getStatus(self):
        return self.hardState['status']['val']
    
    def setRGBLed(self, r, g, b):
        r = Tools.crop(0,255,2.55*r)
        g = Tools.crop(0,255,2.55*g)
        b = Tools.crop(0,255,2.55*b)
        self.softState["ledRGB"]['val'] = [r,g,b]

    def setRadioID(self, newRadioID):
        self.softState['radioID']['val'] = newRadioID

    def setSerialID(self, newSID):
        self.softState['serialID']['val'] = newSID

    def _read(self, key):
        if self.softState[key]['sync'] == False:
            self.softState[key]['sync'] = True
            self.waitForSync() # not read before, wait until true value is resent
        return self.softState[key]['val']

    def getPos(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'currentPosX'
        else: key = 'currentPosY'
        #if motorID == 0: print('Z:', self.softState['posX']['val'], self.hardState['currentPosX']['val'])
        
        return self._read(key)

    def getSpeed(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'currentSpeedX'
        else: key = 'currentSpeedY'
        return self._read(key)

    def getLoad(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'currentLoadX'
        else: key = 'currentLoadY'
        return self._read(key)

    def getMoving(self, motorID):
        if motorID in [0, 'x', 'X']: key = 'currentMovingX'
        else: key = 'currentMovingY'
        return self._read(key)

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
        return ModuleTypes.JOINT

    def getBatteryLevel(self):
        s = self.softState['batteryLevel']
        if s['sync'] == False:
            s['sync']       = True      # start the synchronization
            s['lastSync']   = -100      # trigger an update ASAP
            s['period']     = 1.0       # update every periods seconds
            self.waitForSync()
        return s['val']
