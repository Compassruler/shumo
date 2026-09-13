"""运行全部合成示例，并执行各示例中的独立数值检查。"""
import json
import platform
import numpy
import scipy
from ode_identification import demo as ode
from constrained_allocation import demo as allocation
from causal_filter import demo as filtering
from risk_path import demo as routing
from heat_equation import demo as heat


if __name__ == '__main__':
    results = {'environment': {'python': platform.python_version(),
                              'numpy': numpy.__version__, 'scipy': scipy.__version__}}
    for name, function in [('ode', ode), ('allocation', allocation),
                           ('filter', filtering), ('path', routing), ('heat', heat)]:
        results[name] = function()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print('全部 5 个示例通过。结果仅针对合成教学数据。')
