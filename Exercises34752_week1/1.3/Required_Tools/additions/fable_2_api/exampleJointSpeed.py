import os, sys
from FableAPI.fable_init import api
# Install all dependencies with 'pip' (most are listed in requirements.txt)
# Runs in Python 3.4 only! (NOT Python 2.7, 3.5 or 3.6!)

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

print("Welcome to Joint modules example!")
# Establish connection to dongle.
# blocking=True makes sure rest of the script will only run if the connection
# is established.
api.setup(blocking=True)
# Find all the robots and return their IDs.
print('Search for modules')
moduleids = api.discoverModules()
print('Found modules: ',moduleids)
############################# YOUR CODE GOES HERE #############################
for i in range(10):
    for id in moduleids:
      api.setSpeed(25, 100, id)
      api.setPos(45, -60, id)
    api.sleep(3)
    for id in moduleids:
      api.setSpeed(100, 25, id)
      api.setPos(-45, 0, id)
    api.sleep(3)
###############################################################################


############################## TERMINATE PROGRAM ##############################
print('Terminating')
api.terminate()
###############################################################################
