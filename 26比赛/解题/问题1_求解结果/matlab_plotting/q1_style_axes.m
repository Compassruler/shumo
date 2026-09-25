function q1_style_axes(ax, cfg, panelLetter, panelTitle, yLabel)
%Q1_STYLE_AXES 设置统一的坐标轴、网格、单位标签和子图编号。
    ax.FontName = cfg.fontName;
    ax.FontSize = cfg.fontSize;
    ax.LineWidth = 0.75;
    ax.TickDir = 'out';
    ax.Box = 'off';
    ax.XGrid = 'on';
    ax.YGrid = 'on';
    ax.GridColor = cfg.color.grid;
    ax.GridAlpha = 0.58;
    ax.Layer = 'top';
    xlabel(ax, '时间 / s', 'FontName', cfg.fontName, 'FontSize', cfg.labelFontSize);
    if nargin >= 5 && ~isempty(yLabel)
        ylabel(ax, yLabel, 'FontName', cfg.fontName, 'FontSize', cfg.labelFontSize);
    end
    xlim(ax, [0 35]);
    xticks(ax, 0:5:35);
    title(ax, panelTitle, 'FontName', cfg.fontName, 'FontSize', cfg.labelFontSize, ...
        'FontWeight', 'normal', 'HorizontalAlignment', 'left');
    text(ax, -0.12, 1.04, panelLetter, 'Units', 'normalized', ...
        'FontName', cfg.fontName, 'FontSize', cfg.labelFontSize, ...
        'FontWeight', 'bold', 'HorizontalAlignment', 'left');
end
