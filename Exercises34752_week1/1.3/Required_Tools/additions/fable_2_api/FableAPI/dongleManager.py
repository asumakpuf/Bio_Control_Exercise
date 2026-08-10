from .tools import Tools
from .dongle import Dongle
from .moduleState import DongleState, ModuleState
from .DEFINES import ControlState, Keys, ModuleTypes

class DongleManager():
    def __init__(self, api, dongle):
        self.api = api
        self.dongle = dongle
        pass
    
    def syncState(self):
        #self.api.updateFirmware()
        self.setSID('9AA')
        self.setName("Fable Dongle 9AA")
        self.setHWVersion(1)
        res, data = self.dongle.getState(ModuleState.STATE_SIZE)
        if res == True:
            state = ModuleState.decode(data)
            print(state)
            print("Dongle Data:")
            print(" SID:", sid)
            print(" Type:", type)
            print(" Firmware:", fwVersion)
            print(" Hardware:", hwVersion)
            print(" Radio channel:", radioChannel)
            print(" Radio ID:", radioID)
            print(" Booth Mode:", boothMode)
            print(" Name:", name)
            print(" Reset Count:", resetCount)
            print(" On Time Count:", onTime)
            print(" Button Count:", buttonCount)
            print(" VCC Error Count:", vccError)
            print(" NRF Spi Count:", nrfSpiError)
            print(" BLE Spi Count:", bleSpiError)
            print(" BLE Comm Count:", bleComError)
        
        
    def setState(self, data, n, defaultValue, startIndex):
        idList = list(data)[0:n]
        if isinstance(defaultValue,str):
            data = [ord(defaultValue)] * n
        else:
            data = [defaultValue] * n
        for i in range(len(idList)):
            data[i] = ord(idList[i])
        res = self.dongle.setState(data, startIndex)
        
    def setHWVersion(self, hwVersion):
        self.setState([chr(hwVersion)], 1, ' ', ModuleState.HARDWARE_VER_ADR)

    def setSID(self, SID):
        self.setState(SID, 4, ' ', ModuleState.SERIAL_NUMBER_ADR_0)
        
    def setName(self, name, enable=True):
        check = "1" if enable else "0"
        self.setState(check+name, 20, 0x00, ModuleState.NAME_ADR_0)
        
    def setColorRGB(self,r,g,b):
        r = Tools.crop(0,255,2.55*r)
        g = Tools.crop(0,255,2.55*g)
        b = Tools.crop(0,255,2.55*b)
        res = self.dongle.setRGBLed(r,g,b)
        return res

    def setColorHex(self, hexColor):
        (r,g,b) = Tools.hex2RGB(hexColor)
        return self.setColorRGB(r, g, b)
    
    def updateFirmware(self):
        self.dongle.bootloader()
        pass
    
