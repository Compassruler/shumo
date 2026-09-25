function fig = plot_06_bp_water_energy_balances()
% 图06：含双极板修订模型的水量、热量收支和守恒残差。
% 左轴是累计量，右轴只显示残差，避免微小残差被主量级淹没。

    cfg = q1_config();
    figureHeightCm = 13.0;
    data = {q1_read_table(cfg, 'bp_minus20.csv'), q1_read_table(cfg, 'bp_minus25.csv')};
    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'loose', 'Padding', 'compact');

    for col = 1:2
        d = data{col};
        % 上排：水收支。储水量减去初始存水量，与 Python 图保持一致。
        ax = nexttile(tl, col); hold(ax, 'on'); yyaxis(ax, 'left');
        hW1 = plot(ax, d.t_s, d.water_produced_kg_m2*1e3, '-', 'Color', cfg.color.main, 'LineWidth', cfg.lineWidth);
        hW2 = plot(ax, d.t_s, (d.water_stored_kg_m2-d.water_initial_kg_m2)*1e3, '--', 'Color', cfg.color.pore, 'LineWidth', cfg.lineWidth);
        hW3 = plot(ax, d.t_s, d.water_out_kg_m2*1e3, '-.', 'Color', cfg.color.bp, 'LineWidth', cfg.lineWidth);
        yyaxis(ax, 'right');
        hWR = plot(ax, d.t_s, d.water_balance_kg_m2*1e3, ':', 'Color', cfg.color.residual, 'LineWidth', 1.0);
        ylabel(ax, '水收支残差 / (g/m²)'); ax.YAxis(2).Color = cfg.color.residual;
        yyaxis(ax, 'left');
        q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + col - 1), ...
            sprintf('含双极板修订 · −%d ℃', 15 + 5*col), '水量 / (g/m²)');

        % 下排：能量收支。累计热量换算为 kJ/m²，残差仍保留 J/m²。
        ax = nexttile(tl, 2 + col); hold(ax, 'on'); yyaxis(ax, 'left');
        hH1 = plot(ax, d.t_s, d.heat_gen_J_m2/1e3, '-', 'Color', cfg.color.main, 'LineWidth', cfg.lineWidth);
        hH2 = plot(ax, d.t_s, d.heat_phase_J_m2/1e3, '--', 'Color', cfg.color.phase, 'LineWidth', cfg.lineWidth);
        hH3 = plot(ax, d.t_s, d.heat_loss_J_m2/1e3, '-.', 'Color', cfg.color.loss, 'LineWidth', cfg.lineWidth);
        yyaxis(ax, 'right');
        hHR = plot(ax, d.t_s, d.energy_balance_J_m2, ':', 'Color', cfg.color.residual, 'LineWidth', 1.0);
        ylabel(ax, '能量收支残差 / (J/m²)'); ax.YAxis(2).Color = cfg.color.residual;
        yyaxis(ax, 'left');
        q1_style_axes(ax, cfg, sprintf('(%c)', 'c' + col - 1), ...
            sprintf('含双极板修订 · −%d ℃', 15 + 5*col), '累计热量 / (kJ/m²)');
    end

    % 两组图例分别挂到左侧面板，便于在 MATLAB 中独立拖动。
    lg1 = legend(tl.Children(end), [hW1 hW2 hW3 hWR], ...
        {'累计产水','储水量变化','累计排水','收支残差（右轴）'}, 'Location', 'best');
    lg2 = legend(tl.Children(2), [hH1 hH2 hH3 hHR], ...
        {'累计产热','累计相变放热','累计散热','收支残差（右轴）'}, 'Location', 'best');
    set([lg1 lg2], 'Box', 'off', 'FontName', cfg.fontName, 'FontSize', 7.3);
    q1_export_figure(fig, cfg, "06_bp_water_energy_balances");
end
