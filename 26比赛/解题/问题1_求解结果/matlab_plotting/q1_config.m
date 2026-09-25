function cfg = q1_config()
%Q1_CONFIG 问题一全部 MATLAB 图的统一配置。
% 修改本文件可以一次性改变所有图的宽度、字体、线宽和配色。

    here = fileparts(mfilename('fullpath'));
    cfg.projectRoot = fileparts(here);
    cfg.dataDir = fullfile(cfg.projectRoot, 'data');
    cfg.outputDir = fullfile(here, 'figures');
    if ~isfolder(cfg.outputDir)
        mkdir(cfg.outputDir);
    end

    % 论文通栏宽度；需要单栏图时可改成 8.5。
    cfg.figureWidthCm = 18.03;
    cfg.fontName = localChineseFont();
    cfg.fontSize = 8.5;
    cfg.labelFontSize = 9;
    cfg.lineWidth = 1.35;
    cfg.previewDpi = 300;

    % 色盲友好且黑白打印可通过线型区分的配色。
    cfg.color.main = hex2rgb('#0072B2');
    cfg.color.bp = hex2rgb('#D55E00');
    cfg.color.experiment = hex2rgb('#C44E52');
    cfg.color.pore = hex2rgb('#009E73');
    cfg.color.membrane = hex2rgb('#CC79A7');
    cfg.color.saturation = hex2rgb('#A66F00');
    cfg.color.activation = hex2rgb('#56B4E9');
    cfg.color.ohmic = hex2rgb('#E69F00');
    cfg.color.concentration = hex2rgb('#8C6BB1');
    cfg.color.phase = hex2rgb('#008B8B');
    cfg.color.loss = hex2rgb('#C44E52');
    cfg.color.residual = hex2rgb('#5F6368');
    cfg.color.grid = hex2rgb('#D9DEE5');
end

function name = localChineseFont()
% 优先选择当前操作系统中可用的中文字体。
    available = string(listfonts);
    candidates = ["Heiti SC", "PingFang SC", "Microsoft YaHei", ...
                  "Noto Sans CJK SC", "Source Han Sans SC", "Arial Unicode MS"];
    name = 'Helvetica';
    for k = 1:numel(candidates)
        if any(strcmpi(available, candidates(k)))
            name = char(candidates(k));
            return;
        end
    end
end

function rgb = hex2rgb(hex)
% 将网页十六进制颜色转换为 MATLAB 的 0~1 RGB 三元组。
    hex = erase(hex, '#');
    rgb = sscanf(hex, '%2x%2x%2x', [1 3]) / 255;
end
