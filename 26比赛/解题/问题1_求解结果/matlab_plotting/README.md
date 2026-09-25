# 问题一 MATLAB 绘图工程

本文件夹只负责绘图，不重新计算模型。所有脚本直接读取上一级 `data/` 中由 Python 算法输出的 CSV，因此 Python 重算后再次运行 MATLAB 即可得到同步更新的图。

## 使用方法

1. 在 MATLAB 中把当前文件夹切换到本目录。
2. 单独运行某张图：例如在命令窗口输入 `plot_01_main_experiment_comparison`。
3. 一次生成全部图片：运行 `run_all_figures`。
4. 输出位于 `figures/`：
   - `.fig`：MATLAB 可编辑文件，可修改坐标范围、图窗尺寸、线条、文字和图例；
   - `.pdf`、`.svg`：论文使用的矢量图；
   - `.png`：300 dpi 预览图。

## 调整大小

统一尺寸、字体、颜色在 `q1_config.m` 中修改。每张图调用 `q1_new_figure(cfg, 高度)`，其中宽度由 `cfg.figureWidthCm` 控制，高度在对应绘图文件开头设置。修改尺寸后重新运行，坐标轴和刻度会由 MATLAB 自动重新排布。

每张绘图文件均有“可调参数”注释。数据列名和物理单位保持与 Python 输出一致，不在 MATLAB 中拟合或平滑。
