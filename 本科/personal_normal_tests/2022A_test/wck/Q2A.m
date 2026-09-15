% 参数设置
m_f = 4866;
mu_1 = 1165.992;
lambda_i = 167.8395;
k = 80000;
rho = 1025;
g = 9.8;
Rf = 1;
f = 4890;
omega = 2.2143;
m_z = 2433;

% A, B
A = -omega^2 * (m_f + mu_1) + k + rho * g * pi * Rf^2;
B = -omega^2 * m_z + k;

% C, D
C = A * B - k^2;
D = omega^2 * lambda_i;

% E
E = A + B - 2 * k;

% eta_i_best
eta_i_best = sqrt((C^2 + omega^2 * B^2 * lambda_i^2) / (D^2 + omega^2 * E^2));
disp(['最优阻尼系数 eta_i_best 为: ', num2str(eta_i_best)]);

% 计算 PTO
PTO = 0.5 * (omega^6 * m_z^2 * f^2 * eta_i_best) / ((C - D * eta_i_best)^2 + omega^2 * (E * eta_i_best + B * lambda_i)^2);
disp(['PTO系统平均输出功率为: ', num2str(PTO), ' W']);

% 绘图
eta_i_range = 30000:100:40000;
PTO_values = zeros(size(eta_i_range));
for i = 1:length(eta_i_range)
    eta_i = eta_i_range(i);
    PTO_values(i) = 0.5 * (omega^6 * m_z^2 * f^2 * eta_i) / ((C - D * eta_i)^2 + omega^2 * (E * eta_i + B * lambda_i)^2);
end

figure;
plot(eta_i_range, PTO_values, '-');
title('PTO输出功率随阻尼系数变化曲线');
xlabel('阻尼系数 \eta_i');
ylabel('PTO 输出功率 (W)');
