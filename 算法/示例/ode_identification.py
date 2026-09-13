"""合成一阶热响应：ODE 仿真 + 参数辨识；不代表任何赛题数据。"""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares


def simulate(theta, times):
    k, ambient = theta
    result = solve_ivp(lambda t, y: [-k * (y[0] - ambient)],
                       (times[0], times[-1]), [80.0], t_eval=times,
                       rtol=1e-8, atol=1e-10)
    if not result.success:
        raise RuntimeError(result.message)
    return result.y[0]


def demo():
    t = np.linspace(0, 20, 81)
    observed = simulate([0.22, 23], t) + np.random.default_rng(42).normal(0, .15, len(t))
    train = t <= 12
    fit = least_squares(lambda p: simulate(p, t[train]) - observed[train],
                        [0.1, 20], bounds=([0.01, 0], [2, 50]), loss='soft_l1')
    if not fit.success:
        raise RuntimeError(fit.message)
    prediction = simulate(fit.x, t)
    rmse = np.sqrt(np.mean((prediction[~train] - observed[~train]) ** 2))
    assert abs(fit.x[0] - .22) < .02 and abs(fit.x[1] - 23) < 1
    assert rmse < .5
    return {'estimated_parameters': fit.x.tolist(), 'future_test_rmse': float(rmse)}


if __name__ == '__main__':
    print(demo())
