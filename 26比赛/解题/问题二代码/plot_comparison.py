# -*- coding: utf-8 -*-
"""绘制 模型一直接跑 vs 正确5片热网络 对比图。"""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 中文字体
for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = Path(__file__).resolve().parent
d = np.load(HERE / "q1_direct_vs_stack_data.npz")
tA, TA, VA, iceA = d["tA"], d["TA"], d["VA"], d["iceA"]
tB, TB = d["tB"], d["TB"]
TQ = 20.0 / 0.3

fig, axes = plt.subplots(2, 2, figsize=(13, 9))

# (1) 温度对比
ax = axes[0, 0]
ax.plot(tA, TA, color="tab:red", lw=2.2, label="模型一直接跑（每片两侧对流、无端板）")
ax.plot(tB, TB[2], color="tab:green", lw=2.0, label="正确网络·中片③")
ax.plot(tB, TB[0], color="tab:blue", lw=2.0, label="正确网络·端片①（短板）")
for k in (1, 3):
    ax.plot(tB, TB[k], color="tab:green", lw=1.0, alpha=0.45)
ax.plot(tB, TB[4], color="tab:blue", lw=1.0, alpha=0.55)
ax.axhline(0, color="k", ls="--", lw=1)
ax.axvline(TQ, color="gray", ls=":", lw=1.2)
ax.text(TQ + 1, -9, f"电荷预算耗尽 {TQ:.1f}s", color="gray", fontsize=9)
ax.set_xlabel("时间 / s"); ax.set_ylabel("平均温度 / °C")
ax.set_title("① 温度：模型一 28s 到 0°C；正确端片 63.8s，且断电后回落")
ax.legend(fontsize=8.5, loc="lower right"); ax.grid(alpha=0.3)

# (2) 端-中温差（不一致性）
ax = axes[0, 1]
ax.plot(tB, TB[2] - TB[0], color="tab:purple", lw=2)
ax.fill_between(tB, 0, TB[2] - TB[0], color="tab:purple", alpha=0.15)
ax.axvline(TQ, color="gray", ls=":", lw=1.2)
ax.set_xlabel("时间 / s"); ax.set_ylabel("中片③ − 端片① 温差 / K")
ax.set_title("② 电堆不一致性：峰值约 4.3K，模型一直接跑恒为 0（5条线重合）")
ax.grid(alpha=0.3)

# (3) 电压
ax = axes[1, 0]
ax.plot(tA, VA, color="tab:red", lw=2, label="模型一（无端片浓差倍率、无冰堵）")
ax.axhline(0.30, color="k", ls="--", lw=1.2)
ax.text(2, 0.33, "安全下限 0.30V", fontsize=9)
ax.axvline(TQ, color="gray", ls=":", lw=1.2)
ax.set_ylim(0, 1.35)
ax.set_xlabel("时间 / s"); ax.set_ylabel("电压 / V")
ax.set_title("③ 电压：断电后跳回开路；真实端片还应叠加 冰堵+浓差×10")
ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=0.3)

# (4) 冰体积分数
ax = axes[1, 1]
ax.plot(tA, iceA, color="tab:red", lw=2, label="模型一标定后 ice ≡ 0")
ax.axhline(0.99, color="k", ls="--", lw=1.2)
ax.text(2, 0.90, "严重冰堵阈值 0.99", fontsize=9)
ax.set_ylim(-0.05, 1.1)
ax.set_xlabel("时间 / s"); ax.set_ylabel("最大局部冰体积分数")
ax.set_title("④ 冰：k_freeze 标定退化到 0.0001，冰堵判据名存实亡")
ax.legend(fontsize=8.5, loc="center right"); ax.grid(alpha=0.3)

fig.suptitle("问题一模型直接跑问题二  vs  正确的5片电堆热网络（-10°C、恒流0.3 A/cm²）",
             fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.97])
out = HERE / "q1_direct_vs_stack_compare.png"
fig.savefig(out, dpi=140)
print("saved", out)
