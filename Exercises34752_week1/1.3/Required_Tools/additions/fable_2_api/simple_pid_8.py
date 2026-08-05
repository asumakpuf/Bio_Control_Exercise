# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 21:12:06 2015
__author__ = 'slyto'

"""
import sys, time, math
import os
import numpy as np
import scipy.io
import matplotlib.pyplot as plt


sys.path.append("../../lib/fable_2_api")
sys.path.append("../../lib/Fable20/FableAPI")
sys.path.append("../../lib/Robot_toolboxPy/robot")
sys.path.append("../../projects/lwpr_fable_recurrent/scripts/recurrent_macFableNEW/2modules")

from lwpr import *
from RAFEL_LWPRandC_1box_lwpr import *
from Robot import *
from FableAPI.fable_init import api
from FableAPI.tools import Tools
from simfable import *
from dynamics import *
from datetime import datetime, date
import time, math, threading
from threading import Thread

'''api.BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
api.USER_DIR = os.path.expanduser('~')
if sys.platform == 'win32':
    api.APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'Fable')
else:
    api.APPDATA_DIR = os.path.join(api.USER_DIR, 'Fable')
api.DESKTOP_DIR = os.path.join(api.USER_DIR, 'Desktop')
api.setup(blocking=True)
moduleids = api.discoverModules()
print("module", moduleids)'''
    
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target = fn, args = args, kwargs = kwargs)
        thread.start()
        return thread
    return wrapper

class AFEL():

    def __init__(self, moduleids):
        
        self.ModuleID = moduleids[0]
        #print(moduleids[0])
        self.n_iter = 1500#10501
        self.njoints = 2
        self.nout = 4

        #self.ki = [1.0/1.00, 1.0/1.00]
        #self.kp = [7.5*8.00, 7.5*8.00]
        #self.kv = [6.4/1.00, 6.4/1.00]

        
        #Controller
        self.ki = [0.0, 0.0]
        self.kp = [6.0, 1.05]
        self.kv = [3.2, 7.2]

#        self.ki = [0.0/100.00, 0.0/100.00]
#        self.kp = [9.5, 7.5]
#        self.kv = [4.5, 3.5]        
        
        
        # # PID controller - 10-10-2017 with silvia
        # self.ki = [0.0/1.00, 0.0/1.00]
        # self.kp = [3.0, 10.0]
        # self.kv = [1.500, 1.500]


        self.grav = [0, 0, 9.81]

        # Variable definitions
        self.A1      = 5#0.2 #70
        self.A2      = 10#20#40 #700
        self.f1       = 1
        self.f2       = 1
        self.phase   = math.pi / 2
        self.dt      = 0.01
        self.t0      = 0
        
        self.q1   = [0 for k in range(self.n_iter + 1)]
        self.q2   = [0 for a in range(self.n_iter + 1)]
        self.q    = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.q1d  = [0 for c in range(self.n_iter + 1)]
        self.q2d  = [0 for v in range(self.n_iter + 1)]
        self.qd   = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.q1dd = [0 for o in range(self.n_iter + 1)]
        self.q2dd = [0 for l in range(self.n_iter + 1)]
        
        self.posr = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.velr = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.accr = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.D    = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        #self.erra = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.errp = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.errv = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.epr  = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.eprv = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.etp  = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.etv  = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.ea   = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.ep   = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.ev   = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)

        self.torquesLF   = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        # self.torqLWPR    = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        # self.Ctorques    = np.zeros((self.nout, self.n_iter + 1), dtype = np.double)
        self.outputDCN        = np.zeros((self.nout, self.n_iter + 1), dtype = np.double)
        #self.DCNv        = np.zeros((self.nout, self.n_iter + 1), dtype = np.double)
        # self.torquestot  = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)

        self.outputC  = np.zeros((self.nout, self.n_iter + 1), dtype = np.double)
        #self.velC  = np.zeros((self.nout, self.n_iter + 1), dtype = np.double)
        self.pLWPR = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)
        self.vLWPR = np.zeros((self.njoints, self.n_iter + 1), dtype = np.double)

        self.output_x = np.zeros((self.nout), dtype = np.double)
        self.initD = 0

    def __del__(self):
        print("Class object for Module_{} - Destroyed".format(self.ModuleID))

    
    # Eight figure trajectory
    def calc_trajectory_8(self, fab):
        self.A1 = 0.15
        self.phase = math.pi / 2
        self.f2 = self.f1*2.0

        for i in range(self.n_iter):
            self.q1dd[i] = (self.A1 * math.sin(self.f1 * math.pi * self.t0))*180/math.pi
            self.q1d[i]  = (((-1 / 2) * math.pi) * self.A1 * math.cos(self.f1 * math.pi * self.t0))*180/math.pi
            self.q1[i]   = ((-math.pow(((1 / 2) * math.pi), 2)) * self.A1 * math.sin(self.f1 * math.pi * self.t0))*180/math.pi

            self.q2dd[i]  = (self.A1 * math.cos(self.f2 * math.pi * self.t0 + math.pi / 2))*180/math.pi
            self.q2d[i]   = (((1 / 2) * math.pi)  * self.A1 * math.sin(self.f2 * math.pi * self.t0 + math.pi / 2))*180/math.pi
            self.q2[i]    = ((-math.pow(((1 / 2) * math.pi), 2)) * self.A1 * math.cos(self.f2 * math.pi * self.t0 + math.pi / 2))*180/math.pi
            self.q[:, i]  = (self.q1[i], self.q2[i])
            self.qd[:, i] = (self.q1d[i], self.q2d[i])
            self.t0 += self.dt
        #plt.plot(self.q1, self.q2)   
        #plt.show() 
        return self.q1, self.q2, self.q1d, self.q2d, self.q1dd, self.q2dd

    
    #@threaded
    def run_test(self, mlcj, api, fab, fab17):
        #set accuracy to high for both joints
        #api.setAccurate("HIGH", "HIGH", self.ModuleID)
        torque = np.zeros(self.njoints, dtype = np.double)
        print( 'Test-thread for Module_{}: starting...'.format(self.ModuleID) )
        api.setPos(self.q1[0], self.q2[0], self.ModuleID)    

        api.sleep(1)

        t = self.dt        
        t_total = []
        
        for j in range(self.n_iter):
           
            end_time = time.time()
            
            self.ep[:, j+1] = self.epr[:, j]# + self.outputC[0:2, j] + self.outputDCN[0:2, j] #+ self.etp[:, j] 
            self.ev[:, j+1] = ((self.ep[:, j+1] - self.ep[:, j]) / self.dt)# + self.outputC[2:4, j] + self.outputDCN[2:4, j] 
            self.ea[:, j+1] = 0.22#((self.ev[:, j+1] - self.ev[:, j]) / (self.dt))
            
            
            for i in range(self.njoints):
                # Feedback error learning
                if j > 1:
                    self.D[i, j] = self.D[i, j - 1] + (self.ea[i, j+1]) * self.ki[i] + (self.ep[i, j+1] * (self.kp[i])) + (self.ev[i, j+1] * (self.kv[i]))
                else:
                    self.D[i, j] = (self.ea[i, j+1]) * self.ki[i] + (self.ep[i, j+1] * (self.kp[i])) + (self.ev[i, j+1] * (self.kv[i]))

            tau = rne(fab17, [self.q1[j], self.q2[j]], [0, 0], [1, 1], [0, 0, 0])

            
            self.torquesLF[0, j+1] = tau[0, 0] * self.D[0, j]
            self.torquesLF[1, j+1] = tau[0, 1] * self.D[1, j]

#            print("Current torquesLF:    ", self.torquesLF[:, j+1])  
            # Control in motor torques
            #t4 = time.time()
            #t5 = t4 - end_time
            
            
            api.setTorque(round(self.torquesLF[0, j+1]), round(self.torquesLF[1, j+1]), self.ModuleID)#, self.q[0,j], self.q[1,j])
#            if(abs(self.q[0,j] - api.getPos(0,self.ModuleID)) > 1.0):
#                print("HEREEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")
#                print(self.q[0,j] - api.getPos(0,self.ModuleID))
                
                
#            api.setTorque(round(self.torquesLF[0, j+1], 3), 0, self.ModuleID)
#            api.setTorque(0, self.torquesLF[1, j+1], self.ModuleID)            
#            api.sleep(self.dt)
            # Receive feedback positions from motors
            #t1 = time.time()
            self.posr[0, j+1] = api.getPos(0,self.ModuleID)      # degrees
            self.posr[1, j+1] = api.getPos(1,self.ModuleID)   
            #self.velr[0, j+1] = api.getSpeed(0,self.ModuleID)       # grad/s
            #self.velr[1, j+1] = api.getSpeed(1,self.ModuleID)
            
            #t3 = time.time() - t1
#            print("desired pos:    ", self.q[:, j])
#            print("Current pos:    ", self.posr[:, j+1])
            #print("desired vel:    ", self.qd[:, j])
            #print("Current vel:    ", self.velr[:, j+1])
            
            # print("DCNp", self.DCNp[:, j])

            #self.etp[:, j+1] = self.q[:, j] - self.posr[:, j] 
            #self.etv[:, j+1] = self.qd[:, j] - self.velr[:, j]
            
          
            self.epr[:, j+1]  = (self.q[:,j] - self.posr[:, j])
            self.eprv[:, j+1] = (self.qd[:,j] - self.velr[:, j])
            
            
#            print("\n\n")
            t = (time.time() - end_time)
            t_total.append(time.time())
#            print("Module_{} ".format(self.ModuleID), "- j: ", j, "- t: ", t)
            #t6 = time.time() - t1
        # Save with Matlab compatibility
        now = datetime.now()
        
        plt.plot(self.epr[0])
        plt.show()
        
        plt.plot(self.epr[1])
        plt.show()
        
        plt.plot(self.posr[0])
        plt.plot(self.q1)
        plt.show()
        
        plt.plot(self.posr[1])
        plt.plot(self.q2)
        plt.show()
        
        #plt.plot(self.posr[1])
        #plt.plot(self.q2)
        #plt.show() 
        
        scipy.io.savemat('TestREC_1box_1module_fab{0}_{1}.mat'.format(self.ModuleID, 
                                                                                now.strftime('%d-%m-%Y_%H:%M')),
                          dict( q0 = self.q1,                   q1 = self.q2, 
                                q0d = self.q1d,                 q1d = self.q2d, 
                                velr0 = self.velr[0],           velr1 = self.velr[1], 
                                posr0 = self.posr[0],           posr1 = self.posr[1], 
                                errp0 = self.epr[0],           errp1 = self.epr[1],
                                errv0 = self.eprv[0],           errv1 = self.eprv[1],
                                torquesLF0 = self.torquesLF[0], torquesLF1 = self.torquesLF[1],
                                t_tot = t_total
                          )
        )

        print('Recurrent test for Module_{}: finishing'.format(self.ModuleID))
        return True

if __name__ == '__main__':
    api.BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
    api.USER_DIR = os.path.expanduser('~')
    if sys.platform == 'win32':
        api.APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'Fable')
    else:
        api.APPDATA_DIR = os.path.join(api.USER_DIR, 'Fable')
    api.DESKTOP_DIR = os.path.join(api.USER_DIR, 'Desktop')

    njoints = 2            # 2-DoF Fable modules
    nout = 4
    api.setup(blocking=True)
    moduleids = api.discoverModules()
    print("module", moduleids)
    for id in moduleids:
        #api.setSpeed(100, 100, id)
        api.setAccurate('HIGH','HIGH', id)
    
    '''for i in range(100):
        for id in moduleids:
            api.setPos(i, -45, id)
            print(id)
            api.sleep(1)
            api.setPos(i, 45, id)
        api.sleep(1)
        print("i", i) '''
    
    # Class MLandC object for every joint link of each module
    mlcj_1  = MLandC(10, nout, njoints)

    # Fable api
    grav    = [0, 0, 9.81]
    
    fab     = moduleFable()
    fab17   = fab.Fab()

    # AFEL objects
    afel_1 = AFEL(moduleids)

    # Generation of Trajectories
    afel_1.calc_trajectory_8(fab)
#    afel_1.calc_trajectory_circle(fab)


    afel_1.run_test(mlcj_1, api, fab, fab17)
    # Multithread handling
#    handle_1 = afel_1.run_test(mlcj_1, api, fab, fab17)
#    handle_1.join()

    # Termination of api and class usage
    del afel_1

    time.sleep(1)
    print("Test - Done...")
    api.sleep(1)
    api.terminate()



    # end_time = time.time()

    # for j in range(n_iter):
    #     for i in range(njoints):
    #         # Feedback error learning
    #         if j > 1:
    #             D[i, j] = D[i, j - 1] + (erra[i, j]) * ki[i] + (errp[i, j] * (kp[i])) + (errv[i, j] * (kv[i]))
    #         else:
    #             D[i, j] = (erra[i, j]) * ki[i] + (errp[i, j] * (kp[i])) + (errv[i, j] * (kv[i]))    

    #     torquesLF[0, j] =  D[0, j]
    #     torquesLF[1, j] =  D[1, j]

    #     etp[0, j] = random.randint(0, 10)
    #     etp[1, j] = random.randint(0, 20)
    #     etv[0, j] = random.randint(0, 10)
    #     etv[1, j] = random.randint(0, 20)

    #     # predictions
    #     (output_x, posC[:, j+1], DCNp[:, j+1]) = mlcj.ML_prediction(
    #                     np.array([
    #                         torquesLF[0, j],   torquesLF[1, j], 
    #                         q1[j],             q2[j], 
    #                         q1d[j],            q2d[j], 
    #                         posr[0, j],        posr[1, j], 
    #                         velr[0, j],        velr[1, j] 
    #                     ]), 
    #                     etp[:, j],
    #                     etv[:, j]
    #     )
    #     print("output_x: ", output_x, "\n\n")
        
    #     torquestot[0, j] = torquesLF[0, j] + torqLWPR[0, j] + DCNtorques[0, j]  #+ Ctorques[0, j] #+ torquesP[0, j]  # 2 x 6001
    #     torquestot[1, j] = torquesLF[1, j] + torqLWPR[1, j] + DCNtorques[1, j]  #+ Ctorques[1, j] #+ torquesP[1, j]


    #     t = (time.time() - end_time)

    #     # Receive feedback positions from motors
    #     posr[0, j+1] = q1[j] * 2
    #     posr[1, j+1] = q2[j] * 2
    #     velr[0, j+1] = - q1d[j] * 2
    #     velr[1, j+1] = - q2d[j] * 2
    #     print("t: ", t)

    #     # Compute errors
    #     errp[0, j + 1] = (q1[j] - posr[0, j+1])
    #     errp[1, j + 1] = (q2[j] - posr[1, j+1])
    #     errv[0, j + 1] = (q1d[j] - velr[0, j+1])
    #     errv[1, j + 1] = (q2d[j] - velr[1, j+1])
    #     erra[0, j + 1] = 0.22  
    #     erra[1, j + 1] = 0.22 


    #     mlcj.ML_update(
    #          np.array([
    #             torquesLF[0, j],   torquesLF[1, j], 
    #             q1[j],             q2[j], 
    #             q1d[j],            q2d[j], 
    #             posr[0, j],        posr[1, j], 
    #             velr[0, j],        velr[1, j]
    #         ]), 
    #         np.array([
    #             posr[0, j], posr[1, j], 
    #             velr[0,j], velr[1, j]
    #         ])
    #     )

    #     print("posr:", posr[:, j])
    #     print("velr:", velr[:, j])
