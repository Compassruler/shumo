"""图06：题面 P、C 两种主策略的六项关键指标对比。"""
import numpy as np
import matplotlib.pyplot as plt
from common import (COLORS, NAMES, cells, cli, configure_style, discrete_points,
                    export_and_show, note, num, panel_title, read_summary, read_traces)

# ===== 常用调节区 =====
FIGSIZE = (11.3, 6.6)
MARKER_SIZE = 7.0


def build_figure():
    summary = read_summary()
    traces = read_traces("P", "C")
    fig, axes = plt.subplots(2, 3, figsize=FIGSIZE)
    items = [
        ("辅助加热能耗 / J", lambda key: summary[key]["E_aux_J"], 1),
        ("总启动时间 / s", lambda key: summary[key]["startup_s"], 2),
        (r"累计电荷 / (C·cm$^{-2}$)", lambda key: traces[key]["charge_C_cm2"][-1], 3),
        ("最低单片电压 / V", lambda key: np.min(cells(traces[key], "V")), 3),
        ("最大 MEA 冰体积分数", lambda key: np.max(cells(traces[key], "ice_bulk")), 5),
        ("最大端部孔隙冰饱和度",
         lambda key: np.max(cells(traces[key], "pore_ice_saturation")[:, [0, 4]]), 5),
    ]
    for index, (ax, (label, get_value, digits)) in enumerate(zip(axes.flat, items)):
        values = [float(get_value(key)) for key in ("P", "C")]
        for position, key, value in zip((0, 1), ("P", "C"), values):
            discrete_points(ax, [position], [value], COLORS[key], NAMES[key], MARKER_SIZE)
            ax.annotate(num(value, digits), (position, value), xytext=(0, 7),
                        textcoords="offset points", ha="center", fontsize=10)
        ax.set_xticks([0, 1], [NAMES["P"], NAMES["C"]])
        ax.set_ylabel(label)
        panel_title(ax, f"({chr(97 + index)})")
        ax.grid(axis="x", visible=False)
        maximum = max(values)
        ax.set_ylim(0, maximum * 1.30 if maximum > 0 else 1)
        ax.margins(x=.35)
    note(fig, "仅比较题面 P/C 两种主策略；各指标均截至对应启动窗口末端。P 预热阶段 j = 0，累计电荷为 0。\n首次过零与加载后持续保温不是同一要求；稳定性验证另见图04。")
    return fig


if __name__ == "__main__":
    args = cli(__doc__)
    configure_style()
    export_and_show(build_figure(), "06_主策略关键指标对比", args,
                    dict(left=.08, right=.98, bottom=.16, top=.97, hspace=.40, wspace=.36))
