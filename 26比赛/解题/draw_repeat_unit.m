function draw_repeat_unit()
% draw_repeat_unit  绘制"单片电池热学重复单元及厚度口径"示意图并导出 EPS
% =========================================================================
% 说明：
%   七个色块自左向右：aBP - aGDL - aCL - PEM - cCL - cGDL - cBP
%   五个 MEA 层（aGDL/aCL/PEM/cCL/cGDL）统一采用
%       "英文缩写（上，加粗）+ 横排中文名（下）" 的标注形式，
%   双极板 aBP/cBP 保持原有"英文缩写 + 横排中文名"形式。
%   下方三段尺寸线：2 mm | 五层 MEA：0.3267 mm | 2 mm
%
%   运行本文件将在当前目录生成：
%       repeat_unit.eps   （矢量，供 LaTeX 使用）
%       repeat_unit_preview.png（位图预览，可选）
%
%   中文字体使用 Windows 自带的"微软雅黑"(Microsoft YaHei)，
%   若系统无该字体，可改为 'SimHei'（黑体）或 'SimSun'（宋体）。
% =========================================================================

clc; close all;

%% 1. 数据定义 -----------------------------------------------------------
% 英文缩写
abbr = {'aBP','aGDL','aCL','PEM','cCL','cGDL','cBP'};

% 对应中文名（aBP/cBP 为双极板；中间五层为 MEA）
cn = {'阳极双极板', ...      % aBP
      '阳极气体扩散层', ...  % aGDL
      '阳极催化层', ...      % aCL
      '质子交换膜', ...      % PEM
      '阴极催化层', ...      % cCL
      '阴极气体扩散层', ...  % cGDL
      '阴极双极板'};         % cBP

% 各色块颜色（按原图采样，RGB/255）
fillColor = [ 64 120 184;   % aBP  深蓝
             166 199 227;   % aGDL 浅蓝
             107 171 214;   % aCL  中蓝
             237 209 115;   % PEM  黄
             224 140  77;   % cCL  橙
             184 214 184;   % cGDL 浅绿
              77 163 199] / 255; % cBP 青蓝

% 各色块视觉相对宽度（由原图测得，仅示意、不代表真实几何比例）
blkWidth = [1090 980 655 873 652 983 1087];

% 文字颜色：深色块用白字，浅色块用深色字
textColor = {[1 1 1], ...          % aBP  白
             [0.15 0.19 0.24], ... % aGDL 深
             [0.15 0.19 0.24], ... % aCL  深
             [0.15 0.19 0.24], ... % PEM  深
             [0.15 0.19 0.24], ... % cCL  深
             [0.15 0.19 0.24], ... % cGDL 深
             [1 1 1]};             % cBP  白

edgeColor  = [0.13 0.16 0.20];   % 色块描边（近黑）
cnFont     = 'Microsoft YaHei';  % 中文字体
enFont     = 'Arial';            % 英文/数字字体

%% 2. 画布与坐标 ----------------------------------------------------------
fig = figure('Color','w', 'Units','inches', 'Position',[1 1 12 4.6]);
ax  = axes(fig);
hold(ax,'on'); axis(ax,'off');

totalW = sum(blkWidth);
xLeft  = [0 cumsum(blkWidth(1:end-1))];   % 每块左边界
xRight = cumsum(blkWidth);                % 每块右边界
xCtr   = xLeft + blkWidth/2;              % 每块中心

% 色块几何（数据单位）
yBottom = 0;
yTop    = 1000;

% 坐标范围：上方留标题，下方留尺寸线
xlim(ax,[-60 totalW+60]);
ylim(ax,[-360 1330]);

%% 3. 标题文字 ------------------------------------------------------------
text(ax, totalW/2, 1278, '单片电池热学重复单元及厚度口径', ...
    'HorizontalAlignment','center','VerticalAlignment','middle', ...
    'FontName',cnFont,'FontSize',17,'FontWeight','bold','Color',[0.1 0.12 0.16]);

text(ax, totalW/2, 1165, ...
    '第 k 片：aBP—五层MEA—cBP，完整热域厚度 L_c = 4.3267 mm', ...
    'HorizontalAlignment','center','VerticalAlignment','middle', ...
    'FontName',cnFont,'FontSize',14,'FontWeight','bold','Color',[0.1 0.12 0.16]);

text(ax, totalW/2, 1075, ...
    '组堆示意中，相邻单片的 cBP/aBP 界面合并表示为一块片间共享双极板', ...
    'HorizontalAlignment','center','VerticalAlignment','middle', ...
    'FontName',cnFont,'FontSize',11.5,'Color',[0.32 0.36 0.42]);

%% 4. 七个色块及标注 ------------------------------------------------------
for k = 1:7
    % 色块（含深色描边）
    rectangle(ax, 'Position',[xLeft(k) yBottom blkWidth(k) (yTop-yBottom)], ...
        'FaceColor',fillColor(k,:), 'EdgeColor',edgeColor, ...
        'LineWidth',1.6);

    % 英文缩写（上，加粗）
    text(ax, xCtr(k), 600, abbr{k}, ...
        'HorizontalAlignment','center','VerticalAlignment','middle', ...
        'FontName',enFont,'FontSize',17,'FontWeight','bold', ...
        'Color',textColor{k});

    % 中文名（下，横排）
    text(ax, xCtr(k), 330, cn{k}, ...
        'HorizontalAlignment','center','VerticalAlignment','middle', ...
        'FontName',cnFont,'FontSize',11.5, ...
        'Color',textColor{k});
end

%% 5. 下方三段尺寸线 ------------------------------------------------------
yDim   = -120;   % 尺寸线高度
yTickL = yDim - 45;
yTickR = yDim + 45;

% 三段：[左边界 右边界 颜色 标签]
seg(1) = struct('x0',xLeft(1),  'x1',xRight(1), 'col',fillColor(1,:), 'lab','2 mm');
seg(2) = struct('x0',xRight(1), 'x1',xRight(6), 'col',[0.55 0.38 0.10], ...
                'lab','五层MEA：0.3267 mm');
seg(3) = struct('x0',xRight(6), 'x1',xRight(7), 'col',fillColor(7,:), 'lab','2 mm');

for s = 1:3
    % 主水平线
    plot(ax,[seg(s).x0 seg(s).x1],[yDim yDim],'-', ...
        'Color',seg(s).col,'LineWidth',1.8);
    % 两端竖刻度
    plot(ax,[seg(s).x0 seg(s).x0],[yTickL yTickR],'-', ...
        'Color',seg(s).col,'LineWidth',1.8);
    plot(ax,[seg(s).x1 seg(s).x1],[yTickL yTickR],'-', ...
        'Color',seg(s).col,'LineWidth',1.8);
    % 标签
    text(ax,(seg(s).x0+seg(s).x1)/2, yDim-110, seg(s).lab, ...
        'HorizontalAlignment','center','VerticalAlignment','middle', ...
        'FontName',cnFont,'FontSize',13,'FontWeight','bold', ...
        'Color',seg(s).col);
end

%% 6. 导出 EPS（矢量）及 PNG 预览 ----------------------------------------
set(ax,'Units','normalized','Position',[0.02 0.02 0.96 0.96]);
drawnow;

epsFile = fullfile(pwd,'repeat_unit.eps');
try
    % R2020a 及以上推荐：exportgraphics，字体内嵌、矢量、自动裁切
    exportgraphics(fig, epsFile, 'ContentType','vector');
    fprintf('已用 exportgraphics 导出：%s\n', epsFile);
catch
    % 旧版本回退：painters 矢量打印 EPS
    print(fig, epsFile, '-depsc', '-painters');
    fprintf('已用 print -depsc 导出：%s\n', epsFile);
end

pngFile = fullfile(pwd,'repeat_unit_preview.png');
try
    exportgraphics(fig, pngFile, 'Resolution',300);
    fprintf('已导出 PNG 预览：%s\n', pngFile);
catch
    print(fig, pngFile, '-dpng', '-r300');
    fprintf('已导出 PNG 预览：%s\n', pngFile);
end

fprintf('完成。\n');
end
