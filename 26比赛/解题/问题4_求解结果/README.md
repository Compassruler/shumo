# 问题四完整数值求解

首选打开 **问题四_完整求解报告.html**。Markdown版同名保存，包含完整结果表。

## 目录

- `code/`：可复算Python源代码；`run_problem4.py`是主入口。
- `data/`：全部UTF-8 BOM工作CSV，包括9组主结果、19点扫描、优化候选、完整轨迹、守恒、加密、敏感性与90次扰动试验。
- `figures/`：13张科研图，均有300 dpi PNG与SVG；`figure_manifest.csv`记录数据来源。
- `inputs/`：本次使用的输入快照；`audit/`：方程与口径审计说明。

## 环境与复算

本机使用Python 3.12及固定版本NumPy、SciPy、Numba、pandas、Matplotlib。所附requirements.txt用于重建环境；本机局部依赖位于.python_deps。可直接运行run_all.ps1复算冻结参数与全部检验，添加-Reoptimize则重新搜索控制参数。跨机器运行前请用匹配Python版本安装依赖：

```powershell
python -m pip install --target .python_deps -r requirements.txt
./run_all.ps1
```

该入口默认用已保存控制参数复算全部数值、验证、表格、图和报告。需要重新进行参数搜索时，使用 `./run_all.ps1 -Reoptimize`。图表和报告可分别通过 `python code/plot_results.py`、`python code/build_report.py`重建。

本次执行环境由 `data/run_environment.csv`记录。`.python_deps/`为本次机器上的局部依赖目录（若存在）；Python脚本通过 `bootstrap.py`加载。若存在`requirements.txt`或环境锁文件，请优先按其固定版本安装。完整重优化耗时明显长于重画图；固定随机种子和环境用于复现搜索过程。

已有优化参数时，可执行：

```powershell
python code/run_problem4.py --reuse-controls --skip-precool
python code/plot_results.py
python code/build_report.py
```

## 统计口径

主比较是 `dynamic` 与 `constant_hold`：均在首次全片达标后连续保持2 s再关热；`constant_first`为问题三首次达标参考。第(2)问19点扫描沿用首次达标口径。关热后60 s验证单独列示。

轨迹功率列描述结束于该行时刻的前一积分区间，独立能耗必须用 `25*sum(q_n*(t_n-t_(n-1)))`复算，不用梯形积分。温度单位℃、时间s、单片加热功率密度W/cm²、电流密度A/cm²、能量J；最大温差为同一时刻五片极差的过程最大值。

本解是给定参数化反馈类与有限搜索预算内找到的可行优选解，不提供全局最优证明。两阶段物性与对流位置继承近似、有限扰动范围和关热后验证结论均在报告中明确说明。完整工作精度见CSV，报告显示精度不用于后续复算。
