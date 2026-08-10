import serial, time, sys, math, threading
import serial.tools.list_ports
import urllib.request
import json
import traceback
import subprocess, glob, os
from .dongleManager import DongleManager, DongleState
from .moduleState import ModuleState
from .DEFINES import ModuleTypes

class FirmwareUpdate():
    def __init__(self, api):
        self.api = api
        self.key = None
        self.value = None
        self.ser = None
    
    def detectDevices(self):
        devices = {}
        if self.api.pingDongle():
            self.api.dongle.close()
        for port, name, hwid in sorted(serial.tools.list_ports.comports()):
            if ('VID:PID=03EB:FABE' in hwid) or ("Fable " in name):    
                #print("Found device:", name)
                try:
                    #self.ser = serial.Serial(port, 500000, timeout = 0.015, write_timeout = 0.015)
                    self.ser = serial.Serial(port, 500000, timeout = 0.015, write_timeout = 0.015)
                    res, state = ModuleState.load(self.ser)
                    if res == True:
                        devices[port] = state
                 #       print(port,'=>', state['type'], state['ID'], state['hardware version'], state['firmware version'])
                    self.ser.close()
                except:
                    print('Exception while opening:', name, traceback.print_exc(file=sys.stdout))
        return devices
    
    def checkDevice(self, type, id):
        for port, name, hwid in sorted(serial.tools.list_ports.comports()):
            if ('VID:PID=03EB:FABE' in hwid) or ("Fable " in name):
                try:
                    self.ser = serial.Serial(port, 500000, timeout = 0.015, write_timeout = 0.015)
                    res, state = ModuleState.load(self.ser)
                    self.ser.close()
                    if res == True:
                        if type == state['type'] and id == state['ID']:
                            return True
                except:
                    print('Exception while opening:', name)
        return False
        
    def getNewestFirmwareVersion(self, type):
        url = "https://api.github.com/repos/ShapeRobotics/"+type+"-firmware-release/releases/latest"
        try:
            response =  urllib.request.urlopen(url).read().decode('utf-8')
            obj = json.loads(response)
            version = int(obj['tag_name'])
        except:
            return None
        return version
    
    def downloadFirmware(self, type):
        url = "https://api.github.com/repos/ShapeRobotics/"+type+"-firmware-release/releases/latest"
        try:
            response =  urllib.request.urlopen(url).read().decode('utf-8')
            obj = json.loads(response)
            for i in obj['assets']:
                if type in i['name']:
                    driver_link = i['browser_download_url']
                    file_name = type+"Firmware.hex"
                    urllib.request.urlretrieve(driver_link, file_name)
                    return True
        except:
            traceback.print_exc(file=sys.stdout)
            pass
        return False 
    
    def select(self, key, value):
        self.key = key
        self.value = value
        
    def update(self):
        try:
            if self.key == None: return 'No device detected'
            if self.api.pingDongle():
                self.api.dongle.close()
            self.ser = serial.Serial(self.key, 500000, timeout = 0.015, write_timeout = 0.015)
            res, state = ModuleState.load(self.ser)
            if res == False: return 'Unable to communicate with '+state['type']
            res = self.downloadFirmware(state['type'])
            if res == False: return 'Unable to download firmware from server'
            res = self.enterBootloader()
            if res == False: return 'Unable to make '+state['type']+' enter programming mode'
            res = self.doUpgradeFirmware(state['type']+'Firmware.hex', state['type'], state['ID'])
            if res == False: return 'Unable to download firmware to '+state['type']
            return 'Updated '+state['type']+"-"+state['ID']+" successfully!"
        except:
            traceback.print_exc(file=sys.stdout)
            return 'Error while performing firmware update'
    
    def enterBootloader(self):
        try:
            buffer = []
            buffer.append(0xf6)
            buffer.append(0x0f)
            buffer.append(0xab)
            buffer.append(0x1e)
            self.ser.write(bytes(buffer))
            self.ser.flush()
            self.ser.close()
            time.sleep(1)
            return True
        except serial.serialutil.SerialTimeoutException:
            return False
    
    def waitForBootloaderMode(self, device):
        for i in range(10):
            p = subprocess.Popen(['dfu-programmer', device, 'get'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            res = self.outputProcess(p, 'Bootloader')
            time.sleep(0.25)
            if res == True:
                return True
        return False
    
    def doUpgradeFirmware(self, file, type, id):
        if type == 'Dongle':
            device = 'atxmega32a4u'
        elif type == 'Joint': 
            device = 'atxmega64a4u'
        else: 
            return False
        
        res = self.waitForBootloaderMode(device)
        print('-get? ', res)
                
        p = subprocess.Popen('dfu-programmer '+device+' erase', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = self.outputProcess(p, 'Success')
        time.sleep(1)
        print('-erase? ', res)
        
        p = subprocess.Popen('dfu-programmer '+device+' flash '+type+'Firmware.hex', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = self.outputProcess(p, 'Success')
        time.sleep(1)
        print('-flash? ', res)
        
        p = subprocess.Popen('dfu-programmer '+device+' launch', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.outputProcess(p, '')
        time.sleep(2)
        res = self.checkDevice(type, id)
        print('-launch? ', res)
        return True
    
    def readOutput(self, p):
        data =''
        for i in range(100):
            line = p.stdout.readline().decode("utf-8")
            if line != '':
                data = data + line
            line = p.stderr.readline().decode("utf-8")
            if line != '':
                data = data + line
        return data
        
    def outputProcess(self, p, mustContain):
        while p.poll() == None:
            pass
        data = self.readOutput(p)
        return mustContain in data
    

if __name__ == '__main__':
    updater = FirmwareUpdate()
    devices = updater.detectDevices()
    
    print('Done!')