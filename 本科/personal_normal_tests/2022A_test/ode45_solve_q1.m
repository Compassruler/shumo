clc, clear, close all

% 计算出了前40个波浪周期的垂荡位移和速度
%% q1.1
% y1:xf, y2:xf', y3:xz, y4:xz' 
omega = 1.4005; % s-1
T = 2 * pi / omega; % 波浪周期
t_end = 40 * T;
tspan = [0, t_end];
y0 = zeros(1, 4);
opts = [];
[t, y] = ode45(@def_q1_1, tspan, y0, opts);
% 变为以0.2为间隔
sample = [];
for i = 0: 0.2: T*40
     tem= find(t-i <= 0.1 & t - i >= 0, 1); % 找出离i值最近的t的索引值
     sample = [sample; tem];
end
xf = y(sample, 1); vf = y(sample, 2);
xz = y(sample, 3); vz = y(sample, 4);
xr = xz - xf;
vr = vz - vf;
% 在论文中给出 10 s、20 s、40 s、60 s、100 s 时，浮子与振子的垂荡位移和速度
paper = [10, 20, 40, 60, 100]/0.2;
paper_xf = xf(paper); % 浮子位移
paper_vf = vf(paper); % 浮子速度
paper_xz = xz(paper); % 振子位移
paper_vz = vz(paper); % 振子速度
% 画图
t=1:length(xf); % 将t与xf依次对齐
t=0.2*t;
% 位移(大地坐标系)
figure;
p =plot(t, xf, t, xz);
hold on
p(1).Color = [0,0.7,0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子位移(m)","振子位移(m)")
title("浮子/振子位移随时间的变化a1)")
xlabel("时间(s)")
ylabel("位移(m)")
% 速度(大地坐标系)
figure;
p =plot(t, vf, t, vz);
hold on
p(1).Color = [0 0.7 0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子速度(m/s)","振子速度(m/s)")
title("浮子/振子速度随时间的变化a1)")
xlabel("时间(s)")
ylabel("速度(m/s)")
% 位移(振子相对浮子)
figure;
p =plot(t, xf, t, xr);
hold on
p(1).Color = [0,0.7,0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子位移(m)","振子位移(m)")
title("浮子/振子位移随时间的变化a1)")
xlabel("时间(s)")
ylabel("位移(m)")
% 速度(振子相对浮子)
figure;
p =plot(t, vf, t, vr);
hold on
p(1).Color = [0 0.7 0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子速度(m/s)","振子速度(m/s)")
title("浮子/振子速度随时间的变化a1)")
xlabel("时间(s)")
ylabel("速度(m/s)")
%%  q1.2
omega = 1.4005; % s-1
T = 2 * pi / omega; % 波浪周期
t_end = 40 * T;
tspan = [0, t_end];
y0 = zeros(1, 4);
opts = [];
[t, y] = ode45(@def_q1_2, tspan, y0, opts);

% 变为以0.2为间隔
sample = [];
for i = 0: 0.2: T*40
     tem= find(t-i <= 0.1 & t - i >= 0, 1); % 找出离i值最近的t的索引值
     sample = [sample; tem];
end
xf = y(sample, 1); vf = y(sample, 2);
xz = y(sample, 3); vz = y(sample, 4);
xr = xz - xf;
vr = vz - vf;
% 在论文中给出 10 s、20 s、40 s、60 s、100 s 时，浮子与振子的垂荡位移和速度
paper = [10, 20, 40, 60, 100]/0.2;
paper_xf = xf(paper); % 浮子位移
paper_vf = vf(paper); % 浮子速度
paper_xz = xz(paper); % 振子位移
paper_vz = vz(paper); % 振子速度
% 画图
t=1:length(xf); % 将t与xf依次对齐
t=0.2*t;
% 位移
figure;
p =plot(t, xf, t, xz);
hold on
p(1).Color = [0,0.7,0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子位移(m)","振子位移(m)")
title("浮子/振子位移随时间的变化a2)")
xlabel("时间(s)")
ylabel("位移(m)")
% 速度
figure;
p =plot(t, vf, t, vz);
hold on
p(1).Color = [0 0.7 0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子速度(m/s)","振子速度(m/s)")
title("浮子/振子速度随时间的变化a2)")
xlabel("时间(s)")
ylabel("速度(m/s)")
% 位移(振子相对浮子)
figure;
p =plot(t, xf, t, xr);
hold on
p(1).Color = [0,0.7,0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子位移(m)","振子位移(m)")
title("浮子/振子位移随时间的变化a2)")
xlabel("时间(s)")
ylabel("位移(m)")
% 速度(振子相对浮子)
figure;
p =plot(t, vf, t, vr);
hold on
p(1).Color = [0 0.7 0.9];
p(2).Color = [0.9 0.5 0.0];
legend("浮子速度(m/s)","振子速度(m/s)")
title("浮子/振子速度随时间的变化a2)")
xlabel("时间(s)")
ylabel("速度(m/s)")
