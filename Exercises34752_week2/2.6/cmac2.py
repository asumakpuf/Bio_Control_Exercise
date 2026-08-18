import numpy as np

def GaussianBasisFunction(x, mu, sigma):
    return np.exp(-(x-mu)**2/(sigma**2))

class CMAC:
    def __init__(self, n_rfs, xmin, xmax, beta=1e-3):
        """ Initialize the basis function parameters and output weights """
        self.n_rfs = n_rfs
        self.xmin = np.asarray(xmin, dtype=float)
        self.xmax = np.asarray(xmax, dtype=float)
        self.n_dims = len(self.xmin)

        if self.n_dims != len(self.xmax):
            raise ValueError("xmin and xmax must have the same length")

        self.mu = np.zeros((self.n_dims, self.n_rfs))
        self.sigma = np.zeros(self.n_dims)
        crossval = 0.8 # has to be between 0 and 1 !

        # Exercise 7: make the CMAC dimension-generic instead of hardcoding 2D.
        for k in range(self.n_dims):
            self.sigma[k] = 0.5/np.sqrt(-np.log(crossval)) * (self.xmax[k] - self.xmin[k])/(self.n_rfs-1) # RFs cross at phi = crossval
            self.mu[k] = np.linspace(self.xmin[k], self.xmax[k], self.n_rfs)
        
        self.w = np.random.normal(loc=0.0, scale=0.2, size=(self.n_rfs,) * self.n_dims)

        self.beta = beta

        self.B = None
        self.y = None

    def predict(self, x):
        """ Predict yhat given x
            Saves activations `B` for later weight update
        """
        x = np.asarray(x, dtype=float)
        if len(x) != self.n_dims:
            raise ValueError(f"Expected {self.n_dims} inputs, got {len(x)}")

        phi = np.zeros((self.n_dims, self.n_rfs))
        for k in range(self.n_dims):
            phi[k] = GaussianBasisFunction(x[k], self.mu[k], self.sigma[k]) # for i in phi_ki at the same time

        # Exercise 7: build the N-dimensional RF activation tensor.
        self.B = phi[0]
        for k in range(1, self.n_dims):
            self.B = np.multiply.outer(self.B, phi[k])

        yhat = np.dot(self.w.ravel(), self.B.ravel()) # Element-wise multiplication and summing of all elements

        return yhat

    def learn(self, e):
        """ 
        Update the weights using the covariance learning rule
        For all weights at once.
        """
        self.w += self.beta*e*self.B


if __name__ == '__main__':
    n_rfs = 11

    xmin = [0, 0]
    xmax = [1, 1]

    c = CMAC(n_rfs, xmin, xmax, 1e-2)
    print(c.w.shape)

    for _ in range(1000):
        e_vec = []
        for x1 in np.linspace(0, 1, 11):
            for x2 in np.linspace(0, 1, 11):
                x = [x1, x2]

                yhat = c.predict(x)

                yd = np.arctan2(x[0], x[1])

                e = yd - yhat

                c.learn(e)
                e_vec.append(e**2)

        print(np.mean(e_vec))

    # Test values
    x = [0.5, 0.5]
    print(c.predict(x), np.arctan2(x[0], x[1]))

    x = [0.2, 0.5]
    print(c.predict(x), np.arctan2(x[0], x[1]))
