function fig = plot_04_ice_fraction_saturation()
% 图04：总冰、孔隙冰、膜相冰体积分数和孔隙冰饱和度。
% 左轴显示体积分数，右轴显示饱和度；线型保证黑白打印仍可区分。

    cfg = q1_config();
    figureHeightCm = 13.0;
    files = {'main_minus20.csv','main_minus25.csv','bp_minus20.csv','bp_minus25.csv'};
    modelText = {'五层基线','五层基线','含双极板修订','含双极板修订'};
    tempText = {'−20 ℃','−25 ℃','−20 ℃','−25 ℃'};
    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

    for k = 1:4
        d = q1_read_table(cfg, files{k});
        ax = nexttile(tl, k); hold(ax, 'on');
        yyaxis(ax, 'left');
        h1 = plot(ax, d.t_s, d.ice_max_bulk, '-', 'Color', cfg.color.main, 'LineWidth', cfg.lineWidth);
        h2 = plot(ax, d.t_s, d.ice_pore_max_bulk, '--', 'Color', cfg.color.pore, 'LineWidth', cfg.lineWidth);
        h3 = plot(ax, d.t_s, d.ice_mem_max_bulk, ':', 'Color', cfg.color.membrane, 'LineWidth', 1.7);
        ylabel(ax, '冰体积分数');
        ylim(ax, [0 max([d.ice_max_bulk; d.ice_pore_max_bulk; d.ice_mem_max_bulk])*1.12 + eps]);
        yyaxis(ax, 'right');
        h4 = plot(ax, d.t_s, d.s_ice_pore_max, '-.', 'Color', cfg.color.saturation, 'LineWidth', 1.3);
        ylabel(ax, '孔隙冰饱和度');
        ax.YAxis(2).Color = cfg.color.saturation;
        ylim(ax, [0 max(d.s_ice_pore_max)*1.08 + eps]);
        yyaxis(ax, 'left');
        q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + k - 1), ...
            modelText{k} + " · " + tempText{k}, '冰体积分数');
    end
    lgd = legend([h1 h2 h3 h4], {'最大总冰体积分数','最大孔隙冰体积分数', ...
        '最大膜相冰体积分数','最大孔隙冰饱和度（右轴）'}, ...
        'Orientation', 'horizontal', 'NumColumns', 2);
    lgd.Layout.Tile = 'north';
    set(lgd, 'Box', 'off', 'FontName', cfg.fontName, 'FontSize', cfg.fontSize);
    q1_export_figure(fig, cfg, "04_ice_fraction_saturation");
end
