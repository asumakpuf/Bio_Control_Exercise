# model of one module (17) of Fable
# 23.06.2015
__author__ = 'slyto'

import sys
sys.path.append("../Robot_toolboxPy/robot")
from numpy import *
from Link import *
from SerialLink import *
m1 = 0.220
m2 = 0.150
l1 = 0.1 #0.0308
l2 = 0.1 #0.088
class moduleFable(object):  
    
    def __init__(self):
        self.m1 = m1
        self.m2 = m2
        self.l1 = l1
        self.l2 = l2
    
    def Fab(self):
        
        print("Fable one module (X)")
        L = []
        L.append(Link(alpha=0, a=self.l1, d=0))
        L.append(Link(alpha=math.pi, a=self.l2, d=0))


        L[0].m = self.m1
        L[1].m = self.m2

        L[0].r = mat([self.l1 / 2, 0, 0])
        L[1].r = mat([self.l2 / 2, 0, 0])

        L[0].I = mat([0,      0,      0,      0.0177187,      0.0177187,      0])
        L[1].I = mat([0,      0,      0,      0.00325125,      0.00325125,      0])

        L[0].Jm = 0
        L[1].Jm = 0

        L[0].G = 0
        L[1].G = 0

        # viscous friction (motor referenced)
        L[0].B = 0.01
        L[1].B = 0.01


        # Coulomb friction (motor referenced)
        L[0].Tc = mat([0,     0])
        L[1].Tc = mat([0,     0])

        #
        # some useful poses
        #
        # qz = [0, 0, 0, 0, 0, 0] # zero angles, L shaped pose
        # qr = [0, pi/2, -pi/2, 0, 0, 0] # ready pose, arm up
        # qs = [0, 0, -pi/2, 0, 0, 0]
        # qn = [0, pi/4, pi, 0, pi/4,  0]


        fab17 = SerialLink(L, name='Fable2', manuf='Unimation')  # , comment='params of 8/95')
        return fab17