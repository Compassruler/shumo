# 问题二：逐图 Python 绘图代码说明

本文件夹用于逐张修改问题二的 12 张图。每个 `figXX_*.py` 只负责一张图，直接运行时不会生成其他图片，也不会重新运行问题二模型。

数据读取自：

```text
问题2_求解结果/data/
```

图片输出到：

```text
问题2_求解结果/figures/
```

## 文件作用

| 文件 | 负责的图片 | 主要数据来源 | 可以重点修改 |
|---|---|---|---|
| `fig01_loading_and_charge.py` | 图01：加载策略与累计电荷 | `trajectory_constant/ramp/step.csv` | 三种策略颜色、圆点大小、电荷预算线 |
| `fig02_cell_and_endplate_temperatures.py` | 图02：各单电池与端板温度 | 三种 `trajectory_*.csv` | 单电池颜色、圆点大小、零度参考线 |
| `fig03_cell_voltage_constraints.py` | 图03：各单电池电压与安全约束 | 三种 `trajectory_*.csv` | 单电池颜色、圆点大小、0.30 V 安全线 |
| `fig04_bulk_ice_fraction.py` | 图04：总体积基准冰体积分数 | 三种 `trajectory_*.csv` | 单电池颜色、圆点大小和纵轴范围 |
| `fig05_pore_ice_saturation.py` | 图05：孔隙冰饱和度 | 三种 `trajectory_*.csv` | 单电池颜色、圆点大小和纵轴范围 |
| `fig06_global_heat_balance.py` | 图06：全局热预算与能量守恒 | 三种 `trajectory_*.csv` | 四类热量颜色、圆点大小、上下排比例 |
| `fig07_critical_temperature_trajectories.py` | 图07：最低启动温度两侧轨迹 | `trajectory_critical_success/failure.csv` | 成功/失败侧版式、温度与电压圆点、安全线 |
| `fig08_critical_voltage_losses.py` | 图08：临界启动电压损失分解 | `trajectory_critical_success/failure.csv` | 三类电压损失颜色和圆点大小 |
| `fig09_minimum_temperature_search.py` | 图09：最低初温可行性搜索 | `temperature_search.csv` | 成功/失败颜色、圆点大小、零度参考线 |
| `fig10_discretization_convergence.py` | 图10：时间空间离散收敛性 | `convergence.csv` | 不同空间倍率颜色、圆点大小和对数横轴 |
| `fig11_parameter_sensitivity.py` | 图11：参数与边界假设敏感性 | `sensitivity.csv` | 成功/失败颜色、圆点大小、数值标注 |
| `fig12_ramp_slope_limit.py` | 图12：线性升载斜率极限 | `ramp_slope_limit.csv` | 圆点大小、对数横轴和 0.2 s 参考线 |
| `common.py` | 所有脚本共用功能 | 不单独绘图 | 字体、全局颜色、CSV读取、图01式圆点、导出与交互显示；不能删除 |

## 离散数据绘图规则

所有从 CSV 逐时刻、逐温度、逐网格或逐参数读取的离散结果，都使用与问题一图01相同的方式：

- 实心圆；
- 不使用连接线；
- 细白边；
- 默认计算点大小为 `2.0`；
- 搜索或收敛图因数据点较少，可在对应文件中使用 `3.0`。

公共实现位于 `common.py`：

```python
DISCRETE_MARKER_SIZE = 2.0

def discrete_points(...):
    ...
```

安全阈值、零度线和数值搜索边界是参考线，仍使用虚线。图形中的文字和参考线不是离散数据点。

## 推荐修改位置

每个文件开头都有：

```python
# ===== 常用调节区 =====
```

优先修改其中的 `FIGSIZE`、`MARKER_SIZE`、颜色和参考线数值。需要进一步调整标题、图例或坐标范围时，再修改 `build_figure()`。

## 运行方法

进入本文件夹：

```bash
cd 26比赛/解题/问题2_求解结果/code/figure_scripts
```

例如运行图01：

```bash
python fig01_loading_and_charge.py
```

默认会：

1. 更新对应 PDF、SVG 和 300 dpi PNG；
2. 打开 Matplotlib 交互窗口。

关闭交互窗口后程序结束。

## 只预览、不覆盖图片

```bash
python fig01_loading_and_charge.py --no-save
```

该模式适合细致调整配色、圆点大小和版式。

## 只导出、不显示窗口

```bash
python fig01_loading_and_charge.py --no-show
```

## 必须保留的文件

请保留：

- `fig01_*.py` 至 `fig12_*.py`；
- `common.py`；
- 上两级 `data/` 中的 CSV 文件。

原来的 `code/plot_results.py` 是批量绘图脚本，逐图调整时不需要运行，但建议保留以便追溯原始流程。
