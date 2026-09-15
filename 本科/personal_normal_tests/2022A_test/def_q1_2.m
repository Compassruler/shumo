function dy = def_q1_2(t, y)
%% 参数
omega = 1.4005; % s-1
f = 6250; % N
a2 = 10000 * abs( y(4) - y(2) ) ^ 0.5; 
mz = 2433; % kg
mf = 4866; % kg
m1 = 1335.535; % kg
cw = 656.3616; % N * s / m
k = 80000; % N / m
rho = 1025; % kg / m^3
g = 9.8;
A = pi; % m^2
%% 微分方程
% y1:xf, y2:xf', y3:xz, y4:xz' 
dy = zeros(4, 1);
dy(1, 1) = y(2);
dy(3, 1) = y(4);
dy(4, 1) = (-( a2 * ( y(4) - y(2) ) + k * ( y(3) - y(1) ) ) ) / mz;
dy(2, 1) = ( -rho * g * A * y(1) - cw * y(2) + f * cos(omega * t) + a2 * ( y(4) - y(2) ) + k * ( y(3) - y(1) ) ) / (mf + m1);

end
