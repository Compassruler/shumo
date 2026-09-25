function fig = plot_02_bp_structural_comparison()
% 图02：五层基线、含双极板修订模型与实验值的结构对比。
% 可调参数集中在本函数开头；改变图窗尺寸不会改变数据。

    cfg = q1_config();
    figureHeightCm = 12.7;
    markerSize = 3.6;
    main20 = q1_read_table(cfg, 'main_minus20.csv');
    main25 = q1_read_table(cfg, 'main_minus25.csv');
    bp20 = q1_read_table(cfg, 'bp_minus20.csv');
    bp25 = q1_read_table(cfg, 'bp_minus25.csv');
    mainData = {main20, main25}; bpData = {bp20, bp25};

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    panel = 0;
    for row = 1:2
        for col = 1:2
            panel = panel + 1;
            ax = nexttile(tl, panel); hold(ax, 'on');
            dm = mainData{col}; db = bpData{col};
            if row == 1
                yExp = dm.V_exp_V; yMain = dm.V_model_V; yBp = db.V_model_V; label = '电压 / V';
            else
                yExp = dm.T_exp_C; yMain = dm.T_model_C; yBp = db.T_model_C; label = '温度 / ℃';
            end
            hExp = plot(ax, dm.t_s, yExp, 'o', 'LineStyle', 'none', ...
                'MarkerSize', markerSize, 'MarkerFaceColor', 'white', ...
                'MarkerEdgeColor', [0.12 0.13 0.14], 'LineWidth', 0.7);
            hMain = plot(ax, dm.t_s, yMain, '-', 'Color', cfg.color.main, 'LineWidth', cfg.lineWidth);
            hBp = plot(ax, db.t_s, yBp, '--', 'Color', cfg.color.bp, 'LineWidth', cfg.lineWidth);
            q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + panel - 1), ...
                sprintf('初始温度 −%d ℃', 15 + 5*col), label);
        end
    end
    lgd = legend([hExp hMain hBp], {'实验采样值', '五层基线', '含双极板修订'}, ...
        'Orientation', 'horizontal');
    lgd.Layout.Tile = 'north';
    set(lgd, 'Box', 'off', 'FontName', cfg.fontName, 'FontSize', cfg.fontSize);
    q1_export_figure(fig, cfg, "02_bp_structural_comparison");
end
