"""图06：全局热预算与能量守恒残差。"""
import matplotlib.pyplot as plt
from common import COLORS, NAMES, axis, cli, configure_style, discrete_points, export_and_show, load_trajectories, numeric

FIGURE_HEIGHT=6.0
MARKER_SIZE=2.0


def build_figure():
    trajectories=load_trajectories(); count=len(trajectories)
    fig,axes=plt.subplots(2,count,figsize=(4.35*count,FIGURE_HEIGHT),squeeze=False,
                          layout='constrained',gridspec_kw={'height_ratios':[2.3,1]})
    energy=[('heat_gen_J_m2','电化学产热',COLORS[0]),
            ('heat_phase_J_m2','净相变热',COLORS[1]),
            ('heat_loss_J_m2','向环境散热',COLORS[3]),
            ('heat_sensible_J_m2','总显热增量',COLORS[2])]
    for col,(kind,rows) in enumerate(trajectories.items()):
        t=numeric(rows,'time_s')
        for key,label,color in energy:
            discrete_points(axes[0,col],t,numeric(rows,key)/1000,color,label,MARKER_SIZE)
        axis(axes[0,col],'累计热量 / (kJ/m²)'); axes[0,col].set_title(NAMES[kind]); axes[0,col].legend(frameon=False)
        discrete_points(axes[1,col],t,numeric(rows,'energy_balance_J_m2'),'#555555','守恒残差',MARKER_SIZE)
        axes[1,col].axhline(0,color='#888888',lw=.8)
        axes[1,col].ticklabel_format(axis='y',style='sci',scilimits=(-2,3))
        axis(axes[1,col],'守恒残差 / (J/m²)')
    return fig


if __name__ == '__main__':
    args=cli(__doc__); configure_style()
    export_and_show(build_figure(),'06_全局热预算与能量守恒',args)
