"""图03论文版：两策略电压与协同加热结冰，省略纯预热近零冰量面板。"""
import numpy as np
from common import (CELL_COLORS, COLORS, NAMES, cells, cli, configure_style, decorate,
                    discrete_points, export_and_show, panel_title, read_traces)
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, ScalarFormatter

# ===== 常用调节区 =====
FIGSIZE = (11.3, 6.8)
MARKER_SIZE = 2.6
VOLTAGE_LIMIT = 0.30


def visible_points(ax, time, values, color, label, size=MARKER_SIZE, zorder=3):
    """密集离散点取消白边，避免后画点的白边遮掉前面点的颜色。"""
    artist = discrete_points(ax, time, values, color, label, size,
                             alpha=1., zorder=zorder)
    artist.set_markeredgewidth(0)
    artist.set_markeredgecolor(color)
    return artist


def build_figure():
    traces = read_traces("P", "C")
    fields = {key: {name: cells(trace, name) for name in
                   ("V", "ice_bulk", "pore_ice_saturation")}
              for key, trace in traces.items()}
    for key, values in fields.items():
        if not all(np.isfinite(array).all() for array in values.values()):
            raise ValueError(f"{key} 轨迹存在非有限值。")
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    voltage_top = max(1.30, max(float(v["V"].max()) for v in fields.values()) * 1.06)
    voltage_bottom = min(.26, min(float(v["V"].min()) for v in fields.values()) - .04)
    for col, key in enumerate(("P", "C")):
        time = traces[key]["time_s"]
        label = "最低无载电压" if np.all(traces[key]["j_A_cm2"] == 0) else "最低单片电压"
        visible_points(axes[0, col], time, np.min(fields[key]["V"], axis=1), COLORS[key], label)
        axes[0, col].axhline(VOLTAGE_LIMIT, color=COLORS["danger"], linestyle="--",
                            linewidth=1, label="电压约束 0.30 V")
        axes[0, col].set_ylim(voltage_bottom, voltage_top)
        axes[0, col].set_xlim(0, time[-1])
        panel_title(axes[0, col], f"({chr(97 + col)}) {NAMES[key]}")
        decorate(axes[0, col], "最低单片电压 / V")
        axes[0, col].legend(frameon=False, loc="lower left", fontsize=8, markerscale=1.6)

    # 纯预热冰量仅为数值残差、孔隙冰为零：论文图省略这两个无变化面板。
    # 原始CSV不改动；其统计窗口仍为首次启动前，未混入关热后的加载数据。
    time = traces["C"]["time_s"]
    ice = fields["C"]["ice_bulk"]
    saturation = fields["C"]["pore_ice_saturation"]
    visible_points(axes[1, 0], time, np.max(ice, axis=1), COLORS["neutral"],
                   "全堆最大", size=4.2, zorder=2.5)
    visible_points(axes[1, 0], time, np.max(ice[:, [0, 4]], axis=1), CELL_COLORS[0],
                   "端部单片最大", zorder=3)
    visible_points(axes[1, 0], time, ice[:, 2], CELL_COLORS[2], "中心单片", zorder=4)
    visible_points(axes[1, 1], time, np.max(saturation[:, [0, 4]], axis=1), COLORS["C"],
                   "端部孔隙冰饱和度")
    for col, (values, ylabel, title) in enumerate((
            (ice, "MEA 体积平均冰体积分数", "(c) C 协同加热 · 冰体积分数"),
            (saturation[:, [0, 4]], "端部孔隙冰饱和度", "(d) C 协同加热 · 孔隙冰饱和度"))):
        ax = axes[1, col]
        top = max(float(np.max(values)) * 1.15, 1e-12)
        ax.set_ylim(-.04 * top, top)
        ax.set_xlim(0, time[-1])
        decorate(ax, ylabel)
        panel_title(ax, title)
        ax.yaxis.set_major_locator(MaxNLocator(5, min_n_ticks=3))
        formatter = ScalarFormatter(useMathText=True)
        formatter.set_powerlimits((-3, 3))
        ax.yaxis.set_major_formatter(formatter)
        ax.legend(frameon=False, loc="upper left", fontsize=8, markerscale=1.6)
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "03_主策略电压与结冰", args,
                    dict(left=.09, right=.98, bottom=.10, top=.94, hspace=.40, wspace=.25))
