import numpy as np
from activation import ActivationFunction



class Perceptron:
   """ 
      Perceptron neuron model
      Parameters
      ----------
      n_inputs : int
         Number of inputs
      act_f : Subclass of `ActivationFunction`
         Activation function
   """
   def __init__(self, n_inputs, act_f):
      """
         Perceptron class initialization
         TODO: Write the code to initialize weights and save the given activation function
      """
      if not isinstance(act_f, type) or not issubclass(act_f, ActivationFunction):
         raise TypeError('act_f has to be a subclass of ActivationFunction (not a class instance).')
      # weights
      self.w = np.random.normal(
         loc=0.0,
         scale=0.1,
         size=n_inputs + 1
      )      
      # activation function
      self.f = act_f()

      if self.f is not None and not isinstance(self.f, ActivationFunction):
         raise TypeError("self.f should be a class instance.")

   def activation(self, x):
      """
         It computes the activation `a` given an input `x`
         TODO: Fill in the function to provide the correct output
         NB: Remember the bias
      """
      a = self.w[0] + np.dot(self.w[1:], x)
      return a

   def output(self, a):
      """
         It computes the neuron output `y`, given the activation `a`
         TODO: Fill in the function to provide the correct output
      """
      y = self.f.forward(a)
      return y

   def predict(self, x):
      a = self.activation(x)
      y = self.output(a)
      return y

   def gradient(self, a):
      """
         It computes the gradient of the activation function, given the activation `a`
      """
      return self.f.gradient(a)

