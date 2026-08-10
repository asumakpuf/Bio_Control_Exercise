import time
import multiprocessing

from .fableAPI import FableAPI

# Communication channels between FableProcess and all possible
# process running instances of FableInterface
fable_task = multiprocessing.JoinableQueue()
manager = multiprocessing.Manager()
dict_queue = manager.dict({})

class FableInterface():
    def __init__(self, moduleID):
        self.task = fable_task
        dict_queue[moduleID] = {'motor1': {'pos': 0, 'vel':0}, 'motor2': {'pos': 0, 'vel':0}, 'battery': 0}
        self.current_pos = dict_queue
    
    def getPosVel(self, moduleID):
        self.task.put(FableTask('getPosVel', 0, 1, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()
        return self.current_pos[moduleID]['motor1'], self.current_pos[moduleID]['motor2']

    def setPos(self, posX, posY, moduleID): # 0 - 100 percent speed is set on all motors
        self.task.put(FableTask('setPos', posX, posY, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()
        timer = 20
        while (not ((self.current_pos[moduleID]['motor1']['pos'] > posX - 1.5) and 
                    (self.current_pos[moduleID]['motor1']['pos'] < posX + 1.5) and
                    (self.current_pos[moduleID]['motor2']['pos'] > posY - 1.5) and
                    (self.current_pos[moduleID]['motor2']['pos'] < posY + 1.5))) and timer > 0:
            timer = timer - 1
            time.sleep(0.05)

    def setSpeed(self, speedX, speedY, moduleID): # 0 - 100 percent speed is set on all motors
        self.task.put(FableTask('setSpeed', speedX, speedY, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()

    def setTorque(self, torqueX, torqueY, moduleID):#, desPosX, desPosY):
        self.task.put(FableTask('setTorque', torqueX, torqueY, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()

    def getBattery(self, moduleID):
        self.task.put(FableTask('getBattery', 0, 1, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()
        return self.current_pos[moduleID]['battery']

    def terminate(self, moduleID):
        self.task.put(FableTask('exit', 0, 1, moduleID))
        # Wait for all of the tasks to finish
        self.task.join()

class FableTask():
    def __init__(self, function, x_param, y_param, moduleID):
        self.function = function
        self.x_param = x_param
        self.y_param = y_param
        self.moduleID = moduleID

class FableProcess(multiprocessing.Process):
    def __init__(self):
        # must call this before anything else
        multiprocessing.Process.__init__(self, name='FableProcess')
        # Pipe to receive module behaviour
        self.task_queue = fable_task
        self.dict_queue = dict_queue
        self.motor_status = {}

    def run(self):
        # Fable must be initialised within the process!
        self.fable_api = FableAPI()
        self.fable_api.setup(blocking=True)
        mIDs = self.fable_api.discoverModules()
        print('Fable-wrapper found IDs: {}'.format(mIDs))
        for id in mIDs:
            self.motor_status[id] = {'motor1': {'pos': 0, 'vel':0}, 'motor2': {'pos': 0, 'vel':0}, 'battery': 0}

        while True:
            while self.task_queue.empty():
                # Read angular position in order to have it updated when it is requested
                for id in mIDs:
                    self.motor_status[id]['motor1']['pos'] = self.fable_api.getPos(0, id)
                    self.motor_status[id]['motor2']['pos'] = self.fable_api.getPos(1, id)
                    self.motor_status[id]['motor1']['vel'] = self.fable_api.getSpeed(0, id)
                    self.motor_status[id]['motor2']['vel'] = self.fable_api.getSpeed(1, id)

            next_task = self.task_queue.get()
            if next_task is None:
                # Poison pill means shutdown
                self.task_queue.task_done()
                break
            if next_task.function == 'getPosVel':
                self.dict_queue[next_task.moduleID] = self.motor_status[next_task.moduleID]
            elif next_task.function == 'setPos':
                self.fable_api.setPos(next_task.x_param, next_task.y_param, next_task.moduleID)
            elif next_task.function == 'setSpeed':
                self.fable_api.setSpeed(next_task.x_param, next_task.y_param, next_task.moduleID)
            elif next_task.function == 'setTorque':
                self.fable_api.setTorque(next_task.x_param, next_task.y_param, next_task.moduleID)
            elif next_task.function == 'getBattery':
                self.motor_status[next_task.moduleID]['battery'] = self.fable_api.getBattery(next_task.moduleID)
                self.dict_queue[next_task.moduleID] = self.motor_status[next_task.moduleID]
            # elif next_task.function == 'setModuleMotorMaxSpeed':
            #     self.setModuleMotorMaxSpeed(next_task.index)
            # elif next_task.function == 'createInputData_pos':
            #     self.createInputData_pos(next_task.index)
            # elif next_task.function == 'createInputData_vel':
            #     self.createInputData_vel(next_task.index)
            # elif next_task.function == 'predict':
            #     self.predict(next_task.index)
            # elif next_task.function == 'estimateErrors':
            #     self.estimateErrors(next_task.index)
            # elif next_task.function == 'update':
            #     self.update(next_task.index)
            # elif next_task.function == 'performControl':
            #     self.performControl(next_task.index, next_task.t)
            # elif next_task.function == 'save':
            #     self.save(next_task.num_modules, next_task.now)
            elif next_task.function == 'exit':
                self.fable_api.terminate()
                self.task_queue.task_done()
                break

            # Read angular position in order to have it updated when it is requested
            for id in mIDs:
                self.motor_status[id]['motor1']['pos'] = self.fable_api.getPos(0, id)
                self.motor_status[id]['motor2']['pos'] = self.fable_api.getPos(1, id)
                self.motor_status[id]['motor1']['vel'] = self.fable_api.getSpeed(0, id)
                self.motor_status[id]['motor2']['vel'] = self.fable_api.getSpeed(1, id)

            self.task_queue.task_done()