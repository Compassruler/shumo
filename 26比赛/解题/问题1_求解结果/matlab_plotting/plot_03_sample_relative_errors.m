function fig = plot_03_sample_relative_errors()
% 图03：两类模型在各实验采样时刻的电压、温度相对误差。
% 温度误差直接读取 Python 已输出的摄氏温度口径列，不在此重复计算。

    cfg = q1_config();
    figureHeightCm = 12.7;
    data.main = {q1_read_table(cfg, 'main_minus20.csv'), q1_read_table(cfg, 'main_minus25.csv')};
    data.bp = {q1_read_table(cfg, 'bp_minus20.csv'), q1_read_table(cfg, 'bp_minus25.csv')};

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    panel = 0;
    for row = 1:2
        for col = 1:2
            panel = panel + 1;
            ax = nexttile(tl, panel); hold(ax, 'on');
            dm = data.main{col}; db = data.bp{col};
            if row == 1
                ym = dm.V_rel_error_pct; yb = db.V_rel_error_pct; label = '电压相对误差 / %';
            else
                ym = dm.T_rel_error_pct; yb = db.T_rel_error_pct; label = '温度相对误差（摄氏口径）/ %';
            end
            hMain = plot(ax, dm.t_s, ym, '-', 'Color', cfg.color.main, 'LineWidth', cfg.lineWidth);
            hBp = plot(ax, db.t_s, yb, '--', 'Color', cfg.color.bp, 'LineWidth', cfg.lineWidth);
            yline(ax, 0, '-', 'Color', [0.55 0.57 0.60], 'LineWidth', 0.7);
            q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + panel - 1), ...
                sprintf('初始温度 −%d ℃', 15 + 5*col), label);
        end
    end
    lgd = legend([hMain hBp], {'五层基线', '含双极板修订'}, ...
        'Orientation', 'horizontal');
    lgd.Layout.Tile = 'north';
    set(lgd, 'Box', 'off', 'FontName', cfg.fontName, 'FontSize', cfg.fontSize);
    q1_export_figure(fig, cfg, "03_sample_relative_errors");
end
