"""凸二次代理目标的分配示例，功率单位 MW，目标不是实际疲劳损伤。"""
import numpy as np
from scipy.optimize import minimize


def allocate(coeff, total, lower, upper):
    coeff, lower, upper = [np.asarray(v, dtype=float) for v in (coeff, lower, upper)]
    if not (coeff.shape == lower.shape == upper.shape) or np.any(coeff <= 0):
        raise ValueError('同长度向量，且二次系数必须为正')
    if np.any(lower > upper) or not lower.sum() <= total <= upper.sum():
        raise ValueError('总量与边界不可行')
    slack = (upper - lower).sum()
    x0 = lower.copy() if slack == 0 else lower + (total - lower.sum()) / slack * (upper - lower)
    if slack == 0:
        return x0
    result = minimize(lambda p: np.dot(coeff, p*p), x0,
                      jac=lambda p: 2*coeff*p, method='SLSQP',
                      bounds=list(zip(lower, upper)),
                      constraints={'type': 'eq', 'fun': lambda p: p.sum()-total,
                                   'jac': lambda p: np.ones_like(p)},
                      options={'ftol': 1e-10, 'maxiter': 500})
    if not result.success:
        raise RuntimeError(result.message)
    if abs(result.x.sum()-total) > 1e-6 or np.any(result.x < lower-1e-6) or np.any(result.x > upper+1e-6):
        raise RuntimeError('求解结果违反约束')
    return result.x


def demo():
    rng = np.random.default_rng(42)
    a, b = rng.uniform(.5, 2, (2, 100))
    baseline = np.full(100, 3.)
    s1, s2 = np.dot(a, baseline**2), np.dot(b, baseline**2)
    rows = []
    for weight in (0., .25, .5, .75, 1.):
        coeff = weight*a/s1 + (1-weight)*b/s2
        p = allocate(coeff, 300, np.full(100, 2.), np.full(100, 4.))
        assert np.dot(coeff, p*p) <= np.dot(coeff, baseline**2) + 1e-8
        rows.append({'weight': weight, 'objective1_ratio': float(np.dot(a, p*p)/s1),
                     'objective2_ratio': float(np.dot(b, p*p)/s2),
                     'sum_error': float(abs(p.sum()-300))})
    exact = allocate([1, 2], 3, [0, 0], [5, 5])
    assert np.allclose(exact, [2, 1], atol=1e-5)
    try:
        allocate([1, 1], 11, [0, 0], [5, 5])
    except ValueError:
        pass
    else:
        raise AssertionError('应识别不可行总量')
    return rows


if __name__ == '__main__':
    print(demo())
