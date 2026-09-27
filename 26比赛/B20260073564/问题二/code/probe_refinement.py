from stack_model import simulate
import json,time
for scale,dt in ((8,.003125),(16,.0015625)):
    t=time.perf_counter();s,*_=simulate('constant',[.5],scale=scale,dt=dt)
    print(scale,dt,json.dumps(s),time.perf_counter()-t,flush=True)
