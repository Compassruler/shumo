"""同一电流和电化学参数下，比较含双极板与仅MEA的热域。"""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
if sys.platform == "win32" and sys.version_info[:2] == (3, 12):
    sys.path.insert(0, str(HERE / ".python_deps"))
sys.path.insert(0, str(HERE.parent))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from params import P
from data_io import read_experiments
from cold_start_model import ColdStartModel


def metrics(result, source):
    query = result["t"]
    t_exp = source["t"]
    valid = (query >= t_exp[0]-1e-9) & (query <= t_exp[-1]+1e-9)
    query = query[valid]
    def calc(model, observed):
        diff = model[valid] - np.interp(query, t_exp, observed)
        return dict(mae=float(np.mean(np.abs(diff))),
                    rmse=float(np.sqrt(np.mean(diff**2))),
                    max_abs=float(np.max(np.abs(diff))))
    return dict(status=result["status"], message=result["message"],
                valid_end_s=float(result["t"][-1]), sample_count=len(query),
                average_temperature_C=calc(result["T_mean_C"], source["temperature_exp"]),
                voltage_V=calc(result["V"], source["voltage_exp"]),
                final_average_temperature_C=float(result["T_mean_C"][-1]),
                final_voltage_V=float(result["V"][-1]),
                max_temperature_C=float(np.max(result["T_mean_C"])),
                heat_capacity_J_m2_K=result["diagnostics"]["heat_capacity_J_m2_K"])


def apparent_capacity(source):
    """题目MD第13节的量级诊断，使用实测V/j/T，不作为模型输入。"""
    t = source["t"]
    temp = source["temperature_exp"]
    reaction = np.trapezoid(source["current"] * (P.cold_start.thermoneutral_voltage -
                                                  source["voltage_exp"]), t)
    cooling = np.trapezoid(2 * P.thermal.h * (temp-temp[0]), t)
    return float((reaction-cooling)/(temp[-1]-temp[0]))


def main():
    experiments = read_experiments()
    fit = json.loads((HERE/"results"/"calibration.json").read_text(encoding="utf-8"))
    folder = HERE/"results"/"thermal_domain_comparison"
    folder.mkdir(parents=True, exist_ok=True)
    current_summary = json.loads((HERE/"results"/"summary.json").read_text(encoding="utf-8"))
    report = dict(method="两种热域使用相同F列电流、初温、环境温度、j0_ref及k_freeze；"
                         "含BP结果取已验证基准，MEA-only重新完整积分。",
                  reference_j0_ref_A_m2=fit["j0_ref"], reference_k_freeze_s1=fit["k_freeze"],
                  cases={})
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), sharex="col")
    font_names = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
    if "Microsoft YaHei" in font_names:
        plt.rcParams["font.family"] = "Microsoft YaHei"
    for column, initial in enumerate((-20, -25)):
        source = experiments[initial]
        model = ColdStartModel(P, include_bp=False,
                               j0_ref=fit["j0_ref"], k_freeze=fit["k_freeze"])
        result = model.simulate(source["t"], source["current"], initial,
                                t_eval=source["t"])
        bp = current_summary["cases"][str(initial)]
        no_bp = metrics(result, source)
        report["cases"][str(initial)] = dict(
            with_bipolar_plates=dict(status=bp["solver_status"],
                valid_end_s=bp["valid_time_range_s"][-1],
                average_temperature_C=bp["metrics_at_experimental_sampling_times"]["temperature_C"],
                voltage_V=bp["metrics_at_experimental_sampling_times"]["voltage_V"],
                final_average_temperature_C=bp["final_model_temperature_C"],
                final_voltage_V=bp["final_model_voltage_V"],
                heat_capacity_J_m2_K=bp["diagnostics"]["heat_capacity_J_m2_K"]),
            mea_only=no_bp,
            experiment_based_apparent_heat_capacity_J_m2_K=apparent_capacity(source),
            apparent_capacity_note="用实测V/j/T估算的量级诊断；将实测均温近似为表面温度，忽略潜热。")
        # 含BP数据直接来自已保存的逐时刻结果，避免数值重跑引起比较口径变化。
        import csv
        with (HERE/"results"/f"minus{abs(initial)}C_timeseries.csv").open(
                "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        t_bp = np.asarray([float(row["time_s"]) for row in rows])
        T_bp = np.asarray([float(row["model_mean_temperature_full_domain_C"]) for row in rows])
        V_bp = np.asarray([float(row["model_voltage_V"]) for row in rows])
        for ax, exp, bp_values, alt_values, label in (
            (axes[0, column], source["temperature_exp"], T_bp,
             result["T_mean_C"], "Temperature (°C)"),
            (axes[1, column], source["voltage_exp"], V_bp,
             result["V"], "Voltage (V)")):
            ax.scatter(source["t"][::5], exp[::5], s=11, color="#d97732", label="Experiment")
            ax.plot(t_bp, bp_values, color="#1375a5", label="With BP")
            ax.plot(result["t"], alt_values, color="#c52254", label="MEA only")
            ax.set_ylabel(label)
            ax.grid(alpha=.2)
            ax.set_title(f"Initial {initial} °C")
            ax.legend(loc="best", frameon=False)
        axes[1, column].set_xlabel("Time (s)")
    fig.tight_layout()
    fig.savefig(folder/"with_vs_without_bp.png", dpi=200)
    fig.savefig(folder/"with_vs_without_bp.pdf")
    plt.close(fig)
    (folder/"comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
