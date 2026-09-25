# 问题3：辅助冷启动求解结果

本目录依据《问题3_建模推导源文件.md》及当前问题二共享双极板模型，计算−30 ℃、五片电堆的恒定辅助加热。全部数值为模型仿真结果，不是新增实验测量。

## 先看这些文件

- `reports/问题三结果与分析.md`：第三问两小问的结果、题表4、比较及必要的口径说明。
- `reports/模型与算法.md`：七节点方程、控制变量、单位换算、约束与原MD修正。
- `data/表4_问题三主结果.csv`：题面要求的两种策略结果。
- `data/summary_results.csv`：未过度舍入的主结果及额外稳健预热方案。
- `data/postload_verification.csv`：达到首次启动后继续加载的检查，不将检查终点冒充启动时间。
- `figures/`：论文用矢量 PDF、可编辑 SVG 及 300 dpi PNG 预览图。

## 策略和数据口径

P为题面纯预热：电流为零直至全部电池首次超过0 ℃，随后关热并开始加载。C为恒功率协同：从0时刻加载规定斜坡并同步加热。R是附加稳健预热：延长预热，要求关热后按同一斜坡加载96.6667 s，电池始终不回落至0 ℃以下；R不属于题面两策略主表。

主表中的P冰量和最低电压仅统计预热启动区间，不能视为加载后的表现。P之后的电流曲线题面没有唯一指定；本计算遵循MD，将C的斜坡平移，用作可复现的后验检查。C也另做关热后的继续加载验证。

热容使用六处物理双极板版本，端片分配1.5块板，中间片1块。端板不要求达到0 ℃。冰体积分数包含MEA内的膜冰；孔隙冰饱和度另列，不能混用。

## 代码位置与复算

数值代码位于 `code/`。逐图绘图代码位于 `code/figure_scripts/`，每张图均可独立运行；原批量绘图源码 `../../画图代码/问题3/plot_q3.py` 保留用于追溯。

依赖：Python 3.12、NumPy、SciPy、Numba、Matplotlib。代码优先使用既有问题二的`.python_deps`，不存在时也可使用正常Python环境安装的相同库。共享内核`fast_cell.py`已复制固化，未修改问题一或问题二源代码。

从本目录执行以下命令，或将路径补全后从其他目录执行：

```powershell
python code/preheat_linear.py
python code/optimize_aux.py P
python code/cooperative_search.py
python code/optimize_aux.py R
python code/export_results.py
python code/validate_model.py
python3 code/figure_scripts/fig01_main_strategy_temperatures.py
```

首次运行会编译数值内核，需要等待。完整优化需数分钟到更久，取决于电脑配置。`export_results.py`利用已搜索并验证的活跃功率模式做细网格校正；若改变物性、初温或边界，必须先重新全变量优化，不能只改导出脚本后沿用本题功率模式。

协同搜索采用`(功率,启动时刻,加热时长/启动时刻)`参数化，避免独立截止时间在`th=ts`边界的单侧差分问题。保留多种初值和随机种子，并检查较慢的低功率局部解。最终结果是当前策略类内找到的最优可行方案，不提供数学全局最优证书。

## CSV工作数据

- `trajectory_P/C.csv`：首次启动的内部时间步轨迹。
- `trajectory_P_postload/C_postload.csv`：关热后继续加载的完整连续轨迹。
- `trajectory_R.csv`：延长预热及加载验证轨迹。
- `final_fields_P/C/R.csv`：各片MEA网格上的水、冰库存及位置。
- `optimization_search_P/R.csv`、`cooperative_search.csv`：参数搜索与约束余量。
- `cooperative_multistart.csv`、`preheat_linear_scan.csv`、`fine_center_power_search.csv`：不同初值、线性筛选及细网格中心功率搜索。
- `convergence.csv`：固定最终参数的网格/时间步加密。
- `model_validation.csv`：与问题二回归、镜像、单位、守恒检验。
- `sensitivity.csv`：固定功率分配、重算达到首次成功所需加热时长的敏感性，不是每个扰动都重新优化。
- `energy_budget.csv`：辅助、电化学、相变、对流及显热收支。
- `source_manifest.csv`与`inputs/`：模型来源快照与SHA-256记录。

CSV采用UTF-8 BOM，表头含单位；保留数字精度供复算，报告中适度舍入。`heater_on`表示该行终点之前时间步的加热状态，开关瞬间可结合功率向量与`th_s`确定左右极限。热平衡残差验证的是所实现的离散方程，不等于已完成新工况实验验证。
