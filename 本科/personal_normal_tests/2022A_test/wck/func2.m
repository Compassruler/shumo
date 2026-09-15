function dxdt = func2(t, x, eta_i, alpha)
    % 参数设置
    m_f = 4866;
    mu_1 = 1165.992;
    lambda_i = 167.8395;
    k = 80000;
    rho = 1025;
    g = 9.8;
    R_f = 1;
    f = 4890;
    omega = 2.2143;
    m_z = 2433;
    
    % 初始化 dxdt
    dxdt = zeros(4, 1);
    
    % 位置和速度的微分方程
    dxdt(1) = x(2);
    dxdt(2) = (f * cos(omega * t) - eta_i * (x(2) - x(4)) * abs(x(2) - x(4))^alpha - lambda_i * x(2) - k * (x(1) - x(3)) - rho * g * pi * R_f^2 * x(1)) / (m_f + mu_1);
    dxdt(3) = x(4);
    dxdt(4) = (-eta_i * (x(4) - x(2)) * abs(x(4) - x(2))^alpha - k * (x(3) - x(1))) / m_z;
end
