% 设置 a1 的范围和步长
a1_min = 0;
a1_max = 100000;
step_size = 1; % 固定步长

% 初始化存储变量
a1_values = a1_min:step_size:a1_max; % a1 的所有取值
power_values = zeros(size(a1_values)); % 对应功率的存储数组

% 遍历 a1 的值并计算功率
for i = 1:length(a1_values)
    a1 = a1_values(i);
    % 计算功率
    power_values(i) = -my_fitness_2_1(a1); % 由于目标函数返回的是负的功率，所以取负值
end

% 绘制 a1 和功率的关系图
figure;
plot(a1_values, power_values, '-');
xlabel('a1 值');
ylabel('平均输出功率');
title('a1 和平均输出功率的关系图');
grid on;

% 输出计算结果
disp('a1 值和对应的平均输出功率:');
disp(table(a1_values', power_values', 'VariableNames', {'a1', 'Power'}));
