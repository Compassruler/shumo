# 第七章结果细审证据

仅提取已归档 CSV、核对绘图代码，没有重算物理模型，也没有改动结果源文件。路径基准：`D:\shumo\26比赛\解题\问题4_求解结果`。本文件供论文7.4写作；数字保留工作精度，正文宜适当舍入。

## 1. 16幅图的数据对应核对

核对依据：`figures/figure_manifest.csv` 与 `code/plot_results.py`。全部列出的 CSV 和 PNG/SVG/PDF 文件均存在。图01的几何端板阴影还读取 precooling_layers.csv（manifest主要列数值场源）；没有由此改变温度数据。


### 图源与文件存在性


| 图 | 源CSV | 文件存在 | 注意 |
| --- | --- | --- | --- |
| 图01_预冷温度场族 | precooling_fields.csv | 是 | 连续空间温度场保留曲线与时间色标；浅灰区域为两端端板。 |
| 图02_预冷均温与温差 | precooling_nodes.csv | 是 |  |
| 图03_三工况初始温度 | initial_temperature_cases.csv | 是 |  |
| 图04_case1_动态控制轨迹 | trajectory_case1_guarded.csv;trajectory_case1_constant_hold.csv | 是 | 工况1：完全冷却｜推荐动态全过程；阴影为关热后验证；功率圆点对应前一积分区间的实际加热；所有时刻均保留，圆点之间不连线。 |
| 图05_case2_动态控制轨迹 | trajectory_case2_guarded.csv;trajectory_case2_constant_hold.csv | 是 | 工况2：预冷20 min｜推荐动态全过程；阴影为关热后验证；功率圆点对应前一积分区间的实际加热；所有时刻均保留，圆点之间不连线。 |
| 图06_case3_动态控制轨迹 | trajectory_case3_guarded.csv;trajectory_case3_constant_hold.csv | 是 | 工况3：预冷40 min｜推荐动态全过程；阴影为关热后验证；功率圆点对应前一积分区间的实际加热；所有时刻均保留，圆点之间不连线。 |
| 图07_三工况主指标比较 | guarded_results.csv;main_results.csv | 是 | 推荐动态与固定C：相同传感温度裕度与2 s连续测量保持，统计到实际关热 |
| 图08_预冷时间扫描 | constant_scan.csv | 是 | 固定问题三功率分配，10–100 min预冷共19点扫描 |
| 图09_能量收支与累积能耗 | guarded_results.csv;main_results.csv;trajectory_case1_guarded.csv;trajectory_case2_guarded.csv;trajectory_case3_guarded.csv | 是 |  |
| 图10_网格步长与控制周期检验 | precooling_convergence.csv;guarded_convergence.csv;coupled_convergence.csv | 是 |  |
| 图11_物理参数与控制器敏感性 | precooling_sensitivity.csv;sensitivity.csv | 是 |  |
| 图12_测量噪声与初场扰动 | robustness.csv | 是 | 名义优选策略的测量/初场扰动：全部样本用圆点；红圈为任一约束失败 |
| 图13_名义与留裕度备选 | main_results.csv;guarded_results.csv;robustness.csv;guarded_robustness.csv | 是 | 名义能耗优选与推荐留裕度方案：独立试验通过率和关热后状态分别报告 |
| 图14_重优化恒功率与推荐动态 | optimized_constant_results.csv;guarded_results.csv;main_results.csv | 是 | 共同采样停机规则：固定功率、有限搜索重优化恒功率与推荐动态 |
| 图15_能耗时间候选前沿 | constant_time_frontier.csv;constant_optimization_search.csv;main_results.csv;guarded_results.csv;constant_baselines.csv | 是 | 有限搜索的能耗—时限边界；允许相同最优候选形成平段，不是全局最优证明 |
| 图16_观测器误差与测量停机 | observer_example_results.csv;trajectory_case1_observer_example.csv;trajectory_case2_observer_example.csv;trajectory_case3_observer_example.csv | 是 | 独立观测器：未参与训练的参数失配与测量噪声样例 |

**图源口径提醒：**图04–06绘制的是 `trajectory_case*_guarded.csv`，虽文件名写“动态”，不是名义 dynamic。图07/09主比较为 guarded 与 constant_hold。图10启动部分是 guarded；图11下半是 case1 的名义 dynamic 单因素扰动，不能称推荐方案敏感性。图12全部是名义 dynamic 的1000–1009种子组；图13并列名义组和推荐组各自独立种子比例，不是配对实验。图14比较三种冻结策略。图15为有限候选能耗—时间关系，不是全局 Pareto 前沿证明。图16是7010物性失配＋噪声例子，冰误差图画“经电压修正的风险软测量误差”，与汇总CSV的 `observer_max_ice_error`（冰先验误差）不同。

## 2. 推荐控制逐片能耗、持续时长与实际状态

`code/finalize_tables.py:16–28`：功率列属于截止行时刻的前一区间；状态列属于下一积分区间。average_power 是整段0至t_off上的平均功率，不是只在通电时平均；heating_duration 是q>1e-10的区间总时长，不保证连续。停机状态5在本表0至t_off窗口持续时间为0，不代表停机未执行。


### 逐片加热指标


数据源：`data/per_cell_heater_energy.csv`。line 为 CSV 物理行号（含表头）。


| _line | case | cell | energy_J | average_power_W_cm2 | peak_power_W_cm2 | heating_duration_s |
| --- | --- | --- | --- | --- | --- | --- |
| 47 | case1 | 1 | 1413.246074 | 0.642385 | 1 | 88 |
| 48 | case1 | 2 | 34.528598 | 0.015695 | 0.464798 | 24.4 |
| 49 | case1 | 3 | 34.447143 | 0.015658 | 0.464798 | 24.6 |
| 50 | case1 | 4 | 34.528598 | 0.015695 | 0.464798 | 24.4 |
| 51 | case1 | 5 | 1413.246074 | 0.642385 | 1 | 88 |
| 52 | case2 | 1 | 134.347102 | 0.06872 | 0.124292 | 67.4 |
| 53 | case2 | 2 | 9.67364 | 0.004948 | 0.024672 | 21.6 |
| 54 | case2 | 3 | 5.566152 | 0.002847 | 0.016669 | 17.4 |
| 55 | case2 | 4 | 9.673772 | 0.004948 | 0.024672 | 21.6 |
| 56 | case2 | 5 | 134.348169 | 0.06872 | 0.124293 | 67.4 |
| 57 | case3 | 1 | 899.926696 | 0.392981 | 0.597824 | 91.6 |
| 58 | case3 | 2 | 18.566176 | 0.008108 | 0.219323 | 18.4 |
| 59 | case3 | 3 | 18.398535 | 0.008034 | 0.21895 | 18.4 |
| 60 | case3 | 4 | 18.56623 | 0.008108 | 0.219323 | 18.4 |
| 61 | case3 | 5 | 899.927354 | 0.392981 | 0.597824 | 91.6 |


### 由逐片CSV直接汇总的端部耗电占比


| case | 端部两片能耗J | 端部占比% |
| --- | --- | --- |
| case1 | 2826.492149 | 96.467424 |
| case2 | 268.695271 | 91.514709 |
| case3 | 1799.854049 | 97.007039 |


### 状态持续时长


数据源：`data/controller_state_duration.csv`。line 为 CSV 物理行号（含表头）。


| case | cell | 状态1安全增强/s | 状态2低温温升不足/s | 状态3正常跟踪/s | 状态4近目标渐缩/s | 状态5关热/s |
| --- | --- | --- | --- | --- | --- | --- |
| case1 | 1 | 0 | 0.4 | 85 | 2.6 | 0 |
| case1 | 2 | 0 | 1.2 | 71.2 | 15.6 | 0 |
| case1 | 3 | 0 | 1.2 | 67.4 | 19.4 | 0 |
| case1 | 4 | 0 | 1.2 | 71.2 | 15.6 | 0 |
| case1 | 5 | 0 | 0.4 | 85 | 2.6 | 0 |
| case2 | 1 | 0 | 12 | 62.4 | 3.8 | 0 |
| case2 | 2 | 0 | 7.4 | 38.8 | 32 | 0 |
| case2 | 3 | 0 | 6.2 | 36.6 | 35.4 | 0 |
| case2 | 4 | 0 | 7.4 | 38.8 | 32 | 0 |
| case2 | 5 | 0 | 12 | 62.4 | 3.8 | 0 |
| case3 | 1 | 0 | 0.2 | 88.6 | 2.8 | 0 |
| case3 | 2 | 0 | 0.2 | 67.2 | 24.2 | 0 |
| case3 | 3 | 0 | 0.2 | 62.2 | 29.2 | 0 |
| case3 | 4 | 0 | 0.2 | 67.2 | 24.2 | 0 |
| case3 | 5 | 0 | 0.2 | 88.6 | 2.8 | 0 |

**可解释机制：**加热能量主要分配给端部第1、5片；中部2–4片通电时间显著短。对称结构导致两端近似对称（预冷材料取向不完全对称，勿宣称位数完全相等）。三工况推荐名义轨迹的安全增强状态1均未实际触发，风险通道是后备，不能把“频繁风险触发”当作这三条曲线节能的实证解释。状态2、3即使激活也可能经限幅得到0功率，所以状态时长不同于通电时长。

## 3. 观测误差与测量确认时刻

图16固定例子：seed=7010，初场整体−1 K，G×0.8、G_EP×1.2、h×1.2，测温噪声标准差0.2 K、测压0.005 V。初场扰动作为双方共同先验；没有额外检验未知端板初温偏差。观测器仍用名义物性。


### 观测器与测量停机例子的汇总及图中实际误差指标


数据源：`data/observer_example_results.csv + trajectory_case*_observer_example.csv`。line 为 CSV 物理行号（含表头）。


| case | first_success_s | stop_s | physical_hold_s | observer_max_temperature_error_K | observer_max_ice_error | min_voltage_V | max_ice_bulk | feasible | 图16五片温度误差峰K | 图16端板误差峰K | 图16校正冰风险误差峰 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case1 | 90.697957 | 95 | 4.302043 | 1.810477 | 0.001683 | 0.556907 | 0.3021 | True | 0.689555 | 1.810477 | 0.004409 |
| case2 | 82.613362 | 91 | 8.386638 | 0.689503 | 0.001172 | 0.600532 | 0.114237 | True | 0.689503 | 0.622491 | 0.003686 |
| case3 | 89.074862 | 92.6 | 3.525138 | 1.325942 | 0.001563 | 0.570409 | 0.251331 | True | 0.689418 | 1.325942 | 0.004184 |

`observer_max_temperature_error_K` 是包含端板的七节点热状态预测最大误差；`observer_max_ice_error` 是独立模型冰先验误差，图16风险软测量经电压创新校正后误差另列。名义完全匹配时 guarded_results 中上述观测器误差均为0，这只说明同类模型同步，不是实物估计准确性证据。首次到停机的间隔可以大于2 s，因为滤波温度须超过0.2 ℃并连续满足采样条件。

## 4. 启动能量分解与停机后60 s

启动账目：E_aux + E_gen + E_phase = E_loss + E_sensible；E_phase为净释热，负数表示净吸热。统计窗口到实际t_off，后验段不混入。动态较慢，反应热更大、累计电荷更大，辅助节电不等价于氢耗或全系统能耗下降。


### 推荐与固定C的能量分解


数据源：`data/guarded_results.csv;data/main_results.csv`。line 为 CSV 物理行号（含表头）。


| case | strategy | E_aux_J | E_gen_J | E_phase_J | E_loss_J | E_sensible_J | charge_at_success_C_cm2 | charge_at_stop_C_cm2 | energy_residual_J | max_water_residual_kg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case1 | guarded | 2929.996488 | 1941.572387 | 13.45385 | 272.960995 | 4612.06173 | 16.573314 | 17.4 | 2.03613e-10 | 1.72519e-16 |
| case2 | guarded | 293.608835 | 1533.862102 | -2.020267 | 394.055569 | 1431.3951 | 13.292515 | 14.46 | 2.6148e-11 | 5.86807e-16 |
| case3 | guarded | 1855.38499 | 2027.484304 | 8.318312 | 354.474035 | 3536.71357 | 17.561632 | 18.48 | 6.66773e-11 | 4.66955e-16 |
| case1 | constant_hold | 3260.280649 | 194.958918 | -1.116903 | 105.032366 | 3349.090297 | 1.656527 | 1.9881 | 2.87358e-10 | 6.38427e-17 |
| case2 | constant_hold | 924.902312 | 14.376857 | -0.333089 | 44.003762 | 894.942317 | 0.078571 | 0.16 | 3.42766e-11 | 1.99591e-17 |
| case3 | constant_hold | 2242.888106 | 89.982534 | -0.808891 | 84.485159 | 2247.576591 | 0.725638 | 0.9409 | 1.44169e-10 | 1.33381e-17 |


### 关热状态及60s后验极值


数据源：`data/guarded_results.csv;data/main_results.csv`。line 为 CSV 物理行号（含表头）。


| case | strategy | final_min_T_C | final_max_T_C | final_left_EP_C | post_min_T_C | post_min_voltage_V | post_max_ice_bulk | post_energy_J |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case1 | guarded | 0.881909 | 6.762496 | -14.471409 | -4.50752 | 0.559667 | 0.501042 | 0 |
| case2 | guarded | 0.432521 | 9.48683 | -5.115074 | 0.432521 | 0.613762 | 0.087024 | 0 |
| case3 | guarded | 0.763164 | 7.673405 | -10.288106 | -1.909916 | 0.588533 | 0.295656 | 0 |
| case1 | constant_hold | 1.926528 | 28.929267 | -23.373778 | -7.986187 | 0.576876 | 0.272359 | 0 |
| case2 | constant_hold | 3.026775 | 11.742284 | -8.507928 | -2.676797 | 0.61795 | 0.030161 | 0 |
| case3 | constant_hold | 2.120079 | 21.972409 | -18.618321 | -6.556292 | 0.592336 | 0.178504 | 0 |

**机理可据：**关热时端板仍明显低温，继续从电池吸热；完全冷却与40 min推荐策略后验最低片温降至−4.5075/−1.9099 ℃。但对应后验最低电压0.5597/0.5885 V仍高于0.30 V、最大冰量0.5010/0.2957仍低于0.99，因此本次失败的是持续暖态，不应笼统写为已发生低压或严重冰堵。三工况推荐后验均q=0，不能说仿真自动重新加热维持。

## 5. 单因素敏感性与物性失配：务必区分数据组

`data/sensitivity.csv` 的48组围绕名义 dynamic 冻结参数，不是guarded；源代码 run_problem4.py:68–86。G、G_EP、h各乘0.8/1.2；T_target、K_P、K_I、ice_warn、delta_V各乘0.8/1.2。物理18组全部通过，48组共46组通过。仅T_target×0.8在case1/case3未完成测量停机，首次事件仍出现且电压、冰量未越硬阈值。负stop=-1为缺失事件哨兵。


### 名义单因素敏感性全部失败行


数据源：`data/sensitivity.csv`。line 为 CSV 物理行号（含表头）。


| _line | case | parameter | factor | E_aux_J | first_success_s | stop_s | min_voltage_V | max_ice_bulk | physical_hold_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | case1 | T_target | 0.8 | 2849.438342 | 95.95457 | -1 | 0.550268 | 0.350877 | 0 |
| 40 | case3 | T_target | 0.8 | 1748.116254 | 95.981215 | -1 | 0.568343 | 0.282162 | 0 |


### 名义物理参数单因素响应


数据源：`data/sensitivity.csv`。line 为 CSV 物理行号（含表头）。


| _line | case | parameter | factor | E_aux_J | first_success_s | stop_s | dTmax_K | feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | case1 | G | 0.8 | 2891.274671 | 95.709094 | 98.6 | 8.052442 | True |
| 3 | case1 | G | 1.2 | 2834.854422 | 95.657602 | 98.4 | 5.714619 | True |
| 4 | case1 | G_EP | 0.8 | 2453.250554 | 95.755733 | 98.6 | 6.668441 | True |
| 5 | case1 | G_EP | 1.2 | 3190.956706 | 95.547586 | 98.4 | 6.631891 | True |
| 6 | case1 | h | 0.8 | 2796.769951 | 95.630722 | 98.4 | 6.650717 | True |
| 7 | case1 | h | 1.2 | 2921.150868 | 95.708262 | 98.6 | 6.653155 | True |
| 18 | case2 | G | 0.8 | 0 | 87.012303 | 91.2 | 10.830455 | True |
| 19 | case2 | G | 1.2 | 0 | 83.142734 | 87.2 | 7.454447 | True |
| 20 | case2 | G_EP | 0.8 | 0 | 76.78338 | 80.6 | 8.618724 | True |
| 21 | case2 | G_EP | 1.2 | 0 | 91.276605 | 95.4 | 8.897623 | True |
| 22 | case2 | h | 0.8 | 0 | 80.221034 | 84.2 | 8.780237 | True |
| 23 | case2 | h | 1.2 | 0 | 89.736342 | 94 | 8.873276 | True |
| 34 | case3 | G | 0.8 | 1802.936437 | 95.358769 | 98.4 | 9.025544 | True |
| 35 | case3 | G | 1.2 | 1741.587897 | 95.378595 | 98.4 | 6.415234 | True |
| 36 | case3 | G_EP | 0.8 | 1465.850473 | 95.462229 | 98.6 | 7.505791 | True |
| 37 | case3 | G_EP | 1.2 | 2017.815352 | 95.252164 | 98.4 | 7.478282 | True |
| 38 | case3 | h | 0.8 | 1692.521492 | 95.339633 | 98.4 | 7.491803 | True |
| 39 | case3 | h | 1.2 | 1841.727104 | 95.388067 | 98.4 | 7.492383 | True |

可据数据解释：G增大促进均温，case1最大温差从G×0.8时8.052 K降至G×1.2时5.715 K。端板耦合G_EP最显著改变辅助电耗：case1从2453.251 J升至3190.957 J，case3从1465.850 J升至2017.815 J；更强端板耦合使冷端板热汇加重。h增大增加散热代价；20 min零功率分支能耗保持0，但首次成功对h变化从80.221 s延至89.736 s。K_P/K_I的±20%对名义输出影响较小；冰预警、电压预警变化无输出影响，与这些名义轨迹未触发风险增强相容，不能推断阈值永远不重要。


### 预冷20min代表敏感性数据


数据源：`data/precooling_sensitivity.csv`。line 为 CSV 物理行号（含表头）。


| _line | h_W_m2K | conductance_factor | mean_capacity_C | field_range_K | relative_field_range | Bi_stack |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 20 | 1 | 3.714694 | 0.412286 | 0.012229 | 0.069819 |
| 12 | 40 | 0.1 | -9.051056 | 2.240854 | 0.106967 | 1.156374 |
| 14 | 40 | 0.25 | -9.159413 | 1.062095 | 0.050963 | 0.47855 |
| 16 | 40 | 0.5 | -9.196014 | 0.689541 | 0.033145 | 0.252608 |
| 18 | 40 | 1 | -9.214375 | 0.50693 | 0.024388 | 0.139637 |
| 20 | 40 | 2 | -9.223568 | 0.416527 | 0.020048 | 0.083152 |
| 28 | 80 | 1 | -21.965005 | 0.389712 | 0.048502 | 0.279275 |
| 38 | 160 | 1 | -28.717969 | 0.122954 | 0.095905 | 0.55855 |

预冷敏感性h=20/40/80/160、BP与MEA导热倍率0.1/0.25/0.5/1/2，共40组（20/40 min）；端板本体导热不变。它采用矩阵指数解，而主初场用0.25s后向欧拉，基准均温会相差约0.002 K，不能据此误报数据冲突。绝对温差随h不必单调：h很大时整体已接近环境，剩余温差小；归一化温差与Bi增加更适合说明相对不均匀程度。这是等效参数扰动，不是测得接触热阻。

## 6. 随机与联合失配验证

名义组：种子1000–1009，每工况初场平移−1/0/+1 K，共30次；推荐与固定C、重优化恒功率的配对最终组：6000–6009，相同30场景。所有组温度/电压噪声标准差0.2 K/0.005 V。推荐参数冻结后检验；不是按照6000系列逐次调参。名义与推荐的比例不可作为配对因果估计。


### 三类策略噪声与初温组的事件/安全统计


| 组 | case | strategy | 通过 | 最低电压V | 最大冰量 | 未出现首次数 | 未完成停机数 | 真实保持不足数 | 种子 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 名义dynamic | case1 | 名义dynamic | 0/30 | 0.54765 | 0.360601 | 0 | 30 | 30 | 1000,1001,1002,1003,1004,1005,1006,1007,1008,1009 |
| 名义dynamic | case2 | 名义dynamic | 20/30 | 0.591994 | 0.16908 | 0 | 10 | 10 | 1000,1001,1002,1003,1004,1005,1006,1007,1008,1009 |
| 名义dynamic | case3 | 名义dynamic | 0/30 | 0.56597 | 0.289815 | 0 | 30 | 30 | 1000,1001,1002,1003,1004,1005,1006,1007,1008,1009 |
| 推荐guarded | case1 | 推荐guarded | 30/30 | 0.55752 | 0.290259 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 推荐guarded | case2 | 推荐guarded | 30/30 | 0.601846 | 0.106257 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 推荐guarded | case3 | 推荐guarded | 30/30 | 0.570589 | 0.25104 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case1 | constant_hold | 30/30 | 0.659118 | 0.014129 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case1 | constant_optimized | 30/30 | 0.650798 | 0.019409 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case2 | constant_hold | 30/30 | 0.7304 | 0.000146 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case2 | constant_optimized | 21/30 | 0.591994 | 0.16908 | 0 | 9 | 9 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case3 | constant_hold | 30/30 | 0.681513 | 0.003497 | 0 | 0 | 0 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |
| 恒功率两基准 | case3 | constant_optimized | 10/30 | 0.571846 | 0.275532 | 10 | 20 | 20 | 6000,6001,6002,6003,6004,6005,6006,6007,6008,6009 |

物性联合最终组每工况8次：G/G_EP/h之一±20%、初场不偏移的6次（seed7000–7005），以及(−1 K,G×0.8,G_EP×1.2,h×1.2,7010)和(+1 K,G×1.2,G_EP×0.8,h×0.8,7011)。推荐24/24、固定C24/24，重优化恒功率case1=8/8、case2=7/8、case3=3/8。重优化恒功率仅做名义优化，不能将这些失败说成恒功率类经过稳健整定后的能力上限。


### 重优化恒功率在配对物性失配组的全部失败行


数据源：`data/constant_parameter_validation.csv`。line 为 CSV 物理行号（含表头）。


| _line | case | strategy | seed | initial_shift_K | G_factor | G_EP_factor | h_factor | first_success_s | stop_s | physical_hold_s | min_voltage_V | max_ice_bulk | feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32 | case2 | constant_optimized | 7010 | -1 | 0.8 | 1.2 | 1.2 | -1 | -1 | 0 | 0.587746 | 0.219724 | False |
| 42 | case3 | constant_optimized | 7000 | 0 | 0.8 | 1 | 1 | 96.591575 | -1 | 0 | 0.575424 | 0.249827 | False |
| 43 | case3 | constant_optimized | 7001 | 0 | 1.2 | 1 | 1 | 94.394479 | -1 | 0 | 0.576968 | 0.236272 | False |
| 45 | case3 | constant_optimized | 7003 | 0 | 1 | 1.2 | 1 | -1 | -1 | 0 | 0.571413 | 0.284191 | False |
| 47 | case3 | constant_optimized | 7005 | 0 | 1 | 1 | 1.2 | 98.220923 | -1 | 0 | 0.574991 | 0.2554 | False |
| 48 | case3 | constant_optimized | 7010 | -1 | 0.8 | 1.2 | 1.2 | -1 | -1 | 0 | 0.564956 | 0.332465 | False |


### 开发期guarded_pilot失败保留


数据源：`data/guarded_pilot_robustness.csv;data/guarded_pilot_parameter_validation.csv`。line 为 CSV 物理行号（含表头）。


| case | seed | initial_shift_K | G_factor | G_EP_factor | h_factor | first_success_s | stop_s | min_voltage_V | max_ice_bulk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case3 | 3008 | -1 | 1 | 1 | 1 | 92.916979 | -1 | 0.568135 | 0.271955 |
| case3 | 3008 | 0 | 1 | 1 | 1 | 92.778522 | -1 | 0.570453 | 0.262606 |
| case1 | 5010 | -1 | 0.8 | 1.2 | 1.2 | 94.833609 | -1 | 0.550022 | 0.342221 |

开发版88/90通过，失败主要暴露首次成功有裕度仍不足以保证测量保持及时完成。因此最终训练要求首次与测量停机均不晚于94.6667 s。不要将开发期pilot 3000/5000系列失败混入冻结后6000/7000系列最终验证率。有限试验不构成高斯无界噪声下任意扰动保证。

## 7. 守恒、收敛与图10解读

守恒只证明离散账目一致，独立参考、步长网格、真实约束和观测检验提供不同证据，不能用极小残差代替所有准确性验证。


### 11项预冷验证


数据源：`data/precooling_validation.csv`。line 为 CSV 物理行号（含表头）。


| test | observed | tolerance | unit | passed | note |
| --- | --- | --- | --- | --- | --- |
| total_thickness | 6.93889e-18 | 1e-13 | m | True | 2 EP + 6 BP + 25 MEA constituent layers |
| total_capacity | 0 | 1e-08 | J/m2/K | True | Original material values, no rounded rho*cp |
| seven_node_energy_mapping | 4.65661e-10 | 1e-08 | J/m2 | True | All CVs belong to exactly one node; BP halves split geometrically |
| implicit_energy_balance | 1.56497e-07 | 2e-05 | J | True | Backward Euler loss quadrature matched to thermal equation |
| BE_vs_matrix_exponential | 0.002076 | 0.004 | K | True | dt=0.25 s, 10:5:100 min |
| adiabatic_uniform_limit | 2.71127e-09 | 2e-06 | K | True | h=0, initial 25 C |
| adiabatic_nonuniform_conservation | 2.1816e-09 | 1e-06 | J | True | h=0, nonuniform initial field |
| long_time_ambient_limit | 0 | 1e-08 | K | True | 24 hours |
| maximum_principle | 0 | 1e-10 | K | True | No new extrema under cooling |
| pointwise_monotonic_cooling | 0 | 1e-10 | K | True | Every control volume cools over the sampled times |
| approximate_mirror_symmetry | 4.69128e-05 | 0.001 | K | True | aCL and cCL thicknesses differ; actual oriented five-layer MEA is only approximately mirror symmetric |


### 预冷20min收敛代表数据


数据源：`data/precooling_convergence.csv`。line 为 CSV 物理行号（含表头）。


| study | scale | control_volumes | dt_s | max_field_error_K | max_node_error_K | reference |
| --- | --- | --- | --- | --- | --- | --- |
| time | 1 | 146 | 2 | 0.016596 | 0.016596 | same mesh, matrix exponential |
| time | 1 | 146 | 1 | 0.008301 | 0.008301 | same mesh, matrix exponential |
| time | 1 | 146 | 0.5 | 0.004151 | 0.004151 | same mesh, matrix exponential |
| time | 1 | 146 | 0.25 | 0.002076 | 0.002076 | same mesh, matrix exponential |
| time | 1 | 146 | 0.125 | 0.001038 | 0.001038 | same mesh, matrix exponential |
| space | 1 | 146 | 0 |  | 0.000179 | scale=8 seven-node energy projection, matrix exponential |
| space | 2 | 292 | 0 |  | 4.27272e-05 | scale=8 seven-node energy projection, matrix exponential |
| space | 4 | 584 | 0 |  | 8.96079e-06 | scale=8 seven-node energy projection, matrix exponential |


### 推荐冻结参数联合加密


数据源：`data/coupled_convergence.csv`。line 为 CSV 物理行号（含表头）。


| case | dt_s | scale | period_s | E_aux_J | first_success_s | stop_s | max_ice_bulk | min_voltage_V | feasible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| case1 | 0.025 | 2 | 0.2 | 2929.996488 | 85.244382 | 88 | 0.277253 | 0.560443 | True |
| case1 | 0.0125 | 4 | 0.2 | 2928.953286 | 85.24399 | 88 | 0.283414 | 0.560114 | True |
| case1 | 0.00625 | 8 | 0.2 | 2928.50764 | 85.243852 | 88 | 0.286584 | 0.559938 | True |
| case2 | 0.025 | 2 | 0.2 | 293.608835 | 74.308384 | 78.2 | 0.087293 | 0.604971 | True |
| case2 | 0.0125 | 4 | 0.2 | 293.514285 | 74.303312 | 78.2 | 0.088495 | 0.604847 | True |
| case2 | 0.00625 | 8 | 0.2 | 293.46881 | 74.300809 | 78.2 | 0.089115 | 0.604781 | True |
| case3 | 0.025 | 2 | 0.2 | 1855.38499 | 88.538772 | 91.6 | 0.239568 | 0.573319 | True |
| case3 | 0.0125 | 4 | 0.2 | 1854.729442 | 88.538909 | 91.6 | 0.243973 | 0.573061 | True |
| case3 | 0.00625 | 8 | 0.2 | 1854.43635 | 88.538975 | 91.6 | 0.24623 | 0.572925 | True |


### 正式58控制体/0.025s至232控制体/0.00625s的CSV算术比较


| case | 能耗相对变化% | 冰峰相对变化% | 首次时间差s |
| --- | --- | --- | --- |
| case1 | -0.050814 | 3.365303 | -0.00053 |
| case2 | -0.047691 | 2.088105 | -0.007575 |
| case3 | -0.051129 | 2.78066 | 0.000204 |


### 控制采样周期变化


数据源：`data/guarded_convergence.csv`。line 为 CSV 物理行号（含表头）。


| case | period_s | E_aux_J | first_success_s | stop_s | max_ice_bulk | feasible |
| --- | --- | --- | --- | --- | --- | --- |
| case1 | 0.2 | 2929.996488 | 85.244382 | 88 | 0.277253 | True |
| case1 | 0.1 | 2932.686102 | 85.210015 | 88 | 0.276928 | True |
| case1 | 0.4 | 2926.317942 | 85.287918 | 88 | 0.277747 | True |
| case2 | 0.2 | 293.608835 | 74.308384 | 78.2 | 0.087293 | True |
| case2 | 0.1 | 294.364334 | 74.278616 | 78.2 | 0.08717 | True |
| case2 | 0.4 | 293.011244 | 74.315887 | 78.4 | 0.087396 | True |
| case3 | 0.2 | 1855.38499 | 88.538772 | 91.6 | 0.239568 | True |
| case3 | 0.1 | 1854.300115 | 88.506318 | 91.5 | 0.23931 | True |
| case3 | 0.4 | 1853.01909 | 88.577222 | 91.6 | 0.239892 | True |

联合加密能耗仅约−0.05%，首次事件时间变化很小；冰峰相对仍变化约2.09%–3.37%，固定时间步空间加密时变化更明显。可称“宏观能耗与时间结果稳定，局部冰量对离散仍较敏感”，不能称完全网格无关。采样周期0.1/0.2/0.4 s全部成功，但采样决定停机时刻与保持窗口，不是纯数值积分误差，须独立说明。

## 8. 正文分配建议

7.4初场可用图01–03择重；轨迹图04–06配端部能耗占比和状态时长；综合比较用图07、14或15；预冷扫描图08；关热后可借轨迹阴影和图13；稳健性用图11–13并明确nominal/guarded标签，观测器图16作为独立失配例证；守恒图09，收敛图10。不要为覆盖16图而重复相同主结果，也不要把所有附加CSV大表放入论文正文。
