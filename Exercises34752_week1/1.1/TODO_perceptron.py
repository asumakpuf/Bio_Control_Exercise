import numpy as np
from activation import ActivationFunction
import matplotlib.pyplot as plt


##########################################
"""
TODO:
For each activation function: Sign, Sigmoid, Linear, define the following:
1) Forward function
2) Gradient function

We have provided the function signature for you.

"""
##########################################

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

if __name__ == '__main__':
   data = np.array( [ [0.5, 0.5, 0], [1.0, 0, 0], [2.0, 3.0, 0], [0, 1.0, 1], [0, 2.0, 1], [1.0, 2.2, 1] ] )
   # first two columns are the input data, third column is the label (0 or 1), so third column is the label (output)
   xdata = data[:,:2]
   ydata = data[:,2]
   print(xdata)
   print(ydata)
   
## TODO Test your activation function
a = Sigmoid()
print(a.forward(2))
print(a.forward(0))

## TODO Test Perceptron initialization
p = Perceptron(2, Sigmoid)
## Test the predict function for each of the data points given in x
print(p.predict(xdata[0,:]) )

## TODO Learn/update the weights - write code to use the learning rule to update weights
r = 0.1 # learning rate - change it to see how it affects the learning process

## print the final weights after learning
print(p.w)

n_epochs = 100

for epoch in range(n_epochs):
   for x, y_true in zip(xdata, ydata):
      y_pred = p.predict(x)
      error = y_true - y_pred

      p.w[0] += r * error
      p.w[1:] += r * error * x

print("Final weights:", p.w)

# Create decision boundary
xp = np.linspace(
   xdata[:, 0].min() - 0.5,
   xdata[:, 0].max() + 0.5,
   100
)

yp = -(p.w[0] + p.w[1] * xp) / p.w[2]

# Plot data
plt.scatter(
   xdata[ydata == 0, 0],
   xdata[ydata == 0, 1],
   label="Class 0"
)

plt.scatter(
   xdata[ydata == 1, 0],
   xdata[ydata == 1, 1],
   label="Class 1"
)

plt.plot(xp, yp, "k--", label="Decision boundary")
plt.xlabel("x1")
plt.ylabel("x2")
plt.legend()
plt.show()