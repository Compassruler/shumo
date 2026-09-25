function fig = plot_10_phase_coefficient_sensitivity()
% 图10：六个相变系数的一次一因子敏感性矩阵。
% 单元格数字是实际变化；颜色只用于在四个面板之间比较相对强弱。

    cfg = q1_config();
    figureHeightCm = 13.2;
    d = q1_read_table(cfg, '参数与闭合敏感性.csv');
    parameters = ["kf","km","kcond","kevap","kdep","ksub"];
    parameterLabels = ["冻结 · kf","融化 · km","凝结 · kcond", ...
                       "蒸发 · kevap","凝华 · kdep","升华 · ksub"];
    cases = ["main","minus20"; "main","minus25"; "bp","minus20"; "bp","minus25"];
    titles = ["五层基线 · −20 ℃","五层基线 · −25 ℃", ...
              "含双极板修订 · −20 ℃","含双极板修订 · −25 ℃"];
    metricNames = {'max_delta_V_V','max_delta_T_C','delta_ice_at35'};
    multipliers = [1e3 1 100];
    xLabels = {'max |ΔV| / mV','max |ΔT| / ℃','|Δ冰_{35s}| / 百分点'};

    matrices = cell(1,4);
    for k = 1:4
        base = string(d.model)==cases(k,1) & string(d.condition)==cases(k,2) & ...
               string(d.kind)=="phase_one_at_a_time";
        a = zeros(6,3);
        for i = 1:6
            rows = d(base & string(d.parameter)==parameters(i),:);
            for j = 1:3
                a(i,j) = max(abs(rows.(metricNames{j})),[],'omitnan') * multipliers(j);
            end
        end
        matrices{k} = a;
    end
    stack = cat(3, matrices{:});
    % 固定整理成 1×3 行向量，避免不同 MATLAB 版本 squeeze 方向不同。
    commonMax = reshape(max(stack,[],[1 3]), 1, 3);
    commonMax(commonMax<=0) = eps;

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');
    [~, iceMap] = q1_colormaps(256);
    for k = 1:4
        ax = nexttile(tl,k); a = matrices{k}; z = a ./ commonMax;
        imagesc(ax, 1:3, 1:6, z); colormap(ax, iceMap); clim(ax,[0 1]);
        set(ax,'YDir','normal','XTick',1:3,'XTickLabel',xLabels, ...
            'YTick',1:6,'YTickLabel',parameterLabels,'FontName',cfg.fontName, ...
            'FontSize',8,'TickLength',[0 0],'Box','off');
        title(ax,titles(k),'FontWeight','normal','HorizontalAlignment','left');
        text(ax,-0.16,1.04,sprintf('(%c)','a'+k-1),'Units','normalized', ...
            'FontWeight','bold','FontName',cfg.fontName,'FontSize',cfg.labelFontSize);
        for i = 1:6
            for j = 1:3
                if a(i,j)==0, txt='0'; elseif a(i,j)>=1e-3, txt=sprintf('%.3g',a(i,j));
                else, txt=sprintf('%.1e',a(i,j)); end
                color = [0.12 0.14 0.17]; if z(i,j)>0.65, color=[1 1 1]; end
                text(ax,j,i,txt,'HorizontalAlignment','center','Color',color, ...
                    'FontName',cfg.fontName,'FontSize',8);
            end
        end
    end
    annotation(fig,'textbox',[0.08 0.005 0.84 0.035], ...
        'String','每项取单独调整至 0.1 倍、10 倍时的较大影响；颜色按各指标共同最大值归一化。', ...
        'EdgeColor','none','HorizontalAlignment','center','FontName',cfg.fontName,'FontSize',8);
    q1_export_figure(fig, cfg, "10_phase_coefficient_sensitivity");
end
