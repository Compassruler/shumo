function fig = plot_01_main_experiment_comparison()
% 图01：五层基线计算值与实验采样值对比。
% 实验采样值和五层基线均采用实心圆点表示。
%
% 数据来源：
%   data/main_minus20.csv
%   data/main_minus25.csv

    cfg = q1_config();

    %% ================= 可调参数 =================
    figureHeightCm = 12.7;        % 图的实际高度

    markerSizeExp   = 3.8;        % 实验采样值点大小
    markerSizeModel = 3.2;        % 五层基线点大小

    titleFontSize   = 11;         % 子图标题字号
    legendFontSize  = 10.5;       % 图例字号

    % 科研风格低饱和配色
    colorExp   = [0.84, 0.37, 0.30];   % 实验值：砖红
    colorModel = [0.22, 0.49, 0.72];   % 五层基线：深蓝

    %% ================= 读取数据 =================
    d20 = q1_read_table(cfg, 'main_minus20.csv');
    d25 = q1_read_table(cfg, 'main_minus25.csv');

    data = {d20, d25};

    %% ================= 创建图窗 =================
    fig = q1_new_figure(cfg, figureHeightCm);

    tl = tiledlayout(fig, 2, 2, ...
        'TileSpacing', 'compact', ...
        'Padding', 'compact');

    panel = 0;

    %% ================= 绘图 =================
    for row = 1:2
        for col = 1:2

            panel = panel + 1;

            ax = nexttile(tl, panel);
            hold(ax, 'on');

            d = data{col};

            % 根据行选择电压或温度数据
            if row == 1
                yExp   = d.V_exp_V;
                yModel = d.V_model_V;
                yText  = '电压 / V';
            else
                yExp   = d.T_exp_C;
                yModel = d.T_model_C;
                yText  = '温度 / ℃';
            end

            %% -------- 实验采样值 --------
            hExp = plot(ax, ...
                d.t_s, yExp, ...
                'o', ...
                'LineStyle', 'none', ...
                'MarkerSize', markerSizeExp, ...
                'MarkerFaceColor', colorExp, ...
                'MarkerEdgeColor', 'white', ...
                'LineWidth', 0.35);

            %% -------- 五层基线 --------
            hModel = plot(ax, ...
                d.t_s, yModel, ...
                'o', ...
                'LineStyle', 'none', ...
                'MarkerSize', markerSizeModel, ...
                'MarkerFaceColor', colorModel, ...
                'MarkerEdgeColor', 'white', ...
                'LineWidth', 0.35);

            %% -------- 坐标轴样式 --------
            q1_style_axes(ax, cfg, ...
                sprintf('(%c)', 'a' + panel - 1), ...
                sprintf('初始温度 −%d ℃', 15 + 5 * col), ...
                yText);

            %% -------- 子图标题：放大、加粗、居中 --------
            ax.Title.FontSize = titleFontSize;
            ax.Title.FontWeight = 'bold';
            ax.Title.HorizontalAlignment = 'center';

            % 强制标题在当前坐标轴范围中心
            drawnow;
            titlePos = ax.Title.Position;
            titlePos(1) = mean(ax.XLim);
            ax.Title.Position = titlePos;

        end
    end

    %% ================= 图例 =================
    lgd = legend([hExp, hModel], ...
        {'实验采样值', '五层基线'}, ...
        'Orientation', 'horizontal', ...
        'NumColumns', 2);

    lgd.Layout.Tile = 'north';

    set(lgd, ...
        'Box', 'off', ...
        'FontName', cfg.fontName, ...
        'FontSize', legendFontSize);

    %% ================= 导出 =================
    q1_export_figure(fig, cfg, ...
        "01_main_experiment_comparison");

end