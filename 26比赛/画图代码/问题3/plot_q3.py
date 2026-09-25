"""Q3 publication plots; reads result CSVs, never reruns or changes the model.

Run with the same Python environment as aux_model.py, once CSVs are complete.
P/C are the two formal strategies. R is an explicitly additional post-loading
robustness design, not a third strategy in the original problem.
"""
from pathlib import Path
import argparse
import csv
import os
import sys

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "解题" / "问题3_求解结果"
sys.path.insert(0, str(DEFAULT_ROOT / "code"))
# aux_model inserts the frozen Q2 numerical dependency directory into sys.path.
from aux_model import np, HISTORY

os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_ROOT / "figures" / ".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import MaxNLocator, ScalarFormatter

COLORS = {"P": "#316D9C", "C": "#C77835", "R": "#398476"}
CELL_COLORS = ["#316D9C", "#C77835", "#398476"]
NAMES = {"P": "P 纯预热", "C": "C 协同加热", "R": "R 稳健预热（附加）"}


def setup_style():
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "SimSun"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    font = next((x for x in candidates if x in available), None)
    if font is None:
        raise RuntimeError("A Chinese font is required: Microsoft YaHei / SimHei / Noto Sans CJK SC")
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [font, "DejaVu Sans"],
        "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 11,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "axes.unicode_minus": False, "axes.spines.top": False,
        "axes.spines.right": False, "axes.edgecolor": "#555B61",
        "axes.linewidth": .7, "axes.grid": True, "grid.alpha": .22,
        "grid.linewidth": .55, "lines.linewidth": 1.8,
        "savefig.facecolor": "white", "figure.facecolor": "white",
        "svg.fonttype": "path", "mathtext.fontset": "dejavusans",
    })


def read_summary(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for row in rows:
        key = row.get("strategy", row.get("kind", row.get("code", ""))).strip()
        if key not in NAMES:
            continue
        if key in out:
            raise ValueError(f"Duplicate strategy {key} in {path}")
        parsed = {}
        for k, value in row.items():
            try:
                parsed[k] = float(value)
            except (TypeError, ValueError):
                parsed[k] = value
        out[key] = parsed
    if set(out) != {"P", "C", "R"}:
        raise ValueError("summary_results.csv must contain strategies P, C and R")
    for key, row in out.items():
        for name in ["th_s", "startup_s", "E_aux_J"] + [f"q{k}_W_cm2" for k in range(1, 6)] + [f"E{k}_J" for k in range(1, 6)]:
            if name not in row or not np.isfinite(row[name]):
                raise ValueError(f"Missing/non-finite {key}: {name}")
    return out


def read_trace(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = set(HISTORY) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing {sorted(missing)}")
        rows = [{k: float(row[k]) for k in HISTORY} for row in reader]
    if len(rows) < 2:
        raise ValueError(f"{path.name}: fewer than two samples")
    out = {k: np.array([r[k] for r in rows]) for k in HISTORY}
    if not all(np.all(np.isfinite(v)) for v in out.values()):
        raise ValueError(f"{path.name}: non-finite data")
    if np.any(np.diff(out["time_s"]) < 0):
        raise ValueError(f"{path.name}: non-monotonic time")
    return out


def cells(trace, field):
    return np.column_stack([trace[f"cell{k}_{field}"] for k in range(1, 6)])


def temperatures(trace):
    return np.column_stack([trace[f"T{k}_C"] for k in range(1, 6)])


def num(value, digits=3):
    if abs(value) < 1e-12:
        return "0"
    if abs(value) < 1e-3:
        return f"{value:.2e}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def decorate(ax, ylabel=None, xlabel="时间 / s"):
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(MaxNLocator(6))
    ax.yaxis.set_major_locator(MaxNLocator(6))
    ax.tick_params(direction="out", length=3)
    ax.set_axisbelow(True)


def label_panel(ax, label):
    ax.set_title(label, loc="left", pad=8, fontweight="medium")


def note(fig, text):
    fig.text(.08, .015, text, va="bottom", ha="left", fontsize=8.5, color="#545B62")


def save(fig, output, stem):
    for suffix in ("png", "svg"):
        fig.savefig(output / f"{stem}.{suffix}", dpi=230, bbox_inches="tight", pad_inches=.13)
    plt.close(fig)
    print(f"Saved {stem}.png/.svg")


def pair_temperatures(ax, trace):
    t = trace["time_s"]
    for k, color, label in zip((1, 2, 3), CELL_COLORS, ("单电池 1 / 5", "单电池 2 / 4", "单电池 3")):
        ax.plot(t, trace[f"T{k}_C"], color=color, label=label)
    # Do not silently conceal an asymmetric result.
    for k, mirror, color in ((5, 1, CELL_COLORS[0]), (4, 2, CELL_COLORS[1])):
        if np.max(np.abs(trace[f"T{k}_C"] - trace[f"T{mirror}_C"])) > 1e-5:
            ax.plot(t, trace[f"T{k}_C"], color=color, ls=":", label=f"单电池 {k}（非对称）")
    ax.plot(t, trace["TEL_C"], color="#737A80", ls="--", label="左 / 右端板")
    if np.max(np.abs(trace["TEL_C"] - trace["TER_C"])) > 1e-5:
        ax.plot(t, trace["TER_C"], color="#737A80", ls=":", label="右端板（非对称）")


def figure_temperature(traces, summary, output):
    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.0), sharey=True)
    for ax, key in zip(axes, ("P", "C")):
        trace = traces[key]
        pair_temperatures(ax, trace)
        ax.axhline(0, color="#30373D", lw=.85)
        th = summary[key]["th_s"]
        if th < trace["time_s"][-1] - .1:
            ax.axvline(th, color="#858C92", ls=":", lw=1)
            ax.text(th, .98, "关热", transform=ax.get_xaxis_transform(), va="top", ha="right", fontsize=8)
        label_panel(ax, f"({'a' if key == 'P' else 'b'}) {NAMES[key]}")
        decorate(ax, "温度 / ℃" if key == "P" else None)
        ax.set_xlim(0, trace["time_s"][-1])
        ax.text(.03, .97, f"统计至 {trace['time_s'][-1]:.2f} s", transform=ax.transAxes, va="top", fontsize=9)
    axes[1].legend(loc="lower right", frameon=False)
    note(fig, "P：预热至关热 / 加载开始；C：从通电至首次启动成功。端板温度不计入全部单电池超过 0 ℃ 的判据。")
    fig.subplots_adjust(left=.08, right=.98, bottom=.2, top=.90, wspace=.15)
    save(fig, output, "01_主策略温度历程")


def figure_heaters(summary, output):
    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.0))
    x = np.arange(1, 6)
    for offset, key in zip((-.24, 0, .24), ("P", "C", "R")):
        style = dict(color=COLORS[key], alpha=.95 if key != "R" else .75,
                     edgecolor="white", linewidth=.6)
        if key == "R":
            style["hatch"] = "///"
        q = [summary[key][f"q{k}_W_cm2"] for k in x]
        e = [summary[key][f"E{k}_J"] for k in x]
        axes[0].bar(x + offset, q, width=.23, label=NAMES[key], **style)
        axes[1].bar(x + offset, e, width=.23, label=NAMES[key], **style)
    for ax, ylabel, title in zip(axes, ("加热功率密度 / (W·cm$^{-2}$)", "单片辅助加热能耗 / J"),
                                ("(a) 各片恒定加热功率", "(b) 各片累计辅助能耗")):
        decorate(ax, ylabel, "单电池编号")
        ax.set_xticks(x)
        ax.set_xlim(.5, 5.5)
        ax.grid(axis="x", visible=False)
        label_panel(ax, title)
    axes[0].axhline(1, color="#525A62", ls=":", lw=1)
    axes[0].set_ylim(0, 1.13)
    axes[0].legend(frameon=False, ncol=1, loc="upper center")
    energies = "；".join(f"{key}: {summary[key]['E_aux_J']:.1f} J" for key in ("P", "C", "R"))
    note(fig, f"单片面积 25 cm²；能耗 E_k = 25 q_k t_h。R 为增加加载后不回落要求的附加设计。\n总辅助能耗：{energies}。")
    fig.subplots_adjust(left=.08, right=.98, bottom=.24, top=.90, wspace=.3)
    save(fig, output, "02_分片加热功率与能耗")


def figure_safety(traces, output):
    fig, axes = plt.subplots(3, 2, figsize=(11.3, 8.1), sharex="col")
    for col, key in enumerate(("P", "C")):
        tr = traces[key]
        t = tr["time_s"]
        volt = cells(tr, "V")
        ice = cells(tr, "ice_bulk")
        sat = cells(tr, "pore_ice_saturation")
        axes[0, col].plot(t, np.min(volt, axis=1), color=COLORS[key], label="全堆最低单片电压")
        axes[0, col].axhline(.30, color="#A44848", ls="--", lw=1, label="电压约束 0.30 V")
        axes[0, col].set_ylim(bottom=min(.27, np.min(volt) - .02))
        axes[1, col].plot(t, np.max(ice[:, [0, 4]], axis=1), color=CELL_COLORS[0], label="端部单片最大")
        axes[1, col].plot(t, ice[:, 2], color=CELL_COLORS[2], ls="--", label="中心单片")
        axes[1, col].plot(t, np.max(ice, axis=1), color="#555B61", ls=":", label="全堆最大")
        axes[2, col].plot(t, np.max(sat[:, [0, 4]], axis=1), color=COLORS[key], label="端部孔隙冰饱和度")
        label_panel(axes[0, col], f"({'a' if key == 'P' else 'b'}) {NAMES[key]}")
        axes[0, col].legend(frameon=False, loc="best", fontsize=8)
        axes[1, col].legend(frameon=False, loc="best", fontsize=8)
        axes[2, col].legend(frameon=False, loc="best", fontsize=8)
        for row, ylabel in enumerate(("最低单片电压 / V", "MEA 体积平均冰体积分数", "端部孔隙冰饱和度")):
            decorate(axes[row, col], ylabel if col == 0 else None, "时间 / s" if row == 2 else "")
            axes[row, col].set_xlim(0, t[-1])
            if row > 0:
                axes[row, col].set_ylim(bottom=0)
                if np.max(ice if row == 1 else sat) < 1e-10:
                    axes[row, col].set_ylim(0, 1e-4)
                sf = ScalarFormatter(useMathText=True)
                sf.set_powerlimits((-3, 3))
                axes[row, col].yaxis.set_major_formatter(sf)
    note(fig, "统计窗口与图 01 相同，未包含 P 关热后续加载。ice_bulk 含膜内冰、以整个 MEA 体积平均；\n孔隙冰饱和度仅描述多孔层内的局部孔隙占据，二者分母不同，不可混用。体积分数启动约束为 < 0.99。")
    fig.subplots_adjust(left=.09, right=.98, bottom=.13, top=.95, hspace=.24, wspace=.2)
    save(fig, output, "03_主策略电压与结冰")


def figure_postload(traces, summary, output):
    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.15))
    for key, trace_key in (("P", "P_postload"), ("R", "R")):
        tr = traces[trace_key]
        tau = tr["time_s"] - summary[key]["th_s"]
        keep = tau >= -1e-7
        minimum = np.min(temperatures(tr), axis=1)
        voltage = np.min(cells(tr, "V"), axis=1)
        axes[0].plot(tau[keep], minimum[keep], color=COLORS[key], label=NAMES[key])
        axes[1].plot(tau[keep], voltage[keep], color=COLORS[key], label=NAMES[key])
        idx = np.flatnonzero(keep)[np.argmin(minimum[keep])]
        axes[0].plot(tau[idx], minimum[idx], "o", color=COLORS[key], ms=4)
        axes[0].annotate(f"{minimum[idx]:.2f} ℃", (tau[idx], minimum[idx]),
                         xytext=(5, -15 if key == "P" else 7), textcoords="offset points",
                         color=COLORS[key], fontsize=9)
    axes[0].axhline(0, color="#A44848", ls="--", lw=1)
    axes[1].axhline(.30, color="#A44848", ls="--", lw=1)
    for ax, title, ylabel in zip(axes, ("(a) 关热后最低单片温度", "(b) 关热后最低单片电压"),
                                 ("全堆最低单片温度 / ℃", "全堆最低单片电压 / V")):
        label_panel(ax, title)
        decorate(ax, ylabel, "关热后加载时间 τ = t − t_h / s")
        ax.set_xlim(left=0)
        ax.legend(frameon=False, loc="best")
    note(fig, "τ = 0 时关热并开始规定电流爬升；验证持续至累计电荷 20 C·cm$^{-2}$（τ = 96.6667 s）。\nP 的后续回落不改变题面首次成功的记录；R 另加全过程不低于 0 ℃ 的稳健约束。")
    fig.subplots_adjust(left=.085, right=.98, bottom=.25, top=.90, wspace=.26)
    save(fig, output, "04_关热后回落与稳健验证")


def figure_energy(traces, output):
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.3))
    fields = ("E_aux_J", "E_gen_J", "E_phase_J", "E_loss_J", "E_sensible_J")
    labels = ("辅助热", "反应热", "相变净热", "−散热", "显热增量")
    colors = ("#316D9C", "#C77835", "#9B8AAD", "#B8BDC1", "#398476")
    for ax, key in zip(axes, ("P", "C", "R")):
        tr = traces[key]
        vals = np.array([tr[name][-1] for name in fields])
        vals[3] *= -1
        ax.bar(np.arange(5), vals, color=colors, width=.7)
        ax.axhline(0, color="#626970", lw=.8)
        ax.set_xticks(np.arange(5), labels, rotation=25, ha="right")
        for i, value in enumerate(vals):
            ax.annotate(f"{value:.0f}", (i, value), xytext=(0, 4 if value >= 0 else -12),
                        textcoords="offset points", ha="center", fontsize=8)
        label_panel(ax, NAMES[key])
        decorate(ax, "累计能量 / J" if key == "P" else None, "")
        ax.set_xticks(np.arange(5), labels, rotation=25, ha="right")
        ax.grid(axis="x", visible=False)
        ax.margins(y=.22)
        residual = tr["energy_residual_J"][-1]
        ax.text(.03, .98, f"t = {tr['time_s'][-1]:.2f} s\n守恒残差 {residual:.1e} J",
                transform=ax.transAxes, va="top", fontsize=8)
    note(fig, "能量记账：辅助热 + 反应热 + 相变净热 − 环境散热 = 显热增量（含端板）。\nP/C 取主结果轨迹末端；R 取预热及加载验证完整轨迹末端，因此 R 反应热与显热不与 P 启动窗口直接比较。")
    fig.subplots_adjust(left=.07, right=.99, bottom=.27, top=.91, wspace=.29)
    save(fig, output, "05_能量预算与守恒")


def figure_comparison(traces, summary, output):
    fig, axes = plt.subplots(2, 3, figsize=(11.3, 6.6))
    items = [
        ("辅助加热能耗 / J", lambda k: summary[k]["E_aux_J"], 1),
        ("总启动时间 / s", lambda k: summary[k]["startup_s"], 2),
        ("累计电荷 / (C·cm$^{-2}$)", lambda k: traces[k]["charge_C_cm2"][-1], 3),
        ("最低单片电压 / V", lambda k: np.min(cells(traces[k], "V")), 3),
        ("最大 MEA 冰体积分数", lambda k: np.max(cells(traces[k], "ice_bulk")), 5),
        ("最大端部孔隙冰饱和度", lambda k: np.max(cells(traces[k], "pore_ice_saturation")[:, [0, 4]]), 5),
    ]
    for ax, (label, getval, digits) in zip(axes.flat, items):
        vals = [float(getval(k)) for k in ("P", "C")]
        ax.bar([0, 1], vals, color=[COLORS["P"], COLORS["C"]], width=.54)
        ax.set_xticks([0, 1], [NAMES["P"], NAMES["C"]])
        ax.set_ylabel(label)
        ax.grid(axis="x", visible=False)
        maxval = max(vals)
        ax.set_ylim(0, maxval*1.3 if maxval > 0 else 1)
        ax.yaxis.set_major_locator(MaxNLocator(5))
        for i, value in enumerate(vals):
            ax.annotate(num(value, digits), (i, value), xytext=(0, 5), textcoords="offset points", ha="center", fontsize=10)
    note(fig, "仅比较题面 P/C 两种主策略；各指标均截至对应启动窗口末端。P 的预热阶段 j = 0，累计电荷为 0。\n首次过零与加载后持续保温不是同一要求；稳定性验证另见图 04，不能仅由此图认定实际加载稳定。")
    fig.subplots_adjust(left=.08, right=.98, bottom=.16, top=.97, hspace=.4, wspace=.36)
    save(fig, output, "06_主策略关键指标对比")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT,
                        help="Q3 results directory containing data/")
    args = parser.parse_args()
    data = args.root / "data"
    output = args.root / "figures"
    summary = read_summary(data / "summary_results.csv")
    traces = {k: read_trace(data / f"trajectory_{k}.csv") for k in ("P", "C", "P_postload", "R")}
    output.mkdir(parents=True, exist_ok=True)
    setup_style()
    figure_temperature(traces, summary, output)
    figure_heaters(summary, output)
    figure_safety(traces, output)
    figure_postload(traces, summary, output)
    figure_energy(traces, output)
    figure_comparison(traces, summary, output)


if __name__ == "__main__":
    main()
