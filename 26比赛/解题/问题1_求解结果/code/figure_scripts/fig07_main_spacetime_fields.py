"""图07：五层基线模型的温度与结冰时空分布。"""
from common import cli, configure_style, export_and_show
from field_figure import build_field_figure

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.1)
TEMPERATURE_CMAP = 'coolwarm'
ICE_CMAP = 'YlGnBu'

if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    fig = build_field_figure('main', FIGSIZE, TEMPERATURE_CMAP, ICE_CMAP)
    export_and_show(fig, '07_五层基线温度与结冰时空分布', args)
