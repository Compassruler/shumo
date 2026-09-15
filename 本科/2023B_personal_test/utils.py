import numpy as np
import matplotlib.pyplot as plt
from params import *


def calculate_question_1():
    for i in range(-4, 5):
        # 海水深度 
        D = D0 - 200 * i * np.tan(alpha)
        W1_q1 = np.sin(theta/2) * D / np.sin(np.pi/2 - theta/2 - alpha)
        W2_q1 = np.sin(theta/2) * D / np.sin(np.pi/2 - theta/2 + alpha)
        # 覆盖宽度
        W_q1 = W1_q1 + W2_q1
        # 重叠率
        d_1 = 200 * np.sin(np.pi / 2 - theta/2) / np.sin(np.pi / 2 - alpha + theta / 2)
        yita = 1 - d_1 / W_q1
        if i == -4:
            yita = "None"
        else:
            yita = yita = 1 - d_1 / W_q1
        print("重叠率", yita, "覆盖宽度/m", W_q1, "海水深度/m", D, "测线间距中心点处的距离/m", 200*i)


def calculate_question_2():
    for beta_ in beta:
        print(f"\n当测线方向夹角为{np.degrees(beta_)}时：")
        for i2 in range (0, 8):
            a = np.arctan(-np.tan(alpha) * np.cos(beta_)) # 测线方向在坡面上的投影和在水平面上的投影的夹角a
            b = np.arctan(np.tan(alpha) * np.sin(beta_)) # 与测线垂直方向在坡面上的投影和水平面上的投影的夹角b
            D_a  = D_question2  - 0.3 * 1852 * i2 * np.tan(a)
            W1_q2 = D_a * np.sin(theta / 2) / np.cos(theta / 2 + b)
            W2_q2 = D_a * np.sin(theta / 2) / np.cos(theta / 2 - b)
            W_q2 = W1_q2 + W2_q2
            print(f"当距海域中心的距离为{(0.3 * i2):.1f}时，覆盖宽度为{W_q2}")


def q3_draw():
    # 找到覆盖宽度最大时beta的值
    i2 = 0
    W_q2_values = []

    for beta_ in beta_degrees:
        beta_rad = np.radians(beta_)
        a = np.arctan(-np.tan(alpha) * np.cos(beta_rad))  # 测线方向在坡面上的投影和在水平面上的投影的夹角a
        b = np.arctan(np.tan(alpha) * np.sin(beta_rad))  # 与测线垂直方向在坡面上的投影和水平面上的投影的夹角b
        D_a = D_question2 - 0.3 * 1852 * i2 * np.tan(a)
        W1_q2 = D_a * np.sin(theta / 2) / np.cos(theta / 2 + b)
        W2_q2 = D_a * np.sin(theta / 2) / np.cos(theta / 2 - b)
        W_q2 = W1_q2 + W2_q2
        W_q2_values.append(W_q2)

    plt.plot(beta_degrees, W_q2_values)
    plt.xlabel('β/degree')
    plt.ylabel('W/meter')
    plt.title('w - β change')
    plt.grid(True) # 添加网格线
    plt.show()


def calculate_q3():
    D = [0] * 200
    d = [0] * 200
    x = [0] * 200
    # 初始化
    d[0] = d1
    D[0] = D_1
    x[0] = x1
    for i in range (1 , 50):
        # 迭代
        x[i] = x[i - 1] + d[i - 1]
        D[i] = D[i - 1] - d[i - 1] * np.tan(alpha)
        d[i] = np.sin(theta/2) * D[i] / np.cos(theta / 2 + alpha) + np.sin(theta/2) * D[i] / np.cos(theta / 2 - alpha) * np.sin(np.pi / 2 - alpha - theta / 2) / np.sin(np.pi/2 + theta / 2) * (1 - yita_q3)
        print(f"测线距海底深度:D{[i+1]}:{D[i]}  测线坐标x: x{[i+1]}:{x[i]}")
        if x[i] + np.sin(theta/2) * D[i] / np.sin(np.pi/2 - theta/2 + alpha) > 4 * 1852:
            break

