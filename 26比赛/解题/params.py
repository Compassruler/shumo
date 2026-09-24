"""附件1参数。

所有计算量尽量采用 SI （国际单位制）单位，直接导入 P 使用：

    from params import P
    area = P.geo.area
    rho_ice = P.thermal.ice.rho
"""

from types import SimpleNamespace as S


# 几何参数
P = S()
P.geo = S(
    area=25e-4,              # 活化面积, m^2
    end_plate=0.01,          # 端板厚度, m
    bp_a=0.002,              # 阳极双极板厚度, m
    bp_c=0.002,              # 阴极双极板厚度, m
    gdl_a=150e-6,            # 阳极 GDL 厚度, m
    gdl_c=150e-6,            # 阴极 GDL 厚度, m
    cl_a=3.4e-6,             # 阳极 CL 厚度, m
    cl_c=11.3e-6,            # 阴极 CL 厚度, m
    pem=12e-6,               # 质子交换膜厚度, m
)

# 多孔介质参数
P.porous = S(
    eps_gdl_a=0.8,
    eps_gdl_c=0.8,
    eps_cl_a=0.3916,
    eps_cl_c=0.4207,
    theta_gdl=110.0,            # 接触角, deg
    theta_cl=100.0,             # 接触角, deg
    permeability_gdl=6.2e-12,  # m^2
    permeability_cl=6.2e-13,   # m^2
    # 有效导热系数由孔隙率、相含量及各材料导热系数计算
)

# 电化学参数
P.echem = S(
    voltage_initial=0.95,    # 初始开路电压, V
    temperature_ref=298.15,  # 参考温度, K
    ice_area_exponent=3.5,   # 阴极冰覆盖活性面积指数
    concentration_factor_end=10.0,
    concentration_factor_middle=1.0,
)

# 膜参数
P.membrane = S(
    thickness=12e-6,         # m；附件中与 P.geo.pem 重复
    rho=2150.0,              # kg/m^3
    equivalent_weight=1.0,   # kg/mol，由 1000 g/mol 换算
    lambda_initial=3.0,
    cl_ionomer_fraction=0.3,
)

# 材料物性：rho[kg/m^3], cp[J/(kg K)], k[W/(m K)], sigma[S/m]
P.thermal = S(
    vapor=S(rho=4.8e-3, cp=2000.0, k=0.1),
    ice=S(rho=920.0, cp=2050.0, k=2.3),
    liquid=S(rho=990.0, cp=4182.0, k=0.6),
    hydrogen=S(rho=0.089, cp=14283.0, k=0.1672),
    oxygen=S(rho=1.43, cp=919.31, k=0.0246),
    nitrogen=S(rho=1.35, cp=1041.5, k=0.0235),
    ionomer=S(rho=2150.0, cp=1050.0, k=0.24),
    bp=S(rho=1980.0, cp=766.0, k=95.0, sigma=83000.0),
    gdl=S(rho=185.0, cp=545.0, k=0.3, sigma=375.0),
    cl=S(rho=970.0, cp=240.0, k=0.27),
    end_plate=S(rho=7900.0, cp=500.0, k=15.0),
    h=40.0,                      # 端板对流换热系数, W/(m^2 K)
    latent_condensation=2.5e6,  # 水凝结潜热, J/kg
    latent_freezing=333600.0,   # 水冻结潜热, J/kg
)

# 水传输参数；成对参数按附件原顺序保留
P.water = S(
    membrane_vapor=(0.001, 1.0),
    membrane_liquid=0.5,
    membrane_ice=1.0,
    vapor_liquid=(1.0, 1.0),
    vapor_ice=1e-4,
)

# 运行参数
P.operation = S(
    temperature_initial=253.15,  # K
    temperature_ambient=253.15,  # K
    vapor_mass_fraction_anode=0.0,
    vapor_mass_fraction_cathode=0.0,
    liquid_initial=0.0,
    ice_fraction_initial=0.0,
    pressure=101325.0,            # Pa
    hydrogen_mass_fraction=1.0,
    oxygen_mass_fraction=0.233,
    nitrogen_mass_fraction=0.767,
    tolerance=1e-6,
)

# 第一问代码补充参数。原附件1参数保留原值；下面明确区分题给常数、
# 建模假设和数值设置。不要将优化初猜误认为附件给定或已验证的物性。
P.constants = S(
    R=8.314,                 # 气体常数，J/(mol K)，题备注1
    F=96485.0,               # 法拉第常数，C/mol，题备注1
    M_water=0.018,           # 水摩尔质量，kg/mol，题备注1
    M_oxygen=0.032,          # O2摩尔质量，kg/mol，通用近似常数
    M_nitrogen=0.028,        # N2摩尔质量，kg/mol，通用近似常数
)
P.cold_start = S(
    alpha=0.5,                      # 电荷传递系数，题备注1式(39)
    activation_energy=67000.0,       # 活化能，J/mol，题备注1式(40)
    j0_ref=0.01,                    # 参考交换电流密度优化初猜，A/m²；题给初猜
    contact_resistance=1e-6,         # 面积比接触电阻，Ωm²；0.01 Ωcm²换算
    thermoneutral_voltage=1.48,      # 热中性电压，V；题备注1式(35)
    reference_pressure=101325.0,     # 参考压力，Pa；题备注1
    freezing_temperature=273.15,    # 常压相变温度，K；MD假设H3
    k_freeze=0.1,                   # 冻结速率主情景，s^-1；不是附件1参数，另做0.01--1敏感性
    k_melt_ratio=1.0,               # k_m/k_f，MD暂取对称速率；未经融化数据验证
    boundary_water_transfer_factor=0.1, # 流道有限排湿修正；1为原理想干气边界
    D_hydrogen_ref=1.10e-4,          # H2参考扩散系数，m²/s；题式(17)
    D_oxygen_ref=2.20e-5,            # O2参考扩散系数，m²/s；题式(17)
    D_water_anode_ref=8.69e-5,       # 阳极蒸气参考扩散系数，m²/s；沿用题式(23)，新版相别解释
    D_water_cathode_ref=2.48e-5,     # 阴极蒸气参考扩散系数，m²/s；液水不使用此系数
    temperature_exponent=1.75,      # 扩散温度指数，题式(16)
    porosity_exponent=1.5,          # Bruggeman指数，题式(16)，不参与拟合
    # 数值设置：依次为aBP,aGDL,aCL,PEM,cCL,cGDL,cBP的有限体积单元数。
    # 每层加倍及收紧容差进行收敛检查；不是附件物性。
    grid=(8, 12, 8, 12, 8, 12, 8),
    rtol=1e-6,                     # 尺度化状态的相对积分误差控制
    atol=1e-9,                     # 尺度化状态的绝对积分误差控制
    max_step=0.05,                 # 最大积分步长，s
    fit_j0_bounds=(1e-5, 1e3),      # A/m²，对数搜索边界；数值选择
    fit_k_bounds=(1e-4, 1e2),       # s^-1，初始剖面搜索边界；非已知物性范围
    fit_k_starts=(0.01, 1.0, 100.0),# MD建议多初猜；不代表三组已知物性
)
