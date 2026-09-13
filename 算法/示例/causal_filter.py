"""标量随机游走卡尔曼滤波；NaN 表示缺测，未实现乱序/延迟观测回溯。"""
import numpy as np


def filter_series(observations, q=.01, r=.25, x0=0., p0=1.):
    if q < 0 or r <= 0 or p0 < 0:
        raise ValueError('方差参数不合法')
    x, p = float(x0), float(p0)
    values, variances = [], []
    for z in observations:
        p += q
        if np.isfinite(z):
            gain = p/(p+r)
            x += gain*(z-x)
            p = (1-gain)*p
        values.append(x)
        variances.append(p)
    return np.array(values), np.array(variances)


def demo():
    rng = np.random.default_rng(42)
    truth = np.cumsum(rng.normal(0, .1, 300))
    measured = truth + rng.normal(0, .5, 300)
    measured[100:110] = np.nan
    estimated, variance = filter_series(measured)
    valid = np.isfinite(measured)
    raw_rmse = np.sqrt(np.mean((measured[valid]-truth[valid])**2))
    filtered_rmse = np.sqrt(np.mean((estimated[valid]-truth[valid])**2))
    prefix, _ = filter_series(measured[:150])
    assert np.allclose(prefix, estimated[:150])  # 不受未来数据影响
    assert np.all(np.diff(variance[99:110]) > 0)  # 缺测时不确定性增长
    assert filtered_rmse < raw_rmse
    return {'raw_rmse': float(raw_rmse), 'filtered_rmse': float(filtered_rmse)}


if __name__ == '__main__':
    print(demo())
