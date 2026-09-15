import numpy as np

# question1
D0 = 70 # 中心海水深度70m
alpha = np.radians(1.5) # 把alpha角度转换为弧度
theta = np.radians(120) # 把theta角度转换为弧度


# question2
D_question2 = 120 # 中心海水深度120m
beta = np.radians([0, 45, 90, 135, 180, 225, 270, 315]) # 测线方向夹角beta


# question3
yita_q3 = 0.1
beta_degrees = np.arange(0,360)
D_question3 = 110 # 中心点海水深度110m
L_es = 4 * 1852 # 东西长4海里
D_max = D_question3 + L_es / 2 * np.tan(alpha) # 海域最大深度
x1 = D_max * np.tan(theta / 2) # 第一条测线坐标
D_1 = D_max - x1 * np.tan(alpha) # 第一次测线海水深度
d1 = np.sin(theta/2) * D_1 / np.cos(theta / 2 + alpha) + np.sin(theta/2) * D_1 / np.cos(theta / 2 - alpha) * np.sin(np.pi / 2 - alpha - theta / 2) / np.sin(np.pi/2 + theta / 2) * (1 - yita_q3)