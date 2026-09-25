function fig = plot_12_near_optimal_ice_scenarios()
% 图12：近优冻结情景的逐时刻范围与 k_f=1 粗网格参考。
% 阴影是离散情景包络，不是统计置信区间；数据直接读取 Python 输出。

    cfg = q1_config();
    figureHeightCm = 12.7;
    ranges = q1_read_table(cfg,'近优冻结情景范围_非置信区间.csv');
    series = q1_read_table(cfg,'冻结系数情景全时序.csv');
    cases = ["main","minus20"; "main","minus25"; "bp","minus20"; "bp","minus25"];
    titles = ["五层基线 · −20 ℃","五层基线 · −25 ℃", ...
              "含双极板修订 · −20 ℃","含双极板修订 · −25 ℃"];
    fillColor = [0.44 0.62 0.69]; edgeColor = [0.30 0.49 0.57];

    fig = q1_new_figure(cfg,figureHeightCm);
    tl = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');
    for k = 1:4
        keep = string(ranges.model)==cases(k,1) & string(ranges.condition)==cases(k,2);
        r = sortrows(ranges(keep,:),'t_s');
        refKeep = string(series.model)==cases(k,1) & string(series.condition)==cases(k,2) & ...
                  abs(series.kf_s_inv-1)<1e-12;
        ref = sortrows(series(refKeep,:),'t_s');
        ax = nexttile(tl,k); hold(ax,'on');
        xPoly = [r.t_s; flipud(r.t_s)];
        yPoly = [r.ice_max_bulk_min; flipud(r.ice_max_bulk_max)];
        hRange = fill(ax,xPoly,yPoly,fillColor,'FaceAlpha',0.32,'EdgeColor','none');
        plot(ax,r.t_s,r.ice_max_bulk_min,'-','Color',edgeColor,'LineWidth',0.9);
        plot(ax,r.t_s,r.ice_max_bulk_max,'-','Color',edgeColor,'LineWidth',0.9);
        hRef = plot(ax,ref.t_s,ref.ice_max_bulk,'--','Color',cfg.color.bp,'LineWidth',cfg.lineWidth);
        n = r.n_scenarios(1);
        q1_style_axes(ax,cfg,sprintf('(%c)','a'+k-1), ...
            sprintf('%s（%d 个情景）',titles(k),n),'最大冰体积分数');
        yl=ylim(ax); ylim(ax,[0 max(yl(2),eps)]);
    end
    lgd = legend([hRange hRef],{'校准目标≤最小值×1.05 的情景范围','k_f=1 同粗网格参考'}, ...
        'Orientation','horizontal');
    lgd.Layout.Tile = 'north';
    set(lgd,'Box','off','FontName',cfg.fontName,'FontSize',cfg.fontSize);
    q1_export_figure(fig,cfg,"12_near_optimal_ice_scenarios");
end
