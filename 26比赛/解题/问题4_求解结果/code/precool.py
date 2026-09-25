"""问题4 第1章 / 第(2)问：预冷过程一维有限体积模型。

整堆沿层叠方向由 2 块端板(EP) + 6 块双极板(BP) + 5 层 MEA 组成，共 13 个
区域。预冷阶段无电流、无反应，仅发生一维热传导与两端自然对流（第三类边界）。
用后向欧拉（全隐）推进式(4.11)的三对角系统，得到任意冷却时刻 tau_c 的温度场
T(x, tau_c)，并映射为七节点（5 单电池 + 2 端板）冷启动初始温度。

单位：内部全部采用 SI（m、K、W/(m^2 K)、J/(m^3 K)）；对外输出温度场用 ℃。
"""
from __future__ import annotations

import numpy as np

# 区域材料参数（建模文档式 4.5/4.6 与附件1）
# thickness m / 体积热容 J/(m^3 K) / 导热系数 W/(m K)
EP = dict(d=10e-3, rhocp=3.95e6, k=15.0)
BP = dict(d=2e-3, rhocp=1.517e6, k=95.0)
MEA = dict(d=0.3267e-3, rhocp=1.86e5, k=0.296)

_REGIONS = {
    "EP": EP, "BP": BP, "MEA": MEA,
}

# 沿层叠方向（左端板 -> 右端板）的区域顺序；13 个区域
STACK_ORDER = ["EP", "BP", "MEA", "BP", "MEA", "BP", "MEA", "BP", "MEA", "BP", "MEA", "BP", "EP"]

# 每个区域的基础控制体数量（EP 较厚、MEA 很薄）；scale 用于收敛检验
_BASE_N = {"EP": 20, "BP": 6, "MEA": 3}

T_INIT_K = 298.15   # 25 ℃
T_AMB_K = 243.15    # -30 ℃
H_AMB = 40.0        # W/(m^2 K)，端板外表面自然对流换热系数


def _thomas(diag, lower, upper, rhs):
    """三对角 Thomas 求解（diag 为主对角，lower/upper 为下/上次对角）。"""
    n = len(rhs)
    d = np.asarray(diag, dtype=float).copy()
    u = np.asarray(upper, dtype=float).copy()
    b = np.asarray(rhs, dtype=float).copy()
    x = np.empty(n, dtype=float)
    for i in range(1, n):
        w = lower[i - 1] / d[i - 1]
        d[i] -= w * u[i - 1]
        b[i] -= w * b[i - 1]
    x[-1] = b[-1] / d[-1]
    for i in range(n - 2, -1, -1):
        x[i] = (b[i] - u[i] * x[i + 1]) / d[i]
    return x


class PrecoolModel:
    """一维有限体积预冷模型。

    节点温度按“七节点映射”输出：[T1..T5, T_EP_L, T_EP_R]（单位 ℃）。
    T1..T5 为 5 片单电池平均温度（MEA + 其归属双极板的热容加权平均）。
    """

    def __init__(self, scale: int = 1):
        self.scale = int(scale)
        self._build()

    def _build(self):
        dx_list, k_list, rhocp_list, reg_list = [], [], [], []
        for typ in STACK_ORDER:
            reg = _REGIONS[typ]
            n = _BASE_N[typ] * self.scale
            dx_list.extend([reg["d"] / n] * n)
            k_list.extend([reg["k"]] * n)
            rhocp_list.extend([reg["rhocp"]] * n)
            reg_list.extend([typ] * n)
        self.dx = np.asarray(dx_list)
        self.k = np.asarray(k_list)
        self.rhocp = np.asarray(rhocp_list)
        self.region = np.asarray(reg_list)
        self.x = np.cumsum(self.dx) - self.dx / 2.0          # 节点中心坐标 (m)
        self.Ls = float(np.sum(self.dx))                     # 整堆厚度 (m)
        self.C = self.rhocp * self.dx                        # 单位面积热容 (J/(m^2 K))
        n = len(self.dx)
        # 界面导热系数 g_{i+1/2}（式 4.8）
        g = np.empty(n - 1)
        for i in range(n - 1):
            g[i] = 1.0 / (self.dx[i] / (2 * self.k[i]) + self.dx[i + 1] / (2 * self.k[i + 1]))
        self.g = g
        # 边界对流作为边界半控制体的附加“导热”：g_{1/2}=g_{N+1/2}=h
        self.h = H_AMB
        # 区域 -> 节点的热容加权映射（七节点 = 5 电池 + 2 端板）
        self._node_map()

    def _node_map(self):
        """构造 7x13 的区域->节点热容权重矩阵。

        节点 0..4 为单电池 1..5，节点 5/6 为左/右端板。单电池的热容归属与
        问题2/3 共享双极板模型一致：端片 1.5 块板、中间片 1 块板（共 6 块）。
        """
        # 区域热容（单位面积）
        cap = np.array([_REGIONS[t]["rhocp"] * _REGIONS[t]["d"] for t in STACK_ORDER])
        W = np.zeros((7, 13))
        # 端板
        W[5, 0] = cap[0]          # 左端板
        W[6, 12] = cap[12]        # 右端板
        # 单电池（区域索引：MEA 在 2,4,6,8,10；BP 在 1,3,5,7,9,11）
        # cell k=1..5 -> MEA 区域 2k，左邻 BP 2k-1，右邻 BP 2k+1
        cell_bp = [(1, 3, 1.0, 0.5), (3, 5, 0.5, 0.5), (5, 7, 0.5, 0.5),
                   (7, 9, 0.5, 0.5), (9, 11, 0.5, 1.0)]  # (左BP, 右BP, 左权重, 右权重)
        for c, (bp_l, bp_r, wl, wr) in enumerate(cell_bp):
            mea = 2 * (c + 1)
            W[c, mea] += cap[mea]
            W[c, bp_l] += wl * cap[bp_l]
            W[c, bp_r] += wr * cap[bp_r]
        self._W = W
        self._region_cap = cap
        # 区域切片索引（区域内的控制体范围）
        slices = []
        acc = 0
        for typ in STACK_ORDER:
            n = _BASE_N[typ] * self.scale
            slices.append((acc, acc + n))
            acc += n
        self._region_slices = slices

    def _region_means(self, T_C):
        """节点温度场 -> 13 个区域的平均温度（区内物性均匀即算术平均）。"""
        means = np.zeros(13)
        for r, (a, b) in enumerate(self._region_slices):
            means[r] = np.mean(T_C[a:b])
        return means

    def node_temps(self, T_C):
        """由整堆温度场（节点，℃）映射到七节点温度 [T1..T5, EP_L, EP_R]（℃）。"""
        means = self._region_means(T_C)
        denom = self._W @ np.ones(13)
        return (self._W @ means) / denom

    def _step_rhs(self, T, dt):
        """组装后向欧拉三对角系统 (C/dt - K) T^{m+1} = (C/dt) T^m + b_amb。"""
        n = len(self.dx)
        cdt = self.C / dt
        # 界面导热（含边界对流）
        g_low = np.empty(n - 1)
        g_low[:] = self.g
        # 主对角、次对角
        diag = np.empty(n)
        lower = np.empty(n - 1)
        upper = np.empty(n - 1)
        for i in range(n):
            left = self.h if i == 0 else self.g[i - 1]
            right = self.h if i == n - 1 else self.g[i]
            diag[i] = cdt[i] + left + right
        for i in range(n - 1):
            lower[i] = -self.g[i]
            upper[i] = -self.g[i]
        rhs = cdt * T
        rhs[0] += self.h * T_AMB_K
        rhs[-1] += self.h * T_AMB_K
        return diag, lower, upper, rhs

    def solve(self, tau_c_s, dt=0.5, T0=None):
        """推进至 tau_c_s 并返回温度场（节点，℃）。"""
        if T0 is None:
            T = np.full(len(self.dx), T_INIT_K)
        else:
            T = np.asarray(T0, dtype=float).copy()
        t = 0.0
        while t < tau_c_s - 1e-12:
            step = min(dt, tau_c_s - t)
            diag, lower, upper, rhs = self._step_rhs(T, step)
            T = _thomas(diag, lower, upper, rhs)
            t += step
        return (T - 273.15)

    def scan(self, tau_c_min_list, dt=0.5):
        """对若干冷却时刻做一次时间推进并采样，返回 {tau_min: T_C 场}。"""
        tau_list = sorted(set(tau_c_min_list))
        tmax = max(tau_list) * 60.0
        T = np.full(len(self.dx), T_INIT_K)
        t = 0.0
        out = {}
        idx = 0
        # 在时间推进中逐点采样
        while t < tmax - 1e-12:
            step = min(dt, tmax - t)
            diag, lower, upper, rhs = self._step_rhs(T, step)
            T = _thomas(diag, lower, upper, rhs)
            t += step
            while idx < len(tau_list) and tau_list[idx] * 60.0 <= t + 1e-9:
                out[tau_list[idx]] = (T - 273.15).copy()
                idx += 1
        return out

    def mean_temp(self, T_C):
        """整堆热容加权平均温度（℃），用于能量守恒核算。"""
        return float(np.sum(self.C * (T_C + 273.15)) / np.sum(self.C) - 273.15)

    def node_mean(self, T_C):
        """七节点（5 电池 + 2 端板）算术平均温度（℃），与建模文档“全场均值”口径一致。"""
        return float(np.mean(self.node_temps(T_C)))


def mapping_matrix_region_to_cell():
    """调试用：返回区域热容与七节点映射（供核验口径）。"""
    m = PrecoolModel(scale=1)
    return m._region_cap, m._W


if __name__ == "__main__":
    m = PrecoolModel(scale=1)
    print(f"整堆厚度 Ls = {m.Ls * 1000:.4f} mm（文档 33.6335 mm）")
    print(f"控制体总数 N = {len(m.dx)}")
    # 复现文档表 1.7 的若干取值
    for tc in (10, 20, 30, 40, 60, 80, 100):
        T = m.solve(tc * 60.0)
        nodes = m.node_temps(T)
        print(f"tau_c={tc:3d} min  端板={nodes[5]:6.2f}  T1={nodes[0]:6.2f}  "
              f"T3={nodes[2]:6.2f}  均值={m.mean_temp(T):6.2f} ℃")
