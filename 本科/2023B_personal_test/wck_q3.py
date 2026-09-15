import sympy as sp
import numpy as np

# 定义常量和初始值
a = (1.5 / 360) * 2 * np.pi  # 坡度，单位为弧度
h0 = 110  # 中央深度
ew = 7408  # 海域东西宽度

def get_w1(h):
    return np.sin(60/360*2*np.pi) * h / np.sin((30-1.5)/360*2*np.pi)

def get_w2(h):
    return np.sin(60/360*2*np.pi) * h / np.sin((30+1.5)/360*2*np.pi)

def get_w(h):
    return get_w1(h) + get_w2(h)

def get_x(h):
    return (h0 + (ew/2) * np.tan((1.5/360) * 2 * np.pi) - h) / np.tan((1.5/360) * 2 * np.pi)

hh = sp.symbols('hh')

# 计算海域边界深度
deep_east = h0 - (ew/2) * np.tan(a)   # 海域东边边界的深度
deep_west = h0 + (ew/2) * np.tan(a)   # 海域西边边界的深度

# 解方程得到测线深度
eqn = hh + get_w1(hh) * np.sin(a) - deep_west
S = sp.solve(eqn, hh)

deep = [S[0]]  # 第一条测线所处位置的深度
i = 0
while get_x(deep[i]) + get_w2(deep[i]) * np.cos(a) < ew:
    # 计算下一条测线的深度
    next_deep = deep_west - np.tan(a) * ((deep_west - ((get_x(deep[i]) + get_w2(deep[i]) * np.cos(a)) - (get_w(deep[i]) * np.cos(a) * 0.1)) * np.tan(a)) * np.sqrt(3) + ((get_x(deep[i]) + get_w2(deep[i]) * np.cos(a)) - (get_w(deep[i]) * np.cos(a) * 0.1)))
    deep.append(next_deep)
    i += 1

x_line = [get_x(d) for d in deep]

print("每条测线处的海域深度：", deep)
print("每条测线距离海域西边边界的距离：", x_line)