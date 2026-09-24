# 问题1求解结果

0–35 s、每0.2 s输出：两工况各176行；含双极板与五层对照均已计算。所有文件沿用原目录覆盖，无新增备份目录。

**先阅读：[计算结果与验证报告](reports/RESULTS_REPORT.md)。**

- [含双极板主工作数据：352行](data/含双极板修订_两工况352行工作数据.csv)
- [五层结构对照：352行](data/五层基线_两工况352行工作数据.csv)
- [算法模型与实现说明](reports/算法模型与实现说明.md)
- [相变与新增假设清单](reports/非题给参数与新增假设清单.md)
- [完整数据字段说明](reports/数据字段说明.md)
- [12组PNG与矢量PDF图表](figures)

本次六相变系数统一固定为附件权重/假定1 s参考时间，只拟合j₀；补齐升华并分开液水面/冰面饱和蒸气压。−25℃留出验证：电压平均相对误差9.023%，温度平均相对误差0.695%（摄氏口径）。冰量是依赖闭合假设的条件预测，不能因冰量变大就认定更准确。

六系数均做0.1/10倍敏感性，另检验共同时间尺度；冻结剖面只作非唯一性诊断。近优阴影采用校准目标增加不超过5%的离散情景，明确不是置信区间。

## 复现

建议Python 3.12；基本依赖见code/requirements.txt。inputs保留附件及当前源MD副本，环境和来源哈希见data/运行记录与来源哈希.json。在本目录执行：

```sh
python -m pip install -r code/requirements.txt
python code/run_question1.py
python code/plot_results.py
python code/build_report.py
python code/verify_phase_exports.py
python code/build_parameter_inventory.py
python code/build_parameter_source_pdf.py
```

参数清单PDF另外需要reportlab和中文字体，本机环境已具备。`run_question1.py --reuse`只在模型哈希与当前校准相同时复用j₀；改变模型后请重新校准。不要使用`--no-verify`生成最终交付，因为它不更新敏感性、剖面和数值检查。全套计算耗时取决于机器。

正式结果采用网格倍数2、0.0125 s；敏感性采用倍数2、0.025 s；剖面采用倍数1、0.05 s。图内比较使用各自同网格基准，不能把粗细网格数值的末位差误认为参数影响。

`data`：完整CSV、时空场、相变累计量/区间平均速率、参数来源、敏感性、剖面及检查；`figures`：12组图；`reports`：说明。CSV采用UTF-8 BOM，便于Excel直接打开。
