function fitness = my_fitness_2_1(a1)
omega = 2.2143;
T = 2 * pi / omega;
    try
        % 初始条件和时间跨度
        y0 = [0; 0; 0; 0]; % 初始条件
        tspan = [100,180];    % 时间跨度 (该区间稳定)
        % 调用 ode45 求解微分方程
        [t, y] = ode45(@(t, y) def_q2_1(t, y, a1), tspan, y0);
        vf = y(:, 2);
        vz = y(:, 4);
        % 计算平均输出功率
        PTO = a1 * abs(vz - vf).^(2);
        P_avg = trapz(t, PTO) / (tspan(2) - tspan(1)); % 使用数值积分计算平均值
        % 目标是最大化平均输出功率
        fitness = -P_avg;
    catch ME
        disp('Error in fitness_function:');
        disp(ME.message);
        fitness = inf; % 返回一个大值，表示失败
    end
end
