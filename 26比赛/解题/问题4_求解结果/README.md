# 问题四修订求解结果

首选打开 **问题四_完整求解报告.html**；同名Markdown包含完整结果表。主表4采用 `guarded` 推荐动态与固定问题三功率按相同测量保持规则比较。名义 `dynamic`、重优化恒功率、理想首次口径和所有失败试验独立保留。

## 文件

- `code/`：完整可复算代码。
- `data/`：全部工作CSV、19点预冷扫描、搜索候选、轨迹、收敛、物理扰动、名义与推荐独立噪声验证。
- `figures/`：16张科研图，300 dpi PNG和SVG；图数据源见 `figure_manifest.csv`。
- `inputs/`：输入及来源快照；`audit/`：逻辑和独立验证记录。

## 复算

```powershell
python -m pip install --target .python_deps -r requirements.txt
./run_all.ps1
```

默认使用冻结控制参数重算；`./run_all.ps1 -Reoptimize`重新搜索。运行环境记录在 `data/run_environment.csv`。仅重画图与重建报告可分别运行 `python code/plot_results.py`、`python code/build_report.py`。

## 结果口径

真实首次达标仅作评价；测量温度裕度、电压和独立观测冰量连续满足2 s后实际关热，并锁存功率为0。主能耗统计至实际关热；`first_success_energy_J`为首次真实达标能耗。`constant_first`及19点扫描沿用理想首次口径。关热后60 s观察单独报告；并非所有启动成功方案都能持续暖态。

轨迹第n行功率属于结束于该时刻的区间，能耗按 `25*sum(q_n*(t_n-t_(n-1)))`求和。失败组能耗是已花费的电能，不纳入成功节能均值。有限搜索、有限随机种子与模型内验证均不构成全局最优或任意扰动安全证明。
