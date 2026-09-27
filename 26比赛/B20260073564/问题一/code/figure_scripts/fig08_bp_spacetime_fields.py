"""图08：含双极板修订模型的温度与结冰时空分布。"""
from common import cli, configure_style, export_and_show
from field_figure import build_field_figure

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.1)
TEMPERATURE_CMAP = 'coolwarm'
ICE_CMAP = 'YlGnBu'

if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    fig = build_field_figure('bp', FIGSIZE, TEMPERATURE_CMAP, ICE_CMAP)
    export_and_show(fig, '08_含双极板修订模型温度与结冰时空分布', args)
