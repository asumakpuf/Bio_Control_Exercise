import os, sys, time
import threading
import matplotlib.pyplot as plt

#sys.path.append("/Users/stolu/Documents/CodeSilvia/lwpr_mycode_Jan2016/AFEL_Fable_LWPR/Fable20")
#sys.path.append("../Robot_toolboxPy/robot")
#sys.path.append("../recurrent_Fable20")

sys.path.append("../../lib/fable_2_api")
sys.path.append("../../lib/Fable20/FableAPI")
sys.path.append("../../lib/Robot_toolboxPy/robot")

from FableAPI.fable_init import api
import numpy as np

from Robot import *
from simfable import *
from dynamics import *
# Install all dependencies with 'pip' (most are listed in requirements.txt)
# Runs in Python 3.4 only! (NOT Python 2.7, 3.5 or 3.6!)

def get_out():
    global exit_out
    exit_out = 'k'
    while (exit_out != 'q'):
        exit_out = input()

######################### SETUP PATHS TO DIRECTORIES ##########################
api.BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
api.USER_DIR = os.path.expanduser('~')
if sys.platform == 'win32':
    api.APPDATA_DIR = os.path.join(os.getenv('LOCALAPPDATA'), 'Fable')
else:
    api.APPDATA_DIR = os.path.join(api.USER_DIR, 'Fable')
api.DESKTOP_DIR = os.path.join(api.USER_DIR, 'Desktop')
# api.SOUND_DIR = os.path.join(BASE_DIR,'sounds') # only for api.playSound()
###############################################################################

################### Thread necessary to interact with KEYBOARD ################
global exit_out
threading.Thread( target=get_out ).start()
###############################################################################

print("Welcome to Joint modules example!")
# Establish connection to dongle.
# blocking=True makes sure rest of the script will only run if the connection
# is established.
api.setup(blocking=True)
# Find all the robots and return their IDs.
print('Search for modules')
moduleids = api.discoverModules()
#print('Found modules: ', moduleids[0])
for id in moduleids:
    #api.setSpeed(100, 100, id)
    api.setAccurate('HIGH','HIGH', id)

############################# YOUR CODE GOES HERE #############################
n_iter = 20000
ea   = np.zeros((2, n_iter + 1), dtype = np.double)
ep   = np.zeros((2, n_iter + 1), dtype = np.double)
ev   = np.zeros((2, n_iter + 1), dtype = np.double)
epr  = np.zeros((2, n_iter + 1), dtype = np.double)
posr = np.zeros((2, n_iter + 1), dtype = np.double)
torquesLF = np.zeros((2, n_iter + 1), dtype = np.double)
D    = np.zeros((2, n_iter + 1), dtype = np.double)
# PID controller
ki = [0.0/100.00, 0.0/100.00]
kp = [5.0, 5.0]

#kp = [30000.5/1000.00, 30000.5/1000.00]
#kv = [0.00, 0.00]
kv = [2.2, 2.2]

dt = 0.01
posd = 50 #Desired Pos in degree
fab     = moduleFable()
fab17   = fab.Fab()

print(api.getModuleList())
print("Module ID:    ", moduleids[0])
#api.setPos(posd, posd, moduleids[0])  
#api.sleep(0.5)
posr[0, 1] = api.getPos(0, moduleids[0])  # degrees
posr[1, 1] = api.getPos(1, moduleids[0])
print("Initial pos:    ", posr[:, 1])
api.sleep(1)
end_time = dt
for j in range(20000):
    t = time.time()   
    ep[:, j+1] = epr[:, j] # + self.outputC[0:2, j] + self.outputDCN[0:2, j] #+ self.etp[:, j] 
    ev[:, j+1] = ((ep[:, j+1] - ep[:, j]) / dt) # + self.outputC[2:4, j] + self.outputDCN[2:4, j] 
    ea[:, j+1] = 0.22
    
    for i in range(2):
         #Feedback error learning
        if j > 1:
           D[i, j] = D[i, j - 1] + (ea[i, j+1]) * ki[i] + (ep[i, j+1] * (kp[i])) + (ev[i, j+1] * (kv[i]))
        else:
           D[i, j] = (ea[i, j+1]) * ki[i] + (ep[i, j+1] * (kp[i])) + (ev[i, j+1] * (kv[i]))

    tau = rne(fab17, [posd, posd], [0, 0], [1, 1], [0, 0, 0] )
    
    for mid in moduleids:
        torquesLF[0, j+1] = ((tau[0, 0] * D[0, j]))#*1024/1.5  # np.random.randint(-100,100)
        torquesLF[1, j+1] = ((tau[0, 1] * D[1, j]))#*1024/1.5
        #torquesLF[0, j+1] = kp[0]*(epr[0, j])#((tau[0, 0] * D[0, j]))*1024/1.5  # np.random.randint(-100,100)
        #torquesLF[1, j+1] = kp[1]*(epr[1, j])#((tau[0, 1] * D[1, j]))*1024/1.5
        print('torquesLF: ',torquesLF[:, j+1])
        api.setTorque(torquesLF[0, j+1], torquesLF[1, j+1], mid)
        #api.sleep(0.1)
        posr[0, j+1] = api.getPos(0,mid)      # degrees
        posr[1, j+1] = api.getPos(1,mid)   
    epr[:, j+1] = posd - posr[:, j+1]
    print('epr: ', epr[:, j+1])
    end_time = time.time() - t
    print(end_time)
    # Check for end of execution
    if (exit_out == 'q'):
        break
'''for mid in moduleids:
    api.setSpeed(100, 100, mid)

torquex = 10
for i in range(100):
    
    for mid in moduleids:
        api.setTorque(torquex, torquex, mid)
    api.sleep(1)
    for mid in moduleids:
        api.setTorque(-torquex, -torquex, mid)
    api.sleep(1)
    torquex = torquex + 10
    #print(torquex)'''
    
###############################################################################

############################## TERMINATE PROGRAM ##############################

print('Terminating')
for mid in moduleids:
    api.setTorque(0, 0, mid)
api.terminate()
###############################################################################
plt.plot(epr[0,:])
plt.plot(epr[1,:])
plt.show()