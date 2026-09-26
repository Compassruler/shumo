"""图07/08共用的时空场绘图实现。"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from common import DATA, field_grid, panel_title, read_csv, sample_edges, spatial_edges


def build_field_figure(model, figsize, temperature_cmap, ice_cmap):
    """model 为 main 或 bp；返回尚未保存的 Matplotlib Figure。"""
    fields = {f'{model}_minus{temp}': read_csv(f'fields_{model}_minus{temp}.csv')
              for temp in ['20', '25']}
    keys = [f'{model}_minus20', f'{model}_minus25']
    t_min = min(np.min(fields[k]['T_C']) for k in keys)
    t_max = max(np.max(fields[k]['T_C']) for k in keys)
    ice_max = max(np.max(fields[k]['ice_bulk']) for k in keys)
    ice_max = max(ice_max, 1e-6)
    norms = [colors.Normalize(t_min, t_max), colors.Normalize(0, ice_max)]
    fig, axes = plt.subplots(2, 2, figsize=figsize)
    images = []
    for row, (variable, cmap) in enumerate([('T_C', temperature_cmap), ('ice_bulk', ice_cmap)]):
        for col, temp in enumerate(['20', '25']):
            ax = axes[row, col]
            times, x, z, layers = field_grid(fields[f'{model}_minus{temp}'], variable)
            # 双极板模型的冰图排除 aBP/cBP，只展示 MEA 区域。
            if model == 'bp' and row == 1:
                keep = ~np.isin(layers, ['aBP', 'cBP'])
                x, z, layers = x[keep], z[keep, :], layers[keep]
            x_edges = spatial_edges(x, layers)
            image = ax.pcolormesh(sample_edges(times), x_edges, z, shading='flat',
                                  cmap=cmap, norm=norms[row], rasterized=False)
            for index in np.flatnonzero(layers[1:] != layers[:-1]):
                ax.axhline(x_edges[index+1], color='white', alpha=.6, linewidth=.65, linestyle='--')
            panel_title(ax, f'({chr(97+row*2+col)}) 初始温度 −{temp} ℃')
            ax.set_xlabel('时间 / s')
            ax.set_ylabel('MEA 位置 / μm' if model == 'bp' and row == 1 else '厚度方向位置 / μm')
            ax.set_xlim(0, 35); ax.set_xticks(np.arange(0, 36, 5)); ax.grid(False)
            if col == 0: images.append(image)
    # 每一行共用同一个色标，确保 −20 ℃与−25 ℃可以直接比较。
    fig.subplots_adjust(left=.10, right=.86, bottom=.09, top=.95, wspace=.31, hspace=.42)
    for row, image in enumerate(images):
        pos = axes[row, 1].get_position()
        cax = fig.add_axes([.89, pos.y0, .019, pos.height])
        bar = fig.colorbar(image, cax=cax)
        bar.solids.set_rasterized(False)
        bar.set_label('局部温度 / ℃' if row == 0 else '局部总冰体积分数', labelpad=9)
    return fig
