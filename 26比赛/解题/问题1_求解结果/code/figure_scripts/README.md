# 问题一：逐图 Python 绘图代码说明

本文件夹用于对问题一的 12 张图进行逐张修改和预览。每个 `figXX_*.py` 文件只负责一张图，直接运行时不会生成其他图片。

绘图数据直接读取上两级 `data/` 文件夹中的 Python 算法输出，图片统一输出到上两级 `figures/` 文件夹。本文件夹全部使用 Python 和 Matplotlib，与 MATLAB 绘图文件夹互不影响。

## 文件说明

| 文件 | 作用 | 主要数据来源 | 常见调整内容 |
|---|---|---|---|
| `fig01_main_experiment_comparison.py` | 图01：五层基线电压、温度计算值与实验采样值对比 | `main_minus20.csv`、`main_minus25.csv` | 实验点颜色、实心圆大小、模型曲线颜色和线宽 |
| `fig02_bp_structural_comparison.py` | 图02：实验值、五层基线和含双极板修订模型对比 | 四个 `main/bp_minus*.csv` | 三类曲线的颜色、点型、线型和图例 |
| `fig03_sample_relative_errors.py` | 图03：电压和温度相对误差 | 四个 `main/bp_minus*.csv` | 误差曲线颜色、零线和纵坐标范围 |
| `fig04_ice_fraction_saturation.py` | 图04：总冰、孔隙冰、膜相冰体积分数和孔隙冰饱和度 | 四个 `main/bp_minus*.csv` | 四条曲线的颜色、线型及右侧纵轴 |
| `fig05_voltage_loss_decomposition.py` | 图05：模型电压和活化、欧姆、浓差损失的堆叠分解 | 四个 `main/bp_minus*.csv` | 堆叠区域颜色、透明度和可逆电压虚线 |
| `fig06_bp_water_energy_balances.py` | 图06：含双极板修订模型的水量、热量收支及守恒残差 | `bp_minus20.csv`、`bp_minus25.csv` | 左右纵轴、残差颜色、两组图例和子图间距 |
| `fig07_main_spacetime_fields.py` | 图07：五层基线温度与结冰时空分布 | `fields_main_minus20.csv`、`fields_main_minus25.csv` | 图尺寸、温度色图和冰含量色图 |
| `fig08_bp_spacetime_fields.py` | 图08：含双极板修订模型的温度与结冰时空分布 | `fields_bp_minus20.csv`、`fields_bp_minus25.csv` | 图尺寸、色图和色条；冰图只显示 MEA 区域 |
| `fig09_freezing_identifiability.py` | 图09：冻结系数剖面和参数可辨识性 | `冻结系数剖面.csv` | 点大小、对数坐标、参考线位置和线型 |
| `fig10_phase_coefficient_sensitivity.py` | 图10：六个相变系数的一次一因子敏感性矩阵 | `参数与闭合敏感性.csv` | 色图、单元格数字字号和子图间距 |
| `fig11_phase_cumulative_amounts.py` | 图11：六个相变通道的累计转化水量 | 四个 `main/bp_minus*.csv` | 各工况颜色、线型、纵坐标范围和图例 |
| `fig12_near_optimal_ice_scenarios.py` | 图12：近优冻结情景范围与 `k_f=1` 参考曲线 | `近优冻结情景范围_非置信区间.csv`、`冻结系数情景全时序.csv` | 阴影颜色、透明度和参考曲线样式 |
| `common.py` | 所有单图脚本共用的基础功能 | 不单独绘图 | 中文字体、全局配色、CSV读取、子图编号、图片导出和交互显示；不能删除 |
| `field_figure.py` | 图07和图08共用的时空网格绘制功能 | 四个 `fields_*.csv` | 网格重构、材料层界面和共享色标；图07和图08需要它，不能删除 |

## 推荐修改方法

每个单图文件开头都有：

```python
# ===== 常用调节区 =====
```

优先在这个区域修改尺寸、颜色、点大小、线宽或色图。例如图01：

```python
FIGSIZE = (7.1, 5.0)          # 图宽和图高，单位为英寸
EXPERIMENT_COLOR = '#C44E52' # 实验采样点颜色
MARKER_SIZE = 3.0            # 实心圆大小
MODEL_COLOR = COLORS['main'] # 模型曲线颜色
MODEL_LINEWIDTH = 1.65       # 模型曲线线宽
```

如果需要修改坐标轴、标题、图例位置或特殊标注，可以继续修改该文件中的 `build_figure()` 函数。

## 运行方法

建议先进入本文件夹：

```bash
cd 26比赛/解题/问题1_求解结果/code/figure_scripts
```

以图01为例，直接运行：

```bash
python fig01_main_experiment_comparison.py
```

默认会同时：

1. 更新对应的 PDF、SVG 和 300 dpi PNG；
2. 打开 Matplotlib 交互窗口查看图片。

交互窗口支持平移、框选缩放、恢复视图和另存为。关闭窗口后程序结束。

## 只预览、不覆盖图片

调试过程中推荐使用：

```bash
python fig01_main_experiment_comparison.py --no-save
```

这样会打开交互窗口，但不会覆盖 `figures/` 中已有的图片。确认效果后，再去掉 `--no-save` 正式导出。

## 只导出、不打开窗口

```bash
python fig01_main_experiment_comparison.py --no-show
```

该模式适合自动运行或只需要更新论文图片时使用。

## 输出格式

每次正式运行会输出三种格式：

- `PDF`：论文中优先使用的矢量图；
- `SVG`：备用矢量格式；
- `PNG`：300 dpi 预览图。

例如运行图01后会更新：

```text
figures/01_main_experiment_comparison.pdf
figures/01_main_experiment_comparison.svg
figures/01_main_experiment_comparison.png
```

## 哪些文件不能删除

如果需要保留全部 12 张图的逐图绘制能力，请保留：

- 全部 `fig01_*.py` 至 `fig12_*.py`；
- `common.py`；
- `field_figure.py`；
- 上两级 `data/` 中的 CSV 文件。

其中 `common.py` 被所有图片调用，`field_figure.py` 被图07和图08调用。删除后相应脚本将无法运行。

## 离散数据的圆点设置

所有从 CSV 逐时刻或逐参数读取的离散序列统一调用 `common.py` 中的 `discrete_points()`，样式完全以图01为准：实心圆、无连接线、细白边。图01实验点大小为 2.5，模型及其他计算点默认大小为 2.0。

```python
DISCRETE_MARKER_SIZE = 2.0
```

修改 `DISCRETE_MARKER_SIZE` 会统一改变未单独指定大小的离散计算点。时空分布图、敏感性矩阵、堆叠面积和情景范围阴影不属于点序列，保持原有表达。
