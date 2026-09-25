function fig = plot_09_freezing_identifiability()
% 图09：冻结系数 k_f 的剖面与参数可辨识性。
% 横轴和右列纵轴使用对数坐标；非正冰量不参与对数绘制。

    cfg = q1_config();
    figureHeightCm = 12.7;
    d = q1_read_table(cfg, '冻结系数剖面.csv');
    models = ["main","bp"];
    modelNames = ["五层基线","含双极板修订"];
    conditions = ["minus20","minus25"];
    condNames = ["−20 ℃：校准工况","−25 ℃：留出工况"];
    condColors = {cfg.color.main, cfg.color.bp};
    condStyles = {'-','--'};

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    for row = 1:2
        for col = 1:2
            ax = nexttile(tl, (row-1)*2+col); hold(ax, 'on');
            for c = 1:2
                keep = string(d.model)==models(row) & string(d.condition)==conditions(c);
                s = sortrows(d(keep,:), 'kf_s_inv');
                if col == 1
                    y = s.mean_squared_relative_objective;
                else
                    y = s.ice_at35_bulk; y(y<=0) = NaN;
                end
                h(c) = plot(ax, s.kf_s_inv, y, 'o', 'LineStyle', condStyles{c}, ...
                    'Color', condColors{c}, 'MarkerFaceColor', condColors{c}, ...
                    'MarkerSize', 3.7, 'LineWidth', cfg.lineWidth); %#ok<AGROW>
            end
            xline(ax, 1, ':', 'Color', [0.52 0.52 0.52], 'LineWidth', 0.8);
            set(ax, 'XScale', 'log');
            if col == 2, set(ax, 'YScale', 'log'); end
            ax.FontName = cfg.fontName; ax.FontSize = cfg.fontSize;
            ax.Box = 'off'; ax.TickDir = 'out'; grid(ax, 'on');
            xlabel(ax, '冻结系数 k_f / s^{-1}');
            if col == 1, ylabel(ax, '平均平方相对误差目标');
            else, ylabel(ax, '35 s 最大冰体积分数'); end
            title(ax, modelNames(row), 'FontWeight', 'normal', 'HorizontalAlignment', 'left');
            text(ax, -0.12, 1.04, sprintf('(%c)', 'a'+(row-1)*2+col-1), ...
                'Units','normalized','FontWeight','bold','FontName',cfg.fontName);
        end
    end
    hBase = plot(nan, nan, ':', 'Color', [0.52 0.52 0.52], 'LineWidth', 0.8);
    lgd = legend([h hBase], {condNames(1),condNames(2),'固定基准 k_f=1'}, ...
        'Orientation','horizontal');
    lgd.Layout.Tile = 'north';
    set(lgd,'Box','off','FontName',cfg.fontName,'FontSize',cfg.fontSize);
    q1_export_figure(fig, cfg, "09_freezing_identifiability");
end
