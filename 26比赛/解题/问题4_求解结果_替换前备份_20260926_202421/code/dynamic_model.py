"""问题4：动态辅助加热控制（闭环）与恒功率基准的闭环仿真。

被控对象（plant）沿用问题2/3的七节点电堆热网络 + 问题1 的水/电化学内核
（fast_cell），唯一变化是：
  1. 初始温度场可为非均匀（由预冷模型给出）；
  2. 加热功率 q_k(t) 由反馈控制器在每个控制周期实时给出（时间+按片独立）。

动态控制器实现建模文档第2–3章的“前馈 + 增量式 PI 跟踪 + 冰堵安全增强 +
近成功渐缩 + 全局停止”分层结构；恒功率基准则是问题3策略的复算。

在 Python 3.14 上运行：先导入 3.14 原生库使冻结 cp312 依赖的 sys.path 插入
失效（见 问题3_求解结果/code/verify_uniform_power.py）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy, scipy, numba, matplotlib  # noqa: F401  原生库预导入
import numpy as np
from numba import njit

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from fast_cell import make_config, initial_state, cell_step, electro, properties, diagnostics  # noqa: E402

AREA = 0.0025                 # 单片活化面积 m^2 = 25 cm^2
Q_TIME = 60 + 11 / 0.3        # 统一加载曲线累计电荷的完整时长 (s)
J0 = 0.10255839004732065
# g_c, g_E, EP热容因子, EP对流开关, beta, h因子（与问题3一致）
THERMAL = np.array([1., 1., 1., 0., 10., 1.])

H_AMB = 40.0                  # 端部对流换热系数 W/(m^2 K)
T_AMB_C = -30.0               # 环境温度 ℃
BP_CAP = 0.002 * 1980.0 * 766.0   # 单位面积双极板热容 J/(m^2 K) = 3033.6


# ----------------------------------------------------------------------------
# 数值内核（与问题3 aux_model 一致，逐字复制）
# ----------------------------------------------------------------------------
@njit(cache=True)
def charge(t):
    x = max(t, 0.)
    return 0.0025 * min(x, 60.) ** 2 + 0.3 * max(x - 60., 0.)


@njit(cache=True)
def network(cfg, states, thermal):
    c = np.empty(7)
    r = np.empty(5)
    for k in range(5):
        cm, rm = properties(cfg, states[k])
        c[k] = cm + (1.5 if k == 0 or k == 4 else 1.) * 0.002 * 1980 * 766
        r[k] = rm
    c[5:] = 39500 * thermal[2]
    g = np.zeros((7, 7))
    for k in range(4):
        z = thermal[0] / (0.5 * (r[k] + r[k + 1]) + 0.002 / 95)
        g[k, k] += z; g[k + 1, k + 1] += z; g[k, k + 1] -= z; g[k + 1, k] -= z
    for k, e in ((0, 5), (4, 6)):
        z = thermal[1] / (0.5 * r[k] + 0.002 / 95 + 0.005 / 15)
        g[k, k] += z; g[e, e] += z; g[k, e] -= z; g[e, k] -= z
    h = np.zeros(7)
    if thermal[3] > 0.5:
        h[5:] = 1 / (1 / (40 * thermal[5]) + 0.005 / 15)
    else:
        h[0] = 40 * thermal[5]; h[4] = 40 * thermal[5]
    for k in range(7):
        g[k, k] += h[k]
    return c, g, h


@njit(cache=True)
def evaluate(cfg, states, temp, j, thermal):
    e = np.empty((5, 12))
    d = np.empty((5, 9))
    for k in range(5):
        e[k] = electro(cfg, states[k], temp[k] + 273.15, j * 1e4,
                       thermal[4] if k == 0 or k == 4 else 1.)
        d[k] = diagnostics(cfg, states[k])
    return e, d


@njit(cache=True)
def advance(cfg, states, temp0, j, dt, power, thermal):
    newstates = [states[k] for k in range(5)]
    phase = np.zeros(7); gen = np.zeros(7); aux = np.zeros(7); water = np.zeros(2)
    aux[:5] = power * 1e4
    for k in range(5):
        sn, ph, wp, wo = cell_step(cfg, states[k], temp0[k] + 273.15, j * 1e4, dt)
        newstates[k] = sn; phase[k] = ph; water[0] += wp; water[1] += wo
    c, g, h = network(cfg, newstates, thermal)
    a = g.copy()
    for k in range(7):
        a[k, k] += c[k] / dt
    rhs = c / dt * temp0 + h * T_AMB_C + phase / dt + aux
    temp = temp0.copy(); err = 1.
    for _ in range(30):
        for k in range(5):
            el = electro(cfg, newstates[k], temp[k] + 273.15, j * 1e4,
                         thermal[4] if k == 0 or k == 4 else 1.)
            gen[k] = j * 1e4 * (1.48 - el[0])
        tn = np.linalg.solve(a, rhs + gen)
        err = np.max(np.abs(tn - temp)); temp = tn
        if err < 1e-9:
            break
    energy = np.array([np.sum(aux) * dt, np.sum(gen) * dt, np.sum(phase),
                       np.dot(h, temp + 30) * dt, np.dot(c, temp - temp0)]) * AREA
    return newstates, temp, energy, water, err


# ----------------------------------------------------------------------------
# 恒功率基准（问题3 策略 C 复算，支持非均匀初始温度场）
# ----------------------------------------------------------------------------
CONST_SUMMARY = ['elapsed_s', 'first_success_s', 'min_voltage_V', 'max_ice_bulk',
                 'dTmax_K', 'E_aux_J', 'E_gen_J', 'E_phase_J', 'E_loss_J', 'E_sensible_J',
                 'energy_residual_J', 'final_min_T_C', 'final_max_T_C', 'final_left_EP_C']


@njit(cache=True)
def simulate_raw(cfg, power, th, dt, post, stop, record, thermal, temp0):
    horizon = th if th > 0 else post
    temp = temp0.copy()
    states = [initial_state(cfg, temp0[k] + 273.15) for k in range(5)]
    t = 0.; en = np.zeros(5)
    e, d = evaluate(cfg, states, temp, 0., thermal)
    nmax = int(np.ceil(horizon / dt)) + 80
    hist = np.zeros((nmax, 21)); count = 0
    vmin = np.min(e[:, 0]); imin = 0.; first = -1.
    dTmax = float(np.max(temp[:5]) - np.min(temp[:5]))
    while t < horizon - 1e-10:
        step = min(dt, horizon - t)
        on = t < th - 1e-9
        power_on = power if on else np.zeros(5)
        jm = (charge(t + step) - charge(t)) / step
        ns, nt, ne, nw, er = advance(cfg, states, temp, jm, step, power_on, thermal)
        t += step; states = ns; temp = nt; en += ne
        j = min(0.005 * t, 0.3)
        e, d = evaluate(cfg, states, temp, j, thermal)
        vmin = min(vmin, np.min(e[:, 0])); imin = max(imin, np.max(d[:, 0]))
        spread = np.max(temp[:5]) - np.min(temp[:5])
        dTmax = max(dTmax, spread)
        tm = np.min(temp[:5])
        if first < 0 and tm >= 1e-7 and vmin >= 0.3 and imin < 0.99:
            first = t
        if record and count < nmax:
            hist[count, 0] = t; hist[count, 1] = j; hist[count, 2] = 1. if on else 0.
            hist[count, 3:10] = temp
            hist[count, 10:15] = e[:, 0]
            hist[count, 15:20] = d[:, 0]
            hist[count, 20] = en[0]
            count += 1
        if stop and first >= 0:
            break
    s = np.array([t, first, vmin, imin, dTmax,
                  en[0], en[1], en[2], en[3], en[4],
                  en[4] - en[0] - en[1] - en[2] + en[3],
                  np.min(temp[:5]), np.max(temp[:5]), temp[5]])
    return s, hist[:count], states, temp


def simulate_constant(temp0, power, th, dt=0.05, scale=2, post=None, stop=True, record=True, thermal=None):
    """恒功率冷启动（策略 C：从 t=0 加载电流并同步加热至 th）。

    返回 summary dict（含 E_aux_J / first_success_s / min_voltage_V / max_ice_bulk /
    dTmax_K 等）与轨迹 hist（列 = [t, j, on, T1..T5, TEL, TER, V1..V5, ice1..ice5, E_aux]）。
    """
    power = np.asarray(power, dtype=float)
    if len(power) == 3:
        power = power[[0, 1, 2, 1, 0]]
    if len(power) != 5 or np.any(power < 0) or np.any(power > 1 + 1e-10) or th < 0:
        raise ValueError('Five heater powers in [0,1] and th>=0 required')
    cfg = make_config(scale=scale, j0=J0)
    if post is None:
        post = th
    a, h, states, temp = simulate_raw(cfg, power, float(th), float(dt), float(post), stop, record,
                                      THERMAL if thermal is None else np.asarray(thermal, float),
                                      np.asarray(temp0, dtype=float))
    s = dict(zip(CONST_SUMMARY, a.tolist()))
    s['feasible'] = bool(s['first_success_s'] >= 0 and s['min_voltage_V'] >= 0.3 and s['max_ice_bulk'] < 0.99)
    return s, h, states, temp


# ----------------------------------------------------------------------------
# 动态反馈控制器（建模文档第2–3章）
# ----------------------------------------------------------------------------
def _targ(p, k=None):
    """返回第 k 片的目标温度（支持标量或按片向量）。"""
    v = p['T_targ']
    if np.isscalar(v):
        return float(v)
    v = np.asarray(v, dtype=float)
    return v[k] if k is not None else v


DEFAULT_PARAMS = dict(
    T_targ=[4.0, 18.0, 20.0, 18.0, 4.0],  # ℃ 按片参考目标（端部=冰点+裕度，内部=维持导热支撑）
    t_plan=25.0,         # s 规划时间（参考轨迹上升段）
    K_P=0.50,            # (W/cm²)/K 比例增益
    K_I=0.08,            # (W/cm²)/(K·s) 积分增益
    q_max=1.0,           # W/cm² 功率上限
    eps_warn=0.8,        # 冰体积分数预警阈值
    delta_V=0.1,         # V 电压预警带宽
    R_warn=0.7,          # 冰堵风险预警阈值
    q_min_boost=0.6,     # W/cm² 最小安全增强功率
    dT_taper=2.0,        # K 近成功渐缩带宽
    t_hold=2.0,          # s 全局停止保持时间
    T_success=0.0,       # ℃ 成功温度阈值
    V_safe=0.30,         # V 电压安全下限
    eps_crit=0.99,       # 严重冰堵阈值
    eps_low=0.5,         # 近成功低冰分数
    dV_ref=0.01,         # V/s 电压下降速率参考
    beta_T=0.3, beta_V=0.3, beta_r=0.3,   # 滤波系数
    w1=0.4, w2=0.4, w3=0.2,                 # 冰堵风险权重
)


class Controller:
    """分层动态控制器：前馈 + 增量 PI + 安全增强 + 近成功渐缩 + 全局停止。

    参考轨迹为按片目标：端部单电池目标为冰点+热裕度，内部单电池目标更高，以
    维持向端部（端板热汇）的片间导热支撑——这是对建模文档式(4.30)在强耦合
    七节点热网络下的推广（见 reports/问题四结果与分析.md）。
    """

    def __init__(self, params, T0, cfg):
        p = dict(DEFAULT_PARAMS)
        p.update(params)
        self.p = p
        self.T0 = np.asarray(T0, dtype=float)          # 各片初温 ℃
        self.T_targ = np.full(5, _targ(p)) if np.isscalar(p['T_targ']) else np.asarray(p['T_targ'], float)
        self.q = np.zeros(5)
        self.q_fb = np.zeros(5)
        self.e_prev = np.zeros(5)
        self.Tfilt = np.asarray(T0, dtype=float).copy()
        self.Tfilt_prev = self.Tfilt.copy()
        self.Vfilt = None
        self.Vfilt_prev = None
        self.rT = np.zeros(5)
        self.rV = np.zeros(5)
        self.stopped = False
        self.success_hold = 0.0
        # 前馈显热系数 (W·s/cm²/K)：节点热容 / 1e4
        st0 = initial_state(cfg, 243.15)
        cm, _ = properties(cfg, st0)
        Chat = np.empty(5)
        for k in range(5):
            c_node = cm + (1.5 if k == 0 or k == 4 else 1.) * BP_CAP
            Chat[k] = c_node / 1e4
        self.Chat = Chat

    def ref(self, t, k):
        T0k = self.T0[k]
        if t < self.p['t_plan']:
            return T0k + (self.T_targ[k] - T0k) * t / self.p['t_plan']
        return self.T_targ[k]

    def step(self, t, dt, T, V, ice):
        """依据当前测量（T,V,ice 各为 5 维）计算下一控制周期的功率 q_k（W/cm²）。"""
        p = self.p
        # 1) 一阶低通滤波
        self.Tfilt_prev = self.Tfilt.copy()
        self.Tfilt = p['beta_T'] * self.Tfilt + (1 - p['beta_T']) * T
        if self.Vfilt is None:
            self.Vfilt = V.copy(); self.Vfilt_prev = V.copy()
        else:
            self.Vfilt_prev = self.Vfilt.copy()
            self.Vfilt = p['beta_V'] * self.Vfilt + (1 - p['beta_V']) * V
        # 2) 速率估计
        rV_new = (self.Vfilt - self.Vfilt_prev) / dt
        self.rT = p['beta_r'] * self.rT + (1 - p['beta_r']) * (self.Tfilt - self.Tfilt_prev) / dt
        self.rV = p['beta_r'] * self.rV + (1 - p['beta_r']) * rV_new
        dV = np.maximum(0.0, -self.rV)
        # 3) 参考轨迹 + 跟踪误差
        T_ref = np.array([self.ref(t, k) for k in range(5)])
        e = T_ref - T
        # 4) 前馈（显热 + 端部对流损失估计）
        slope = np.array([(self.T_targ[k] - self.T0[k]) / p['t_plan'] if t < p['t_plan'] else 0.0
                          for k in range(5)])
        q_ff = self.Chat * slope
        q_ff[0] += H_AMB * (T_ref[0] - T_AMB_C) / 1e4
        q_ff[4] += H_AMB * (T_ref[4] - T_AMB_C) / 1e4
        # 5) 增量式 PI
        dq_fb = p['K_P'] * (e - self.e_prev) + p['K_I'] * e * dt
        self.q_fb += dq_fb
        self.q_fb = np.clip(self.q_fb, 0.0, p['q_max'])
        q_bar = q_ff + self.q_fb
        # 6) 冰堵风险指标 + 安全增强（仅在风险越限时介入）
        R_ice = (p['w1'] * np.minimum(ice / p['eps_crit'], 1.0)
                 + p['w2'] * np.maximum(0.0, (p['V_safe'] + p['delta_V'] - V) / p['delta_V'])
                 + p['w3'] * np.minimum(dV / p['dV_ref'], 1.0))
        boost = np.clip((R_ice - p['R_warn']) / (1.0 - p['R_warn']), 0.0, 1.0)
        q_boost = np.where(R_ice > p['R_warn'],
                           p['q_min_boost'] + (p['q_max'] - p['q_min_boost']) * boost, 0.0)
        q = np.maximum(q_bar, q_boost)
        # 7) 近成功渐缩（仅当越过各片目标后才平滑递减，避免对支撑片的提前削减；
        #    支撑片——端部与近端——在达到目标后仍需维持片间导热支撑，故不提前渐缩）
        over = np.clip(T - self.T_targ, 0.0, None)
        taper = np.ones(5)
        for k in range(5):
            if over[k] > 0 and ice[k] < p['eps_low']:
                taper[k] = np.clip(1.0 - over[k] / p['dT_taper'], 0.0, 1.0)
        q *= taper
        # 8) 饱和限幅
        q = np.clip(q, 0.0, p['q_max'])
        # 9) 全局停止
        success = (np.min(T) > p['T_success'] and np.min(V) >= p['V_safe']
                   and np.max(ice) < p['eps_crit'])
        if success:
            self.success_hold += dt
        else:
            self.success_hold = 0.0
        if self.success_hold >= p['t_hold']:
            self.stopped = True
            q = np.zeros(5)
        self.q = q
        self.e_prev = e
        return q


# ----------------------------------------------------------------------------
# 动态闭环仿真
# ----------------------------------------------------------------------------
def simulate_dynamic(temp0, params=None, dt=0.05, scale=2, t_horizon=120.0,
                     post_stop=10.0, record=True):
    """闭环动态控制冷启动。返回 summary dict 与轨迹 dict（各字段 numpy 数组）。

    temp0 : 七节点初始温度 [T1..T5, EP_L, EP_R]（℃），由预冷模型或均匀 -30 给出。
    """
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    cfg = make_config(scale=scale, j0=J0)
    states = [initial_state(cfg, temp0[k] + 273.15) for k in range(5)]
    temp = np.asarray(temp0, dtype=float).copy()
    ctrl = Controller(p, temp0[:5], cfg)
    e, d = evaluate(cfg, states, temp, 0.0, THERMAL)
    en = np.zeros(5)
    water = np.zeros(2)

    traj = {'time_s': [], 'j_A_cm2': [], 'T1_C': [], 'T2_C': [], 'T3_C': [], 'T4_C': [],
            'T5_C': [], 'TEL_C': [], 'TER_C': []}
    for k in range(1, 6):
        traj[f'q{k}_W_cm2'] = []
        traj[f'V{k}_V'] = []
        traj[f'ice{k}'] = []
    traj.update({'E_aux_J': [], 'E_gen_J': [], 'E_phase_J': [], 'E_loss_J': [], 'E_sensible_J': []})

    def rec(t, j, q, temp, e, d, en):
        traj['time_s'].append(t); traj['j_A_cm2'].append(j)
        for k in range(5):
            traj[f'T{k+1}_C'].append(temp[k])
        traj['TEL_C'].append(temp[5]); traj['TER_C'].append(temp[6])
        for k in range(5):
            traj[f'q{k+1}_W_cm2'].append(q[k])
            traj[f'V{k+1}_V'].append(e[k, 0])
            traj[f'ice{k+1}'].append(d[k, 0])
        traj['E_aux_J'].append(en[0]); traj['E_gen_J'].append(en[1])
        traj['E_phase_J'].append(en[2]); traj['E_loss_J'].append(en[3])
        traj['E_sensible_J'].append(en[4])

    q0 = np.zeros(5)
    rec(0.0, 0.0, q0, temp, e, d, en)
    t = 0.0
    t_first = -1.0
    t_stop = -1.0
    vmin = np.min(e[:, 0]); imax = np.max(d[:, 0])
    errmax = 0.0
    while t < t_horizon:
        jm = (charge(t + dt) - charge(t)) / dt
        q = ctrl.step(t, dt, temp[:5], e[:, 0], d[:, 0])
        ns, nt, ne, nw, er = advance(cfg, states, temp, jm, dt, q, THERMAL)
        states, temp = ns, nt
        en += ne; water += nw; errmax = max(errmax, er)
        t += dt
        j = min(0.005 * t, 0.3)
        e, d = evaluate(cfg, states, temp, j, THERMAL)
        vmin = min(vmin, np.min(e[:, 0])); imax = max(imax, np.max(d[:, 0]))
        if t_first < 0 and np.min(temp[:5]) > 1e-7 and np.min(e[:, 0]) >= 0.30 and np.max(d[:, 0]) < 0.99:
            t_first = t
        if ctrl.stopped and t_stop < 0:
            t_stop = t
        rec(t, j, q, temp, e, d, en)
        if ctrl.stopped and t > t_stop + post_stop:
            break

    tr = {k: np.asarray(v) for k, v in traj.items()}
    Tmat = np.column_stack([tr[f'T{k}_C'] for k in range(1, 6)])
    dTmax = float(np.max(np.max(Tmat, axis=1) - np.min(Tmat, axis=1)))
    feasible = bool(t_first >= 0 and vmin >= 0.30 and imax < 0.99)
    summary = {
        'feasible': feasible,
        't_first_s': float(t_first),
        't_stop_s': float(t_stop),
        'E_aux_J': float(en[0]), 'E_gen_J': float(en[1]), 'E_phase_J': float(en[2]),
        'E_loss_J': float(en[3]), 'E_sensible_J': float(en[4]),
        'energy_residual_J': float(en[4] - en[0] - en[1] - en[2] + en[3]),
        'min_voltage_V': float(vmin), 'max_ice_bulk': float(imax),
        'dTmax_K': dTmax,
        'final_min_T_C': float(np.min(temp[:5])), 'final_max_T_C': float(np.max(temp[:5])),
        'final_left_EP_C': float(temp[5]),
    }
    return summary, tr, states, temp


if __name__ == "__main__":
    # 自检：均匀 -30 初始场，动态控制应可行
    from precool import PrecoolModel
    temp0 = np.full(7, -30.0)
    s, tr, _, _ = simulate_dynamic(temp0, dt=0.05, scale=2)
    print("feasible =", s['feasible'])
    print("t_first = %.2f s, t_stop = %.2f s" % (s['t_first_s'], s['t_stop_s']))
    print("E_aux = %.1f J, Vmin = %.3f V, ice_max = %.4f, dTmax = %.2f K"
          % (s['E_aux_J'], s['min_voltage_V'], s['max_ice_bulk'], s['dTmax_K']))
