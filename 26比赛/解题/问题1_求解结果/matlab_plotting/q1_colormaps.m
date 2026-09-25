function [temperatureMap, iceMap] = q1_colormaps(n)
%Q1_COLORMAPS 生成适合论文的温度发散色图和冰含量顺序色图。
    if nargin < 1, n = 256; end
    x = linspace(0, 1, n)';
    temperatureMap = interp1([0 0.5 1], ...
        [0.18 0.36 0.62; 0.97 0.97 0.94; 0.72 0.20 0.18], x);
    iceMap = interp1([0 0.45 1], ...
        [0.97 0.98 0.96; 0.48 0.73 0.70; 0.05 0.30 0.48], x);
end
