"""一维单电池瞬态自冷启动模型（建模说明 M1--M49）。

独立积分状态为局部温度、总水、冰、孔隙内氢/氧摩尔库存以及累计收支。
温度/电压观测不进入此模块；唯一外部时间输入为电流密度 j(t)，单位 A/m²。
多孔层质量浓度均按控制体总体积计，膜内 mw 表示吸附水。

数值试探点的有限延拓仅为 BDF 非线性迭代提供有限值；真实轨迹越过
物理边界时由终止事件报告，绝不修改或逐步裁剪积分状态。
"""
from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter

_HERE = Path(__file__).resolve().parent
if sys.platform == "win32" and sys.version_info[:2] == (3, 12):
    sys.path.insert(0, str(_HERE / ".python_deps"))
sys.path.insert(0, str(_HERE.parent))

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from scipy.sparse import csr_matrix


class ColdStartModel:
    """有限体积 + BDF 求解器；参数来源保存在上级目录 params.py。

    Parameters
    ----------
    config : SimpleNamespace
        通常为 ``from params import P`` 得到的 P。
    grid_scale : float
        各层网格数乘子；1 为 68 个热单元、52 个质量单元，2 为加密。
    include_bp : bool
        True 使用 BP--MEA--BP 热域；False 提供原五层热域对照。
    freezing : bool
        False 关闭冰动力学，用于退化检查。
    j0_ref, k_freeze : float or None
        校准参数覆盖；None 时采用 params 中明确注明为初猜的值。
    """

    def __init__(self, config, grid_scale=1, include_bp=True, freezing=True,
                 j0_ref=None, k_freeze=None):
        self.P = config
        self.cs = config.cold_start
        self.include_bp = bool(include_bp)
        self.freezing = bool(freezing)
        self.j0_ref = float(self.cs.j0_ref if j0_ref is None else j0_ref)
        self.k_freeze = float(self.cs.k_freeze if k_freeze is None else k_freeze)
        if self.j0_ref <= 0 or self.k_freeze < 0 or grid_scale <= 0:
            raise ValueError("j0_ref、grid_scale 必须为正，k_freeze 必须非负。")
        self.k_melt = self.k_freeze * self.cs.k_melt_ratio
        self.R, self.F = config.constants.R, config.constants.F
        self.Mw = config.constants.M_water
        self.rhoi, self.rhol = config.thermal.ice.rho, config.thermal.liquid.rho
        self.water_per_lambda = config.membrane.rho * self.Mw / config.membrane.equivalent_weight
        self._make_grid(float(grid_scale))
        self._make_state_layout()

    def _make_grid(self, grid_scale):
        P = self.P
        names = ("aBP", "aGDL", "aCL", "PEM", "cCL", "cGDL", "cBP")
        lengths = (P.geo.bp_a, P.geo.gdl_a, P.geo.cl_a, P.geo.pem,
                   P.geo.cl_c, P.geo.gdl_c, P.geo.bp_c)
        counts = [max(1, int(round(n * grid_scale))) for n in self.cs.grid]
        if not self.include_bp:
            counts[0] = counts[-1] = 0
        self.layer_counts = dict(zip(names, counts))
        self.layer_slices = {}
        dx, labels = [], []
        for name, length, n in zip(names, lengths, counts):
            start = len(dx)
            if n:
                dx.extend([length / n] * n)
                labels.extend([name] * n)
            self.layer_slices[name] = slice(start, len(dx))
        self.dxT = np.asarray(dx)
        self.labelsT = np.asarray(labels)
        self.nT = len(dx)
        self.xT = np.cumsum(self.dxT) - self.dxT / 2
        if self.include_bp:
            self.xT -= P.geo.bp_a
        self.mea_T = np.flatnonzero(np.isin(self.labelsT, names[1:-1]))
        self.dx = self.dxT[self.mea_T]
        self.x = self.xT[self.mea_T]
        self.labels = self.labelsT[self.mea_T]
        self.n = len(self.dx)
        self.a = np.flatnonzero(np.isin(self.labels, ("aGDL", "aCL")))
        self.c = np.flatnonzero(np.isin(self.labels, ("cCL", "cGDL")))
        self.mem = np.flatnonzero(self.labels == "PEM")
        self.acl = np.flatnonzero(self.labels == "aCL")
        self.ccl = np.flatnonzero(self.labels == "cCL")
        self.porous = np.r_[self.a, self.c]
        self.np = len(self.porous)
        self.na, self.nc = len(self.a), len(self.c)
        self.local_porous = np.full(self.n, -1, dtype=int)
        self.local_porous[self.porous] = np.arange(self.np)
        self.eps0 = np.zeros(self.n)
        for name, val in (("aGDL", P.porous.eps_gdl_a), ("aCL", P.porous.eps_cl_a),
                          ("cCL", P.porous.eps_cl_c), ("cGDL", P.porous.eps_gdl_c)):
            self.eps0[self.labels == name] = val
        self.Lmea = self.dx.sum()
        self.Lthermal = self.dxT.sum()
        mat = P.thermal
        mea_lengths = np.array(lengths[1:-1])
        mats = (mat.gdl, mat.cl, mat.ionomer, mat.cl, mat.gdl)
        self.C_mea = sum(m.rho * m.cp * L for m, L in zip(mats, mea_lengths)) / self.Lmea
        self.k_mea = self.Lmea / sum(L / m.k for m, L in zip(mats, mea_lengths))
        self.capacity = np.full(self.nT, mat.bp.rho * mat.bp.cp)
        self.conductivity = np.full(self.nT, mat.bp.k)
        self.capacity[self.mea_T] = self.C_mea
        self.conductivity[self.mea_T] = self.k_mea
        self.heat_face_conductance = 1 / (self.dxT[:-1] / (2 * self.conductivity[:-1])
                                         + self.dxT[1:] / (2 * self.conductivity[1:]))
        self.heat_boundary_conductance = 1 / (1 / mat.h + self.dxT[[0, -1]] / (2 * self.conductivity[[0, -1]]))
        self.heat_capacity_area = float(self.capacity @ self.dxT)
        # M27: 从阴极 CL 中心到流道的串联扩散阻力，含准确的半个 CL。
        cathode_path_start = P.geo.gdl_a + P.geo.cl_a + P.geo.pem + P.geo.cl_c / 2
        left = self.x[self.c] - self.dx[self.c] / 2
        right = left + self.dx[self.c]
        self.oxygen_path_dx = np.maximum(0, right - np.maximum(left, cathode_path_start))
        self.Ldiff = float(self.oxygen_path_dx.sum())
        self.acl_gas = np.flatnonzero(self.labels[self.a] == "aCL")
        self.ccl_gas = np.flatnonzero(self.labels[self.c] == "cCL")
        self.interface_a = int(self.mem[0])
        self.interface_c = int(self.ccl[0])
        self.internal_mem_faces = self.mem[:-1] + 1
        yO = P.operation.oxygen_mass_fraction / P.constants.M_oxygen
        yN = P.operation.nitrogen_mass_fraction / P.constants.M_nitrogen
        self.y_oxygen = yO / (yO + yN)

    def _make_state_layout(self):
        starts = np.cumsum([0, self.nT, self.n, self.np, self.na, self.nc, 9])
        self.slT, self.slw, self.sli, self.slh, self.slo, self.slbudget = [
            slice(starts[k], starts[k + 1]) for k in range(6)]
        self.size = int(starts[-1])
        # 温差 20 K、水 100 kg/m³、气体 50 mol/m³、面积收支分别缩放。
        self.scale = np.ones(self.size)
        self.scale[self.slT] = 20.
        self.scale[self.slw] = 100.
        self.scale[self.sli] = 100.
        self.scale[self.slh] = self.scale[self.slo] = 50.
        self.scale[self.slbudget] = np.array([.01, .01, 1e5, 1e5, 1e5, 1., 1., 1., 1.])
        # 保守稀疏结构：电压反馈使所有热行依赖水/冰/气体状态；
        # 其余传输行仅依赖相邻单元。收支积分不反馈到任何物理状态。
        sp = np.zeros((self.size, self.size), dtype=bool)
        physical_end = self.slo.stop
        sp[self.slT, :physical_end] = True
        sp[self.slbudget, :physical_end] = True
        for r in range(self.n):
            row = self.slw.start + r
            for k in range(max(0, r - 1), min(self.n, r + 2)):
                sp[row, self.slw.start + k] = True
                sp[row, self.slT.start + self.mea_T[k]] = True
                p = self.local_porous[k]
                if p >= 0:
                    sp[row, self.sli.start + p] = True
        for p, r in enumerate(self.porous):
            row = self.sli.start + p
            sp[row, self.slw.start + r] = True
            sp[row, self.sli.start + p] = True
            sp[row, self.slT.start + self.mea_T[r]] = True
        for domain, sl in ((self.a, self.slh), (self.c, self.slo)):
            for q, r in enumerate(domain):
                row = sl.start + q
                for qq in range(max(0, q - 1), min(len(domain), q + 2)):
                    k = domain[qq]
                    sp[row, sl.start + qq] = True
                    sp[row, self.slw.start + k] = True
                    sp[row, self.sli.start + self.local_porous[k]] = True
                    sp[row, self.slT.start + self.mea_T[k]] = True
        self.jac_sparsity = csr_matrix(sp)

    @staticmethod
    def saturation_pressure(T, liquid_reference=False):
        """M5 Buck，M42 液面参考负温延拓；Pa。"""
        Tc = np.asarray(T) - 273.15
        liquid = 611.21 * np.exp((18.678 - Tc / 234.5) * Tc / (257.14 + Tc))
        if liquid_reference:
            return liquid
        ice = 611.15 * np.exp((23.036 - Tc / 333.7) * Tc / (279.82 + Tc))
        return np.where(Tc >= 0, liquid, ice)

    @staticmethod
    def sorption_lambda(activity):
        """M41，Springer 吸水平衡关系，低温属于经验外推。"""
        a = activity
        return 0.043 + a * (17.81 + a * (-39.85 + 36 * a))

    def phase_partition(self, mw, mi, T):
        """M1--M7；返回未经状态裁剪的 mv,ml,eps_g,lambda。"""
        u = mw - mi
        p = self.porous
        rho_v = self.Mw * self.saturation_pressure(T[p]) / (self.R * T[p])
        b = self.eps0[p] - mi[p] / self.rhoi
        ml = np.zeros(self.n)
        ml[p] = np.maximum(u[p] - b * rho_v, 0.) / (1 - rho_v / self.rhol)
        mv = np.zeros(self.n)
        mv[p] = u[p] - ml[p]
        eps_g = np.zeros(self.n)
        eps_g[p] = b - ml[p] / self.rhol
        lam = mw[self.mem] / self.water_per_lambda
        return mv, ml, eps_g, lam

    def _interface_flux(self, p, m, sigma, mw, mi, T, Dw, j):
        """M43：饱和段线性求根，不饱和段在活度区间求单根。

        返回全局 +x 面通量、可行根距区间边界的裕度、归一化残差。
        分母物性取各中心当前值，与 MD M43 的指定离散严格一致。
        """
        AP = Dw[p] / (self.dx[p] / 2)
        AM = Dw[m] / (self.dx[m] / 2)
        Tg = (T[p] / self.dx[p] + T[m] / self.dx[m]) / (1 / self.dx[p] + 1 / self.dx[m])
        b = self.eps0[p] - mi[p] / self.rhoi
        safe_b = max(b, 1e-14)
        psat = float(self.saturation_pressure(Tg))
        psat_l = float(self.saturation_pressure(Tg, liquid_reference=True))
        a_cap = min(psat / psat_l, 1.)
        K = self.Mw * safe_b * psat_l / (self.R * Tg)
        E = 2.5 / 22 * self.Mw * sigma * j / self.F
        uP = mw[p] - mi[p]
        B = AM * self.water_per_lambda + E
        C = AP * uP + AM * mw[m]
        lam_cap = self.sorption_lambda(a_cap)
        def residual_a(a):
            return C - AP * K * a - B * self.sorption_lambda(a)
        f0, fc = residual_a(0.), residual_a(a_cap)
        upper = max(safe_b * self.rhol, 1e-14)
        if f0 >= 0 and fc <= 0:
            a = brentq(residual_a, 0., a_cap, xtol=2e-13, rtol=1e-13)
            ug = K * a
            lam_g = self.sorption_lambda(a)
        elif fc > 0:
            ug = (C - B * lam_cap) / AP
            lam_g = lam_cap
        else:
            # 无非负根时只为求解器试探提供有限延拓；事件会终止真实轨迹。
            ug = f0 / max(AP + abs(B) * 17.81 / max(K, 1e-30), 1e-30)
            a = ug / max(K, 1e-30)
            lam_g = self.sorption_lambda(a)
        flux_local = AP * (uP - ug)
        eq_error = flux_local - (AM * (self.water_per_lambda * lam_g - mw[m]) + E * lam_g)
        flux_scale = max(abs(flux_local), abs(AM * mw[m]), abs(C), 1e-10)
        margin = min(ug + 1e-9, upper - ug, b)  # 1e-9 kg/m³ 为根的数值容差。
        return sigma * flux_local, margin, eq_error / flux_scale

    def _fields(self, t, y):
        z = y * self.scale
        Tfull = self.T0 + z[self.slT]
        T = Tfull[self.mea_T]
        mw = z[self.slw]
        mi = np.zeros(self.n)
        mi[self.porous] = z[self.sli]
        mv, ml, eps_g, lam = self.phase_partition(mw, mi, T)
        j = float(np.interp(t, self.input_time, self.input_current))
        # 以下 max 只延拓 RHS 系数；mw、mi 与气体库存的 ODE 状态没有被覆盖。
        eg = np.maximum(eps_g, 1e-12)
        temperature_factor = (np.maximum(T, 100) / 298.15) ** self.cs.temperature_exponent
        factor = temperature_factor * (self.cs.reference_pressure / self.P.operation.pressure) * eg ** self.cs.porosity_exponent
        Dw = np.empty(self.n)
        Dw[self.a] = self.cs.D_water_anode_ref * factor[self.a]
        Dw[self.c] = self.cs.D_water_cathode_ref * factor[self.c]
        Dmem_raw = 1e-10 * np.exp(2416 * (1 / 303.15 - 1 / T[self.mem])) * (
            2.563 - .33 * lam + .0264 * lam ** 2 - .000671 * lam ** 3)
        Dw[self.mem] = np.maximum(Dmem_raw, 1e-20)
        Dh = self.cs.D_hydrogen_ref * factor[self.a]
        Do = self.cs.D_oxygen_ref * factor[self.c]
        ch = z[self.slh] / eg[self.a]
        co = z[self.slo] / eg[self.c]
        kappa_raw = (.5139 * lam - .326) * np.exp(1268 * (1 / 303.15 - 1 / T[self.mem]))
        kappa = np.maximum(kappa_raw, 1e-12)
        Tcc = float(np.dot(T[self.ccl], self.dx[self.ccl]) / self.P.geo.cl_c)
        ph = float(np.dot(self.R * T[self.acl] * ch[self.acl_gas], self.dx[self.acl]) / self.P.geo.cl_a)
        po = float(np.dot(self.R * T[self.ccl] * co[self.ccl_gas], self.dx[self.ccl]) / self.P.geo.cl_c)
        cbar_o = float(np.dot(co[self.ccl_gas], self.dx[self.ccl]) / self.P.geo.cl_c)
        si = mi[self.ccl] / (self.rhoi * self.eps0[self.ccl])
        fa = np.maximum(1 - si, 1e-14) ** self.P.echem.ice_area_exponent
        fa_bar = float(np.dot(fa, self.dx[self.ccl]) / self.P.geo.cl_c)
        j0_eff = fa_bar * self.j0_ref * np.exp(-self.cs.activation_energy / self.R * (
            1 / Tcc - 1 / self.P.echem.temperature_ref))
        oxygen_resistance = float(np.sum(self.oxygen_path_dx / np.maximum(Do, 1e-30)))
        jlim = 4 * self.F * cbar_o / oxygen_resistance
        Erev = 1.229 - 8.5e-4 * (Tcc - 298.15) + self.R * Tcc / (2 * self.F) * np.log(
            max(ph / self.cs.reference_pressure, 1e-30) * np.sqrt(max(po / self.cs.reference_pressure, 1e-30)))
        eta_act = self.R * Tcc / (self.cs.alpha * self.F) * np.arcsinh(j / (2 * max(j0_eff, 1e-100)))
        eta_ohm = j * (np.sum(self.dx[self.mem] / kappa) + self.cs.contact_resistance)
        eta_con = -self.R * Tcc / (4 * self.F) * np.log(max(1 - j / max(jlim, 1e-30), 1e-12))
        voltage = Erev - eta_act - eta_ohm - eta_con
        rates = np.zeros(self.n)
        if self.freezing:
            rates[self.porous] = self.k_freeze * ml[self.porous] * (T[self.porous] < self.cs.freezing_temperature)
            rates[self.porous] -= self.k_melt * mi[self.porous] * (T[self.porous] > self.cs.freezing_temperature)
        return dict(z=z, Tfull=Tfull, T=T, mw=mw, mi=mi, mv=mv, ml=ml, eps_g=eps_g,
                    lam=lam, j=j, Dw=Dw, Dmem=Dmem_raw, Dh=Dh, Do=Do, ch=ch, co=co,
                    kappa=kappa_raw, fa_bar=fa_bar, j0_eff=j0_eff, jlim=jlim,
                    Erev=Erev, eta_act=eta_act, eta_ohm=eta_ohm, eta_con=eta_con,
                    V=voltage, rates=rates)

    def _transport(self, d):
        mw, mi, T, Dw, j = (d[k] for k in ("mw", "mi", "T", "Dw", "j"))
        u = mw - mi
        Nw = np.zeros(self.n + 1)
        conductance = 1 / (self.dx[:-1] / (2 * Dw[:-1]) + self.dx[1:] / (2 * Dw[1:]))
        Nw[1:-1] = -conductance * np.diff(u)
        Nw[0] = -Dw[0] * u[0] / (self.dx[0] / 2)
        Nw[-1] = Dw[-1] * u[-1] / (self.dx[-1] / 2)
        # 膜内迎风面 λ：电渗沿 +x，保正且网格收敛时恢复 M11。
        # 外膜面使用 M43 的界面 λ，不重复加拖曳通量。
        if len(self.internal_mem_faces):
            left_cells = self.internal_mem_faces - 1
            nd_face = 2.5 / 22 * mw[left_cells] / self.water_per_lambda
            Nw[self.internal_mem_faces] += nd_face * self.Mw * j / self.F
        Na, ma, ra = self._interface_flux(self.acl[-1], self.mem[0], 1, mw, mi, T, Dw, j)
        Nc, mc, rc = self._interface_flux(self.ccl[0], self.mem[-1], -1, mw, mi, T, Dw, j)
        Nw[self.interface_a], Nw[self.interface_c] = Na, Nc
        Nh, No = np.zeros(self.na + 1), np.zeros(self.nc + 1)
        for domain, D, c, N in ((self.a, d["Dh"], d["ch"], Nh), (self.c, d["Do"], d["co"], No)):
            dx = self.dx[domain]
            G = 1 / (dx[:-1] / (2 * D[:-1]) + dx[1:] / (2 * D[1:]))
            N[1:-1] = -G * np.diff(c)
        Nh[0] = d["Dh"][0] * (self.c_h_in - d["ch"][0]) / (self.dx[self.a[0]] / 2)
        No[-1] = d["Do"][-1] * (d["co"][-1] - self.c_o_in) / (self.dx[self.c[-1]] / 2)
        q = np.zeros(self.nT + 1)
        q[1:-1] = -self.heat_face_conductance * np.diff(d["Tfull"])
        q[0] = -self.heat_boundary_conductance[0] * (d["Tfull"][0] - self.T0)
        q[-1] = self.heat_boundary_conductance[1] * (d["Tfull"][-1] - self.T0)
        return Nw, Nh, No, q, min(ma, mc), max(abs(ra), abs(rc))

    def _rhs(self, t, y):
        d = self._fields(t, y)
        Nw, Nh, No, q, _, _ = self._transport(d)
        j = d["j"]
        dydt = np.zeros(self.size)
        dwater = -np.diff(Nw) / self.dx
        dwater[self.ccl] += self.Mw * j / (2 * self.F * self.P.geo.cl_c)
        dydt[self.slw] = dwater
        dydt[self.sli] = d["rates"][self.porous]
        dh = -np.diff(Nh) / self.dx[self.a]
        dh[self.acl_gas] -= j / (2 * self.F * self.P.geo.cl_a)
        do = -np.diff(No) / self.dx[self.c]
        do[self.ccl_gas] -= j / (4 * self.F * self.P.geo.cl_c)
        dydt[self.slh], dydt[self.slo] = dh, do
        qgen = j * (self.cs.thermoneutral_voltage - d["V"])
        qphase = self.P.thermal.latent_freezing * d["rates"]
        heat = -np.diff(q) / self.dxT
        heat[self.mea_T] += qgen / self.Lmea + qphase
        dydt[self.slT] = heat / self.capacity
        dydt[self.slbudget] = [self.Mw * j / (2 * self.F), Nw[-1] - Nw[0],
                              qgen, q[-1] - q[0], qphase @ self.dx,
                              Nh[0], j / (2 * self.F), -No[-1], j / (4 * self.F)]
        return dydt / self.scale

    def _physical_margins(self, t, y):
        d = self._fields(t, y)
        _, _, _, _, interface_margin, _ = self._transport(d)
        # 非负状态约束采用 1e-6 kg/m³ 及 5e-7 mol/m³ 的数值裕度。
        # 数量级远低于主要水/气体库存，最大负值另在诊断中原样报告。
        return np.array([
            min(np.min(d["mw"] - d["mi"]) + 1e-6, np.min(d["mi"][self.porous]) + 1e-6),
            np.min(d["eps_g"][self.porous]) - 1e-9,
            min(np.min(d["z"][self.slh]), np.min(d["z"][self.slo])) + 5e-7,
            np.min(d["kappa"]) - 1e-9,
            np.min(d["Dmem"]) - 1e-20,
            (d["jlim"] - d["j"]) / max(abs(d["jlim"]), 1),
            interface_margin,
        ])

    def _jacobian(self, t, y):
        """有限差分Jacobian，显式跳过不反馈的累计收支列。

        SciPy自适应差分对恒为零的累计列可反复增大扰动并溢出。
        使用固定相对尺度扰动，累计列直接置零，避免该数值问题。
        """
        f0 = self._rhs(t, y)
        jac = np.zeros((self.size, self.size))
        for k in range(self.slo.stop):
            dy = 1e-7 * max(abs(y[k]), 0.01)
            trial = y.copy()
            trial[k] += dy
            jac[:, k] = (self._rhs(t, trial) - f0) / dy
        return csr_matrix(jac)

    def simulate(self, time, current, initial_celsius, t_eval=None, max_step=None,
                 rtol=None, atol=None, dense_output=False):
        """积分并返回包含原始空间场、曲线、事件和累计守恒误差的字典。

        输入 time/current 同长、严格递增，current 为非负 A/m²。
        t_eval 缺省为输入时刻；物理事件终止时额外保留实际终点。
        返回的 success 仅表示完整走完积分区间且检查通过，不等于启动成功。
        """
        self.input_time = np.asarray(time, dtype=float)
        self.input_current = np.asarray(current, dtype=float)
        if (self.input_time.ndim != 1 or len(self.input_time) < 2
                or self.input_current.shape != self.input_time.shape
                or not np.all(np.isfinite(self.input_time)) or not np.all(np.isfinite(self.input_current))
                or np.any(np.diff(self.input_time) <= 0) or np.any(self.input_current < 0)):
            raise ValueError("time/current 须为同长度有限一维数组，时间递增且电流非负。")
        self.T0 = float(initial_celsius) + 273.15
        self.c_h_in = self.P.operation.pressure / (self.R * self.T0)
        self.c_o_in = self.y_oxygen * self.c_h_in
        y0 = np.zeros(self.size)
        y0[self.slw.start + self.mem] = self.water_per_lambda * self.P.membrane.lambda_initial
        y0[self.slh] = self.eps0[self.a] * self.c_h_in
        y0[self.slo] = self.eps0[self.c] * self.c_o_in
        y0 /= self.scale
        te = self.input_time.copy() if t_eval is None else np.asarray(t_eval, dtype=float)
        if (te.ndim != 1 or len(te) == 0 or np.any(np.diff(te) <= 0)
                or te[0] < self.input_time[0] or te[-1] > self.input_time[-1]):
            raise ValueError("t_eval 必须递增，且在输入时间范围内。")
        names = ["negative_water_or_ice", "pore_blockage", "gas_depletion",
                 "membrane_conductivity_invalid", "membrane_diffusivity_invalid",
                 "limiting_current_exceeded", "membrane_interface_no_feasible_root"]
        events = []
        for index in range(len(names)):
            def event(t, y, i=index):
                return self._physical_margins(t, y)[i]
            event.terminal = True
            event.direction = -1
            events.append(event)
        initial_margins = self._physical_margins(self.input_time[0], y0)
        bad = np.flatnonzero(initial_margins < 0)
        start = perf_counter()
        if len(bad):
            return self._assemble(np.array([self.input_time[0]]), y0[:, None], y0,
                                  "physical_failure", names[bad[0]], float(self.input_time[0]),
                                  {"nfev": 0, "njev": 0, "nlu": 0, "elapsed_s": 0.}, None)
        sol = solve_ivp(self._rhs, (self.input_time[0], self.input_time[-1]), y0,
                        method="BDF", t_eval=te, dense_output=True,
                        rtol=self.cs.rtol if rtol is None else rtol,
                        atol=self.cs.atol if atol is None else atol,
                        max_step=self.cs.max_step if max_step is None else max_step,
                        jac=self._jacobian, events=events)
        status = "completed" if sol.status == 0 else "numerical_failure"
        event_time, message = None, sol.message
        ts, ys = sol.t, sol.y
        if sol.status == 1:
            status = "physical_failure"
            for name, et in zip(names, sol.t_events):
                if len(et):
                    event_time, message = float(et[0]), name
                    if len(ts) == 0 or event_time > ts[-1] + 1e-12:
                        ts = np.r_[ts, event_time]
                        ys = np.column_stack((ys, sol.sol(event_time)))
                    break
        stats = {"nfev": sol.nfev, "njev": sol.njev, "nlu": sol.nlu,
                 "elapsed_s": perf_counter() - start}
        return self._assemble(ts, ys, y0, status, message, event_time, stats,
                              sol.sol if dense_output else None)

    def _assemble(self, ts, ys, y0, status, message, event_time, stats, dense):
        fields = [self._fields(t, y) for t, y in zip(ts, ys.T)]
        def stack(key):
            return np.asarray([d[key] for d in fields])
        if not len(ts):
            raise RuntimeError("积分器在第一个请求输出时刻之前失败；请令 t_eval 包含初始时刻。")
        z = ys.T * self.scale
        T_C, mw, mi = stack("Tfull") - 273.15, stack("mw"), stack("mi")
        initial = y0 * self.scale
        W0 = initial[self.slw] @ self.dx
        water_mass = mw @ self.dx
        ice_mass = mi @ self.dx
        energy = (T_C - (self.T0 - 273.15)) @ (self.capacity * self.dxT)
        budget = z[:, self.slbudget]
        water_error = water_mass - W0 - budget[:, 0] + budget[:, 1]
        energy_error = energy - budget[:, 2] + budget[:, 3] - budget[:, 4]
        H0 = initial[self.slh] @ self.dx[self.a]
        O0 = initial[self.slo] @ self.dx[self.c]
        hydrogen_error = z[:, self.slh] @ self.dx[self.a] - H0 - budget[:, 5] + budget[:, 6]
        oxygen_error = z[:, self.slo] @ self.dx[self.c] - O0 - budget[:, 7] + budget[:, 8]
        interface_residual = np.asarray([self._transport(d)[-1] for d in fields])
        water_scale = max(W0, float(np.max(np.abs(budget[:, 0]))), 1e-8)
        energy_scale = max(float(np.max(np.abs(budget[:, 2]))), 1.)
        diagnostics = dict(stats,
            heat_capacity_J_m2_K=self.heat_capacity_area,
            water_initial_kg_m2=float(W0),
            max_water_balance_abs_kg_m2=float(np.max(np.abs(water_error))),
            max_water_balance_relative=float(np.max(np.abs(water_error)) / water_scale),
            max_energy_balance_abs_J_m2=float(np.max(np.abs(energy_error))),
            max_energy_balance_relative=float(np.max(np.abs(energy_error)) / energy_scale),
            max_hydrogen_balance_abs_mol_m2=float(np.max(np.abs(hydrogen_error))),
            max_oxygen_balance_abs_mol_m2=float(np.max(np.abs(oxygen_error))),
            max_interface_normalized_residual=float(np.max(interface_residual)),
            min_unfrozen_water_kg_m3=float(np.min(mw - mi)),
            min_ice_kg_m3=float(np.min(mi[:, self.porous])),
            min_gas_porosity=float(np.min(stack("eps_g")[:, self.porous])),
            min_membrane_lambda=float(np.min(stack("lam"))),
            min_membrane_conductivity_S_m=float(np.min(stack("kappa"))),
            min_current_margin_A_m2=float(np.min(stack("jlim") - stack("j"))),
            negative_voltage_count=int(np.count_nonzero(stack("V") < 0)),
            thermal_cells=self.nT, mass_cells=self.n,
            grid_counts=self.layer_counts,
            numerical_extension="仅 RHS 有限延拓；原始状态不裁剪，物理事件终止。",
            membrane_drag_faces="一阶迎风；电渗沿 +x；界面用 M43。",
        )
        residual_ok = diagnostics["max_interface_normalized_residual"] <= 1e-6
        if status == "completed" and not residual_ok:
            status, message = "numerical_failure", "membrane_interface_residual_exceeds_1e-6"
        result = dict(
            t=np.asarray(ts), j=stack("j"), T_mean_C=T_C @ self.dxT / self.Lthermal,
            T_mea_C=T_C[:, self.mea_T] @ self.dx / self.Lmea, V=stack("V"),
            eps_ice_max=np.max(mi[:, self.porous] / self.rhoi, axis=1),
            eps_ice_mean=(mi @ self.dx / self.rhoi) / self.Lmea,
            T_C=T_C, mw=mw, mi=mi, mv=stack("mv"), ml=stack("ml"),
            eps_g=stack("eps_g"), lambda_mem=stack("lam"),
            hydrogen_concentration=stack("ch"), oxygen_concentration=stack("co"),
            fa_bar=stack("fa_bar"), j0_eff=stack("j0_eff"), jlim=stack("jlim"),
            Erev=stack("Erev"), eta_act=stack("eta_act"), eta_ohm=stack("eta_ohm"), eta_con=stack("eta_con"),
            x_um=self.xT * 1e6, x_mea_um=self.x * 1e6, dx_m=self.dx,
            x_edges_um=np.r_[self.xT[0] - self.dxT[0] / 2,
                               self.xT + self.dxT / 2] * 1e6,
            x_mea_edges_um=np.r_[self.x[0] - self.dx[0] / 2,
                                   self.x + self.dx / 2] * 1e6,
            dx=self.dxT.copy(), dx_mea=self.dx.copy(),
            labels=self.labels.copy(), labels_thermal=self.labelsT.copy(),
            water_mass_kg_m2=water_mass, ice_mass_kg_m2=ice_mass,
            water_balance_error_kg_m2=water_error, energy_balance_error_J_m2=energy_error,
            cumulative_water_generated_kg_m2=budget[:, 0], cumulative_water_out_kg_m2=budget[:, 1],
            cumulative_reaction_heat_J_m2=budget[:, 2], cumulative_heat_loss_J_m2=budget[:, 3],
            cumulative_phase_heat_J_m2=budget[:, 4],
            diagnostics=diagnostics, status=status, success=status == "completed",
            message=message, event_time=event_time, initial_celsius=self.T0 - 273.15,
            j0_ref=self.j0_ref, k_freeze=self.k_freeze, include_bp=self.include_bp,
            freezing=self.freezing,
        )
        if dense is not None:
            result["dense_scaled_state"] = dense
        return result
