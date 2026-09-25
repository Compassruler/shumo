function q1_export_figure(fig, cfg, stem)
%Q1_EXPORT_FIGURE 同时导出可编辑 FIG、矢量 PDF/SVG 和 300 dpi PNG。
% PDF/SVG 强制使用矢量内容；FIG 可在 MATLAB 中继续改坐标轴和版式。
    drawnow;
    savefig(fig, fullfile(cfg.outputDir, stem + ".fig"));
    exportgraphics(fig, fullfile(cfg.outputDir, stem + ".pdf"), ...
        'ContentType', 'vector', 'BackgroundColor', 'white');
    % MATLAB 对彩色网格使用 exportgraphics 时有时会在 SVG 中嵌入位图；
    % vector 模式优先保留曲线、文字和色块的矢量结构。
    print(fig, fullfile(cfg.outputDir, stem + ".svg"), '-dsvg', '-vector');
    exportgraphics(fig, fullfile(cfg.outputDir, stem + ".png"), ...
        'Resolution', cfg.previewDpi, 'BackgroundColor', 'white');
end
