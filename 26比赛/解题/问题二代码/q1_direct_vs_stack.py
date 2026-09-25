# -*- coding: utf-8 -*-
"""
对比实验：
  A) 问题一模型原样跑（单片热域 aBP-MEA-cBP，两侧外边界直接 h=40 对流）
     —— 若直接复制5份各自独立跑，每一片都是这条曲线，且5条完全重合。
  B) 正确的5片电堆热网络（集总平均温度节点 + 两块独立热容端板）：
     仅两端板外表面对环境对流，片间导热耦合。
  为保证对比干净，B 的内热源（电化学热+相变潜热，单位面积）直接取 A 轨迹，
  差异只来自散热/热耦合网络。
"""
import sys
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "问题一代码"))
sys.path.insert(0, str(HERE.parent))

from params import P
from cold_start_model import ColdStartModel

# ---------------- A. 问题一模型原样 ----------------
J_CM2 = 0.3                      # 恒流 0.3 A/cm^2
J = J_CM2 * 1e4                  # A/m^2
T0_C = -10.0
TEND = 150.0
TQ = 20.0 / J_CM2                # 电荷预算耗尽时刻 = 66.67s

m = ColdStartModel(P,
                   j0_ref=0.1202193291279339,
                   k_freeze=0.00010011135907000225)
# 0..TQ 恒流，之后电流为0（预算耗尽，仅热再分配）
t_in = np.array([0.0, TQ - 1e-6, TQ, TEND])
j_in = np.array([J, J, 0.0, 0.0])
resA = m.simulate(t_in, j_in, T0_C,
                  t_eval=np.arange(0, TEND + 1e-9, 0.5),
                  max_step=0.5)

tA = resA["t"]
TA = resA["T_mean_C"]            # 热域平均温度, °C
VA = resA["V"]
iceA = resA["eps_ice_max"]
print("=== A: 问题一模型原样（单片，两侧对流）===")
print("status:", resA["status"], resA["message"])
for tk in (0, 10, 20, 30, 40, 60, 66.7, 80, 100, 150):
    i = np.argmin(np.abs(tA - tk))
    print(f"t={tA[i]:6.1f}s  T={TA[i]:7.3f}°C  V={VA[i]:.3f}V  ice_max={iceA[i]:.4f}")

# 从A轨迹提取单位面积内热源（W/m^2）：电化学热 + 相变潜热
Eth = P.cold_start.thermoneutral_voltage
qgen = J * (Eth - VA)                                  # W/m^2
cum_phase = resA["cumulative_phase_heat_J_m2"]         # J/m^2 累计
qphase = np.gradient(cum_phase, tA)                    # W/m^2
qsrc = np.interp(np.arange(0, TEND + 1e-9, 0.25), tA, qgen + qphase)
qsrc[np.arange(0, TEND + 1e-9, 0.25) > TQ] = 0.0   # 预算断电后无内热源
tgrid = np.arange(0, TEND + 1e-9, 0.25)

def source(t):
    return float(np.interp(t, tgrid, qsrc))

# ---------------- B. 正确的5片热网络 ----------------
Lc = m.Lthermal                       # 单片热域厚度 0.0043267 m
CAc = float(m.heat_capacity_area)    # 单片单位面积热容 J/m^2K
Le = P.geo.end_plate
CAe = P.thermal.end_plate.rho * P.thermal.end_plate.cp * Le
# 单片串联热阻 -> 等效导热 -> 片间热导
Rc = sum(L / k for L, k in zip(
    [P.geo.bp_a, P.geo.gdl_a, P.geo.cl_a, P.geo.pem, P.geo.cl_c, P.geo.gdl_c, P.geo.bp_c],
    [P.thermal.bp.k, m.k_mea, m.k_mea, m.k_mea, m.k_mea, m.k_mea, P.thermal.bp.k]))
# 注：内部MEA用等效 k_mea；bp 用 k=95
Rc = (P.geo.bp_a / P.thermal.bp.k + (m.Lmea / m.k_mea) + P.geo.bp_c / P.thermal.bp.k)
keff = Lc / Rc
Gcc = keff / Lc
ke = P.thermal.end_plate.k
Gce = 1.0 / (Rc / 2 + Le / (2 * ke))
h = P.thermal.h
Gea = 1.0 / (1 / h + Le / (2 * ke))
print(f"\n=== 热网络参数 ===  CAc={CAc:.1f} CAe={CAe:.1f} Gcc={Gcc:.1f} Gce={Gce:.1f} Gea={Gea:.2f}")

# 状态 y = [T1..T5 (°C), ThL, ThR]
def rhs(t, y):
    T = y[:5]; ThL, ThR = y[5], y[6]
    q = source(t)
    dT = np.zeros(5)
    dT[0]  = (q + Gcc*(T[1]-T[0]) + Gce*(ThL-T[0])) / CAc
    for k in (1, 2, 3):
        dT[k] = (q + Gcc*(T[k-1]-2*T[k]+T[k+1])) / CAc
    dT[4]  = (q + Gcc*(T[3]-T[4]) + Gce*(ThR-T[4])) / CAc
    dThL = (Gce*(T[0]-ThL) - Gea*(ThL-T0_C)) / CAe
    dThR = (Gce*(T[4]-ThR) - Gea*(ThR-T0_C)) / CAe
    return np.r_[dT, dThL, dThR]

y0 = np.r_[np.full(5, T0_C), T0_C, T0_C]
solB = solve_ivp(rhs, (0, TEND), y0, t_eval=tgrid, rtol=1e-7, atol=1e-9,
                 max_step=0.5)
TB = solB.y[:5]
print("\n=== B: 正确电堆热网络（端片1 / 中片3）===")
for tk in (0, 10, 20, 30, 40, 60, 66.7, 80, 100, 150):
    i = np.argmin(np.abs(solB.t - tk))
    print(f"t={solB.t[i]:6.1f}s  端片T1={TB[0,i]:7.3f}°C  中片T3={TB[2,i]:7.3f}°C  端-中温差={TB[2,i]-TB[0,i]:6.3f}K")

# 到0°C时间
def cross0(t, T):
    idx = np.flatnonzero(T > 0)
    return t[idx[0]] if len(idx) else np.inf
print("\n=== 达到 0°C 时刻 ===")
print("A 模型一(每片):", round(cross0(tA, TA), 2), "s")
print("B 端片1       :", round(cross0(solB.t, TB[0]), 2), "s")
print("B 中片3       :", round(cross0(solB.t, TB[2]), 2), "s")

np.savez(HERE / "q1_direct_vs_stack_data.npz",
         tA=tA, TA=TA, VA=VA, iceA=iceA,
         tB=solB.t, TB=TB,
         params=np.array([CAc, CAe, Gcc, Gce, Gea]))
print("\nsaved data npz")
