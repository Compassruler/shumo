# 问题2求解交付

已完成第二问两小问。主结果：−10 ℃下0.5 A/cm²恒流约16.40 s成功，电荷8.1978 C/cm²；最低初温约-16.4 ℃，端部1和5在更冷时因电荷耗尽仍未过0 ℃而失败。

- [完整结果报告](reports/问题2_结果报告.md)
- [表3 CSV](data/表3_不同策略最优启动结果.csv)
- [第二小问初温区间 CSV](data/第二小问_最低初温区间.csv)
- [第二小问成功与失败工况 CSV](data/第二小问_临界与更冷工况.csv)
- [算法模型与代码说明](reports/算法模型与代码说明.md)
- [MD推导核验](reports/MD推导核验.md)
- [图表目录](figures)
- [工作数据字段说明](reports/数据字段说明.md)

线性升载主表a=2.5只是在tp≥0.2 s的有限范围内最优；原题未设斜率上限，其数值极限趋近恒流。阶梯最优三档相等，不能预先要求三种曲线一定不同。

## 复现

Python 3.12。首次安装后运行，建议在本结果文件夹中执行：

```powershell
python -m pip install -r code/requirements.txt
python code/run_question2.py
python code/finalize_results.py
python code/verify_model.py
python code/verify_exports.py
python code/plot_results.py
python code/build_report.py
```

`run_question2.py --reuse-search`仅跳过随机搜索，不能作为新增优化证据；完整复现请不加该选项。Numba首次运行需要编译，后续会复用本地缓存。`source_audit.py`和`inspect_sources.py`用于本机原始来源整理，常规复现无需重跑；输入原件已经保存于inputs。

正式数据为232空间单元/片、Δt=0.003125 s，另用464单元/片、Δt=0.0015625 s核验。CSV使用UTF-8 BOM，便于Excel打开。figures提供PNG、SVG和PDF，后两者为可缩放矢量图。实际运行平台及依赖版本记录于data/run_metadata.json。优化历史与主数据可追溯；没有外部试验直接验证本题预测的冰量和临界温度。
