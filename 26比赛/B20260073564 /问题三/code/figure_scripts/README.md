# 问题三：逐图 Python 绘图代码说明

本文件夹用于逐张修改问题三的 6 张图。每个 `figXX_*.py` 只负责一张图，直接运行不会生成其他图片，也不会重新运行问题三的优化或仿真模型。

绘图数据读取自上两级 `data/` 文件夹，图片统一输出到上两级 `figures/` 文件夹。

## 文件作用

| 文件 | 负责的图片 | 主要数据来源 | 可以重点修改 |
|---|---|---|---|
| `fig01_main_strategy_temperatures.py` | 图01：纯预热与协同加热的单电池和端板温度历程 | `trajectory_P.csv`、`trajectory_C.csv`、`summary_results.csv` | 单电池颜色、圆点大小、零度线、关热标记和图例 |
| `fig02_heater_power_and_energy.py` | 图02：P、C、R 三种方案的分片加热功率与单片能耗 | `summary_results.csv` | 三种策略颜色、圆点横向偏移、圆点大小和 1 W·cm⁻² 参考线 |
| `fig03_voltage_and_icing.py` | 图03：两种主策略的最低电压、冰体积分数和孔隙冰饱和度 | `trajectory_P.csv`、`trajectory_C.csv` | 电压约束线、圆点大小、冰指标颜色和纵轴范围 |
| `fig04_postload_robustness.py` | 图04：关热加载后的温度回落与稳健预热验证 | `trajectory_P_postload.csv`、`trajectory_R.csv`、`summary_results.csv` | P/R 配色、最低点标注、温度与电压阈值线 |
| `fig05_energy_budget.py` | 图05：三种方案的累计能量预算与守恒残差 | `trajectory_P.csv`、`trajectory_C.csv`、`trajectory_R.csv` | 五类能量颜色、圆点大小、数字标注和子图间距 |
| `fig06_main_strategy_comparison.py` | 图06：题面 P、C 两种主策略的六项关键指标对比 | `summary_results.csv`、`trajectory_P.csv`、`trajectory_C.csv` | P/C 配色、圆点大小、数值标注和纵轴留白 |
| `common.py` | 所有单图脚本共用功能 | 不单独绘图 | 中文字体、全局配色、CSV读取、图01式圆点、PDF/SVG/PNG导出和交互显示；不能删除 |

## 离散数据绘图规则

所有从 CSV 逐时刻、逐单电池、逐策略或逐能量项读取的离散结果，统一使用与问题一图01相同的样式：

- 实心圆；
- 不使用连接线；
- 细白边；
- 时间序列默认圆点大小为 `2.0`；
- 分类对比图因点数较少，可在对应脚本中使用更大的实心圆。

公共实现位于 `common.py`：

```python
DISCRETE_MARKER_SIZE = 2.0

def discrete_points(...):
    ...
```

零度线、电压约束线、加热功率上限和关热时刻是参考线，不属于离散数据，因此仍可使用实线、虚线或点线。

## 推荐修改位置

每个单图文件开头都有：

```python
# ===== 常用调节区 =====
```

优先修改其中的 `FIGSIZE`、`MARKER_SIZE`、颜色、阈值线或圆点偏移。需要进一步调整标题、图例、坐标范围和注释时，再修改 `build_figure()`。

## 运行方法

进入本文件夹：

```bash
cd 26比赛/解题/问题3_求解结果/code/figure_scripts
```

例如单独运行图01：

```bash
python3 fig01_main_strategy_temperatures.py
```

默认会同时：

1. 更新对应的矢量 PDF、可编辑 SVG 和 300 dpi PNG；
2. 打开 Matplotlib 交互窗口查看图片。

关闭交互窗口后程序结束。

## 只预览、不覆盖图片

```bash
python3 fig01_main_strategy_temperatures.py --no-save
```

## 只导出、不显示窗口

```bash
python3 fig01_main_strategy_temperatures.py --no-show
```

## 输出文件

每个脚本使用对应的中文作用名称输出三种格式。例如图01会生成：

```text
figures/01_主策略温度历程.pdf
figures/01_主策略温度历程.svg
figures/01_主策略温度历程.png
```

## 必须保留的文件

请保留：

- `fig01_*.py` 至 `fig06_*.py`；
- `common.py`；
- 上两级 `data/` 文件夹中的相关 CSV。

原批量绘图脚本 `26比赛/画图代码/问题3/plot_q3.py` 建议保留用于追溯原始流程。逐图修改时只运行本文件夹中的对应脚本。

## 图03论文版（2026-09-27）

图03采用2×2布局：P纯预热无载电压、C协同加热最低电压、C的MEA平均冰体积分数、C的端部孔隙冰饱和度。删除解释性文本框、曲线重合说明和图内脚注，仅保留坐标轴、图例及子图标题。

P纯预热窗口电流为零，孔隙冰饱和度为零，MEA平均冰体积分数最大约4.24×10⁻²⁰，因此省略P的两个近零冰量面板。该事实可在论文正文或图注说明。图中仍不含P关热后的加载阶段；平均冰体积分数与局部孔隙冰饱和度分母不同。原CSV和模型结果不修改。

图03密集实心圆点取消白边，防止白边相互遮盖导致颜色发白；不添加连接线。运行 `python3 fig03_voltage_and_icing.py --no-show` 即覆盖原PNG、PDF、SVG。
