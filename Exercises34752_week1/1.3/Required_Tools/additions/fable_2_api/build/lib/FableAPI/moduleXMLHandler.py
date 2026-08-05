'''
Created on 17/05/2015

@author: djchr
'''
import os.path
import sys
import time, datetime
from xml.etree import ElementTree
import xml.etree.ElementTree as ET

class ModuleXMLHandler():
    def __init__(self, fileName = 'myModules.xml'):
        self.fileName = fileName
        if not os.path.isfile(self.fileName):
            self._createXMLFile(fileName)
            
        try:
            self.tree = ET.parse(self.fileName)
            self.root = self.tree.getroot()
        except:
            print("Broken XML file, creating new",sys.exc_info()[0])
            self._createXMLFile(fileName)
            self.tree = ET.parse(self.fileName)
            self.root = self.tree.getroot()
    
    def _createXMLFile(self, fileName):
        root = ET.Element("data")
        dummy = ET.SubElement(root, "dummy")
        tree = ET.ElementTree(root)
        tree.write(fileName)
    
    def findModule(self, moduleID, moduleType):
        for module in self.root.findall('Module'):
            mid = module.find('id').text
            mtype = module.find('type').text
            if mid == moduleID and mtype == moduleType:
                return module
        return None

    def hasModule(self, moduleID, moduleType):
        if self.findModule(moduleID, moduleType) == None:
            return False
        else:
            return True
    
    def addModule(self, module):
        mType = module.find('type').text
        mID = module.find('id').text
        if not self.hasModule(mID, mType):
            self.root.append(module)
        else:
            #TODO: throw exception?
            return
        
    def createModule(self, moduleID, moduleType, hwVersion = "", swVersion=""):
        element = ElementTree.Element('Module')
        ElementTree.SubElement(element, 'type').text = moduleType
        ElementTree.SubElement(element, 'id').text = str(moduleID)
        ElementTree.SubElement(element, 'first_seen_raw').text = str(time.clock())
        ElementTree.SubElement(element, 'last_seen_raw').text = str(time.clock())
        ElementTree.SubElement(element, 'first_seen').text = time.asctime()
        ElementTree.SubElement(element, 'last_seen').text = time.asctime()
        ElementTree.SubElement(element, 'hw_version').text = hwVersion
        ElementTree.SubElement(element, 'sw_version').text = swVersion
        return element
    
    def removeModule(self, moduleID, moduleType):
        module = self.findModule(moduleID, moduleType)
        if not module == None:
            self.root.remove(module)
                
    def seenModule(self, moduleID, moduleType):
        #print("Seen module: ", moduleID,", ", moduleType)
        module = self.findModule(moduleID, moduleType)
        if not module == None:
            #print("Seen it before, booring...")
            module.find("last_seen").text = time.asctime()
            module.find("last_seen_raw").text = str(time.clock())
            self.saveModules() #TODO: Do something more efficient that writing direclty to the file here! 
        else: 
            print("Creating module module: ", moduleID,", ", moduleType)
            module = self.createModule(moduleID, moduleType)
            self.addModule(module)
            self.saveModules()
    
    def getAllModulesSeen(self):
        moduleList = []
        for module in self.root.findall('Module'):
            mtype = module.find('type').text
            mid = module.find('id').text
            moduleList.append([mid,mtype])
        return moduleList

    def getResentModules(self, n, moduleTypes):
        moduleList = []
        for module in self.root.findall('Module'):
            mtype = module.find('type').text
            if moduleTypes.count(mtype) > 0 or moduleTypes.count('any') > 0:
                #moduleList.append(int(module.find('id').text))
                moduleList.append(module.find('id').text)
                #print(module.find('id').text, '->',module.find("last_seen").text)
                #moduleList.append("ABA")
        return moduleList
    #find n modules which has been seen the last        
    '''def :
        moduleList = []
        for module in self.root.findall('Module'):
            mtype = module.find('type').text
            if moduleTypes.count(mtype) > 0 or moduleTypes.count('any') > 0:
                moduleList.append(module)
        #TODO: sort list here
        #print(datetime.strptime(m.find("last_seen").text))
        #moduleList.sort(key=lambda m: datetime.strptime(m.find("last_seen").text, "%b %d %H:%M:%S %Y"), reverse=False)
        return moduleList[0:n]'''
    
    def saveModules(self):
        self.tree.write(self.fileName)
        
    
if __name__ == '__main__':          
    xmlHandler = ModuleXMLHandler("myModules_test.xml")
    module = xmlHandler.createModule('9', "joint", "2.1", "12")
    xmlHandler.addModule(module)
    module = xmlHandler.createModule('11', "joint", "2.1", "12")
    xmlHandler.addModule(module)
    module = xmlHandler.createModule('13', "joint", "2.1", "12")
    xmlHandler.addModule(module)
    time.sleep(3)
    xmlHandler.seenModule('9', "joint")
    xmlHandler.removeModule('13', "joint")
    print("Find module id=13? ", xmlHandler.findModule('13', 'joint'))
    print("Find module id=9? ", xmlHandler.findModule('9', 'joint'))
    print("Get rescent modules: ",xmlHandler.getResentModules(n=10, moduleTypes = ["any"]))
    xmlHandler.saveModules()


