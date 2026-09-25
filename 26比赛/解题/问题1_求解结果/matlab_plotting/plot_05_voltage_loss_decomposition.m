function fig = plot_05_voltage_loss_decomposition()
% 图05：模型电压与活化、欧姆、浓差损失的堆叠分解。
% area 的四列依次为模型电压和三类损失；可逆电压以黑色虚线表示。

    cfg = q1_config();
    figureHeightCm = 12.7;
    files = {'main_minus20.csv','main_minus25.csv','bp_minus20.csv','bp_minus25.csv'};
    titles = {'五层基线 · −20 ℃','五层基线 · −25 ℃', ...
              '含双极板修订 · −20 ℃','含双极板修订 · −25 ℃'};
    areaColors = {[0.86 0.90 0.93], cfg.color.activation, ...
                  cfg.color.ohmic, cfg.color.concentration};
    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

    for k = 1:4
        d = q1_read_table(cfg, files{k});
        ax = nexttile(tl, k); hold(ax, 'on');
        hArea = area(ax, d.t_s, [d.V_model_V d.eta_act_V d.eta_ohm_V d.eta_con_V], ...
            'LineStyle', 'none');
        for j = 1:4
            hArea(j).FaceColor = areaColors{j};
            hArea(j).FaceAlpha = 0.88;
        end
        plot(ax, d.t_s, d.V_model_V, '-', 'Color', cfg.color.main, 'LineWidth', 1.0);
        hRev = plot(ax, d.t_s, d.E_rev_V, '--', 'Color', [0.15 0.16 0.20], 'LineWidth', 1.1);
        q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + k - 1), titles{k}, '电压及损失 / V');
        yl = ylim(ax); ylim(ax, [0 max(yl(2), eps)]);
    end
    lgd = legend([hArea(:); hRev], {'模型电压','活化损失','欧姆损失','浓差损失','可逆电压'}, ...
        'Orientation', 'horizontal', 'NumColumns', 5);
    lgd.Layout.Tile = 'north';
    set(lgd, 'Box', 'off', 'FontName', cfg.fontName, 'FontSize', 7.6);
    q1_export_figure(fig, cfg, "05_voltage_loss_decomposition");
end
