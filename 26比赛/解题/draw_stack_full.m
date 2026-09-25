function draw_stack_full()
% draw_stack_full  自包含绘制"问题二电堆热网络与计算节点示意图"并导出 EPS
% =========================================================================
%  不引用任何外部 PDF/PNG，全部图形由本脚本绘制（矢量）。
%  内容：
%    上：五片电堆热网络（环境-端板-双极板-单电池）、温度节点、热导标注、
%        电流串联箭头、启动成功判据框；
%    下：单片电池热学重复单元（aBP-五层MEA-cBP），五层 MEA 采用
%        "英文缩写(加粗)+横排中文名"，含尺寸线与"计算域说明"；
%    底：图例与注释。
%  运行后在当前目录生成：问题二电堆热网络与计算节点示意图.eps / .pdf
%  中文字体：微软雅黑 Microsoft YaHei（无则改 SimHei）。
% =========================================================================
clc; close all;

CN = 'Microsoft YaHei';   % 中文字体
EN = 'Arial';             % 英文/数字字体

% ---- 颜色 ----
C.envEdge=[0.18 0.55 0.35]; C.envFill=[0.94 0.98 0.95];
C.plate=[0.29 0.32 0.37];
C.bpA=[0.25 0.47 0.72];    % 阳极边界双极板(深蓝)
C.bpS=[0.23 0.53 0.74];    % 片间共享双极板(蓝)
C.bpC=[0.34 0.66 0.79];    % 阴极边界双极板(青)
C.cell=[0.94 0.68 0.24];   % 单电池MEA(橙)
C.nodeFill=[1 1 1]; C.nodeEdge=[0.13 0.16 0.20];
C.red=[0.85 0.20 0.17]; C.green=[0.12 0.62 0.39]; C.purple=[0.48 0.25 0.63];
C.boxEdge=[0.35 0.50 0.71]; C.boxFill=[0.95 0.97 0.99];
C.dark=[0.15 0.19 0.24]; C.white=[1 1 1]; C.gray=[0.32 0.36 0.42];

fig=figure('Color','w','Units','inches','Position',[0.4 0.4 13.5 7.4]);
ax=axes(fig,'Units','normalized','Position',[0.01 0.01 0.98 0.98]);
hold(ax,'on'); axis(ax,'off');
xlim(ax,[0 140]); ylim(ax,[0 82]);

%% ===== 顶部标题 =====
txt(ax,70,79.5,'问题二电堆热网络与计算节点示意图',CN,19,'bold',C.dark);
txt(ax,70,76.3,'五片单电池电学串联、热学耦合；相邻电池共用一块双极板（宽度仅作示意）',CN,11.5,'normal',C.gray);

%% ===== 主电堆几何参数 =====
bandB=50; bandT=68;
bpW=3; cellW=13;
cellL=31.5+(0:4)*(bpW+cellW);          % 五片电池左边界
shrL=cellL+cellW;                      % 四个共享板左边界
cellC=cellL+cellW/2;                   % 电池中心
shrC=shrL+bpW/2;                       % 共享板中心
bpAx=[28.5 31.5]; bpCx=[108.5 111.5];  % 两端边界双极板
epL=[21 26]; epR=[114 119];            % 两端板
envL=[3 14]; envR=[126 137];           % 环境框

% ---- 环境框 ----
envbox(ax,envL); envbox(ax,envR);
txt(ax,mean(envL),61.5,'环境',CN,12,'bold',C.dark);
txt(ax,mean(envL),56.5,'T_{amb}',EN,12,'bold',C.dark);
txt(ax,mean(envR),61.5,'环境',CN,12,'bold',C.dark);
txt(ax,mean(envR),56.5,'T_{amb}',EN,12,'bold',C.dark);

% ---- 端板 ----
rectf(ax,[epL(1) bandB diff(epL) bandT-bandB],C.plate,C.nodeEdge,1.4);
rectf(ax,[epR(1) bandB diff(epR) bandT-bandB],C.plate,C.nodeEdge,1.4);
% 端板竖排文字
text(ax,22.7,59,'10 mm','Rotation',90,'FontName',EN,'FontSize',10,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');
text(ax,24.6,59,'左端板','Rotation',90,'FontName',CN,'FontSize',11,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');
text(ax,115.4,59,'10 mm','Rotation',90,'FontName',EN,'FontSize',10,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');
text(ax,117.3,59,'右端板','Rotation',90,'FontName',CN,'FontSize',11,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');

% ---- 两端边界双极板 ----
rectf(ax,[bpAx(1) bandB diff(bpAx) bandT-bandB],C.bpA,C.nodeEdge,1.4);
rectf(ax,[bpCx(1) bandB diff(bpCx) bandT-bandB],C.bpC,C.nodeEdge,1.4);
text(ax,mean(bpAx),59,'阳极双极板','Rotation',90,'FontName',CN,'FontSize',8.5,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');
text(ax,mean(bpCx),59,'阴极双极板','Rotation',90,'FontName',CN,'FontSize',8.5,'Color',C.white,...
    'HorizontalAlignment','center','VerticalAlignment','middle');

% ---- 五片电池 ----
for k=1:5
    rectf(ax,[cellL(k) bandB cellW bandT-bandB],C.cell,C.nodeEdge,1.4);
    txt(ax,cellC(k),63.5,sprintf('单电池%d',k),CN,11,'normal',C.dark);
    text(ax,cellC(k),58.3,sprintf('T_%d, V_%d',k,k),'FontName',EN,'FontSize',10.5,...
        'Color',C.dark,'HorizontalAlignment','center');
    txt(ax,cellC(k),53.3,'j(t) 相同',CN,9.5,'normal',C.gray);
end

% ---- 四块片间共享双极板 ----
for k=1:4
    rectf(ax,[shrL(k) bandB bpW bandT-bandB],C.bpS,C.nodeEdge,1.4);
    text(ax,shrC(k),59,'片间双极板','Rotation',90,'FontName',CN,'FontSize',8.5,'Color',C.white,...
        'HorizontalAlignment','center','VerticalAlignment','middle');
end

% ---- 温度节点 T1..T5（竖线+椭圆）----
for k=1:5
    plot(ax,[cellC(k) cellC(k)],[bandT 71.1],'-','Color',C.nodeEdge,'LineWidth',1.2);
    ellipse(ax,cellC(k),73.5,2.5,2.0,C.nodeFill,C.nodeEdge,1.3);
    text(ax,cellC(k),73.5,sprintf('T_%d',k),'FontName',EN,'FontSize',11,'FontWeight','bold',...
        'HorizontalAlignment','center','VerticalAlignment','middle','Color',C.dark);
end
% 端板节点 theta
for xx=[mean(epL) mean(epR)]
    plot(ax,[xx xx],[bandT 71.1],'-','Color',C.nodeEdge,'LineWidth',1.2);
    ellipse(ax,xx,73.5,2.7,2.1,C.nodeFill,C.nodeEdge,1.3);
end
text(ax,mean(epL),73.5,'\theta_L','FontName',EN,'FontSize',11,'FontWeight','bold',...
    'HorizontalAlignment','center','VerticalAlignment','middle','Color',C.dark);
text(ax,mean(epR),73.5,'\theta_R','FontName',EN,'FontSize',11,'FontWeight','bold',...
    'HorizontalAlignment','center','VerticalAlignment','middle','Color',C.dark);

% ---- G_cc 片间热导（红色双向小箭头）----
for k=1:4
    darrow(ax,shrC(k)-1.1,shrC(k)+1.1,70.6,C.red);
    text(ax,shrC(k),71.9,'G_{cc}','FontName',EN,'FontSize',9.5,'FontWeight','bold',...
        'HorizontalAlignment','center','Color',C.red);
end
% ---- G_ce 端板-边界板（红） ----
darrow(ax,epL(2)+0.3,bpAx(1)-0.3,59,C.red);
text(ax,(epL(2)+bpAx(1))/2,60.6,'G_{ce}','FontName',EN,'FontSize',9.5,'FontWeight','bold',...
    'HorizontalAlignment','center','Color',C.red);
darrow(ax,bpCx(2)+0.3,epR(1)-0.3,59,C.red);
text(ax,(bpCx(2)+epR(1))/2,60.6,'G_{ce}','FontName',EN,'FontSize',9.5,'FontWeight','bold',...
    'HorizontalAlignment','center','Color',C.red);
% ---- G_ea 环境-端板（绿） ----
darrow(ax,envL(2)+0.3,epL(1)-0.3,59,C.green);
text(ax,(envL(2)+epL(1))/2,60.8,'G_{ea}','FontName',EN,'FontSize',9.5,'FontWeight','bold',...
    'HorizontalAlignment','center','Color',C.green);
txt(ax,(envL(2)+epL(1))/2,55.6,'对流',CN,9,'normal',C.green);
darrow(ax,epR(2)+0.3,envR(1)-0.3,59,C.green);
text(ax,(epR(2)+envR(1))/2,60.8,'G_{ea}','FontName',EN,'FontSize',9.5,'FontWeight','bold',...
    'HorizontalAlignment','center','Color',C.green);
txt(ax,(epR(2)+envR(1))/2,55.6,'对流',CN,9,'normal',C.green);

%% ===== 电流串联紫色箭头 =====
sarrow(ax,28.5,111.5,45.2,C.purple);
txt(ax,70,46.9,'电学串联：五片通过相同电流密度 j(t)',CN,11,'bold',C.purple);

%% ===== 启动成功判据框 =====
rectangle(ax,'Position',[20 33 100 8.2],'Curvature',[0.06 0.18],...
    'FaceColor',C.boxFill,'EdgeColor',C.boxEdge,'LineWidth',1.4);
txt(ax,70,38.6,'启动成功温度判据：T_1,T_2,T_3,T_4,T_5 均大于 0 ℃；端板温度 \theta_L、\theta_R 不计入该判据',CN,11,'bold',C.dark);
txt(ax,70,35.2,'同时检查：各片局部冰体积分数 < 0.99，且启动过程中各片电压均不低于 0.30 V',CN,10.5,'normal',C.gray);

%% ===== 下方：单片电池热学重复单元 =====
txt(ax,56,30.3,'单片电池热学重复单元及厚度口径',CN,14,'bold',C.dark);
txt(ax,56,27.0,'第 k 片：aBP—五层MEA—cBP，完整热域厚度 L_c = 4.3267 mm',CN,11,'bold',C.dark);
txt(ax,56,24.1,'组堆示意中，相邻单片的 cBP/aBP 界面合并表示为一块片间共享双极板',CN,9.5,'normal',C.gray);

% 七块：缩写 / 中文 / 颜色
abbr={'aBP','aGDL','aCL','PEM','cCL','cGDL','cBP'};
cnName={'阳极双极板','阳极气体扩散层','阳极催化层','质子交换膜','阴极催化层','阴极气体扩散层','阴极双极板'};
repFill=[[64 120 184];[166 199 227];[107 171 214];[237 209 115];[224 140 77];[184 214 184];[77 163 199]]/255;
repW=[1090 980 655 873 652 983 1087];
x0=17; xEnd=95; sc=(xEnd-x0)/sum(repW);
repL=x0+[0 cumsum(repW(1:end-1))]*sc; repWw=repW*sc; repC=repL+repWw/2;
rbB=11; rbT=21;
tc=repmat(C.dark,7,1); tc(1,:)=C.white; tc(7,:)=C.white;
for k=1:7
    rectf(ax,[repL(k) rbB repWw(k) rbT-rbB],repFill(k,:),C.nodeEdge,1.3);
    text(ax,repC(k),18.0,abbr{k},'FontName',EN,'FontSize',12,'FontWeight','bold',...
        'HorizontalAlignment','center','VerticalAlignment','middle','Color',tc(k,:));
    text(ax,repC(k),13.7,cnName{k},'FontName',CN,'FontSize',9.5,...
        'HorizontalAlignment','center','VerticalAlignment','middle','Color',tc(k,:));
end
% 尺寸线
yDim=9.3;
segdim(ax,x0,repL(2),repFill(1,:),'2 mm');
segdim(ax,repL(2),repL(7),[0.55 0.38 0.10],'五层MEA：0.3267 mm');
segdim(ax,repL(7),xEnd,repFill(7,:),'2 mm');

% ---- 计算域说明 ----
rectangle(ax,'Position',[102 10.5 32 12.3],'Curvature',[0.07 0.10],...
    'FaceColor',[0.98 0.98 0.96],'EdgeColor',[0.6 0.58 0.52],'LineWidth',1.2);
txt(ax,118,21.0,'计算域说明',CN,11,'bold',C.dark);
bullets={'五层MEA：质量传输、反应与相变','双极板：只计算热传导','反应热只布置在MEA',...
         '端板是独立热容节点','片间热流在全堆求和后抵消'};
for i=1:5
    text(ax,104,19.0-(i-1)*2.05,['\bullet ',bullets{i}],'FontName',CN,'FontSize',9,...
        'HorizontalAlignment','left','Color',C.dark);
end

%% ===== 底部图例 =====
ly=4.6;
swatch(ax,8,ly,C.bpA); txt(ax,11.5,ly,'阳极边界双极板',CN,9.5,'normal',C.dark);
swatch(ax,40,ly,C.cell); txt(ax,43.5,ly,'单电池MEA',CN,9.5,'normal',C.dark);
swatch(ax,64,ly,C.bpS); txt(ax,67.5,ly,'片间共享双极板',CN,9.5,'normal',C.dark);
swatch(ax,96,ly,C.bpC); txt(ax,99.5,ly,'阴极边界双极板',CN,9.5,'normal',C.dark);
ly2=2.0;
swatch(ax,32,ly2,C.plate); txt(ax,35.5,ly2,'端板',CN,9.5,'normal',C.dark);
plot(ax,[58 64],[ly2 ly2],'-','Color',C.red,'LineWidth',1.8); txt(ax,67,ly2,'导热方向',CN,9.5,'normal',C.dark);
plot(ax,[86 92],[ly2 ly2],'-','Color',C.green,'LineWidth',1.8); txt(ax,95,ly2,'环境对流',CN,9.5,'normal',C.dark);
txt(ax,70,0.5,'注：示意图用于说明模型节点与传热关系；各层绘制宽度不代表实际几何比例。',CN,8.5,'normal',C.gray);

%% ===== 导出 EPS / PDF（矢量，带重试与句柄保护）=====
drawnow; drawnow; pause(0.8);
base=fullfile(pwd,'问题二电堆热网络与计算节点示意图');
ok=false;
for attempt=1:4
    if ~isvalid(fig), break; end
    try
        exportgraphics(ax,[base,'.eps'],'ContentType','vector');
        exportgraphics(ax,[base,'.pdf'],'ContentType','vector');
        ok=true; break;
    catch
        pause(1.2);
    end
end
if ~ok && isvalid(fig)
    print(fig,[base,'.eps'],'-depsc','-painters');
    print(fig,[base,'.pdf'],'-dpdf','-painters');
    ok=true;
end
% 位图预览
if isvalid(fig)
    try, exportgraphics(ax,[base,'.png'],'Resolution',200); catch, end
end
if ok, fprintf('完成：已导出 EPS / PDF。\n'); else, fprintf('导出失败：图窗句柄失效。\n'); end
end

%% ================= 本地辅助函数 =================
function txt(ax,x,y,s,font,fs,wgt,col)
text(ax,x,y,s,'FontName',font,'FontSize',fs,'FontWeight',wgt,'Color',col,...
    'HorizontalAlignment','center','VerticalAlignment','middle');
end

function rectf(ax,pos,face,edge,lw)
rectangle(ax,'Position',pos,'FaceColor',face,'EdgeColor',edge,'LineWidth',lw);
end

function envbox(ax,xx)
rectangle(ax,'Position',[xx(1) 52 diff(xx) 16],'Curvature',[0.12 0.12],...
    'FaceColor',[0.94 0.98 0.95],'EdgeColor',[0.18 0.55 0.35],'LineWidth',1.4);
end

function ellipse(ax,xc,yc,rx,ry,face,edge,lw)
rectangle(ax,'Position',[xc-rx yc-ry 2*rx 2*ry],'Curvature',[1 1],...
    'FaceColor',face,'EdgeColor',edge,'LineWidth',lw);
end

function swatch(ax,xc,yc,col)
rectangle(ax,'Position',[xc-2.2 yc-1.1 4.4 2.2],'FaceColor',col,...
    'EdgeColor',[0.13 0.16 0.20],'LineWidth',1.1);
end

function darrow(ax,x0,x1,y,col)   % 水平双向箭头
ah=0.75; aw=0.85;
plot(ax,[x0+ah x1-ah],[y y],'-','Color',col,'LineWidth',1.5);
fill(ax,[x1 x1-ah x1-ah],[y y+aw y-aw],col,'EdgeColor','none');
fill(ax,[x0 x0+ah x0+ah],[y y+aw y-aw],col,'EdgeColor','none');
end

function sarrow(ax,x0,x1,y,col)   % 水平单向箭头
ah=1.1; aw=0.95;
plot(ax,[x0 x1-ah],[y y],'-','Color',col,'LineWidth',1.8);
fill(ax,[x1 x1-ah x1-ah],[y y+aw y-aw],col,'EdgeColor','none');
end

function segdim(ax,x0,x1,col,lab)
yDim=9.5;
plot(ax,[x0 x1],[yDim yDim],'-','Color',col,'LineWidth',1.6);
plot(ax,[x0 x0],[yDim-0.8 yDim+0.8],'-','Color',col,'LineWidth',1.6);
plot(ax,[x1 x1],[yDim-0.8 yDim+0.8],'-','Color',col,'LineWidth',1.6);
text(ax,(x0+x1)/2,7.6,lab,'FontName','Microsoft YaHei','FontSize',10,'FontWeight','bold',...
    'HorizontalAlignment','center','VerticalAlignment','middle','Color',col);
end
