"""问题4 出图：三工况初始场、工况1动态vs恒功率、10~100min扫描、能耗对比。"""
import json
from pathlib import Path

import numpy, scipy, numba, matplotlib  # noqa: F401
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
FIG = HERE.parent / "figures"
FIG.mkdir(exist_ok=True)

NODE_LABELS = ["T1", "T2", "T3", "T4", "T5", "EP_L", "EP_R"]
COND_COLORS = {"工况1_完全冷却": "#1f77b4", "工况2_预冷20min": "#ff7f0e", "工况3_预冷40min": "#2ca02c"}


def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def fig01():
    init = load("三工况初始温度场_七节点.json")
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = np.arange(len(NODE_LABELS))
    for name, vals in init.items():
        ax.plot(x, vals, "o-", label=name.replace("_", " "), color=COND_COLORS[name], lw=1.6)
    ax.axhline(0, color="k", lw=0.8, ls="--", alpha=0.5)
    ax.set_xticks(x); ax.set_xticklabels(NODE_LABELS)
    ax.set_xlabel("节点（5 片单电池 + 左右端板）")
    ax.set_ylabel("初始温度 / ℃")
    ax.set_title("三种预冷工况的冷启动初始温度场")
    ax.legend(frameon=False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"01_三工况预冷初始温度场.{ext}", dpi=200)
    plt.close(fig)


def fig02():
    traj = load("三工况轨迹_供绘图.json")["工况1_完全冷却"]
    dyn = traj["dynamic"]; con = traj["constant"]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 6.5), sharex=False)

    ax = axes[0, 0]
    for k in range(5):
        ax.plot(dyn["time_s"], dyn[f"q{k+1}_W_cm2"], lw=1.4, label=f"片{k+1}")
    ax.set_xlabel("时间 / s"); ax.set_ylabel("功率密度 q / W/cm²")
    ax.set_title("动态控制：分片功率 q_k(t)")
    ax.set_ylim(0, 1.05); ax.legend(ncol=5, fontsize=8, frameon=False); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    for k in range(5):
        ax.plot(con["time_s"], np.where(np.asarray(con["time_s"]) < 25.73, 1.0 if k != 2 else 0.6245, 0.0),
                lw=1.4, label=f"片{k+1}")
    ax.set_xlabel("时间 / s"); ax.set_ylabel("功率密度 q / W/cm²")
    ax.set_title("恒功率（问题3策略C）：q=[1,1,0.6245,1,1]")
    ax.set_ylim(0, 1.05); ax.legend(ncol=5, fontsize=8, frameon=False); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    for k in range(5):
        ax.plot(dyn["time_s"], dyn[f"T{k+1}_C"], lw=1.4, label=f"片{k+1}")
    ax.axhline(0, color="k", ls="--", lw=0.8, alpha=0.5)
    ax.set_xlabel("时间 / s"); ax.set_ylabel("温度 / ℃")
    ax.set_title("动态控制：分片温度 T_k(t)")
    ax.legend(ncol=5, fontsize=8, frameon=False); ax.grid(alpha=0.3)

    ax = axes[1, 1]
    for k in range(5):
        ax.plot(con["time_s"], con[f"T{k+1}_C"], lw=1.4, label=f"片{k+1}")
    ax.axhline(0, color="k", ls="--", lw=0.8, alpha=0.5)
    ax.set_xlabel("时间 / s"); ax.set_ylabel("温度 / ℃")
    ax.set_title("恒功率：分片温度 T_k(t)")
    ax.legend(ncol=5, fontsize=8, frameon=False); ax.grid(alpha=0.3)

    fig.suptitle("工况1（完全冷却 −30 ℃）：动态控制 vs 恒功率", y=1.0)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"02_工况1动态vs恒功率.{ext}", dpi=200)
    plt.close(fig)


def fig03():
    scan = load("预冷10到100min_恒功率冷启动.json")
    tc = [r["冷却时间_min"] for r in scan]
    E = [r["E_aux_J"] for r in scan]
    ts = [r["first_success_s"] for r in scan]
    dT = [r["dTmax_K"] for r in scan]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    axes[0].plot(tc, E, "o-", color="#1f77b4", lw=1.6)
    axes[0].set_xlabel("预冷时间 τ_c / min"); axes[0].set_ylabel("辅助加热总能耗 E_aux / J")
    axes[0].set_title("能耗随预冷时间"); axes[0].grid(alpha=0.3)
    axes[1].plot(tc, ts, "o-", color="#ff7f0e", lw=1.6)
    axes[1].set_xlabel("预冷时间 τ_c / min"); axes[1].set_ylabel("总启动时间 t_s / s")
    axes[1].set_title("启动时间随预冷时间"); axes[1].grid(alpha=0.3)
    axes[2].plot(tc, dT, "o-", color="#2ca02c", lw=1.6)
    axes[2].set_xlabel("预冷时间 τ_c / min"); axes[2].set_ylabel("电堆最大温差 ΔT_max / K")
    axes[2].set_title("最大温差随预冷时间"); axes[2].grid(alpha=0.3)
    fig.suptitle("第(2)问：10~100 min 预冷下的恒功率冷启动结果", y=1.02)
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"03_预冷10到100min扫描.{ext}", dpi=200)
    plt.close(fig)


def fig04():
    t4 = load("表4_问题四主结果.json")
    names = [r["工况"].replace("_", " ")[:4] for r in t4]
    dyn_E = [r["E_aux_J"] for r in t4 if r["策略"] == "动态控制"]
    con_E = [r["E_aux_J"] for r in t4 if r["策略"] == "恒功率(问题3基准)"]
    x = np.arange(3); w = 0.38
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.bar(x - w/2, dyn_E, w, label="动态控制", color="#1f77b4")
    ax.bar(x + w/2, con_E, w, label="恒功率（问题3）", color="#ff7f0e")
    ax.set_xticks(x); ax.set_xticklabels(["工况1\n(−30 ℃)", "工况2\n(20 min, −9 ℃)", "工况3\n(40 min, −22 ℃)"])
    ax.set_ylabel("辅助加热总能耗 E_aux / J")
    ax.set_title("三种工况下动态 vs 恒功率能耗对比")
    ax.legend(frameon=False); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(FIG / f"04_三工况能耗对比.{ext}", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    fig01(); print("fig01 done")
    fig02(); print("fig02 done")
    fig03(); print("fig03 done")
    fig04(); print("fig04 done")
