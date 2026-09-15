%%q2.1
% 设置遗传算法的选项，启用显示功能
options = optimoptions('ga', 'Display', 'iter', 'PlotFcn', {@gaplotbestf},'MaxGenerations',200);

% 使用遗传算法优化 a1
[a1_optimal, fval] = ga(@my_fitness_2_1, 1, [], [], [], [], 0, 100000, [], options);

% 输出最优的 a1 值
disp(['最优的 a1 值为: ', num2str(a1_optimal)]);
disp(['最优的目标函数值为: ', num2str(fval)]);

%%q2.2
% 设置遗传算法的选项，启用显示功能
options = optimoptions('ga', 'Display', 'iter', 'PlotFcn', {@gaplotbestf}, 'MaxGenerations', 200);

% 定义目标函数，该函数接受一个包含两个元素的向量 
fitnessFunction = @(x) my_fitness_2_2(x(1), x(2));

% 使用遗传算法优化 a1 和 alpha
[x_optimal, fval] = ga(fitnessFunction, 2, [], [], [], [], [0, 0], [100000, 1], [], options);

% 输出最优的 a1 和 alpha 值
disp(['最优的 a1 值为: ', num2str(x_optimal(1))]);
disp(['最优的 alpha 值为: ', num2str(x_optimal(2))]);
disp(['最优的目标函数值为: ', num2str(-fval)]);

