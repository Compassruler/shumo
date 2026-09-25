function figs = plot_01_main_experiment_comparison()
% 图01：五层基线计算值与实验采样值对比。
% 分别绘制 −20 ℃ 和 −25 ℃ 两张图。
%
% 每张图包含：
%   (a) 电压对比
%   (b) 温度对比
%
% 实验采样值和五层基线均采用实心圆点表示。
%
% 数据来源：
%   data/main_minus20.csv
%   data/main_minus25.csv

    cfg = q1_config();

    %% ================= 可调参数 =================
    figureHeightCm = 13.5;        % 每张图的实际高度

    markerSizeExp   = 4.0;        % 实验采样值点大小
    markerSizeModel = 4.0;        % 五层基线点大小

    fontSizeAll = 24;             % 所有文字统一字号

    % 科研风格低饱和配色
    colorExp   = [0.84, 0.37, 0.30];   % 实验值：砖红
    colorModel = [0.22, 0.49, 0.72];   % 五层基线：深蓝

    %% ================= 读取数据 =================
    d20 = q1_read_table(cfg, 'main_minus20.csv');
    d25 = q1_read_table(cfg, 'main_minus25.csv');

    data = {d20, d25};

    % 两个工况对应初始温度
    initialTemps = [-20, -25];

    % 导出文件名
    exportNames = {
        "01_main_experiment_comparison_minus20"
        "01_main_experiment_comparison_minus25"
    };

    %% ================= 创建 Figure 句柄数组 =================
    figs = gobjects(1, 2);

    %% ================= 分别绘制 −20 ℃ 和 −25 ℃ =================
    for k = 1:2

        d = data{k};
        initialTemp = initialTemps(k);

        %% -------- 创建图窗 --------
        figs(k) = q1_new_figure(cfg, figureHeightCm);

        tl = tiledlayout(figs(k), 2, 1, ...
            'TileSpacing', 'compact', ...
            'Padding', 'compact');

        %% =====================================================
        %  (a) 电压
        % ======================================================
        ax1 = nexttile(tl, 1);
        hold(ax1, 'on');

        hExp = plot(ax1, ...
            d.t_s, d.V_exp_V, ...
            'o', ...
            'LineStyle', 'none', ...
            'MarkerSize', markerSizeExp, ...
            'MarkerFaceColor', colorExp, ...
            'MarkerEdgeColor', 'white', ...
            'LineWidth', 0.35);

        hModel = plot(ax1, ...
            d.t_s, d.V_model_V, ...
            'o', ...
            'LineStyle', 'none', ...
            'MarkerSize', markerSizeModel, ...
            'MarkerFaceColor', colorModel, ...
            'MarkerEdgeColor', 'white', ...
            'LineWidth', 0.35);

        q1_style_axes(ax1, cfg, ...
            '(a)', ...
            sprintf('初始温度 −%d ℃', abs(initialTemp)), ...
            '电压 / V');

        %% -------- 所有字号统一为 24 --------
        ax1.FontSize = fontSizeAll;
        ax1.XLabel.FontSize = fontSizeAll;
        ax1.YLabel.FontSize = fontSizeAll;
        ax1.Title.FontSize = fontSizeAll;

        ax1.Title.FontWeight = 'bold';
        ax1.Title.HorizontalAlignment = 'center';

        % 强制标题水平居中
        drawnow;
        titlePos = ax1.Title.Position;
        titlePos(1) = mean(ax1.XLim);
        ax1.Title.Position = titlePos;


        %% =====================================================
        %  (b) 温度
        % ======================================================
        ax2 = nexttile(tl, 2);
        hold(ax2, 'on');

        plot(ax2, ...
            d.t_s, d.T_exp_C, ...
            'o', ...
            'LineStyle', 'none', ...
            'MarkerSize', markerSizeExp, ...
            'MarkerFaceColor', colorExp, ...
            'MarkerEdgeColor', 'white', ...
            'LineWidth', 0.35);

        plot(ax2, ...
            d.t_s, d.T_model_C, ...
            'o', ...
            'LineStyle', 'none', ...
            'MarkerSize', markerSizeModel, ...
            'MarkerFaceColor', colorModel, ...
            'MarkerEdgeColor', 'white', ...
            'LineWidth', 0.35);

        q1_style_axes(ax2, cfg, ...
            '(b)', ...
            sprintf('初始温度 −%d ℃', abs(initialTemp)), ...
            '温度 / ℃');

        %% -------- 所有字号统一为 24 --------
        ax2.FontSize = fontSizeAll;
        ax2.XLabel.FontSize = fontSizeAll;
        ax2.YLabel.FontSize = fontSizeAll;
        ax2.Title.FontSize = fontSizeAll;

        ax2.Title.FontWeight = 'bold';
        ax2.Title.HorizontalAlignment = 'center';

        % 强制标题水平居中
        drawnow;
        titlePos = ax2.Title.Position;
        titlePos(1) = mean(ax2.XLim);
        ax2.Title.Position = titlePos;


        %% ================= 图例 =================
        lgd = legend([hExp, hModel], ...
            {'实验采样值', '五层基线'}, ...
            'Orientation', 'horizontal', ...
            'NumColumns', 2);

        lgd.Layout.Tile = 'north';

        set(lgd, ...
            'Box', 'off', ...
            'FontName', cfg.fontName, ...
            'FontSize', fontSizeAll);


        %% ================= 导出 =================
        q1_export_figure(figs(k), cfg, exportNames{k});

    end

end