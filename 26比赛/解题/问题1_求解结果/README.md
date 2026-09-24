# 问题1求解结果

已完成0–35 s、0.2 s间隔的两组工况计算（每组176行），并提供代码、算法说明、校准/验证、敏感性与9组图表。

**首先阅读：[计算结果与验证报告](reports/RESULTS_REPORT.md)。**

- [主要工作数据：含双极板修订、两工况352行](data/含双极板修订_两工况352行工作数据.csv)
- [五层原热域对照、两工况352行](data/五层基线_两工况352行工作数据.csv)
- [算法模型与实现说明](reports/算法模型与实现说明.md)
- [数据字段说明](reports/数据字段说明.md)
- [图表目录](figures)

修订模型在−25℃独立验证中的电压平均相对误差约8.09%，温度约0.47%。电压谷仍有系统偏差，冻结系数触及搜索下界，冰量属于尚未被实验验证的条件预测。请同时保留这些结论边界。

## 复现

建议Python 3.12；依赖见code/requirements.txt，运行环境实测版本在data/运行记录与来源哈希.json。inputs包含原始附件副本。可在本文件所在目录执行：

```sh
python -m pip install -r code/requirements.txt
python code/run_question1.py
python code/plot_results.py
python code/build_report.py
```

`python code/run_question1.py --reuse` 复用已保存标定并重算结果与验证；修改物理模型后应去掉`--reuse`重新校准。完整运行约数分钟，取决于机器。当前工作目录已有`.python_deps`供本机运行，其内容不放入交付压缩包。

`data`保留正式全采样CSV、空间场、每5秒表、原始数据审计、标定日志、网格/步长检查、敏感性及来源哈希；`figures`为PNG预览和矢量PDF；`reports`为完整说明。CSV使用UTF-8 BOM，数值是数字而非带单位字符串。
