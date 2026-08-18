from cmac import CMAC3
import numpy as np
import matplotlib.pyplot as plt
from Bio_Control_Exercise.Project_final.target_simulator import Simulator, SimpleOscillation, TwoHarmonicMotion


def plot_prediction(times, y_true, y_pred):
    """Plot the true trajectory against the CMAC's one-step-ahead prediction."""
    times = np.array(times)
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    fig, (ax_traj, ax_err) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    ax_traj.plot(times, y_true, label="True", linewidth=2)
    ax_traj.plot(times, y_pred, label="Predicted", linestyle="--")
    ax_traj.set_ylabel("Position")
    ax_traj.set_title("CMAC prediction vs. true trajectory")
    ax_traj.legend()
    ax_traj.grid(True, alpha=0.3)

    ax_err.plot(times, y_true - y_pred, color="tab:red")
    ax_err.axhline(0, color="black", linewidth=0.8)
    ax_err.set_xlabel("Time")
    ax_err.set_ylabel("Error")
    ax_err.grid(True, alpha=0.3)

    fig.tight_layout()
    plt.show()


def main():

    model = SimpleOscillation(x_min=0.0, x_max=3.0, T=10.0)
    model = TwoHarmonicMotion(x_min=0.0, x_max=3.0, T=10.0, phase2=np.pi/3, ratio2=0.4)
    sim = Simulator(dt=0.5, model=model)

    cmac = CMAC3(n_centers=9, input_range=(0.0, 3.0), beta=0.05)

    errors = []
    times, y_true_hist, y_pred_hist = [], [], []

    for step in range(500):
        if step == 0:
            # Initialize the first 3 positions for the sliding window
            sim.step()  # t=0
            sim.step()  # t=0.5
            sim.step()  # t=1.0
        sim.step()
        x1 = sim.model.x(sim.time - 3 * sim.dt)   # oldest
        x2 = sim.model.x(sim.time - 2 * sim.dt)   # middle
        x3 = sim.state                            # newest (== x(sim.time - dt))

        y_hat, B = cmac.predict(x1, x2, x3)
        y_true = sim.model.x(sim.time)            # the very next position after x3

        error = y_true - y_hat
        cmac.update(B, error)
        errors.append(error ** 2)

        times.append(sim.time)
        y_true_hist.append(y_true)
        y_pred_hist.append(y_hat)

        print(f"Step {step}: Predicted={y_hat:.4f}, True={y_true:.4f}, Error={error:.4f}")

    errors = np.array(errors)
    print(f"Initial MSE (first 20 steps):  {errors[:20].mean():.5f}")
    print(f"Final MSE   (last 20 steps):   {errors[-20:].mean():.5f}")

    plot_prediction(times, y_true_hist, y_pred_hist)


if __name__ == "__main__":
    main()