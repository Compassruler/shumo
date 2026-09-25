function fig = plot_11_phase_cumulative_amounts()
% 图11：凝结、蒸发、凝华、升华、冻结、融化六通道的累计转化水量。
% 各面板纵轴独立；全零通道明确标注“本窗口内未激活”。

    cfg = q1_config();
    figureHeightCm = 12.2;
    files = {'main_minus20.csv','main_minus25.csv','bp_minus20.csv','bp_minus25.csv'};
    data = cellfun(@(f) q1_read_table(cfg,f), files, 'UniformOutput', false);
    phaseKeys = {'cond','evap','dep','sub','frz','mlt'};
    phaseNames = {'凝结','蒸发','凝华','升华','冻结','融化'};
    caseNames = {'五层基线 · −20 ℃','五层基线 · −25 ℃', ...
                 '含双极板修订 · −20 ℃','含双极板修订 · −25 ℃'};
    colors = {cfg.color.main,cfg.color.main,cfg.color.bp,cfg.color.bp};
    styles = {'-','--','-','--'};

    fig = q1_new_figure(cfg, figureHeightCm);
    tl = tiledlayout(fig,2,3,'TileSpacing','compact','Padding','compact');
    for p = 1:6
        ax = nexttile(tl,p); hold(ax,'on'); peak = 0;
        for k = 1:4
            column = ['phase_' phaseKeys{p} '_kg_m2'];
            amount = data{k}.(column)*1e3;
            peak = max(peak,max(amount));
            h(k) = plot(ax,data{k}.t_s,amount,'LineStyle',styles{k}, ...
                'Color',colors{k},'LineWidth',cfg.lineWidth); %#ok<AGROW>
        end
        q1_style_axes(ax,cfg,sprintf('(%c)','a'+p-1),phaseNames{p}, ...
            '累计转化水量 / (g/m²)');
        if peak<=0
            ylim(ax,[-0.05 1]); grid(ax,'off');
            text(ax,0.5,0.52,'本窗口内未激活','Units','normalized', ...
                'HorizontalAlignment','center','Color',[0.4 0.4 0.4]);
        else
            ylim(ax,[0 peak*1.12]);
        end
    end
    lgd = legend(h,caseNames,'Orientation','horizontal','NumColumns',4);
    lgd.Layout.Tile = 'north';
    set(lgd,'Box','off','FontName',cfg.fontName,'FontSize',7.5);
    q1_export_figure(fig,cfg,"11_phase_cumulative_amounts");
end
