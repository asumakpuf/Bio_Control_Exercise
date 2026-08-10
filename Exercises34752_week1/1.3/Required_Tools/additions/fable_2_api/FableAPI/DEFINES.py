class ControlState():
    running = 1
    paused = 2
    stopped = 3
    terminated = 4
    crashed = 5

class Keys():
    SPACEBAR = 32
    ARROW_UP = 38
    ARROW_DOWN = 40
    ARROW_LEFT = 37
    ARROW_RIGHT = 39

class FaceEmotions():
    NEUTRAL     = 0
    HAPPY       = 1
    SAD         = 2
    ANGRY       = 3
    TIRED       = 4

class SpinEvents():
    @staticmethod
    def getListOfEvents():
        return ['irWrite', 'speedA', 'speedB', 'stopPosA', 'stopPosB', 'posA', 'posB']

    #TODO: Remove once gesture detection is implemented on firmware level
    @staticmethod
    def getKeysToTrack():
        return ['sensor1p', 'sensor2p', 'sensor3p']

class FaceOrientations():
    UNKNOWN                 = 0
    PORTRAIT                = 1
    PORTRAIT_UPSIDE_DOWN    = 2
    LANDSCAPE_LEFT          = 3
    LANDSCAPE_RIGHT         = 4
    FACE_UP                 = 5
    FACE_DOWN               = 6

class ModuleTypes():
    ANY         = 255
    DEVELOPMENT = 0
    DONGLE      = 1
    HEAD        = 2
    JOINT       = 3
    SPIN        = 4
    FACE        = 5

    ''''Passive module types: '''
    BRANCH_4WAY = 51
    FOOT_1WAY   = 52

    @staticmethod
    def getNumberOfConnectors(typeNr):
        if typeNr == ModuleTypes.ANY: return 0
        elif typeNr == ModuleTypes.DEVELOPMENT: return 0
        elif typeNr == ModuleTypes.DONGLE: return 0
        elif typeNr == ModuleTypes.HEAD: return 1
        elif typeNr == ModuleTypes.JOINT: return 2
        elif typeNr == ModuleTypes.NR_DONGLE: return 0
        elif typeNr == ModuleTypes.BRANCH_3WAY: return 3
        elif typeNr == ModuleTypes.BRANCH_4WAY: return 4
        elif typeNr == ModuleTypes.FOOT_1WAY: return 1
        elif typeNr == ModuleTypes.WHEEL: return 1
        return 0

    @staticmethod
    def getNumberOfBatCells(typeNr):
        if typeNr == ModuleTypes.ANY: return 0
        elif typeNr == ModuleTypes.DEVELOPMENT: return 0
        elif typeNr == ModuleTypes.DONGLE: return 0
        elif typeNr == ModuleTypes.HEAD: return 1
        elif typeNr == ModuleTypes.JOINT: return 3
        elif typeNr == ModuleTypes.NR_DONGLE: return 0
        elif typeNr == ModuleTypes.BRANCH_3WAY: return 0
        elif typeNr == ModuleTypes.BRANCH_4WAY: return 0
        elif typeNr == ModuleTypes.FOOT_1WAY: return 0
        elif typeNr == ModuleTypes.WHEEL: return 1
        return 0

    @staticmethod
    def toString(typeNr):
        if typeNr == ModuleTypes.ANY: return 'Any'
        elif typeNr == ModuleTypes.DEVELOPMENT: return 'Development'
        elif typeNr == ModuleTypes.DONGLE: return 'Dongle'
        elif typeNr == ModuleTypes.HEAD: return 'Head'
        elif typeNr == ModuleTypes.JOINT: return 'Joint'
        elif typeNr == ModuleTypes.FACE: return 'Face'
        elif typeNr == ModuleTypes.NR_DONGLE: return 'Neuro Dongle'
        elif typeNr == ModuleTypes.BRANCH_3WAY: return 'Branch 3-Way'
        elif typeNr == ModuleTypes.BRANCH_4WAY: return 'Branch 4-Way'
        elif typeNr == ModuleTypes.FOOT_1WAY: return 'Foot 1-Way'
        elif typeNr == ModuleTypes.WHEEL: return 'Wheel'
        return 'Unknown'