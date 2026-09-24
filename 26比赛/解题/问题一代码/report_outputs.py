"""第一问第一小问的可追溯结果输出。

时间曲线只覆盖有效积分时段；温度取模型提供的厚度加权空间平均。
式(9)的冰体积分数为 mi/rho_ice，以整个控制体积为分母，不能除以孔隙率。
本模块负责报告与绘图，不执行参数校准，也不据数值积分成功宣布冷启动成功。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# data_io 负责加载随项目安装的依赖，便于使用同一个 Python 环境复现。
from data_io import error_metrics, write_csv
import numpy as np
import matplotlib
from params import P

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


RHO_ICE = P.thermal.ice.rho  # kg/m³，从统一params读取；附件1原值为920。
_TIME_FIELDS = (
    "j", "T_mean_C", "T_mea_C", "V", "eps_ice_max", "T_C", "mw", "mi",
    "mv", "ml", "eps_g", "lambda_mem",
)


def _jsonable(value: Any) -> Any:
    """无 NaN/Infinity 的标准 JSON；不把未知自定义对象序列化成可执行内容。"""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _configure_plotting() -> bool:
    """优先使用 Windows 微软雅黑；无中文字体时改用英文，避免缺字图。"""
    names = {f.name for f in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC"):
        if candidate in names:
            plt.rcParams["font.family"] = candidate
            chinese = True
            break
    else:
        plt.rcParams["font.family"] = "DejaVu Sans"
        chinese = False
    plt.rcParams.update({
        "axes.unicode_minus": False, "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.22, "lines.linewidth": 1.7,
        "savefig.dpi": 220, "pdf.fonttype": 42,
    })
    return chinese


def _clean_result(result: dict) -> tuple[dict, list[str]]:
    """删除非有限输出起点之后的无效尾部，并留下显式审计说明。"""
    clean = dict(result)
    t = np.asarray(result["t"], dtype=float)
    if t.ndim != 1 or not t.size:
        raise ValueError("结果 t 必须为非空一维数组")
    if not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
        raise ValueError("结果时间必须有限且严格递增")
    n = t.size
    valid = np.ones(n, dtype=bool)
    for key in _TIME_FIELDS:
        if key not in result:
            continue
        a = np.asarray(result[key], dtype=float)
        if a.ndim == 0 or a.shape[0] != n:
            raise ValueError(f"{key} 的时间维长度 {a.shape} 与 t 的 {n} 不一致")
        clean[key] = a
        if key in ("j", "T_mean_C", "V", "T_C", "mi"):
            valid &= np.all(np.isfinite(a.reshape(n, -1)), axis=1)
    if any(key not in clean for key in ("j", "T_mean_C", "V", "T_C", "mi")):
        raise ValueError("输出缺少 j/T_mean_C/V/T_C/mi 中的必需字段")
    invalid = np.flatnonzero(~valid)
    end = int(invalid[0]) if invalid.size else n
    if end == 0:
        raise ValueError("首时刻输出已非有限，无法报告有效模型轨迹")
    notes = []
    if end != n:
        notes.append(f"删除从 t={t[end]:.9g} s 起的 {n-end} 个非有限或后续输出点。")
    clean["t"] = t[:end]
    for key in _TIME_FIELDS:
        if key in clean:
            clean[key] = clean[key][:end]
    # 从空间冰量独立计算每个时刻的空间最大值，避免误用历史最大值或孔隙饱和度。
    ice = clean["mi"] / RHO_ICE
    if ice.ndim != 2:
        raise ValueError("mi 必须为 (时间, MEA单元) 的二维数组")
    correct_max = np.max(ice, axis=1)
    if "eps_ice_max" in clean and not np.allclose(
            clean["eps_ice_max"], correct_max, rtol=1e-7, atol=1e-12):
        notes.append("传入 eps_ice_max 与 mi/rho_ice 的空间最大值不一致；报告采用后者。")
    clean["eps_ice_max"] = correct_max
    clean["eps_ice"] = ice
    return clean, notes


def _interp(t, values, query):
    """仅在数据实际覆盖的闭区间内插值；区间外返回 NaN，禁止端点外推。"""
    t, values, query = np.asarray(t), np.asarray(values), np.asarray(query, dtype=float)
    out = np.full(query.shape, np.nan)
    tol = 1e-9 * max(1.0, abs(float(t[-1])))
    use = (query >= t[0] - tol) & (query <= t[-1] + tol)
    out[use] = np.interp(np.clip(query[use], t[0], t[-1]), t, values)
    return out


def _relative_percent(predicted, observed):
    predicted, observed = np.asarray(predicted), np.asarray(observed)
    return np.divide(100.0 * np.abs(predicted - observed), np.abs(observed),
                     out=np.full(predicted.shape, np.nan),
                     where=np.abs(observed) > 1e-12)


def _csv_columns(columns):
    """缺失值写成空单元格，而非假定零值。"""
    return {key: [None if isinstance(v, (float, np.floating)) and not np.isfinite(v)
                  else v for v in values] for key, values in columns.items()}


def _aligned_columns(result, experiment, query):
    t = result["t"]
    tm = _interp(t, result["T_mean_C"], query)
    vm = _interp(t, result["V"], query)
    te = _interp(experiment["t"], experiment["temperature_exp"], query)
    ve = _interp(experiment["t"], experiment["voltage_exp"], query)
    cols = {
        "time_s": query,
        "input_current_density_A_m2": _interp(experiment["t"], experiment["current"], query),
        "experiment_voltage_V": ve,
        "model_voltage_V": vm,
        "voltage_relative_error_percent": _relative_percent(vm, ve),
        "experiment_temperature_C": te,
        "model_mean_temperature_full_domain_C": tm,
        "temperature_relative_error_percent_C_basis": _relative_percent(tm, te),
        "model_max_ice_volume_fraction": _interp(t, result["eps_ice_max"], query),
        "voltage_absolute_error_V": np.abs(vm - ve),
        "temperature_absolute_error_C": np.abs(tm - te),
    }
    if "T_mea_C" in result:
        cols["model_mean_temperature_MEA_C"] = _interp(t, result["T_mea_C"], query)
    return cols


def _metrics_on_observation_times(result, experiment):
    """在有效区间内的实际实验采样点评价，避免数值输出加密改变误差权重。"""
    et = np.asarray(experiment["t"], dtype=float)
    tol = 1e-9 * max(1.0, float(result["t"][-1]))
    use = (et >= result["t"][0]-tol) & (et <= result["t"][-1]+tol)
    et = et[use]
    if not et.size:
        return {"count": 0, "note": "有效计算时段内没有实验采样点"}
    metrics = {"count": len(et), "time_range_s": [et[0], et[-1]]}
    for name, modelkey, expkey in (
            ("voltage_V", "V", "voltage_exp"),
            ("temperature_C", "T_mean_C", "temperature_exp")):
        pred = _interp(result["t"], result[modelkey], et)
        exp = np.asarray(experiment[expkey])[use]
        finite = np.isfinite(pred) & np.isfinite(exp)
        if not np.any(finite):
            metrics[name] = {"count": 0}
            continue
        # data_io 的相对误差按原始单位计算；温度绝不改用 K 分母。
        if np.any(np.abs(exp[finite]) > 1e-12):
            item = error_metrics(pred[finite], exp[finite])
        else:
            d = pred[finite] - exp[finite]
            item = {"mae": np.mean(np.abs(d)), "rmse": np.sqrt(np.mean(d*d)),
                    "max_abs": np.max(np.abs(d)), "mean_relative_percent": None,
                    "max_relative_percent": None}
        item["count"] = int(finite.sum())
        item["near_zero_experiment_count"] = int(np.sum(np.abs(exp[finite]) <= 1e-12))
        metrics[name] = item
    return metrics


def _space_edges(result, coordinate_key, edge_key, notes):
    centers = np.asarray(result[coordinate_key], dtype=float)
    if centers.ndim != 1 or not centers.size or np.any(np.diff(centers) <= 0):
        raise ValueError(f"{coordinate_key} 必须严格递增")
    if edge_key in result:
        edges = np.asarray(result[edge_key], dtype=float)
        if (len(edges) != len(centers)+1 or np.any(np.diff(edges) <= 0)
                or np.any(centers <= edges[:-1]) or np.any(centers >= edges[1:])):
            raise ValueError(f"{edge_key} 与控制体中心不一致")
        return edges
    # 只有中心时无法精确恢复材料层间界面，因此将这一限制记录到摘要中。
    if len(centers) == 1:
        raise ValueError(f"单一空间单元必须提供 {edge_key}")
    edges = np.r_[centers[0]-(centers[1]-centers[0])/2,
                  (centers[:-1]+centers[1:])/2,
                  centers[-1]+(centers[-1]-centers[-2])/2]
    notes.append(f"缺少 {edge_key}，时空图边界由单元中心中点推导；材料界面位置近似。")
    return edges


def _save_figure(fig, folder, stem):
    paths = []
    for suffix in ("png", "pdf"):
        path = folder / f"{stem}.{suffix}"
        fig.savefig(path, bbox_inches="tight")
        paths.append(path.name)
    plt.close(fig)
    return paths


def _plot_main(results, experiments, output_dir, chinese):
    cases = sorted(results, reverse=True)
    fig, axes = plt.subplots(3, len(cases), figsize=(6.1*len(cases), 10.2),
                             squeeze=False, constrained_layout=True)
    blue, orange = "#176B9A", "#D77828"
    labels = (("平均温度 / ℃", "Mean temperature / °C"),
              ("电压 / V", "Voltage / V"),
              ("最大冰体积分数", "Maximum ice volume fraction"))
    for column, initial in enumerate(cases):
        result, exp = results[initial], experiments[initial]
        t = result["t"]
        et = np.asarray(exp["t"])
        use = (et >= t[0]-1e-9) & (et <= t[-1]+1e-9)
        for row, key, expkey in ((0, "T_mean_C", "temperature_exp"),
                                 (1, "V", "voltage_exp"),
                                 (2, "eps_ice_max", None)):
            ax = axes[row, column]
            ax.plot(t, result[key], color=blue, label="模型" if chinese else "Model")
            if expkey:
                ax.plot(et[use], np.asarray(exp[expkey])[use], linestyle="none",
                        marker="o", markersize=3, markevery= 1,
                        color=orange, alpha=.8, label="实验" if chinese else "Experiment")
            else:
                ax.text(.02, .95, "冰量为模型预测；附件无冰量观测" if chinese
                        else "Model prediction; no measured ice data",
                        transform=ax.transAxes, va="top", fontsize=8.8)
                ax.set_ylim(bottom=0)
            ax.set_ylabel(labels[row][0 if chinese else 1])
            ax.set_xlabel("时间 / s" if chinese else "Time / s")
            if len(t) > 1:
                ax.set_xlim(t[0], t[-1])
            if row < 2:
                ax.legend(loc="best", fontsize=9)
        axes[0, column].set_title(f"初始温度 {initial:g} ℃" if chinese
                                  else f"Initial temperature {initial:g} °C")
    fig.suptitle("一维单电池瞬态自冷启动模型：有效计算时段" if chinese
                 else "1D transient cold-start model: valid simulation interval", fontsize=15)
    return _save_figure(fig, output_dir, "temperature_voltage_ice")


def _plot_fields(result, output_dir, stem, initial, chinese, notes):
    if len(result["t"]) < 2:
        notes.append("有效输出仅一个时刻，未生成空间—时间图。")
        return []
    fig, axes = plt.subplots(2, 1, figsize=(10.2, 8.0), constrained_layout=True)
    for ax, valuekey, xkey, edgekey, cmap, title, colorlabel in (
        (axes[0], "T_C", "x_um", "x_edges_um", "inferno", "完整热域温度" if chinese
         else "Temperature in full thermal domain", "温度 / ℃" if chinese else "Temperature / °C"),
        (axes[1], "eps_ice", "x_mea_um", "x_mea_edges_um", "Blues", "MEA冰体积分数（模型预测）" if chinese
         else "Ice volume fraction in MEA (model prediction)", "冰体积分数" if chinese else "Ice volume fraction"),
    ):
        edges = _space_edges(result, xkey, edgekey, notes)
        field = np.asarray(result[valuekey])
        if field.shape != (len(result["t"]), len(edges)-1):
            raise ValueError(f"{valuekey} 形状与时间/空间网格不一致")
        # 时间坐标取真实采样时刻；上下两条边不延伸到计算时段之外。
        # C 值在相邻时间中点分界的条带中绘制，空间严格用有限体积边界。
        t = result["t"]
        t_edges = np.r_[t[0], (t[:-1]+t[1:])/2, t[-1]]
        mesh = ax.pcolormesh(edges, t_edges, field, shading="flat", cmap=cmap,
                             rasterized=True, vmin=0 if valuekey == "eps_ice" else None)
        ax.grid(False)
        ax.set_title(f"{initial:g} ℃ — {title}")
        ax.set_xlabel("厚度方向位置 / μm" if chinese else "Through-plane position / μm")
        ax.set_ylabel("时间 / s" if chinese else "Time / s")
        ax.set_ylim(t[0], t[-1])
        fig.colorbar(mesh, ax=ax, label=colorlabel)
    return _save_figure(fig, output_dir, f"{stem}_space_time")


def _plot_errors(results, experiments, output_dir, chinese):
    cases = sorted(results, reverse=True)
    fig, axes = plt.subplots(2, len(cases), figsize=(6.1*len(cases), 6.5),
                             squeeze=False, constrained_layout=True)
    for column, initial in enumerate(cases):
        r, e = results[initial], experiments[initial]
        t = np.asarray(e["t"])
        t = t[(t >= r["t"][0]-1e-9) & (t <= r["t"][-1]+1e-9)]
        cols = _aligned_columns(r, e, t)
        for row, key, label in (
            (0, "temperature_absolute_error_C", "温度绝对误差 / ℃" if chinese else "Temperature absolute error / °C"),
            (1, "voltage_absolute_error_V", "电压绝对误差 / V" if chinese else "Voltage absolute error / V"),
        ):
            ax = axes[row, column]
            ax.plot(t, cols[key], color="#7252A3")
            ax.set(xlabel="时间 / s" if chinese else "Time / s", ylabel=label)
            ax.set_ylim(bottom=0)
            if len(t) > 1:
                ax.set_xlim(t[0], t[-1])
        axes[0, column].set_title(f"{initial:g} ℃")
    fig.suptitle("有效时段内的模型与实验绝对误差" if chinese
                 else "Absolute errors on observed times in valid simulation interval")
    return _save_figure(fig, output_dir, "errors")


def _plot_convergence(metadata, output_dir, chinese):
    """兼容驱动程序的 convergence 列表及 convergence.records 字典。"""
    convergence = metadata.get("convergence", {})
    records = convergence.get("records", []) if isinstance(convergence, dict) else convergence
    if not records or not all(isinstance(row, dict) for row in records):
        return []
    records = [dict(row) for row in records]
    for row in records:
        for dest, source in (("temperature_max_abs_C", "T_mean_C_max_abs_difference"),
                             ("voltage_max_abs_V", "V_max_abs_difference"),
                             ("ice_max_abs", "eps_ice_max_max_abs_difference")):
            if dest not in row and source in row:
                row[dest] = row[source]
        row.setdefault("case", row.get("initial_celsius", ""))
        row.setdefault("label", "加密比较" if chinese else "Refined")
    fields = ("temperature_max_abs_C", "voltage_max_abs_V", "ice_max_abs")
    available = [field for field in fields if any(field in row for row in records)]
    if not available:
        return []
    labels = [f'{row.get("case", "")} {row.get("label", str(i+1))}'
              for i, row in enumerate(records)]
    fig, axes = plt.subplots(1, len(available), figsize=(5*len(available), 4.2),
                             squeeze=False, constrained_layout=True)
    titles = {"temperature_max_abs_C": "最大温度差 / ℃" if chinese else "Max temperature difference / °C",
              "voltage_max_abs_V": "最大电压差 / V" if chinese else "Max voltage difference / V",
              "ice_max_abs": "最大冰体积分数差" if chinese else "Max ice fraction difference"}
    for ax, field in zip(axes[0], available):
        values = [row.get(field, np.nan) for row in records]
        ax.bar(np.arange(len(values)), values, color="#176B9A")
        ax.set_xticks(np.arange(len(values)), labels, rotation=25, ha="right")
        ax.set_ylabel(titles[field])
        ax.set_ylim(bottom=0)
    fig.suptitle("网格/时间收敛比较（同一物理参数）" if chinese
                 else "Grid/time convergence comparison (same physical parameters)")
    return _save_figure(fig, output_dir, "convergence")


def write_outputs(results: dict, experiments: dict, output_dir: Path,
                  metadata: dict | None = None) -> dict:
    """输出 CSV、NPZ、PNG/PDF、summary.json、results.md，并返回摘要字典。

    必需字段见驱动程序；精确时空图推荐提供 x_edges_um、x_mea_edges_um。
    metadata 原样保存参数/校准/收敛来源；diagnostics 原样保存求解器核查值。
    可选 metadata['convergence']['records'] 的字段见 _plot_convergence。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = dict(metadata or {})
    chinese = _configure_plotting()
    clean_results, cases = {}, {}
    artifacts = []
    for initial in sorted(results, reverse=True):
        if initial not in experiments:
            raise KeyError(f"缺少 {initial} ℃ 的实验输入")
        r, notes = _clean_result(results[initial])
        e = experiments[initial]
        clean_results[initial] = r
        stem = f"minus{abs(float(initial)):g}C" if float(initial) < 0 else f"plus{float(initial):g}C"
        columns = _aligned_columns(r, e, r["t"])
        columns["model_input_current_density_A_m2"] = r["j"]
        for key, value in r.get("diagnostics", {}).items():
            if isinstance(value, (list, tuple, np.ndarray)):
                a = np.asarray(value)
                if (a.ndim == 1 and len(a) == len(results[initial]["t"])
                        and np.issubdtype(a.dtype, np.number)):
                    columns[f"diagnostic_{key}"] = a[:len(r["t"])]
        write_csv(output_dir / f"{stem}_timeseries.csv", _csv_columns(columns))
        artifacts.append(f"{stem}_timeseries.csv")
        table_t = np.arange(0.0, 35.0+0.01, 5.0)
        table = _aligned_columns(r, e, table_t)
        reasons = []
        for time, val in zip(table_t, table["model_voltage_V"]):
            if np.isfinite(val):
                reason = ""
            else:
                reason = (f"超出有效计算区间 [{r['t'][0]:.9g}, {r['t'][-1]:.9g}] s；"
                          f"{r.get('message', '')}")
            if time < e["t"][0]-1e-9 or time > e["t"][-1]+1e-9:
                reason += "；超出实验数据区间"
            reasons.append(reason)
        table["missing_value_reason"] = reasons
        write_csv(output_dir / f"{stem}_table_0_to_35s.csv", _csv_columns(table))
        artifacts.append(f"{stem}_table_0_to_35s.csv")
        # 只保存数值数组，np.load(..., allow_pickle=False) 可直接读取。
        arrays = {key: value for key, value in r.items()
                  if isinstance(value, np.ndarray) and np.issubdtype(value.dtype, np.number)}
        for key in ("x_um", "x_mea_um", "x_edges_um", "x_mea_edges_um"):
            if key in r:
                arrays[key] = np.asarray(r[key], dtype=float)
        np.savez_compressed(output_dir / f"{stem}_fields.npz", **arrays)
        artifacts.append(f"{stem}_fields.npz")
        artifacts.extend(_plot_fields(r, output_dir, stem, initial, chinese, notes))
        cases[str(initial)] = {
            "initial_temperature_C": initial,
            "valid_output_count": len(r["t"]),
            "valid_time_range_s": [r["t"][0], r["t"][-1]],
            "requested_experiment_end_s": float(e["t"][-1]),
            "covers_experiment_interval": bool(r["t"][0] <= e["t"][0]+1e-8
                                               and r["t"][-1] >= e["t"][-1]-1e-8),
            "solver_success": bool(r.get("success", False)),
            "solver_status": r.get("status"),
            "solver_message": r.get("message", ""),
            "event_time_s": r.get("event_time"),
            "final_model_temperature_C": r["T_mean_C"][-1],
            "final_model_voltage_V": r["V"][-1],
            "final_max_ice_volume_fraction": r["eps_ice_max"][-1],
            "peak_max_ice_volume_fraction_over_valid_interval": np.max(r["eps_ice_max"]),
            "metrics_at_experimental_sampling_times": _metrics_on_observation_times(r, e),
            "diagnostics": r.get("diagnostics", {}),
            "input_audit": e.get("audit", {}),
            "report_notes": notes,
        }
    artifacts.extend(_plot_main(clean_results, experiments, output_dir, chinese))
    artifacts.extend(_plot_errors(clean_results, experiments, output_dir, chinese))
    convergence_files = _plot_convergence(metadata, output_dir, chinese)
    artifacts.extend(convergence_files)
    summary = {
        "scope": "问题一第一小问：一维单电池瞬态自冷启动模型的数值轨迹",
        "definitions": {
            "mean_temperature": "由局部温度按控制体厚度加权，在完整计算热域求空间平均",
            "ice_volume_fraction": f"mi/({RHO_ICE:g} kg/m³)，分母为整个控制体积，非孔隙体积",
            "max_ice_volume_fraction": "每个时刻在多孔层取空间最大值，不是历史最大值",
            "temperature_percent_error": "按摄氏温度原值作分母；接近0℃时另看绝对误差",
            "time_table": "在0、5、10、15、20、25、30、35 s仅于有效区间内线性插值",
            "solver_success": "仅代表数值积分状态，不能解释为物理冷启动成功",
        },
        "metadata": metadata, "cases": cases,
        "artifacts": artifacts + ["summary.json", "results.md"],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(_jsonable(summary), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    lines = [
        "# 第一问第一小问计算结果", "",
        "电流密度直接使用附件2的 −20 ℃、−25 ℃工作表 F 列（A/m²），按原始时间分段线性插值。"
        "实验温度和电压用于参数校准与结果比较，不作为模型温度轨迹或反应热源输入。", "",
        "平均温度是局部温度在完整计算热域内按控制体厚度加权的空间平均；"
        "同时在时序表中保留 MEA 域平均温度（若求解器提供）。"
        f"冰体积分数按式(9)取 mi/{RHO_ICE:g}，并在每个时刻取空间最大值，不能与孔隙冰饱和度混用。", "",
        "| 初始温度 | 有效末时刻/s | 末时刻模型均温/℃ | 末时刻模型电压/V | 末时刻最大冰体积分数 | 实验区间完整覆盖 |",
        "|---:|---:|---:|---:|---:|:---:|",
    ]
    for initial, case in cases.items():
        lines.append(f"| {float(initial):g} ℃ | {case['valid_time_range_s'][1]:.6g} | "
                     f"{case['final_model_temperature_C']:.6g} | {case['final_model_voltage_V']:.6g} | "
                     f"{case['final_max_ice_volume_fraction']:.6g} | "
                     f"{'是' if case['covers_experiment_interval'] else '否'} |")
    lines.extend(["", "## 实验比较与计算状态", "",
                  "下列误差在有效计算区间内的实验采样点评价；温度单位为℃。"
                  "百分误差使用题目摄氏温度分母，没有改成K以减小误差。"])
    for initial, case in cases.items():
        metrics = case["metrics_at_experimental_sampling_times"]
        lines.extend(["", f"- **{float(initial):g} ℃**：{case['solver_message'] or case['solver_status']}；"
                      f"有效实验比较点 {metrics['count']} 个。"])
        if "temperature_C" in metrics and "mae" in metrics["temperature_C"]:
            mt, mv = metrics["temperature_C"], metrics["voltage_V"]
            lines.append(f"  温度 MAE={mt['mae']:.6g} ℃、RMSE={mt['rmse']:.6g} ℃；"
                         f"电压 MAE={mv['mae']:.6g} V、RMSE={mv['rmse']:.6g} V。")
        if case["event_time_s"] is not None:
            lines.append(f"  事件时刻：{case['event_time_s']} s，具体原因与守恒检查见 summary.json。")
        lines.extend(f"  {note}" for note in case["report_notes"])
    lines.extend(["", "## 解释范围", "",
        "本次是第一小问的模型计算输出。参数采用值、参数来源和求解设置保存在 summary.json 的 metadata 中，"
        "守恒、可行性与求解器诊断保存在各工况 diagnostics 中。"
        "题目未给统一5%误差限，预测能力按实际误差评价。冻结速率的来源及可辨识性须与拟合误差一起解释。", "",
        "附件2没有冰量观测，冰量与空间冰分布均是模型预测。两工况的实验温度全程低于0 ℃，"
        "不能由本段结果宣布已验证成功启动或融化阶段。solver_success 仅表示数值求解状态。", "",
        ("已生成网格/时间收敛对比图；具体设置与差异见 metadata.convergence。" if convergence_files
         else "本次输出未包含可绘制的网格/时间收敛序列；如已由驱动程序检查，具体记录见 metadata。"
              "缺少该检查时，不能仅据求解器正常返回宣布数值收敛。"), "",
        "## 文件说明", "",
        "- temperature_voltage_ice.png/pdf：两工况3行×2列温度、电压、最大冰体积分数主图。",
        "- minus20C/minus25C_timeseries.csv：所有有效输出时刻的模型值、实验插值与误差。",
        "- minus20C/minus25C_table_0_to_35s.csv：题目指定时刻表；超出有效时段留空并写明原因。",
        "- minus20C/minus25C_space_time.png/pdf：温度和冰量时空图；采用有限体积空间边界。",
        "- minus20C/minus25C_fields.npz：局部温度、总水/蒸气/液水/冰、有效孔隙率、膜含水量等数值数组及坐标。",
        "- errors.png/pdf：有效时段内的温度和电压绝对误差。",
        "- summary.json：精确数值、运行状态、输入审计、物理/数值诊断和运行元数据。", "",
        "所有图中的模型线仅显示有效积分区间。有效区间内输出时刻之间的表格值为线性插值，"
        "不把提前终止后的空白填成预测，不修改附件或建模MD。", "",
    ])
    calibration = metadata.get("calibration", {})
    if isinstance(calibration, dict) and calibration:
        parameter_lines = ["", "## 本次参数记录", ""]
        for key, label in (("j0_ref", "参考交换电流密度 j0_ref / (A/m²)"),
                           ("k_freeze", "一阶冻结速率 k_freeze / s⁻¹"),
                           ("objective", "归一化拟合目标值"), ("note", "校准说明")):
            if key in calibration:
                parameter_lines.append(f"- {label}：{calibration[key]}")
        parameter_lines.append("多初猜、冻结速率剖面及可辨识性信息（如有）保留在 summary.json 中。")
        profile = calibration.get("fixed_j0_kf_profile", [])
        if len(profile) >= 2:
            scores = [float(item["objective"]) for item in profile]
            spread = (max(scores)-min(scores))/max(min(scores), 1e-15)
            parameter_lines.append(f"固定j0后，本次冻结速率扰动对应目标函数相对极差约 {spread*100:.4g}%。")
            if spread < .02:
                parameter_lines.append("该误差变化很小，说明冻结速率在本次实验和本模型下约束较弱。"
                                       "输出数值是代表性有效参数，不应作为唯一准确的物性常数；冰量预测对该参数的依赖仍须保留。")
        lines.extend(parameter_lines)
    (output_dir / "results.md").write_text("\n".join(lines), encoding="utf-8")
    return _jsonable(summary)
