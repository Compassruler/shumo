"""Export independent noisy/mismatched observer examples with frozen controls."""
import bootstrap
from pathlib import Path
import numpy as np
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'

def main():
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    controls=pd.read_csv(DATA/'guarded_parameters.csv').set_index('case')
    cols=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C'];rows=[]
    for _,r in initial.iterrows():
        case=r['case'];temp=r[cols].to_numpy(float)-1.
        p=controls.loc[case,m.PARAM_NAMES].to_numpy(float)
        thermal=m.THERMAL.copy();thermal[0]*=.8;thermal[1]*=1.2;thermal[5]*=1.2
        s,h,*_=m.simulate(temp,params=p,thermal=thermal,dt=.025,scale=2,
                          noise_T=.2,noise_V=.005,seed=7010,post=60.,record=True)
        rows.append(dict(case=case,strategy='observer_example',seed=7010,initial_shift_K=-1.,
             G_factor=.8,G_EP_factor=1.2,h_factor=1.2,noise_T_K=.2,noise_V_V=.005,**s))
        pd.DataFrame(h,columns=m.HISTORY).to_csv(DATA/f'trajectory_{case}_observer_example.csv',
                       index=False,encoding='utf-8-sig',float_format='%.12g')
    pd.DataFrame(rows).to_csv(DATA/'observer_example_results.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
    print('Independent observer stress examples saved',flush=True)

if __name__=='__main__':main()
