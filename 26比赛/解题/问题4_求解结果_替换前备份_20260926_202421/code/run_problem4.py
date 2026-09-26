"""问题4：一次性最小化重跑 —— 补齐表4 + 10~100min 扫描,并把结果落盘。

运行方式（Python 3.14）:
    cd 问题4_求解结果/code
    python run_problem4.py

先预导入 3.14 原生库,使 fast_cell 里针对 cp312 的 .python_deps sys.path 插入失效
（见 问题3_求解结果/code/verify_uniform_power.py 与 memory/shumo-python-env.md）。
"""
import json
import sys
import time
from pathlib import Path

import numpy, scipy, numba, matplotlib  # noqa: F401  3.14 原生库预导入
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from precool import PrecoolModel          # noqa: E402
import dynamic_model as dm                # noqa: E402

DATA = HERE.parent / "data"
DATA.mkdir(exist_ok=True)

# 问题3 策略C 的恒功率分配（对 -30℃ 整定的最小可行协同恒功率）
CONST_POWER = [1.0, 1.0, 0.6245115587719579, 1.0, 1.0]

# 数值分辨率（问题4 dynamic_model 原生默认；与问题3 基准的一致性在工况1 另行核对）
DT = 0.05
SCALE = 2


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
    t_start = time.time()

    # ------------------------------------------------------------------
    # 0) 预冷初始场
    # ------------------------------------------------------------------
    pm = PrecoolModel(scale=1)
    cases = {
        "工况1_完全冷却": np.full(7, -30.0),
        "工况2_预冷20min": pm.node_temps(pm.solve(20 * 60.0)),
        "工况3_预冷40min": pm.node_temps(pm.solve(40 * 60.0)),
    }
    init_fields = {k: v.tolist() for k, v in cases.items()}
    dump_json(init_fields, DATA / "三工况初始温度场_七节点.json")
    print("== 三工况初始温度场 [T1..T5, EP_L, EP_R] ℃ ==")
    for k, v in cases.items():
        print(f"  {k}: {np.round(v, 3).tolist()}")
    print(flush=True)

    # ------------------------------------------------------------------
    # 1) 表4：动态控制 vs 恒功率基准（三种工况）
    # ------------------------------------------------------------------
    table4 = []
    traj_out = {}
    for cname, temp0 in cases.items():
        # 动态控制
        s_dyn, tr_dyn, _, _ = dm.simulate_dynamic(
            temp0, dt=DT, scale=SCALE, t_horizon=150.0)
        print(f"[动态] {cname}: feasible={s_dyn['feasible']} "
              f"t_first={s_dyn['t_first_s']:.2f}s E_aux={s_dyn['E_aux_J']:.1f}J "
              f"Vmin={s_dyn['min_voltage_V']:.3f}V ice={s_dyn['max_ice_bulk']:.4f} "
              f"dTmax={s_dyn['dTmax_K']:.2f}K", flush=True)
        # 恒功率基准（问题3 策略C 复算）
        s_con, h_con, _, _ = dm.simulate_constant(
            temp0, CONST_POWER, th=150.0, dt=DT, scale=SCALE, stop=True, record=True)
        print(f"[恒功率] {cname}: feasible={s_con['feasible']} "
              f"t_first={s_con['first_success_s']:.2f}s E_aux={s_con['E_aux_J']:.1f}J "
              f"Vmin={s_con['min_voltage_V']:.3f}V ice={s_con['max_ice_bulk']:.4f} "
              f"dTmax={s_con['dTmax_K']:.2f}K", flush=True)

        table4.append({"工况": cname, "策略": "动态控制", **s_dyn})
        table4.append({"工况": cname, "策略": "恒功率(问题3基准)", **summarize_const(s_con)})

        # 保存代表性轨迹（供绘图）
        traj_out[cname] = {
            "dynamic": {k: np.asarray(v).tolist() for k, v in tr_dyn.items()},
            "constant": {
                "time_s": h_con[:, 0].tolist(),
                "j_A_cm2": h_con[:, 1].tolist(),
                "T1_C": h_con[:, 3].tolist(), "T2_C": h_con[:, 4].tolist(),
                "T3_C": h_con[:, 5].tolist(), "T4_C": h_con[:, 6].tolist(),
                "T5_C": h_con[:, 7].tolist(), "TEL_C": h_con[:, 8].tolist(),
                "TER_C": h_con[:, 9].tolist(),
                "V1_V": h_con[:, 10].tolist(), "V3_V": h_con[:, 12].tolist(),
                "V5_V": h_con[:, 14].tolist(),
                "ice1": h_con[:, 15].tolist(), "ice3": h_con[:, 17].tolist(),
                "ice5": h_con[:, 19].tolist(),
                "E_aux_J": h_con[:, 20].tolist(),
            },
        }

    dump_json(table4, DATA / "表4_问题四主结果.json")
    dump_json(traj_out, DATA / "三工况轨迹_供绘图.json")

    # 表4 CSV（字段对齐建模文档 5.3）
    import csv
    cols = ["工况", "策略", "feasible", "first_success_s", "E_aux_J", "min_voltage_V",
            "max_ice_bulk", "dTmax_K", "final_min_T_C", "final_max_T_C"]
    with open(DATA / "表4_问题四主结果.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for row in table4:
            w.writerow([row.get(c, "") for c in cols])

    # ------------------------------------------------------------------
    # 2) 第(2)问：10~100min 预冷 + 恒功率冷启动扫描
    # ------------------------------------------------------------------
    scan_min = [10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]
    fields = pm.scan(scan_min)   # {tau_min: 整堆温度场 ℃}
    scan_rows = []
    scan_traj = {}
    for tc in scan_min:
        temp0 = pm.node_temps(fields[tc])
        s_con, h_con, _, _ = dm.simulate_constant(
            temp0, CONST_POWER, th=150.0, dt=DT, scale=SCALE, stop=True, record=(tc in (10, 40, 100)))
        row = {"冷却时间_min": tc,
               "初始场均温_C": float(pm.mean_temp(fields[tc])),
               "初始场T1_C": float(temp0[0]), "初始场T3_C": float(temp0[2]),
               "初始场T5_C": float(temp0[4])}
        row.update(summarize_const(s_con))
        scan_rows.append(row)
        print(f"[扫描] tau_c={tc:3d}min 初始均温={row['初始场均温_C']:6.2f}℃ "
              f"feasible={s_con['feasible']} t_first={s_con['first_success_s']:.2f}s "
              f"E_aux={s_con['E_aux_J']:.1f}J", flush=True)
        if tc in (10, 40, 100):
            scan_traj[str(tc)] = {
                "time_s": h_con[:, 0].tolist(), "T1_C": h_con[:, 3].tolist(),
                "T3_C": h_con[:, 5].tolist(), "T5_C": h_con[:, 7].tolist(),
                "V1_V": h_con[:, 10].tolist(), "ice1": h_con[:, 15].tolist(),
                "E_aux_J": h_con[:, 20].tolist()}

    dump_json(scan_rows, DATA / "预冷10到100min_恒功率冷启动.json")
    dump_json(scan_traj, DATA / "扫描代表性轨迹.json")
    with open(DATA / "预冷10到100min_恒功率冷启动.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(scan_rows[0].keys()))
        w.writeheader()
        w.writerows(scan_rows)

    print(f"\n[完成] 总耗时 {time.time() - t_start:.1f}s，结果已落盘至 {DATA}")
    print("表4 主结果:", flush=True)
    for row in table4:
        st = "成功" if row.get("feasible") else "失败"
        print(f"  {row['工况']} / {row['策略']}: {st} "
              f"t_s={row.get('first_success_s', -1):.2f}s "
              f"E_aux={row.get('E_aux_J', float('nan')):.1f}J "
              f"Vmin={row.get('min_voltage_V', float('nan')):.3f}V "
              f"ice_max={row.get('max_ice_bulk', float('nan')):.4f} "
              f"dTmax={row.get('dTmax_K', float('nan')):.2f}K")


if __name__ == "__main__":
    main()
