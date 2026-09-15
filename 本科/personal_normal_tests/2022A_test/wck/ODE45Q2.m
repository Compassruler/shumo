% 参数设置
m_f = 4866;
mu_1 = 1165.992;
eta_i = 3.7194e+04;
lambda_i = 167.8395;
k = 80000;
rho = 1025;
g = 9.8;
Rf = 1;
f = 4890;
omega = 2.2143;
m_z = 2433;
alpha = 0; % 这里是代码1，所以alpha为0
x_0 = [0 0 0 0];
tspan = 0:0.2:400;

% 求解微分方程
[t, x] = ode45(@(t, x) func2(t, x, eta_i, alpha), tspan, x_0);

% 绘图
figure;
plot(t, x(:, 1), "-", t, x(:, 3), "-*");
title('浮子与振子的垂荡位移');
xlabel('时间 (s)');
ylabel('位移 (m)');
legend('浮子', '振子');

figure;
plot(t, x(:, 2) - x(:, 4), "-");
title('浮子与振子的相对速度');
xlabel('时间 (s)');
ylabel('速度 (m/s)');

% 计算 PTO
delta_v = x(1000:2000, 2) - x(1000:2000, 4);
pto = eta_i .* delta_v.^2;
PTO = trapz(pto) / (200 * 0.2); % 校正PTO的计算方法，在总时间上进行平均
disp(['PTO输出功率为: ', num2str(PTO), ' W']);
