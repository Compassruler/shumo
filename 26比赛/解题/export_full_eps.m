function export_full_eps()
% export_full_eps  将修正后的完整示意图封装导出为 EPS / PDF
% =========================================================================
%   读取 问题二电堆热网络与计算节点示意图_修正.png（整体框架保持原图，
%   仅底部五层 MEA 改为"英文缩写 + 横排中文名"），按图像原样嵌入导出：
%       问题二电堆热网络与计算节点示意图_修正.eps
%       问题二电堆热网络与计算节点示意图_修正.pdf
%   所有文字已烘焙进图像，EPS 不依赖系统字体、不会出现中文方框。
% =========================================================================

clc;
workDir = fileparts(mfilename('fullpath'));
if isempty(workDir), workDir = pwd; end
pngFile = fullfile(workDir,'问题二电堆热网络与计算节点示意图_修正.png');
if ~isfile(pngFile), pngFile = fullfile(pwd,'问题二电堆热网络与计算节点示意图_修正.png'); end

[img,~,alpha] = imread(pngFile);
[h,w,~] = size(img);
fprintf('读取图像：%dx%d\n', w, h);

% 目标物理宽度(英寸)，高度按比例
targetW = 11.5;
targetH = targetW * h / w;

fig = figure('Color','w','Units','inches','Position',[1 1 targetW targetH]);
ax  = axes(fig,'Units','normalized','Position',[0 0 1 1]);
if isempty(alpha)
    imshow(img,'Border','tight','Parent',ax);
else
    imshow(img,alpha,'Border','tight','Parent',ax);
end
axis(ax,'off');
drawnow;

epsFile = fullfile(workDir,'问题二电堆热网络与计算节点示意图_修正.eps');
pdfFile = fullfile(workDir,'问题二电堆热网络与计算节点示意图_修正.pdf');

try
    exportgraphics(fig, epsFile, 'ContentType','vector');
    fprintf('已导出 EPS：%s\n', epsFile);
catch
    print(fig, epsFile, '-depsc', '-painters');
    fprintf('已导出 EPS(print)：%s\n', epsFile);
end

try
    exportgraphics(fig, pdfFile, 'ContentType','vector');
    fprintf('已导出 PDF：%s\n', pdfFile);
catch
    print(fig, pdfFile, '-dpdf', '-painters');
end

fprintf('完成。\n');
end
