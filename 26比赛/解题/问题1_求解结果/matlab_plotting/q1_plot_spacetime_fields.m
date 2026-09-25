function fig = q1_plot_spacetime_fields(model)
%Q1_PLOT_SPACETIME_FIELDS 图07/08共用的时空场绘图函数。
% model 取 "main" 或 "bp"。每个彩色单元对应 Python 输出的原始时空网格，
% 不做插值；白色虚线是材料层界面。

    cfg = q1_config();
    figureHeightCm = 13.0;
    d20 = q1_read_table(cfg, sprintf('fields_%s_minus20.csv', model));
    d25 = q1_read_table(cfg, sprintf('fields_%s_minus25.csv', model));
    allData = {d20, d25};
    tempLimits = [min([d20.T_C; d25.T_C]) max([d20.T_C; d25.T_C])];
    iceLimits = [0 max([d20.ice_bulk; d25.ice_bulk])];
    if iceLimits(2) <= 0, iceLimits(2) = 1e-6; end
    [tempMap, iceMap] = q1_colormaps(256);

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');
    panel = 0;
    for row = 1:2
        for col = 1:2
            panel = panel + 1;
            d = allData{col};
            variable = 'T_C';
            if row == 2, variable = 'ice_bulk'; end
            % 双极板模型的冰图只显示 MEA，温度图仍显示完整结构。
            if model == "bp" && row == 2
                keep = string(d.layer) ~= "aBP" & string(d.layer) ~= "cBP";
                d = d(keep, :);
            end
            [~, ~, z, layers, tEdges, xEdges] = makeFieldGrid(d, variable);
            ax = nexttile(tl, panel); hold(ax, 'on');
            zPad = [z z(:,end); z(end,:) z(end,end)];
            h = pcolor(ax, tEdges, xEdges, zPad);
            h.EdgeColor = 'none'; h.FaceColor = 'flat';
            if row == 1
                colormap(ax, tempMap); clim(ax, tempLimits); cbText = '局部温度 / ℃';
            else
                colormap(ax, iceMap); clim(ax, iceLimits); cbText = '局部总冰体积分数';
            end
            addLayerLines(ax, xEdges, layers);
            yText = '厚度方向位置 / μm';
            if model == "bp" && row == 2, yText = 'MEA 位置 / μm'; end
            q1_style_axes(ax, cfg, sprintf('(%c)', 'a' + panel - 1), ...
                sprintf('初始温度 −%d ℃', 15 + 5*col), yText);
            grid(ax, 'off');
            cb = colorbar(ax); cb.Label.String = cbText;
            cb.FontName = cfg.fontName; cb.FontSize = cfg.fontSize;
        end
    end
    if model == "main"
        stem = "07_main_spacetime_fields";
    else
        stem = "08_bp_spacetime_fields";
    end
    q1_export_figure(fig, cfg, stem);
end

function [times, x, z, layers, tEdges, xEdges] = makeFieldGrid(d, variable)
% 将长表转换为“空间×时间”矩阵，并按有限体积单元宽度恢复边界。
    times = unique(d.t_s, 'sorted');
    x = unique(d.x_um, 'sorted');
    z = nan(numel(x), numel(times));
    for k = 1:height(d)
        ix = find(x == d.x_um(k), 1); it = find(times == d.t_s(k), 1);
        z(ix,it) = d.(variable)(k);
    end
    assert(all(isfinite(z), 'all'), '时空场存在缺失或非有限值。');
    first = d(d.t_s == min(d.t_s), :);
    [~, order] = sort(first.x_um); first = first(order,:);
    layers = string(first.layer);
    dx = first.dx_um;
    xEdges = [x(1)-dx(1)/2; x+dx/2];
    tEdges = [times(1)-(times(2)-times(1))/2; ...
              (times(1:end-1)+times(2:end))/2; ...
              times(end)+(times(end)-times(end-1))/2];
end

function addLayerLines(ax, xEdges, layers)
% 在材料名称变化处画层界面，不改变任何数据。
    changes = find(layers(1:end-1) ~= layers(2:end));
    for k = reshape(changes, 1, [])
        yline(ax, xEdges(k+1), '--', 'Color', [1 1 1], 'LineWidth', 0.65);
    end
end
