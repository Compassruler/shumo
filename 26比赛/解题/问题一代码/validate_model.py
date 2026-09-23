"""有物理意义的独立检查：零负载、相分配、相变符号、守恒及失效事件。"""
from pathlib import Path
import sys
import json

HERE = Path(__file__).resolve().parent
if sys.platform == "win32" and sys.version_info[:2] == (3, 12):
    sys.path.insert(0, str(HERE / ".python_deps"))
sys.path.insert(0, str(HERE.parent))
import numpy as np
from params import P
from cold_start_model import ColdStartModel


def main():
    checks = {}
    model = ColdStartModel(P, j0_ref=.2)
    r = model.simulate(np.array([0., .1, 1.]), np.zeros(3), -20, dense_output=True)
    assert r["success"], r["message"]
    checks["zero_current_temperature_drift_K"] = float(np.max(np.abs(r["T_C"]+20)))
    assert checks["zero_current_temperature_drift_K"] < 1e-9
    assert np.max(np.abs(r["mi"])) < 1e-9
    assert abs(model.heat_capacity_area-6127.47966) < 1e-7
    checks["heat_capacity_J_m2_K"] = model.heat_capacity_area

    # 构造含液水/冰的状态，以独立质量和体积恒等式检查相分配。
    T = np.full(model.n, 253.15)
    mi = np.zeros(model.n)
    mi[model.porous] = model.eps0[model.porous]*P.thermal.ice.rho*.2
    mw = mi.copy()
    mw[model.porous] += 2.0
    mw[model.mem] = model.water_per_lambda * 3
    mv, ml, eps, lam = model.phase_partition(mw, mi, T)
    p = model.porous
    mass_error = np.max(np.abs(mv[p]+ml[p]+mi[p]-mw[p]))
    volume_error = np.max(np.abs(eps[p]+ml[p]/P.thermal.liquid.rho+
                                  mi[p]/P.thermal.ice.rho-model.eps0[p]))
    vapor_pressure = mv[p]/eps[p] * P.constants.R*T[p]/P.constants.M_water
    saturation_error = np.max(np.abs(vapor_pressure-model.saturation_pressure(T[p])))
    assert mass_error < 1e-12 and volume_error < 1e-12 and saturation_error < 1e-6
    checks.update(phase_mass_error=float(mass_error), phase_volume_error=float(volume_error),
                  saturated_vapor_pressure_error_Pa=float(saturation_error))

    # 取积分器真实初值，替换水冰场，不调用任何新的实验数据。
    y = r["dense_scaled_state"](0.).copy()
    z = y * model.scale
    z[model.slw] = mw
    z[model.sli] = mi[p]
    y = z/model.scale
    for celsius, expected_sign in ((-20., 1), (1., -1)):
        trial = y.copy()
        trial[model.slT] = (celsius+20)/model.scale[model.slT]
        d = model._fields(0., trial)
        f = model._rhs(0., trial)*model.scale
        Nw, _, _, q, _, _ = model._transport(d)
        water_rate = f[model.slw] @ model.dx
        heat_rate = (f[model.slT]*model.capacity) @ model.dxT
        phase_heat = P.thermal.latent_freezing * (d["rates"] @ model.dx)
        assert expected_sign * (d["rates"][p].sum()) > 0
        assert abs(water_rate - (Nw[0]-Nw[-1])) < 1e-10
        assert abs(heat_rate-(q[0]-q[-1]+phase_heat)) < 1e-7
        checks[f"phase_{celsius}_C_heat_W_m2"] = float(phase_heat)

    dry = y.copy()
    dry[model.slw.start+model.mem] = (model.water_per_lambda*.5)/model.scale[model.slw.start+model.mem]
    margins = model._physical_margins(0., dry)
    assert margins[3] < 0, "lambda=0.5应触发膜电导失效"
    checks["dry_membrane_invalid_detected"] = True
    checks["zero_current_diagnostics"] = r["diagnostics"]
    output = HERE/"results"/"physical_checks.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
