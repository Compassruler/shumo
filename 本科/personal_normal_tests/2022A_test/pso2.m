%% 清空环境
clc;clear all;close all;
%% 目标函数
fun= @(a) def_q2_1(a);
%  绘图函数，可舍弃
figure(1);
y0=fun(a);
plot(a,y0);
hold on;
%% 设置种群参数
%   需要自行配置
sizepop = 500;                         % 初始种群个数
dim = 1;                           % 空间维数
ger = 300;                       % 最大迭代次数     
xlimit = [ -5,5 ; -5 ,5 ];        % 设置位置参数限制(矩阵的形式可以多维)
vlimit = [ -1.5,1.5 ; -1.5,1.5]; % 设置速度限制
c_1 = 0.8;                       % 惯性权重
c_2 = 0.5;                       % 自我学习因子
c_3 = 0.5;                       % 群体学习因子 
%% 生成初始种群
%  首先随机生成初始种群位置
%  然后随机生成初始种群速度
%  然后初始化个体历史最佳位置，以及个体历史最佳适应度
%  然后初始化群体历史最佳位置，以及群体历史最佳适应度
%  绘图（可舍弃）
 for i = 1:dim
    pop_x(i,:) = xlimit(i, 1) + (xlimit(i, 2) - xlimit(i, 1)) * rand(1, sizepop);%初始种群的位置
end    
pop_v = rand(dim, sizepop);                   % 初始种群的速度
gbest = pop_x;                                % 每个个体的历史最佳位置
fitness_gbest = fun(pop_x(1,:),pop_x(2,:));   % 每个个体的历史最佳适应度
zbest = pop_x(:,1);                          % 种群的历史最佳位置
fitness_zbest = fitness_gbest(1);             % 种群的历史最佳适应度
for j=1:sizepop
    if fitness_gbest(j) < fitness_zbest       % 如果求最小值，则为<; 如果求最大值，则为>; 
        zbest = pop_x(:,j);
        fitness_zbest=fitness_gbest(j);
    end
end

plot3(gbest(1,:),gbest(2,:),fun(gbest(1,:),gbest(2,:)), 'ro');title('初始状态图');
hold on;
figure(2);
mesh(x0_1, x0_2, y0);
hold on;
plot3(gbest(1,:),gbest(2,:),fun(gbest(1,:),gbest(2,:)), 'ro');
hold on;

%% 粒子群迭代
%    更新速度并对速度进行边界处理    
%    更新位置并对位置进行边界处理
%    进行自适应变异
%    计算新种群各个个体位置的适应度
%    新适应度与个体历史最佳适应度做比较
%    个体历史最佳适应度与种群历史最佳适应度做比较
%    再次循环或结束

iter = 1;                        %迭代次数
times = 1;                       %用于显示，可舍弃
record = zeros(ger, 1);          % 记录器
while iter <= ger
    
    %    更新速度并对速度进行边界处理 
    pop_v =  c_1 * pop_v  + c_2 * rand *(gbest - pop_x) + c_3 * rand *(repmat(zbest, 1, sizepop) - pop_x);% 速度更新
    for i=1:dim 
        for j=1:sizepop
            if  pop_v(i,j)>vlimit(i,2)
                pop_v(i,j)=vlimit(i,2);
            end
            if  pop_v(i,j) < vlimit(i,1)
                pop_v(i,j)=vlimit(i,1);
            end
        end
    end 
    
    %    更新位置并对位置进行边界处理
    pop_x = pop_x + pop_v;% 位置更新
    % 边界位置处理
    for i=1:dim 
        for j=1:sizepop
            if  pop_x(i,j)>xlimit(i,2)
                pop_x(i,j)=xlimit(i,2);
            end
            if  pop_x(i,j) < xlimit(i,1)
                pop_x(i,j)=xlimit(i,1);
            end
        end
    end
    
    %    自适应变异
    for j=1:sizepop
        if rand > 0.85
            i=ceil(dim*rand);
            pop_x(i,j)=xlimit(i, 1) + (xlimit(i, 2) - xlimit(i, 1)) * rand;
        end
    end
    
    %    计算新种群各个个体位置的适应度
    fitness_pop = fun(pop_x(1,:),pop_x(2,:)) ; % 当前所有个体的适应度
    
    %    新适应度与个体历史最佳适应度做比较
    for j = 1:sizepop      
        if fitness_pop(j) < fitness_gbest(j)       % 如果求最小值，则为<; 如果求最大值，则为>; 
            gbest(:,j) = pop_x(:,j);               % 更新个体历史最佳位置            
            fitness_gbest(j) = fitness_pop(j);     % 更新个体历史最佳适应度
        end 
    end
    
    %    个体历史最佳适应度与种群历史最佳适应度做比较
    for j = 1:sizepop  
        if fitness_gbest(j) < fitness_zbest        % 如果求最小值，则为<; 如果求最大值，则为>; 
            zbest = gbest(:,j);                    % 更新群体历史最佳位置  
            fitness_zbest=fitness_gbest(j);        % 更新群体历史最佳适应度  
        end
    end
    
    record(iter) = fitness_zbest;%最大值记录
    
    if times >= 10        %显示函数 可以舍去
        cla;
        mesh(x0_1, x0_2, y0);
        plot3(pop_x(1,:),pop_x(2,:),fun(pop_x(1,:),pop_x(2,:)), 'ro');title('状态位置变化');
        pause(0.5);
        times=0;
    end
    
    iter = iter+1;
    times=times+1;        %显示函数 可以舍去
end
%% 迭代结果输出

figure(3);plot(record);title('收敛过程')
figure(4);
mesh(x0_1, x0_2, y0);
hold on;
plot3(pop_x(1,:),pop_x(2,:),fun(pop_x(1,:),pop_x(2,:)), 'ro');title('最终状态图');

disp(['最优值：',num2str(fitness_zbest)]);
disp('变量取值：');
disp(zbest);