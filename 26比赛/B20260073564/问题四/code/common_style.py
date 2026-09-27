"""问题四统一绘图样式：与前三问相同的实心圆、字体、配色与导出规范。

所有离散结果保持原始数据点，不抽样、不连接。连续空间温度场和科学
阈值参考线由各图显式绘制；分类对比使用稍大的圆点。
"""
from pathlib import Path
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import to_rgb

COLORS = ['#316D9C', '#C77835', '#398476', '#9B8AAD', '#737A80']
STRATEGY_COLORS = {
    'dynamic': COLORS[0], 'D': COLORS[0],
    'constant': COLORS[1], 'constant_hold': COLORS[1],
    'constant_first': COLORS[1], 'C': COLORS[1],
    'guarded': COLORS[2], 'constant_optimized': COLORS[3],
    'zero_heater': COLORS[4],
}
DANGER = '#A44848'
DISCRETE_MARKER_SIZE = 2.0
CATEGORY_MARKER_SIZE = 6.0


def configure_style():
    font_path = Path('/System/Library/Fonts/STHeiti Light.ttc')
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        font = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        candidates = ['Noto Sans CJK SC', 'Source Han Sans SC', 'Microsoft YaHei', 'SimHei']
        available = {item.name for item in font_manager.fontManager.ttflist}
        font = next((name for name in candidates if name in available), 'DejaVu Sans')
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': [font, 'DejaVu Sans'],
        'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 11,
        'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 9,
        'axes.unicode_minus': False, 'axes.spines.top': False,
        'axes.spines.right': False, 'axes.edgecolor': '#555B61',
        'axes.linewidth': .7, 'axes.grid': True, 'grid.alpha': .35,
        'grid.color': '#D9DEE3', 'grid.linewidth': .55,
        'axes.axisbelow': True, 'xtick.direction': 'out', 'ytick.direction': 'out',
        'legend.frameon': False, 'savefig.facecolor': 'white',
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'pdf.fonttype': 42, 'svg.fonttype': 'none',
        'mathtext.fontset': 'dejavusans', 'axes.prop_cycle': plt.cycler(color=COLORS),
    })


def points(ax, x, y, *legacy_format, color=None, label=None,
           size=DISCRETE_MARKER_SIZE, alpha=.92, zorder=3, **legacy):
    """实心圆、无连线、0.25 pt白边；旧调用的线型/散点参数兼容但不沿用。"""
    if color is None:
        color = legacy.pop('c', None)
    if color is None:
        color = legacy.pop('edgecolors', None)
    if color is None:
        color = ax._get_lines.get_next_color()
    # Draw the complete white rim layer before all coloured centres. Dense
    # neighbouring markers then cannot erase the preceding coloured centres.
    # Both layers contain every input sample, with no data thinning.
    ax.plot(x, y, linestyle='None', marker='o', markersize=size,
            markerfacecolor='white', markeredgecolor='white',
            markeredgewidth=.25, color='white', alpha=.92,
            label='_nolegend_', zorder=zorder)
    return ax.plot(x, y, linestyle='None', marker='o', markersize=max(.1,size-.25),
                   markerfacecolor=color, markeredgecolor='none',
                   markeredgewidth=0, color=color, alpha=.92,
                   label=label, zorder=zorder+.01)[0]


def log_points(ax, x, y, *fmt, **kwargs):
    ax.set_xscale('log')
    ax.set_yscale('log')
    return points(ax, x, y, *fmt, **kwargs)


def failed_points(ax, x, y, color=DANGER, label=None, size=3.5):
    """红色外圈标记失败，内部实心圆仍保留工况颜色；不删除失败样本。"""
    points(ax, x, y, color=DANGER, size=size+2., zorder=4)
    if label:
        ax.plot([], [], linestyle='None', marker='o', markersize=size+2., markerfacecolor='none', markeredgecolor=DANGER, markeredgewidth=1., label=label)
    return points(ax, x, y, color=color, size=size, zorder=5)


def category_points(ax, x, y, color, label=None, labels=None, size=CATEGORY_MARKER_SIZE):
    artist = points(ax, x, y, color=color, label=label, size=size)
    ax.margins(x=.18)
    if labels is not None:
        for xx, yy, caption in zip(x, y, labels):
            if np.isfinite(yy):
                ax.annotate(caption, (xx, yy), xytext=(0, 7 if yy >= 0 else -8),
                            textcoords='offset points', ha='center',
                            va='bottom' if yy >= 0 else 'top', fontsize=8,
                            color='#545B62')
    return artist


def lighter(color, amount=.52):
    rgb = np.asarray(to_rgb(color))
    return tuple(rgb + (1-rgb)*amount)


def finish_style(fig):
    """最终统一字体、左标题与图例；将原总标题作为底部口径注释。"""
    note = ''
    if fig._suptitle is not None:
        note = fig._suptitle.get_text()
        fig._suptitle.remove()
        fig._suptitle = None
    explicit = getattr(fig, '_q4_note', '')
    note = '\n'.join(text for text in (note, explicit) if text)
    panel_index = 0
    for ax in fig.axes:
        if ax.get_label() == '<colorbar>':
            ax.tick_params(labelsize=9, direction='out', length=3)
            ax.yaxis.label.set_size(10)
            continue
        title = ax.get_title()
        if not re.match(r'^\([a-z]\)', title):
            title = f'({chr(97+panel_index)}) ' + title
        panel_index += 1
        ax.set_title('', loc='center')
        ax.set_title(title.rstrip(), loc='left', pad=8, fontsize=11, fontweight='medium')
        ax.xaxis.label.set_size(10)
        ax.yaxis.label.set_size(10)
        ax.tick_params(direction='out', length=3, labelsize=9)
        ax.set_axisbelow(True)
        legend = ax.get_legend()
        if legend is not None:
            legend.set_frame_on(False)
            for text in legend.get_texts():
                text.set_fontsize(9)
            legend.get_title().set_fontsize(9)
    if note:
        height = .055 + .027*(note.count('\n'))
        engine = fig.get_layout_engine()
        if engine is not None:
            engine.set(rect=(0, height, 1, 1-height))
        fig.text(.065, .013, note, va='bottom', ha='left', fontsize=8.5, color='#545B62')
    return note

def align_regular_panels(fig):
    """按最终渲染的边界统一三列/三行网格间距，保留足够轴标签空间。"""
    fig.canvas.draw()
    panels=[ax for ax in fig.axes if ax.get_label() != '<colorbar>' and ax.get_subplotspec() is not None]
    if not panels:
        return
    specs=[ax.get_subplotspec() for ax in panels]
    if len({id(s.get_gridspec()) for s in specs}) != 1:
        return
    nrows,ncols=specs[0].get_gridspec().get_geometry()
    if max(nrows,ncols)<3 or len(panels)!=nrows*ncols:
        return
    if any(s.rowspan.stop-s.rowspan.start!=1 or s.colspan.stop-s.colspan.start!=1 for s in specs):
        return
    boxes={(s.rowspan.start,s.colspan.start):ax.get_position().frozen() for ax,s in zip(panels,specs)}
    left=min(b.x0 for b in boxes.values());right=max(b.x1 for b in boxes.values())
    bottom=min(b.y0 for b in boxes.values());top=max(b.y1 for b in boxes.values())
    gx=max((boxes[r,c+1].x0-boxes[r,c].x1 for r in range(nrows) for c in range(ncols-1)),default=0.)
    gy=max((boxes[r,c].y0-boxes[r+1,c].y1 for r in range(nrows-1) for c in range(ncols)),default=0.)
    width=(right-left-(ncols-1)*gx)/ncols
    height=(top-bottom-(nrows-1)*gy)/nrows
    fig.set_layout_engine(None)
    for ax,s in zip(panels,specs):
        r,c=s.rowspan.start,s.colspan.start
        ax.set_position([left+c*(width+gx),top-(r+1)*height-r*gy,width,height])
    fig.canvas.draw()
