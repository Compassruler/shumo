function dy = def_q2_1(t, y, a1)
%% 参数
omega = 2.2143; % s-1
T = 2 * pi / omega;
f = 4890; % N
mz = 2433; % kg
mf = 4866; % kg
m1 = 1165.992; % kg
cw = 167.8395; % N * s / m
k = 80000; % N / m
rho = 1025; % kg / m^3
g = 9.81;
A = pi; % m^2

%% 微分方程
% y1:xf, y2:xf', y3:xz, y4:xz' 
dy = zeros(4, 1);
dy(1, 1) = y(2);
dy(3, 1) = y(4);
dy(4, 1) = (-( a1 * ( y(4) - y(2) ) + k * ( y(3) - y(1) ) ) ) / mz;
dy(2, 1) = ( -rho * g * A * y(1) - cw * y(2) + f * cos(omega * t) + a1 * ( y(4) - y(2) ) + k * ( y(3) - y(1) ) ) / (mf + m1);

end
