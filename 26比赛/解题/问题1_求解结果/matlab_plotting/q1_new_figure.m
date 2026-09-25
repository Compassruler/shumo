function fig = q1_new_figure(cfg, heightCm)
%Q1_NEW_FIGURE 按论文实际尺寸建立图窗。
% 改变 cfg.figureWidthCm 或 heightCm 后重新运行，坐标轴会自动重排。
    fig = figure('Color', 'w', 'Units', 'centimeters', ...
        'Position', [2 2 cfg.figureWidthCm heightCm], ...
        'PaperPositionMode', 'auto');
end
