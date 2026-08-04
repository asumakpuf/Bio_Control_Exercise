from abc import ABC, abstractmethod
import numpy as np

class ActivationFunction(ABC):
   @abstractmethod
   def forward(self, x):
      pass
   @abstractmethod
   def gradient(self, x):
      pass


class SignActivation(ActivationFunction):
   """ 
         Sign activation: `f(x) = 1 if x > 0, 0 if x <= 0`
   """
   # TODO: Define the correct return function, given input `x``
   def forward(self, x):

      fx = 0
      if x > 0:
         fx = 1

      return fx
      """
         TODO: Return the output of the activation function, given input `x`
      """
      
   def gradient(self, x):
      """
         TODO: Return the derivatinve of the activation function, given input `x`
      """
      return 0


class Sigmoid(ActivationFunction):

   def forward(self, x):
      return 1 / (1 + np.exp(-x))
      
   def gradient(self, x):
      fx = self.forward(x)
      return fx * (1 - fx)


class LinearActivation(ActivationFunction):
   def forward(self, x):
      return x
   def gradient(self, x):
      return 1
