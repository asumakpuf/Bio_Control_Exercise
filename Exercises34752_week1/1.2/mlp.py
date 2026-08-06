import numpy as np
import matplotlib.pyplot as plt

from perceptron import Perceptron
from activation import Sigmoid, LinearActivation

"""
HINT: Reuse your perceptron.py and activation.py files, and apply the functions directly.
"""


class Layer:
   def __init__(self, num_inputs, num_units, act_f):
      """ 
         Initialize the layer, creating `num_units` perceptrons with `num_inputs` each. 
      """
      # TODO Create the perceptrons required for the layer
      self.num_units = num_units
      self.ps = [Perceptron(num_inputs, act_f) for _ in range(self.num_units)]

   def activation(self, x):
      """ Returns the activation `a` of all perceptrons in the layer, given the input vector`x`. """
      return np.array([p.activation(x) for p in self.ps])

   def output(self, a):
      """ Returns the output `o` of all perceptrons in the layer, given the activation vector `a`. """
      return np.array([p.output(ai) for p, ai in zip(self.ps, a)])

   def predict(self, x):
      """ Returns the output `o` of all perceptrons in the layer, given the input vector `x`. """
      return np.array([p.predict(x) for p in self.ps])

   def gradient(self, a):
      """ Returns the gradient of the activation function for all perceptrons in the layer, given the activation vector `a`. """
      return np.array([p.gradient(ai) for p, ai in zip(self.ps, a)])

   def update_weights(self, dw):
      """ 
      Update the weights of all of the perceptrons in the layer, given the weight change of each.
      Input size: (n_inputs+1, n_units)
      """
      for i in range(self.num_units):
         self.ps[i].w += dw[:,i]

   @property
   def w(self):
      """
         Returns the weights of the neurons in the layer.
         Size: (n_inputs+1, n_units)
      """
      return np.array([p.w for p in self.ps]).T

   def import_weights(self, w):
      """ 
         Import the weights of all of the perceptrons in the layer.
         Input size: (n_inputs+1, n_units)
      """
      for i in range(self.num_units):
         self.ps[i].w = w[:,i]


class MLP:
   """ 
      Multi-layer perceptron class

   Parameters
   ----------
   n_inputs : int
      Number of inputs
   n_hidden_units : int
      Number of units in the hidden layer
   n_outputs : int
      Number of outputs
   alpha : float
      Learning rate used for gradient descent
   """
   def __init__(self, num_inputs, n_hidden_units, n_outputs, alpha=1e-3):
      self.num_inputs = num_inputs
      self.n_hidden_units = n_hidden_units
      self.n_outputs = n_outputs

      self.alpha = alpha

      # TODO: Define a hidden layer and the output layer
      self.l1 = Layer(self.num_inputs, self.n_hidden_units, Sigmoid) # hidden layer 1
      self.l_out = Layer(self.n_hidden_units, self.n_outputs, LinearActivation) # output layer

   def predict(self, x):
      """ 
      Forward pass prediction given the input x
      TODO: Write the function
      """
      return self.l_out.predict(self.l1.predict(x))

   def train(self, inputs, outputs):
      """
         Train the network

      Parameters
      ----------
      `x` : numpy array
         Inputs (size: n_examples, n_inputs)
      `t` : numpy array
         Targets (size: n_examples, n_outputs)

      TODO: Write the function to iterate through training examples and apply gradient descent to update the neuron weights
      """
      N = len(inputs)
      dw1 = np.zeros_like(self.l1.w)
      dw3 = np.zeros_like(self.l_out.w)
      # Loop over training examples
      for inp, target in zip(inputs, outputs):
         # Forward pass
         a1 = self.l1.activation(inp)
         o1 = self.l1.output(a1)
         a_out = self.l_out.activation(o1)
         o_out = self.l_out.output(a_out)

         # Backpropagation 
         error = o_out - target
         delta_out = error * self.l_out.gradient(a_out)
         delta1 = self.l_out.w[1:, :].dot(delta_out) * self.l1.gradient(a1)

         # Add weight change contributions to temporary array
         o0 = np.insert(inp, 0, 1)
         o1_aug = np.insert(o1, 0, 1)

         dw1 += np.outer(o0, delta1)
         dw3 += np.outer(o1_aug, delta_out)

      # Update weights 
      self.l1.update_weights(-(self.alpha / N) * dw1)
      self.l_out.update_weights(-(self.alpha / N) * dw3)


   def export_weights(self):
      return [self.l1.w, self.l_out.w]
   
   def import_weights(self, ws):
      if ws[0].shape == (self.num_inputs+1, self.l1.num_units) and ws[1].shape == (self.l1.num_units+1, self.l_out.num_units):
         print("Importing weights..")
         self.l1.import_weights(ws[0])
         self.l_out.import_weights(ws[1])
      else:
         print("Sizes do not match")


def calc_prediction_error(model, x, t):
   """ Calculate the average prediction error """
   # TODO Write the function
   errors = []
   for inp, target in zip(x, t):
      pred = model.predict(inp)
      error_squared = np.mean((pred - target) ** 2)
      errors.append(error_squared)
   return np.mean(errors)



if __name__ == "__main__":

   # 1. Test the Sigmoid and LinearActivation functions  
   xs = np.linspace(-5, 5, 11)
   sig = Sigmoid()
   lin = LinearActivation()
   print("x           :", xs)
   print("sigmoid(x)  :", sig.forward(xs))
   print("sigmoid'(x) :", sig.gradient(xs))
   print("linear(x)   :", lin.forward(xs))
   print("linear'(x)  :", lin.gradient(xs))
   print()

   # 2. Test the Layer class: 5 neurons, input [pi, 1] 
   test_input = np.array([np.pi, 1])
   layer = Layer(2, 5, Sigmoid)
   print("Layer output for [pi, 1]:", layer.predict(test_input))
   print("Layer weights shape (expect (n_inputs+1, n_units) = (3, 5)):", layer.w.shape)
   print("Layer weights:\n", layer.w)
   print()

   # 3/4. Test MLP init and predict: 2 inputs, 1 output
   n_hidden_units = 4
   mlp = MLP(2, n_hidden_units, 1)
   print("Hidden layer: %d units, each with %d weights (incl. bias)"
         % (len(mlp.l1.ps), mlp.l1.ps[0].w.shape[0]))
   print("Output layer: %d units, each with %d weights (incl. bias)"
         % (len(mlp.l_out.ps), mlp.l_out.ps[0].w.shape[0]))
   print("MLP prediction for [pi, 1]:", mlp.predict(test_input))
   print()

   # 5. Test calc_prediction_error on the untrained network 
   xor_x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
   xor_t = np.array([[0], [1], [1], [0]])
   print("Untrained network MSE on XOR data:", calc_prediction_error(mlp, xor_x, xor_t))
   print()

   #  6/7. Train a fresh network as an XOR gate, compare learning rates
   
   n_epochs = 20000
   learning_rates = [0.1, 0.5, 1, 1.5, 2]

   plt.figure()
   for r in learning_rates:
      np.random.seed(0)
      xor_mlp = MLP(2, 2, 1, alpha=r)
      mse_history = np.zeros(n_epochs)
      for epoch in range(n_epochs):
         xor_mlp.train(xor_x, xor_t)
         mse_history[epoch] = calc_prediction_error(xor_mlp, xor_x, xor_t)
      plt.plot(mse_history, label=f"alpha={r}")
      print(f"alpha={r:>5}: final MSE={mse_history[-1]:.6g}")

   plt.yscale("log")
   plt.ylim(1e-9, 1e3)  # fixed window: keeps converged curves (~1e-27) and
                        # diverging ones on a readable common scale
   plt.xlabel("Epoch")
   plt.ylabel("MSE")
   plt.title("XOR training: MSE vs epoch for different learning rates")
   plt.legend()
   plt.show()
