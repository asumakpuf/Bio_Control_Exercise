import pickle
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import torch
import TODO_torch_model as torch_model
from tqdm import tqdm # progress bar

# Load data
data = pickle.load( open( "training_data.p", "rb" ) )

print(data.shape)
angles = data[:,:2].T
end_pos = data[:,2:].T

# Use GPU?
device = 'cpu'
if torch.cuda.is_available():
    print("Using GPU")
    device = 'cuda'
    torch.set_default_tensor_type('torch.cuda.FloatTensor')

x = torch.from_numpy(end_pos.T).float()
y = torch.from_numpy(angles.T).float()
# TODO split the training set and test set
# Eventually normalize the data
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)   

# Normalization of the data
x_mean, x_std = x_train.mean(0), x_train.std(0)
x_train = (x_train - x_mean) / x_std
x_test  = (x_test  - x_mean) / x_std

x_train = x_train.to(device)
x_test = x_test.to(device)
y_train = y_train.to(device)
y_test = y_test.to(device)

# Define neural network - an example
model = torch_model.MLPNet(2, 16, 2).to(device)
# model = torch_model.Net(n_feature=2, n_hidden1=h, n_hidden2=h, n_output=2)
#print(model)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
loss_func = torch.nn.MSELoss()
num_epochs = 500

#h = 16
g = 0.999
scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100, gamma=g)

train_loss_vec = np.zeros(num_epochs)
test_loss_vec = np.zeros(num_epochs)

for t in tqdm(range(num_epochs)):
    # TODO Train network
    model.train()
    prediction = model(x_train) # Forward pass prediction. Saves intermediary values required for backwards pass
    loss = loss_func(prediction, y_train) # Computes the loss for each example, using the loss function defined above
    optimizer.zero_grad() # Clears gradients from previous iteration
    loss.backward() # Backpropagation of errors through the network
    optimizer.step() # Updating weights
    scheduler.step()

    train_loss_vec[t] = loss.item()

    # TODO Test the network
    model.eval()
    with torch.no_grad():
        test_prediction = model(x_test)
        test_loss = loss_func(test_prediction, y_test)
        test_loss_vec[t] = test_loss.item()
    

plt.figure()
plt.plot(train_loss_vec, label='Train loss')
plt.plot(test_loss_vec, label='Test loss')
plt.xlabel('Epoch')
plt.ylabel('MSE loss')
plt.yscale('log')
plt.legend()
plt.tight_layout()

torch.save(model.state_dict(), 'trained_model.pth')
plt.show()


## Parameter TIPS - Try
# Adam with lr = 0.001
# StepLR scheduler with step_size=100, and gamma = 0.999
# Two hidden layers with 18 units each
