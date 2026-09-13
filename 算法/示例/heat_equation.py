"""u_t = alpha*u_xx；[0,1] 零 Dirichlet 边界，初值 sin(pi*x)。"""
import numpy as np


def solve_heat(nx=51, alpha=.1, end_time=.2):
    if nx < 3 or alpha <= 0 or end_time <= 0:
        raise ValueError('网格数、扩散系数和时间不合法')
    x = np.linspace(0, 1, nx)
    dx = x[1]-x[0]
    steps = int(np.ceil(end_time/(.4*dx*dx/alpha)))
    dt = end_time/steps
    ratio = alpha*dt/dx**2
    assert ratio <= .5
    u = np.sin(np.pi*x)
    u[[0, -1]] = 0
    for _ in range(steps):
        u[1:-1] += ratio*(u[2:] - 2*u[1:-1] + u[:-2])
    exact = np.exp(-alpha*np.pi**2*end_time)*np.sin(np.pi*x)
    return float(np.max(np.abs(u-exact)))


def demo():
    coarse, fine = solve_heat(26), solve_heat(51)
    assert fine < coarse and fine < 1e-3
    return {'coarse_max_error': coarse, 'fine_max_error': fine,
            'error_ratio': coarse/fine}


if __name__ == '__main__':
    print(demo())
