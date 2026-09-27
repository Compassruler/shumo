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
    add('trajectory_schema_128_named_columns',abs(hs.shape[1]-128)+abs(len(m.HISTORY)-128),0.)
    mask=hs[:,0]>sh['stop_s']+1e-8
    add('shutdown_latch_power_zero',np.max(abs(hs[mask,11:16])),0.)
    add('shutdown_latch_energy_zero',abs(sh['post_energy_J']),1e-10)
    add('physical_hold_at_least_two_seconds',max(0.,2.-sh['physical_hold_s']),1e-7)
    add('sensor_shutdown_sample_alignment',abs(sh['stop_s']/.2-round(sh['stop_s']/.2)),1e-7)
    add('sensor_shutdown_meets_physical_hold',1.-sh['physical_hold_completed'],0.)
    stoprow=hs[np.argmin(abs(hs[:,0]-sh['stop_s']))]
    add('shutdown_row_latch_and_state',abs(stoprow[3]-1.)+np.max(abs(stoprow[56:61]-5.)),0.)
    # The budget ends at true first success. A sampled 2 s confirmation may
    # finish later; a sample exactly at horizon+hold must still be processed.
    edge=m.simulate(temp,kind='constant',horizon=sh['stop_s']-2.)[0]
    add('shutdown_boundary_sample_not_skipped',abs(edge['stop_s']-sh['stop_s']),1e-7)
    add('first_success_budget_independent_of_hold',0. if edge['feasible'] and edge['stop_s']>edge['first_success_s'] else 1.,0.)
    fmask=hs[:,0]<=sh['first_success_s']+1e-8
    add('first_window_min_voltage',abs(sh['first_min_voltage_V']-hs[fmask,16:21].min()),1e-10)
    add('first_window_max_ice',abs(sh['first_max_ice_bulk']-hs[fmask,21:26].max()),1e-10)
    add('first_window_max_spread',abs(sh['first_dTmax_K']-np.ptp(hs[fmask,4:9],axis=1).max()),1e-10)
    add('heater_energy_matches_interval_ending_power',abs(sh['E_aux_J']-np.sum(np.diff(hs[:,0])*hs[1:,11:16].sum(axis=1)*25.)),1e-7)
    cfg=m.make_config();states=[m.initial_state(cfg,293.15) for k in range(5)]
    t7=np.full(7,20.);e,d=m.evaluate(cfg,states,t7,.1,m.THERMAL)
    e[:,0]=.31;cs=np.zeros((5,7));cs[:,0]=20.;cs[:,1]=.31
    q=m.control(20.,.2,np.full(7,-30.),t7,e[:,0],states,cfg,m.DEFAULT,cs,np.zeros(5))
    add('safety_priority_survives_zero_taper',max(0.,m.DEFAULT[6]-np.min(q)),1e-12)
    add('per_cell_power_bounds',max(0.,-np.min(q),np.max(q)-1.),0.)
    add('nominal_independent_observer_temperature_matches',sh['observer_max_temperature_error_K'],1e-7)
    add('nominal_independent_observer_ice_matches',sh['observer_max_ice_error'],1e-8)
    thermal=m.THERMAL.copy();thermal[1]*=.8
    shifted=m.simulate(temp,kind='constant',thermal=thermal,horizon=35.)[0]
    add('observer_does_not_receive_true_thermal_parameter',0. if shifted['observer_max_temperature_error_K']>1e-4 else 1.,0.)
    noisy,hn,*_=m.simulate(temp,kind='constant',horizon=35.,record=True,noise_T=.2,noise_V=.005,seed=73)
    add('recorded_observer_temperature_error_recomputable',
        abs(noisy['observer_max_temperature_error_K']-np.max(abs(hn[1:,91:98]-hn[1:,4:11]))),1e-10)
    add('recorded_observer_ice_error_recomputable',
        abs(noisy['observer_max_ice_error']-np.max(abs(hn[1:,113:118]-hn[1:,21:26]))),1e-10)
    add('sensor_stop_filtered_margin_exported',max(0.,m.SENSOR_STOP_MARGIN-np.min(hn[-1,118:123])),0.)
    errors=0
    for kw in [dict(kind='typo'),dict(dt=0),dict(period=.01),dict(power=np.ones(5)*1.1)]:
        try:m.simulate(temp,**kw)
        except ValueError:errors+=1
    add('invalid_inputs_rejected',4-errors,0.)
    df=pd.DataFrame(checks);df.to_csv(ROOT/'data'/'model_validation.csv',index=False,encoding='utf-8-sig')
    print(df.to_string(index=False))
    if not df.passed.all():raise AssertionError('Model validation failed')
if __name__=='__main__':main()
