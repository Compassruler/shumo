"""问题一第一小问入口：F列输入，-20℃标定，-25℃留出计算。

用法：python run_question1.py --fit --verify
      python run_question1.py              # 有已保存标定时复现，否则先标定
      python run_question1.py --no-fit      # 仅题给/假设初猜，明确标记未标定
实测电压和温度只在本文件的误差目标中使用，不进入物理求解器。
"""
from pathlib import Path
import argparse
import json
import hashlib
import sys
import time

HERE = Path(__file__).resolve().parent
if sys.platform == "win32" and sys.version_info[:2] == (3, 12) and (HERE / ".python_deps").exists():
    sys.path.insert(0, str(HERE / ".python_deps"))
sys.path.insert(0, str(HERE.parent))
import numpy as np
import scipy
from scipy.optimize import least_squares
from params import P
from data_io import read_experiments, write_csv
from cold_start_model import ColdStartModel


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def dump_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    default=json_default), encoding="utf-8")


def model_fingerprint():
    """防止更换方程或物性后静默沿用旧标定。"""
    h = hashlib.sha256()
    for path in (HERE.parent / "params.py", HERE / "cold_start_model.py"):
        h.update(path.read_bytes())
    return h.hexdigest()


def solve(data, j0, kf, **options):
    constructor = {key: options.pop(key) for key in tuple(options)
                   if key in ("grid_scale", "include_bp", "freezing")}
    model = ColdStartModel(P, j0_ref=j0, k_freeze=kf, **constructor)
    return model.simulate(data["t"], data["current"], data["initial_celsius"],
                          t_eval=data["t"], **options)


def calibrate(data, output_dir, max_nfev=24):
    """M50–51：训练工况全184点、两个正参数、固定标准差权重。"""
    dv = float(np.std(data["voltage_exp"]))
    dt = float(np.std(data["temperature_exp"]))
    if min(dv, dt) <= 0:
        raise ValueError("训练序列标准差为零，需另行明确残差尺度")
    trace, accepted, cache = [], [], {}
    lower = np.log10([P.cold_start.fit_j0_bounds[0], P.cold_start.fit_k_bounds[0]])
    upper = np.log10([P.cold_start.fit_j0_bounds[1], P.cold_start.fit_k_bounds[1]])

    def objective(log_parameters):
        key = tuple(np.round(log_parameters, 12))
        if key in cache:
            return cache[key]
        j0, kf = 10 ** np.asarray(log_parameters)
        start = time.perf_counter()
        entry = dict(j0_ref=float(j0), k_freeze=float(kf))
        try:
            r = solve(data, j0, kf)
            full = bool(r["success"] and len(r["t"]) == len(data["t"]) and
                        np.allclose(r["t"], data["t"], atol=1e-8))
            if full:
                residual = np.r_[(r["V"]-data["voltage_exp"])/dv,
                                 (r["T_mean_C"]-data["temperature_exp"])/dt]
                score = float(np.dot(residual, residual)/len(data["t"]))
                entry.update(success=True, objective=score)
                accepted.append((score, float(j0), float(kf)))
            else:
                # 失效候选不补曲线、不视为可接受结果，保存具体失败原因。
                end = float(r["t"][-1]) if len(r["t"]) else 0.0
                residual = np.full(2*len(data["t"]), 100.+data["t"][-1]-end)
                entry.update(success=False, objective=None, message=r["message"], end_s=end)
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            residual = np.full(2*len(data["t"]), 200.)
            entry.update(success=False, objective=None, message=str(exc))
        entry["runtime_s"] = round(time.perf_counter()-start, 3)
        trace.append(entry)
        cache[key] = residual
        print(f"标定 {len(trace):03d}: j0={j0:.6g}, kf={kf:.6g}, "
              f"J={entry.get('objective')}, {entry['runtime_s']} s", flush=True)
        dump_json(output_dir / "calibration_trace.json", trace)
        return residual

    starts = []
    # 0.2 A/m²由训练工况初始电压量级估计，仅作新增搜索初猜；
    # 每次仍完整积分，最终值不由单点代入决定。
    start_j0 = 0.2
    for kf in P.cold_start.fit_k_starts:
        opt = least_squares(objective, np.log10([start_j0, kf]),
                            bounds=(lower, upper), diff_step=0.003,
                            ftol=3e-4, xtol=3e-4, gtol=3e-4, max_nfev=max_nfev)
        starts.append(dict(start_kf=kf, parameters=(10**opt.x).tolist(),
                           scipy_success=bool(opt.success), message=opt.message,
                           nfev=opt.nfev, cost=float(opt.cost)))
    if not accepted:
        dump_json(output_dir / "calibration_failure.json", dict(starts=starts, trace=trace))
        raise RuntimeError("所有标定候选均不能完成实验时段。请查看calibration_failure.json，"
                           "不得将提前失效后的时段补成正常预测。")
    score, j0, kf = min(accepted)
    # 固定j0的冻结速率剖面仅作敏感性诊断，不是统计置信区间。
    profile = []
    for factor in (0.1, 1., 10.):
        trial = np.clip(kf*factor, *P.cold_start.fit_k_bounds)
        residual = objective(np.log10([j0, trial]))
        profile.append(dict(k_freeze=float(trial),
                            objective=float(residual @ residual / len(data["t"]))))
    record = dict(j0_ref=j0, k_freeze=kf, k_melt=kf*P.cold_start.k_melt_ratio,
                  objective=score, training_celsius=-20, validation_celsius=-25,
                  residual_scale_voltage_V=dv, residual_scale_temperature_K=dt,
                  source_sha256=data["audit"]["sha256"], model_sha256=model_fingerprint(), starts=starts,
                  fixed_j0_kf_profile=profile, n_simulations=len(trace),
                  bounds=dict(j0=P.cold_start.fit_j0_bounds, kf=P.cold_start.fit_k_bounds),
                  note="冻结系数为本闭合模型的有效标定参数；融化速率采用km=kf假设。")
    dump_json(output_dir / "calibration.json", record)
    return record


def verify_convergence(experiments, baseline, calibration, output_dir):
    """每层网格加倍，同时步长减半/容差收紧；各工况独立检查。"""
    rows = []
    for initial, data in experiments.items():
        fine = solve(data, calibration["j0_ref"], calibration["k_freeze"],
                     grid_scale=2, max_step=P.cold_start.max_step/2,
                     rtol=P.cold_start.rtol/5)
        base = baseline[initial]
        entry = dict(initial_celsius=initial, success=bool(fine["success"]),
                     message=fine["message"])
        if fine["success"] and len(fine["t"]) == len(base["t"]):
            for name, scale in (("T_mean_C", 1.), ("V", 1.),
                                ("eps_ice_max", P.porous.eps_cl_c)):
                err = float(np.max(np.abs(fine[name]-base[name])))
                entry[name+"_max_abs_difference"] = err
                entry[name+"_difference_over_scale"] = err/scale
                if name == "eps_ice_max":
                    peak = max(float(np.max(np.abs(base[name]))), 1e-15)
                    entry["ice_difference_relative_to_predicted_peak"] = err/peak
            entry["note"] = "温度尺度1K，电压尺度1V，冰尺度阴极CL初始孔隙率；同时保存绝对差。"
            entry["within_one_percent"] = all(entry[name+"_difference_over_scale"] < .01
                                               for name in ("T_mean_C", "V", "eps_ice_max"))
        rows.append(entry)
        print(f"收敛检查 {initial}℃: {entry}", flush=True)
    dump_json(output_dir / "convergence.json", rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fit", action="store_true", help="重新标定两个有效参数")
    group.add_argument("--no-fit", action="store_true", help="使用params中的未标定初猜")
    parser.add_argument("--verify", action="store_true", help="两工况网格/时间加密检查")
    parser.add_argument("--max-nfev", type=int, default=24)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    experiments = read_experiments()
    dump_json(args.output / "input_audit.json", {k:v["audit"] for k,v in experiments.items()})
    saved = args.output / "calibration.json"
    if args.no_fit:
        calibration = dict(j0_ref=P.cold_start.j0_ref, k_freeze=P.cold_start.k_freeze,
                           note="未标定，仅题给/假设优化初猜，不作为拟合结果")
    elif saved.exists() and not args.fit:
        calibration = json.loads(saved.read_text(encoding="utf-8"))
        if calibration["source_sha256"] != experiments[-20]["audit"]["sha256"]:
            raise ValueError("附件2已改变，请使用--fit重新标定")
        if calibration.get("model_sha256") != model_fingerprint():
            raise ValueError("模型或params.py已改变，请使用--fit重新标定")
    else:
        calibration = calibrate(experiments[-20], args.output, args.max_nfev)
    results = {}
    for initial, data in experiments.items():
        print(f"计算 {initial}℃，F列直接输入A/m²...", flush=True)
        results[initial] = solve(data, calibration["j0_ref"], calibration["k_freeze"])
        print(results[initial]["message"], flush=True)
    metadata = dict(calibration=calibration, current_input="附件2 F列，A/m²，不重复换算",
                    temperature_domain="aBP + 五层MEA + cBP，总长0.0043267m，厚度加权空间平均",
                    ice_definition="epsilon_ice=mi/rho_ice，控制体总体积基准",
                    software=dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__),
                    numerical_settings=dict(grid=P.cold_start.grid, method="BDF",
                                            rtol=P.cold_start.rtol, atol=P.cold_start.atol,
                                            max_step_s=P.cold_start.max_step),
                    model_sha256=model_fingerprint())
    if args.verify:
        metadata["convergence"] = verify_convergence(experiments, results, calibration, args.output)
    elif not args.no_fit and (args.output / "summary.json").exists():
        # 同一方程、输入和参数的复现可保留已经完成的加密检查。
        previous = json.loads((args.output / "summary.json").read_text(encoding="utf-8"))
        old_meta = previous.get("metadata", {})
        old_fit = old_meta.get("calibration", {})
        if all(old_fit.get(k) == calibration.get(k)
               for k in ("j0_ref", "k_freeze", "source_sha256", "model_sha256")):
            if "convergence" in old_meta:
                metadata["convergence"] = old_meta["convergence"]
    for record in metadata.get("convergence", []):
        initial = int(record["initial_celsius"])
        if "eps_ice_max_max_abs_difference" in record:
            peak = max(float(np.max(np.abs(results[initial]["eps_ice_max"]))), 1e-15)
            record["ice_difference_relative_to_predicted_peak"] = record["eps_ice_max_max_abs_difference"]/peak
    if "convergence" in metadata:
        dump_json(args.output / "convergence.json", metadata["convergence"])
    from report_outputs import write_outputs
    write_outputs(results, experiments, args.output, metadata)
    print(f"输出完成：{args.output}", flush=True)


if __name__ == "__main__":
    main()
