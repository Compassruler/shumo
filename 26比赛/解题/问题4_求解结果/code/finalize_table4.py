"""问题4：表4 终稿 —— 动态控制器采用自适应 t_plan。

自适应 t_plan：参考轨迹以最大可行加热速率 v_max=2.0 K/s 规划，
t_plan = (T_targ_中心 - T0_中心) / v_max，随初始温度自适应：
  工况1(-30) → 25 s；工况2(-9) → ~14.5 s；工况3(-22) → ~21 s。
其余沿用 DEFAULT_PARAMS（端部目标 4℃=冰点+热裕度，中心/近端 18~20℃ 提供导热支撑）。
"""
import json
import sys
import time
from pathlib import Path

import numpy, scipy, numba, matplotlib  # noqa: F401
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from precool import PrecoolModel          # noqa: E402
import dynamic_model as dm                # noqa: E402

DATA = HERE.parent / "data"
CONST_POWER = [1.0, 1.0, 0.6245115587719579, 1.0, 1.0]
DT = 0.05
SCALE = 2
V_MAX = 2.0   # K/s 最大可行加热速率（满功率下中心片温升率）


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=float)


def summarize_const(s):
    return {k: s[k] for k in ("feasible", "first_success_s", "elapsed_s",
                              "min_voltage_V", "max_ice_bulk", "dTmax_K",
                              "E_aux_J", "E_gen_J", "E_phase_J", "E_loss_J",
                              "E_sensible_J", "energy_residual_J",
                              "final_min_T_C", "final_max_T_C", "final_left_EP_C")}


def main():
    pm = PrecoolModel(scale=1)
    cases = {
        "工况1_完全冷却": np.full(7, -30.0),
        "工况2_预冷20min": pm.node_temps(pm.solve(20 * 60.0)),
        "工况3_预冷40min": pm.node_temps(pm.solve(40 * 60.0)),
    }

    table4 = []
    traj_out = {}
    for cname, temp0 in cases.items():
        # 自适应 t_plan：以中心片目标 20℃ 与中心片初温之差、按 2 K/s 规划
        t_plan = max(5.0, (20.0 - float(temp0[2])) / V_MAX)
        s_dyn, tr_dyn, _, _ = dm.simulate_dynamic(
            temp0, params={"t_plan": t_plan}, dt=DT, scale=SCALE, t_horizon=150.0)
        s_con, h_con, _, _ = dm.simulate_constant(
            temp0, CONST_POWER, th=150.0, dt=DT, scale=SCALE, stop=True, record=True)

        print(f"[{cname}] t_plan={t_plan:.1f}s")
        print(f"  动态  : E_aux={s_dyn['E_aux_J']:.1f}J t={s_dyn['t_first_s']:.2f}s "
              f"Vmin={s_dyn['min_voltage_V']:.3f} ice={s_dyn['max_ice_bulk']:.4f} dTmax={s_dyn['dTmax_K']:.2f}K")
        print(f"  恒功率: E_aux={s_con['E_aux_J']:.1f}J t={s_con['first_success_s']:.2f}s "
              f"Vmin={s_con['min_voltage_V']:.3f} ice={s_con['max_ice_bulk']:.4f} dTmax={s_con['dTmax_K']:.2f}K", flush=True)

        table4.append({"工况": cname, "策略": "动态控制", "t_plan_s": t_plan, **s_dyn})
        table4.append({"工况": cname, "策略": "恒功率(问题3基准)", "t_plan_s": None, **summarize_const(s_con)})

        traj_out[cname] = {
            "t_plan_s": t_plan,
            "dynamic": {k: np.asarray(v).tolist() for k, v in tr_dyn.items()},
            "constant": {
                "time_s": h_con[:, 0].tolist(), "j_A_cm2": h_con[:, 1].tolist(),
                "T1_C": h_con[:, 3].tolist(), "T2_C": h_con[:, 4].tolist(),
                "T3_C": h_con[:, 5].tolist(), "T4_C": h_con[:, 6].tolist(),
                "T5_C": h_con[:, 7].tolist(), "TEL_C": h_con[:, 8].tolist(),
                "TER_C": h_con[:, 9].tolist(),
                "V1_V": h_con[:, 10].tolist(), "V3_V": h_con[:, 12].tolist(),
                "V5_V": h_con[:, 14].tolist(),
                "ice1": h_con[:, 15].tolist(), "ice3": h_con[:, 17].tolist(),
                "ice5": h_con[:, 19].tolist(), "E_aux_J": h_con[:, 20].tolist(),
            },
        }

    dump_json(table4, DATA / "表4_问题四主结果.json")
    dump_json(traj_out, DATA / "三工况轨迹_供绘图.json")

    import csv
    cols = ["工况", "策略", "t_plan_s", "feasible", "first_success_s", "E_aux_J",
            "min_voltage_V", "max_ice_bulk", "dTmax_K", "final_min_T_C", "final_max_T_C"]
    with open(DATA / "表4_问题四主结果.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in table4:
            w.writerow([row.get(c, "") for c in cols])

    print("\n== 表4 终稿 ==")
    for row in table4:
        st = "成功" if row.get("feasible") else "失败"
        ts = row.get("first_success_s", -1)
        print(f"  {row['工况']} / {row['策略']}: {st} "
              f"t_s={ts:.2f}s E_aux={row.get('E_aux_J', float('nan')):.1f}J "
              f"Vmin={row.get('min_voltage_V', float('nan')):.3f}V "
              f"ice={row.get('max_ice_bulk', float('nan')):.4f} "
              f"dTmax={row.get('dTmax_K', float('nan')):.2f}K")


if __name__ == "__main__":
    main()
