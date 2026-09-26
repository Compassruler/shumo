"""Paired frozen-constant benchmarks on the guarded validation scenarios."""
import bootstrap
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def main():
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    powers=pd.read_csv(DATA/'optimized_constant_parameters.csv').set_index('case')
    cols=[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C'];rows=[];physical=[]
    for _,r in initial.iterrows():
        case=r['case'];temp=r[cols].to_numpy(float)
        for strategy,q in [('constant_hold',m.CONSTANT),('constant_optimized',powers.loc[case,[f'q{k}_W_cm2' for k in range(1,6)]].to_numpy(float))]:
            def trial(z):
                shift,G,Gep,h,seed=z;thermal=m.THERMAL.copy()
                thermal[0]*=G;thermal[1]*=Gep;thermal[5]*=h
                s=m.simulate(temp+shift,kind='constant',power=q,dt=.025,scale=2,
                     thermal=thermal,noise_T=.2,noise_V=.005,seed=seed)[0]
                return dict(case=case,strategy=strategy,initial_shift_K=shift,G_factor=G,
                     G_EP_factor=Gep,h_factor=h,seed=seed,noise_T_K=.2,noise_V_V=.005,**s)
            scenarios=[(shift,1.,1.,1.,seed) for shift in (-1.,0.,1.) for seed in range(6000,6010)]
            extra=[]
            for ix in range(3):
                for factor in (.8,1.2):
                    factors=[1.,1.,1.];factors[ix]=factor
                    extra.append((0.,*factors,7000+2*ix+int(factor>1.)))
            extra.extend([(-1.,.8,1.2,1.2,7010),(1.,1.2,.8,.8,7011)])
            with ThreadPoolExecutor(max_workers=4) as pool:
                rows.extend(pool.map(trial,scenarios));physical.extend(pool.map(trial,extra))
            print(case,strategy,'paired validation completed',flush=True)
            pd.DataFrame(rows).to_csv(DATA/'constant_robustness.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
            pd.DataFrame(physical).to_csv(DATA/'constant_parameter_validation.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
if __name__=='__main__':main()
