"""问题4：动态控制器离线参数整定（建模文档第4章）。

初次运行发现 DEFAULT_PARAMS 的 T_targ=[4,18,20,18,4] 过度加热中心片，
动态能耗反而高于恒功率。此处按文档 3.2 的"各片目标=冰点+裕度(≈4℃)"、
以及恒功率策略C"中心片少给功率"的机理，扫描 T_targ 剖面与 t_plan，
以工况1（最冷、最难）为主，找能耗最小的可行参数。

只读不写结果，把扫描表打印出来供人工选定。
"""
import sys
from pathlib import Path

import numpy, scipy, numba, matplotlib  # noqa: F401
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dynamic_model as dm  # noqa: E402

DT = 0.05
SCALE = 2

# 工况1 初始场（完全冷却均匀 -30℃）
TEMP0 = np.full(7, -30.0)


def eval_params(t_targ, t_plan, kp=0.5, ki=0.08):
    s, tr, _, _ = dm.simulate_dynamic(
        TEMP0, params={"T_targ": t_targ, "t_plan": t_plan, "K_P": kp, "K_I": ki},
        dt=DT, scale=SCALE, t_horizon=150.0)
    return s


def main():
    profiles = {
        "uniform 4": [4, 4, 4, 4, 4],
        "4,3,3,3,4": [4, 3, 3, 3, 4],
        "4,2,2,2,4": [4, 2, 2, 2, 4],
        "4,1,1,1,4": [4, 1, 1, 1, 4],
        "uniform 3": [3, 3, 3, 3, 3],
        "uniform 2": [2, 2, 2, 2, 2],
        "6,4,4,4,6": [6, 4, 4, 4, 6],
        "8,4,4,4,8": [8, 4, 4, 4, 8],
    }
    t_plans = [3.0, 5.0, 8.0, 12.0]

    print(f"{'T_targ':14s} {'t_plan':>6s} {'feas':>5s} {'t_first':>8s} "
          f"{'E_aux':>9s} {'Vmin':>6s} {'ice':>8s} {'dTmax':>7s}")
    best = None
    for name, tt in profiles.items():
        for tp in t_plans:
            s = eval_params(tt, tp)
            line = (f"{name:14s} {tp:6.1f} {str(s['feasible']):>5s} "
                    f"{s['t_first_s']:8.2f} {s['E_aux_J']:9.1f} "
                    f"{s['min_voltage_V']:6.3f} {s['max_ice_bulk']:8.4f} "
                    f"{s['dTmax_K']:7.2f}")
            print(line, flush=True)
            if s['feasible'] and (best is None or s['E_aux_J'] < best[2]):
                best = (name, tt, s['E_aux_J'], tp, s['t_first_s'],
                        s['min_voltage_V'], s['max_ice_bulk'], s['dTmax_K'])

    print("\n== 工况1 最优（能耗最小可行）==")
    print(f"T_targ={best[1]}  t_plan={best[3]}  E_aux={best[2]:.1f}J "
          f"t_first={best[4]:.2f}s Vmin={best[5]:.3f} ice={best[6]:.4f} dTmax={best[7]:.2f}")


if __name__ == "__main__":
    main()
