# 问题四逐图绘图入口

本目录提供16张图的独立入口。每个入口只替换对应图的PDF、SVG与PNG；保留现有文件名和报告链接，不重新运行模型或优化。

样式沿用问题三：中文黑体，柔和蓝橙绿配色，离散结果为实心圆、无连接线、细白边；科学阈值线、空间连续温度场及后验观察阴影保留。统一样式在上一级common_style.py，各图绘制逻辑在上一级plot_results.py。

## 使用

- 运行某个figXX脚本：导出并打开交互预览。
- 加 --no-show：仅导出，适用于批处理。
- 加 --no-save：仅预览，不覆盖图片与清单。
- 全部重绘：运行上一级plot_results.py --no-show。

例如：

    python fig07_main_strategy_comparison.py --no-show

输出格式为同名矢量PDF、保留文字的SVG和300 dpi PNG。画布随面板数量安排，字号、标记和边距统一。所有离散采样点保留，不为美化抽样或平滑；失败样本使用红色外圈强调。

## 图目

- fig01_precooling_temperature_fields.py：预冷温度场族
- fig02_precooling_temperature_difference.py：预冷均温与温差
- fig03_initial_temperature_cases.py：三工况初始温度
- fig04_case1_control_trajectories.py：完全冷却工况控制轨迹
- fig05_case2_control_trajectories.py：预冷20分钟控制轨迹
- fig06_case3_control_trajectories.py：预冷40分钟控制轨迹
- fig07_main_strategy_comparison.py：三工况主指标比较
- fig08_precooling_time_scan.py：预冷时间扫描
- fig09_energy_budget.py：能量收支与累积能耗
- fig10_numerical_convergence.py：网格步长与控制周期检验
- fig11_parameter_sensitivity.py：物理参数与控制器敏感性
- fig12_measurement_robustness.py：测量噪声与初场扰动
- fig13_nominal_and_guarded.py：名义与留裕度备选
- fig14_constant_and_dynamic.py：重优化恒功率与推荐动态
- fig15_energy_time_candidates.py：能耗时间候选前沿
- fig16_observer_diagnostics.py：观测器误差与测量停机
