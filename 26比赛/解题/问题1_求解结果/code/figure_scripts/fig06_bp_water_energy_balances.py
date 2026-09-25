"""图06：含双极板修订模型的水量、能量收支与守恒残差。"""
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from common import COLORS, cli, configure_style, discrete_points, export_and_show, panel, read_cases

# ===== 常用调节区 =====
FIGSIZE = (7.1, 5.1)
RESIDUAL_COLOR = COLORS['residual']


def build_figure():
    data = read_cases()
    fig, axes = plt.subplots(2, 2, figsize=FIGSIZE)
    water_handles, heat_handles = [], []
    for col, temp in enumerate(['20', '25']):
        d = data[f'bp_minus{temp}']
        # 上排：累计水量；储水量先扣除初始存水量。
        ax = axes[0, col]
        for key, label, color in [
                ('water_produced_kg_m2', '累计产水', COLORS['main']),
                ('water_stored_kg_m2', '储水量变化', COLORS['pore']),
                ('water_out_kg_m2', '累计排水', COLORS['bp'])]:
            amount = d[key]-d['water_initial_kg_m2'] if key == 'water_stored_kg_m2' else d[key]
            line = discrete_points(ax, d['t_s'], amount*1e3, color, label)
            if col == 0: water_handles.append(line)
        right = ax.twinx()
        discrete_points(right, d['t_s'], d['water_balance_kg_m2']*1e3,
                        RESIDUAL_COLOR, '收支残差')
        right.grid(False); right.spines['right'].set_visible(True)
        right.set_ylabel('水收支残差 / (g/m²)', color=RESIDUAL_COLOR)
        right.tick_params(axis='y', colors=RESIDUAL_COLOR)
        panel(ax, f'({chr(97+col)}) 含双极板修订 · −{temp} ℃', '水量 / (g/m²)')

        # 下排：累计热量；主量使用 kJ/m²，右轴残差保留 J/m²。
        ax = axes[1, col]
        for key, label, color in [
                ('heat_gen_J_m2', '累计产热', COLORS['main']),
                ('heat_phase_J_m2', '累计相变放热', COLORS['phase']),
                ('heat_loss_J_m2', '累计散热', COLORS['loss'])]:
            line = discrete_points(ax, d['t_s'], d[key]/1e3, color, label)
            if col == 0: heat_handles.append(line)
        right = ax.twinx()
        discrete_points(right, d['t_s'], d['energy_balance_J_m2'],
                        RESIDUAL_COLOR, '收支残差')
        right.grid(False); right.spines['right'].set_visible(True)
        right.set_ylabel('能量收支残差 / (J/m²)', color=RESIDUAL_COLOR)
        right.tick_params(axis='y', colors=RESIDUAL_COLOR)
        panel(ax, f'({chr(99+col)}) 含双极板修订 · −{temp} ℃', '累计热量 / (kJ/m²)')
    residual = Line2D([0], [0], color=RESIDUAL_COLOR, marker='o', linestyle='None',
                      markersize=2.0, label='收支残差（右轴）')
    legend_kw = dict(ncol=4, fontsize=7.5, frameon=False, columnspacing=1.15, handlelength=1.7)
    fig.legend(handles=water_handles+[residual], loc='upper center', bbox_to_anchor=(.5,.985), **legend_kw)
    fig.legend(handles=heat_handles+[residual], loc='center', bbox_to_anchor=(.5,.475), **legend_kw)
    return fig


if __name__ == '__main__':
    args = cli(__doc__); configure_style()
    export_and_show(build_figure(), '06_bp_water_energy_balances', args,
                    dict(left=.09, right=.96, bottom=.10, top=.84, wspace=.52, hspace=.75))
