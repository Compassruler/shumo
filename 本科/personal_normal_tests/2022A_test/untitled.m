% 设置 c 和 alpha 的范围和步长
c_min = 0;
c_max = 100000;
alpha_min = 0;
alpha_max = 1;
c_step_size = 1000; % c 的步长
alpha_step_size = 0.01; % alpha 的步长

% 初始化存储变量
c_values = c_min:c_step_size:c_max; % c 的所有取值
alpha_values = alpha_min:alpha_step_size:alpha_max; % alpha 的所有取值
[C, Alpha] = meshgrid(c_values, alpha_values); % 创建 c 和 alpha 的网格
power_values = zeros(size(C)); % 初始化功率值矩阵

% 遍历 c 和 alpha 的值并计算功率
for i = 1:numel(C)
    c = C(i);
    alpha = Alpha(i);
    % 计算功率
    power_values(i) = -my_fitness_2_2(c, alpha); % 由于目标函数返回的是负的功率，所以取负值
end

% 绘制 c, alpha 和功率的三维关系图
figure;
surf(C, Alpha, power_values);
xlabel('c 值');
ylabel('alpha 值');
zlabel('平均输出功率');
title('c 和 alpha 与平均输出功率的关系图');
colorbar; % 显示颜色条
grid on;

% 输出计算结果
disp('c 值、alpha 值和对应的平均输出功率:');
disp(table(C(:), Alpha(:), power_values(:), 'VariableNames', {'c', 'alpha', 'Power'}));

