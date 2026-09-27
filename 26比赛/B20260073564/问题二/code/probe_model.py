from stack_model import simulate
import json
for T in [-10,-12,-14,-16,-18,-20,-25]:
    s,*_=simulate('constant',[.5],T0=T,dt=.05)
    print(T,json.dumps(s),flush=True)
