from .DEFINES import ControlState, Keys, ModuleTypes
import time

class ModuleState():
    SERIAL_NUMBER_ADR_0                 =    0
    SERIAL_NUMBER_ADR_1                 =    1
    SERIAL_NUMBER_ADR_2                 =    2
    SERIAL_NUMBER_ADR_3                 =    3
    TYPE_ADR                            =    4
    FIRMWARE_VER_ADR                    =    5
    HARDWARE_VER_ADR                    =    6
    RADIO_CHANNEL_ADR                   =    7
    RADIO_ID_ADR                        =    8
    BOOTH_MODE_ADR                      =    9
    NAME_ADR_0                          =    10
    NAME_ADR_1                          =    11
    NAME_ADR_2                          =    12
    NAME_ADR_3                          =    13
    NAME_ADR_4                          =    14
    NAME_ADR_5                          =    15
    NAME_ADR_6                          =    16
    NAME_ADR_7                          =    17
    NAME_ADR_8                          =    18
    NAME_ADR_9                          =    19
    NAME_ADR_10                         =    20
    NAME_ADR_11                         =    21
    NAME_ADR_12                         =    22
    NAME_ADR_13                         =    23
    NAME_ADR_14                         =    24
    NAME_ADR_15                         =    25
    NAME_ADR_16                         =    26
    NAME_ADR_17                         =    27
    NAME_ADR_18                         =    28
    NAME_ADR_19                         =    29
    RESET_COUNT_ADR_0                   =    30
    RESET_COUNT_ADR_1                   =    31
    ON_TIME_ADR_0                       =    32
    ON_TIME_ADR_1                       =    33
    BUTTON_PRESS_ADR_0                  =    34
    BUTTON_PRESS_ADR_1                  =    35
    VOLTAGE_3V3_RANGE_ERROR_ADR_0       =    36
    VOLTAGE_3V3_RANGE_ERROR_ADR_1       =    37
    NRF24_SPI_ERROR_ADR_0               =    38
    NRF24_SPI_ERROR_ADR_1               =    39
    STATE_SIZE                          =    40

    @staticmethod
    def decode(state):
        data = state
        sid = chr(data[ModuleState.SERIAL_NUMBER_ADR_0]) + chr(data[ModuleState.SERIAL_NUMBER_ADR_1]) + chr(data[ModuleState.SERIAL_NUMBER_ADR_2])+ chr(data[ModuleState.SERIAL_NUMBER_ADR_3])
        type = ModuleTypes.toString(data[ModuleState.TYPE_ADR])
        fwVersion = data[ModuleState.FIRMWARE_VER_ADR]
        hwVersion = data[ModuleState.HARDWARE_VER_ADR]
        radioChannel = data[ModuleState.RADIO_CHANNEL_ADR]
        radioID = data[ModuleState.RADIO_ID_ADR]
        boothMode = data[ModuleState.BOOTH_MODE_ADR]
        resetCount = data[ModuleState.RESET_COUNT_ADR_0] + 256*data[ModuleState.RESET_COUNT_ADR_1]
        onTime = 10*(data[ModuleState.ON_TIME_ADR_0] + 256*data[ModuleState.ON_TIME_ADR_1])
        buttonCount = data[ModuleState.BUTTON_PRESS_ADR_0] + 256*data[ModuleState.BUTTON_PRESS_ADR_1]
        vccError = data[ModuleState.VOLTAGE_3V3_RANGE_ERROR_ADR_0] + 256*data[ModuleState.VOLTAGE_3V3_RANGE_ERROR_ADR_1]
        nrfSpiError = data[ModuleState.NRF24_SPI_ERROR_ADR_0] + 256*data[ModuleState.NRF24_SPI_ERROR_ADR_1]
        name =''
        for i in range(20):
            name = name + chr(data[ModuleState.NAME_ADR_0+i])

        state =  {
            'name' : name,
            'ID' : sid,
            'type' : type,
            'firmware version' : fwVersion,
            'hardware version' : hwVersion,
            'radio channel' : radioChannel,
            'radio ID' : radioID,
            'booth mode' : boothMode,
            'reset count' : resetCount,
            'on time' : onTime,
            'button count' : buttonCount,
            'vcc errors' : vccError,
            'nrf spi errors' : nrfSpiError,
        }
        return state

    @staticmethod
    def load(serial):
        serial.write(bytes([0xf8, ModuleState.STATE_SIZE, 0]))
        serial.flush()
        reply = serial.read(ModuleState.STATE_SIZE)

        if len(reply) ==  ModuleState.STATE_SIZE:
            state = ModuleState.decode(reply)
            return True, state
        else:
            return False, None

class DongleState():
    BLE_SPI_ERROR_ADR_0                 =    40
    BLE_SPI_ERROR_ADR_1                 =    41
    BLE_COMM_ERROR_ADR_0                =    42
    BLE_COMM_ERROR_ADR_1                =    43
    STATE_SIZE                          =    44
    @staticmethod
    def decode(state):
        data = state
        bleSpiError = data[DongleState.BLE_SPI_ERROR_ADR_0] + 256*data[DongleState.BLE_SPI_ERROR_ADR_1]
        bleComError = data[DongleState.BLE_COMM_ERROR_ADR_1] + 256*data[DongleState.BLE_COMM_ERROR_ADR_1]
        state =  {
            'ble spi errors' : bleSpiError,
            'ble com errors' : bleComError
        }
        state.update(ModuleState.decode(data))
        return state

class JointState():
    CHARGE_TIME_ADR_0                       = 40
    CHARGE_TIME_ADR_1                       = 41
    HIGH_LOAD_TIME_ADR_0                    = 42
    HIGH_LOAD_TIME_ADR_1                    = 43

    #Event counters - Errors Specific for Joint
    SELF_PROTECT_LOW_BATT_ADR_0             = 44    # Self-protect due to low battery
    SELF_PROTECT_LOW_BATT_ADR_1             = 45
    SELF_PROTECT_HIGH_LOAD_ADR_0            = 46    # Self-protect high load
    SELF_PROTECT_HIGH_LOAD_ADR_1            = 47
    COMM_FAIL_SERVO_X_ADR_0                 = 48    # Servo X COMM If communication fails, count every 100 errors (but this always happens at high load!)
    COMM_FAIL_SERVO_X_ADR_1                 = 49
    COMM_FAIL_SERVO_Y_ADR_0                 = 50    # Servo Y COMM If communication fails, count every 100 errors (but this always happens at high load!)
    COMM_FAIL_SERVO_Y_ADR_1                 = 51
    VOLTAGE_12V_RANGE_ERROR_ADR_0           = 52    # Voltage 12v - if voltage is outside 11-13v range (count every 10 minutes)
    VOLTAGE_12V_RANGE_ERROR_ADR_1           = 53
    BATTERY_LOW_ERROR_ADR_0                 = 54    # average battery level measured lower than 3.3v (count every 10 minutes)
    BATTERY_LOW_ERROR_ADR_1                 = 55
    BATTERY_HIGH_ERROR_ADR_0                = 56    # average battery level measured higher than 4.3v (count every 10 minutes)
    BATTERY_HIGH_ERROR_ADR_1                = 57
    BATTERY_DROP_ERROR_ADR_0                = 58    # battery observed to drop more than 0.9v within 1 second in active mode (count # of drops)
    BATTERY_DROP_ERROR_ADR_1                = 59
    BATTERY_LEAK_ERROR_ADR_0                = 60    # Voltage Battery Leak - battery level observed to have dropped more than 0.3v after power down
    BATTERY_LEAK_ERROR_ADR_1                = 61


    # RAM STATE
    X_GOAL_POS_0                        = 62
    X_GOAL_POS_1                        = 63
    X_MOVING_SPEED_0                    = 64
    X_MOVING_SPEED_1                    = 65
    X_CURRENT_POS_0                     = 66
    X_CURRENT_POS_1                     = 67
    X_SPEED_0                           = 68
    X_SPEED_1                           = 69
    X_LOAD_0                            = 70
    X_LOAD_1                            = 71
    X_TORQUE_LIMIT_0                    = 72
    X_TORQUE_LIMIT_1                    = 73
    X_CW_COMPLIANCE_MARGIN              = 74
    X_CCW_COMPLIANCE_MARGIN             = 75
    X_CW_COMPLIANCE_SLOPE               = 76
    X_CCW_COMPLIANCE_SLOPE              = 77
    X_PUNCH_0                           = 78
    X_PUNCH_1                           = 79
    X_TORQUE_ENABLE                     = 80
    X_MOVING                            = 81
    X_VOLTAGE                           = 82
    X_TEMPERATURE                       = 83

    Y_GOAL_POS_0                        = 84
    Y_GOAL_POS_1                        = 85
    Y_MOVING_SPEED_0                    = 86
    Y_MOVING_SPEED_1                    = 87
    Y_CURRENT_POS_0                     = 88
    Y_CURRENT_POS_1                     = 89
    Y_SPEED_0                           = 90
    Y_SPEED_1                           = 91
    Y_LOAD_0                            = 92
    Y_LOAD_1                            = 93
    Y_TORQUE_LIMIT_0                    = 94
    Y_TORQUE_LIMIT_1                    = 95
    Y_CW_COMPLIANCE_MARGIN              = 96
    Y_CCW_COMPLIANCE_MARGIN             = 97
    Y_CW_COMPLIANCE_SLOPE               = 98
    Y_CCW_COMPLIANCE_SLOPE              = 99
    Y_PUNCH_0                           = 100
    Y_PUNCH_1                           = 101
    Y_TORQUE_ENABLE                     = 102
    Y_MOVING                            = 103
    Y_VOLTAGE                           = 104
    Y_TEMPERATURE                       = 105

    LED_R                               = 106
    LED_G                               = 107
    LED_B                               = 108
    BATTERY_LEVEL_0                     = 109
    BATTERY_LEVEL_1                     = 110
    VCC_LEVEL_0                         = 111
    VCC_LEVEL_1                         = 112
    CURRENT_FLOW_0                      = 113
    CURRENT_FLOW_1                      = 114
    CHARGING                            = 115
    JOINT_STATUS                        = 116

    STATE_SIZE                          = 117

    STATUS_BOOT                         = 0
    STATUS_READY                        = 1
    STATUS_LOAD_ERROR                   = 2
    STATUS_DIST_ERROR                   = 3
    STATUS_LOW_BATTERY                  = 4
    STATUS_RUNNING                      = 5
    STATUS_LOCKED                       = 6

    @staticmethod
    def decode(state):
        data = state
        chargeTime = data[JointState.CHARGE_TIME_ADR_0] + 256*data[JointState.CHARGE_TIME_ADR_1]
        highLoadTime = data[JointState.HIGH_LOAD_TIME_ADR_0] + 256*data[JointState.HIGH_LOAD_TIME_ADR_1]
        state =  {
            'charge time' : chargeTime,
            'high load time' : highLoadTime
        }
        state.update(ModuleState.decode(data))
        return state

class FaceState():
    STATUS_READY                    = 0
    STATUS_RUNNING                  = 1

    COMM_FAIL                       = 40 # Not connected to a Face

    # RAM STATE

    BATTERY_LEVEL_0                 = 41
    BATTERY_LEVEL_1                 = 42
    FACE_STATUS                     = 43

    ## Emotion
    EMOTION_CURRENT                 = 44 # GET emotion

    EMOTION_GOAL                    = 45 # SET emotion

    ## Focus
    FOCUS_CURRENT_X_0               = 46 # GET focus
    FOCUS_CURRENT_X_1               = 47
    FOCUS_CURRENT_Y_0               = 48
    FOCUS_CURRENT_Y_1               = 49
    FOCUS_CURRENT_Z_0               = 50
    FOCUS_CURRENT_Z_1               = 51

    FOCUS_GOAL_X_0                  = 52 # SET focus
    FOCUS_GOAL_X_1                  = 53
    FOCUS_GOAL_Y_0                  = 54
    FOCUS_GOAL_Y_1                  = 55
    FOCUS_GOAL_Z_0                  = 56
    FOCUS_GOAL_Z_1                  = 57

    ## Orientation
    ORIENTATION_CURRENT             = 58

    ## Compass
    COMPASS_CURRENT_0               = 59
    COMPASS_CURRENT_1               = 60

    ## Acceleration
    ACCELERATION_CURRENT_X_0        = 61
    ACCELERATION_CURRENT_X_1        = 62
    ACCELERATION_CURRENT_Y_0        = 63
    ACCELERATION_CURRENT_Y_1        = 64
    ACCELERATION_CURRENT_Z_0        = 65
    ACCELERATION_CURRENT_Z_1        = 66

    STATE_SIZE                      = 67

    @staticmethod
    def decode(state):
        data = state
        state.update(ModuleState.decode(data))
        return state

class SpinState():
#moduleState_t
    CHARGE_TIME_ADR_0                       = 40
    CHARGE_TIME_ADR_1                       = 41
    HIGH_LOAD_TIME_ADR_0                    = 42
    HIGH_LOAD_TIME_ADR_1                    = 43
    
    SELF_PROTECT_LOW_BATT_ADR_0             = 44    # Self-protect due to low battery
    SELF_PROTECT_LOW_BATT_ADR_1             = 45
    SELF_PROTECT_HIGH_LOAD_ADR_0            = 46    # Self-protect high load
    SELF_PROTECT_HIGH_LOAD_ADR_1            = 47
    COMM_FAIL_SERVO_X_ADR_0                 = 48    # Servo X COMM If communication fails, count every 100 errors (but this always happens at high load!)
    COMM_FAIL_SERVO_X_ADR_1                 = 49
    COMM_FAIL_SERVO_Y_ADR_0                 = 50    # Servo Y COMM If communication fails, count every 100 errors (but this always happens at high load!)
    COMM_FAIL_SERVO_Y_ADR_1                 = 51
    VOLTAGE_12V_RANGE_ERROR_ADR_0           = 52    # Voltage 12v - if voltage is outside 11-13v range (count every 10 minutes)
    VOLTAGE_12V_RANGE_ERROR_ADR_1           = 53
    BATTERY_LOW_ERROR_ADR_0                 = 54    # average battery level measured lower than 3.3v (count every 10 minutes)
    BATTERY_LOW_ERROR_ADR_1                 = 55
    BATTERY_HIGH_ERROR_ADR_0                = 56    # average battery level measured higher than 4.3v (count every 10 minutes)
    BATTERY_HIGH_ERROR_ADR_1                = 57
    BATTERY_DROP_ERROR_ADR_0                = 58    # battery observed to drop more than 0.9v within 1 second in active mode (count # of drops)
    BATTERY_DROP_ERROR_ADR_1                = 59
    BATTERY_LEAK_ERROR_ADR_0                = 60    # Voltage Battery Leak - battery level observed to have dropped more than 0.3v after power down
    BATTERY_LEAK_ERROR_ADR_1                = 61
    
#genericState_t
    LED_R								    = 62
    LED_G								    = 63
    LED_B								    = 64
    BATTERY_LEVEL_0						    = 65
    BATTERY_LEVEL_1						    = 66
    VCC_LEVEL_0							    = 67
    VCC_LEVEL_1							    = 68
    A_TORQUE				    		    = 69
    B_TORQUE    						    = 70
    CHARGING							    = 71
    SPIN_STATUS     						= 72

    A_GOAL_POS_0						    = 73
    A_GOAL_POS_1						    = 74
    A_GOAL_SPEED_0 						    = 75
    A_GOAL_SPEED_1 						    = 76
    A_GOAL_STOP_POS_0					    = 77
    A_GOAL_STOP_POS_1					    = 78
    A_CURRENT_SPEED_0					    = 79
    A_CURRENT_SPEED_1					    = 80
    A_CURRENT_POS_0						    = 81
    A_CURRENT_POS_1						    = 82
    A_ACHIEVED_STOP_POS					    = 83
    A_RESET_ENCODER					        = 84

    B_GOAL_POS_0						    = 85
    B_GOAL_POS_1						    = 86
    B_GOAL_SPEED_0 						    = 87
    B_GOAL_SPEED_1 						    = 88
    B_GOAL_STOP_POS_0					    = 89
    B_GOAL_STOP_POS_1					    = 90
    B_CURRENT_SPEED_0 					    = 91
    B_CURRENT_SPEED_1 					    = 92
    B_CURRENT_POS_0						    = 93
    B_CURRENT_POS_1						    = 94
    B_ACHIEVED_STOP_POS					    = 95
    B_RESET_ENCODER					        = 96

    HEADLIGHT_INTENSITY						= 97


    SENSORINIT1                             = 98
    SENSOR1C                                = 99
    SENSOR1R                                = 100
    SENSOR1G                                = 101
    SENSOR1B                                = 102
    SENSOR1P							    = 103

    SENSORINIT2                             = 104
    SENSOR2C                                = 105
    SENSOR2R                                = 106
    SENSOR2G                                = 107
    SENSOR2B                                = 108
    SENSOR2P							    = 109

    SENSORINIT3                             = 110
    SENSOR3C                                = 111
    SENSOR3R                                = 112
    SENSOR3G                                = 113
    SENSOR3B                                = 114
    SENSOR3P							    = 115

    IR_WRITE							    = 116
    IR_READ								    = 117

    STATE_SIZE							    = 118
    
    STATUS_BOOT                             = 0
    STATUS_READY                            = 1
    STATUS_LOAD_ERROR                       = 2
    STATUS_DIST_ERROR                       = 3
    STATUS_LOW_BATTERY                      = 4
    STATUS_RUNNING                          = 5
    STATUS_LOCKED                           = 6
    
    @staticmethod
    def decode(state):
        data = state
        chargeTime = data[SpinState.CHARGE_TIME_ADR_0] + 256*data[SpinState.CHARGE_TIME_ADR_1]
        highLoadTime = data[SpinState.HIGH_LOAD_TIME_ADR_0] + 256*data[SpinState.HIGH_LOAD_TIME_ADR_1]
        state =  {
            'charge time' : chargeTime,
            'high load time' : highLoadTime
        }
        state.update(ModuleState.decode(data))
        return state