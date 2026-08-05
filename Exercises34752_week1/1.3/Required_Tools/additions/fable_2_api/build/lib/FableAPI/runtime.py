import threading, sys, time, traceback
from .jointManager import JointManager
from .spinManager import SpinManager
from .faceManager import FaceManager
from .ostime import OSTime
from .tools import Tools
from .DEFINES import ControlState, Keys, ModuleTypes

class FableRuntime(threading.Thread):
    def __init__(self, dongle, api):
        self.modules = {}
        self.api = api
        self.dongle = dongle
        self.syncing = False
        self.paused = False
        self.resetState()
        threading.Thread.__init__(self, name='RuntimeThread')


    def resetState(self):
        self.syncCounter = 0
        self.syncTime = 0
        self.commTime = 0
        self.syncTimeGoal = 20

    def run(self):
        while True:
            try:
                if self.dongle.isConnected():
                    self.sync()
                else:
                    time.sleep(0.1)
                while self.paused:
                    time.sleep(0)
            except Exception:
                print("Exception in runtime thread! ", sys.exc_info())
                traceback.print_exc(file=sys.stdout)

    def _getKey(self, moduleID, moduleType):
        #return str(moduleType)+'-'+str(moduleID)
        return str(moduleID)

    def getModuleIDs(self):
        ids = []
        for id in list(self.modules.keys()):
            m = self.modules[id]
            ids.append(m.getSerialID())
        return ids

    def getActiveModuleIDs(self):
        ids = []
        for id in list(self.modules.keys()):
            m = self.modules[id]
            if m.getConnectionQuality() > 0:
                ids.append(m.getSerialID())
            #if m.getSerialID() =='FACE':
                #print(m.getSerialID(), 'has',m.getConnectionQuality(),'quality')
        return ids

    def isAscii(self, string):
        try:
            string.encode('ascii')
        except Exception:
            print("Module with non-ascii name seen!")
            return False
        else:
            return True

    def seenModule(self, moduleID, moduleType, radioID):
        if moduleID is '0': return
        if moduleID is None: return
        if moduleID is 'None': return
        if not self.isAscii(moduleID): return
        key = self._getKey(moduleID, moduleType)
        if not key in self.modules:
            print("Runtime Created", moduleID)
            m = self._createModule(moduleID, moduleType, radioID)
        m = self.modules[key]
        m.setRadioID(radioID)
        m.seen()

    def _createModule(self, moduleID, moduleType, radioID):
        key = self._getKey(moduleID, moduleType)
        if moduleType == ModuleTypes.JOINT:
            self.modules[key] = JointManager(moduleID, radioID, self.dongle, self.api, self)
            return self.modules[key]
        elif moduleType == ModuleTypes.FACE:
            self.modules[key] = FaceManager(moduleID, radioID, self.dongle, self.api, self)
            return self.modules[key]
        elif moduleType == ModuleTypes.SPIN:
             self.modules[key] = SpinManager(moduleID, radioID, self.dongle, self.api, self)
#             self.modules[key].isDummy = dummy
             return self.modules[key]
        else:
            print("Error: Unsupported module type", moduleType)
            return None

    def removeModule(self, moduleID, moduleType):
        key = self._getKey(moduleID, moduleType)
        self.module.pop(key, None)

    def getModule(self, moduleID, moduleType = None):
        if type(moduleID) is int:
            print("Error - use new ID system")
        if len(moduleID) == 3: moduleID = moduleID + ' '
        if moduleType == None:
            moduleType = ModuleTypes.JOINT
        key = self._getKey(moduleID, moduleType)
        if not key in self.modules:
            self._createModule(moduleID, moduleType, None)
            print("ERROR Module", moduleID, "not found! - dummy created")
        return self.modules[key]

    def pause(self):
        self.paused = True
        while self.syncing:
            time.sleep(0)

    def isPaused(self):
        return self.paused

    def restart(self):
        self.paused = False

    def syncQ(self, m):
        if (1 + m.getLastSyncTime()) < OSTime.getOSTime(): #always sync every second (highest priority)
            return True

        if m.isOwnedByAnotherDongle(): #don't sync if it is running a program from another pc
            return False

        if m.getConnectionQuality() > 0: #sync if there is a connection
            return True

        return False
        #if m.getConnectionQuality() > 0:
        #    return True
        #else:
        #    if ((1 + m.getLastSyncTime()) < OSTime.getOSTime()):
        #       return True
        #    return False

    tComp = 0
    def syncSleep(self, wtime):
        endTime = OSTime.getOSTime()+wtime-self.tComp
        sleepTime = wtime-self.tComp
        if sleepTime < 0: sleepTime = 0
        time.sleep(sleepTime)
        self.tComp = OSTime.getOSTime()-endTime

        #endTime = OSTime.getOSTime()+wtime-self.tComp
        #while True:
        #    if endTime > (OSTime.getOSTime()):
        #        time.sleep(0)
        #    else:
        #        if (OSTime.getOSTime()-endTime) > 0.003:
        #            #print('Warning slept more than',round(1000*(endTime-OSTime.getOSTime()),2),'ms too long')
        #            pass
        #        self.tComp = OSTime.getOSTime()-endTime
        #        return

    def sync(self):
        self.syncing = True
        cTime = OSTime.getOSTime()
        for id in list(self.modules.keys()):
            m = self.modules[id]
            if self.syncQ(m):
                success = m.sync()
                #time.sleep(0.01)
                if not success:
                    #print("Unable to sync module", id)
                    pass
            #else:
            #    print("Ignore module", id)
        self.syncCounter = self.syncCounter + 1
        commSyncTime = 1000*(OSTime.getOSTime() - cTime)
        sleepTime = (self.syncTimeGoal - commSyncTime)
        if sleepTime < 0:
            sleepTime = 0
            #print("Warning should  sleep",sleepTime)
        else:
            #time.sleep(sleepTime/1000)
            self.syncSleep(sleepTime/1000)
        fullSyncTime = 1000*(OSTime.getOSTime() - cTime)
        self.commTime = self.commTime + commSyncTime
        self.syncTime = self.syncTime + fullSyncTime
        if self.syncTime > 1000:
            syncDelay = (self.syncTime/self.syncCounter)
#            print(round(OSTime.getOSTime(), 1),
#                  'sec\t', round(syncDelay, 5),
#                  "ms\t", round(1000/syncDelay, 5),
#                  "Hz\t", round(100*self.commTime/self.syncTime, 5), "%")
            self.syncCounter = 0
            self.syncTime = 0
            self.commTime = 0
        self.syncing = False

    def terminate(self):
        self.pause()
        for _, m in self.modules.items():
            m.terminate()
        time.sleep(50/1000) #wait for synchronize to end
        self.resetState()
        self.restart()
