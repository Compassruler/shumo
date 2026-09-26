"""Executable numerical regression/limit tests independent of optimization."""
import bootstrap
import numpy as np
import pandas as pd
from pathlib import Path
import control_model as m
import q3_reference as q3

ROOT=Path(__file__).resolve().parents[1]
def main():
    checks=[]
    def add(name,value,tol):checks.append(dict(test=name,value=float(value),tolerance=tol,passed=bool(value<=tol)))
    temp=np.full(7,-30.);p=m.DEFAULT.copy();p[5]=0.
    s,h,*_=m.simulate(temp,kind='constant',params=p,dt=.025,scale=2,record=True)
    ref,hh,*_=q3.simulate('C',m.CONSTANT,100,dt=.025,scale=2,post=m.Q_TIME,stop=True,record=True)
    add('Q3_constant_success_time_error_s',abs(s['first_success_s']-ref['first_success_s']),1e-6)
    add('Q3_constant_heater_energy_error_J',abs(s['E_aux_J']-ref['E_aux_J']),1e-4)
    add('Q3_constant_voltage_error_V',abs(s['min_voltage_V']-ref['min_voltage_V']),1e-7)
    add('Q3_constant_ice_error',abs(s['max_ice_bulk']-ref['max_ice_bulk']),1e-7)
    warm,hw,*_=m.simulate(np.full(7,4.),kind='constant',post=10.,record=True)
    add('initially_warm_first_success_zero',abs(warm['first_success_s']),0.)
    add('initially_warm_energy_zero',warm['E_aux_J']+warm['post_energy_J'],0.)
    add('initially_warm_heater_locked_zero',np.max(abs(hw[:,11:16])),0.)
    sh,hs,*_=m.simulate(temp,kind='constant',post=60.,record=True)
    mask=hs[:,0]>sh['stop_s']+1e-8
    add('shutdown_latch_power_zero',np.max(abs(hs[mask,11:16])),0.)
    add('shutdown_latch_energy_zero',abs(sh['post_energy_J']),1e-10)
    add('hold_duration_error_s',abs(sh['stop_s']-sh['first_success_s']-2.),1e-7)
    cfg=m.make_config();states=[m.initial_state(cfg,293.15) for k in range(5)]
    t7=np.full(7,20.);e,d=m.evaluate(cfg,states,t7,.1,m.THERMAL)
    e[:,0]=.31;cs=np.zeros((5,7));cs[:,0]=20.;cs[:,1]=.31
    q=m.control(20.,.2,np.full(7,-30.),t7,e,d,states,cfg,m.DEFAULT,m.THERMAL,
                cs,np.zeros(5),np.zeros((5,2)))
    add('safety_priority_survives_zero_taper',max(0.,m.DEFAULT[6]-np.min(q)),1e-12)
    add('per_cell_power_bounds',max(0.,-np.min(q),np.max(q)-1.),0.)
    errors=0
    for kw in [dict(kind='typo'),dict(dt=0),dict(period=.01),dict(power=np.ones(5)*1.1)]:
        try:m.simulate(temp,**kw)
        except ValueError:errors+=1
    add('invalid_inputs_rejected',4-errors,0.)
    df=pd.DataFrame(checks);df.to_csv(ROOT/'data'/'model_validation.csv',index=False,encoding='utf-8-sig')
    print(df.to_string(index=False))
    if not df.passed.all():raise AssertionError('Model validation failed')
if __name__=='__main__':main()
