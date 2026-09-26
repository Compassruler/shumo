"""Additional spatial refinement for local peak ice fraction, which converges
more slowly than integrated auxiliary energy. Does not retune the controller.
"""
import bootstrap
from pathlib import Path
import pandas as pd
import control_model as m
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def main():
    rows=pd.read_csv(DATA/'startup_convergence.csv').to_dict('records')
    initial=pd.read_csv(DATA/'initial_temperature_cases.csv')
    params=pd.read_csv(DATA/'optimized_parameters.csv').set_index('case')
    for _,r in initial.iterrows():
        temp=r[[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']].to_numpy(float)
        for scale in (8,16):
            if any(x['case']==r['case'] and x['scale']==scale for x in rows):continue
            s=m.simulate(temp,params=params.loc[r['case'],m.PARAM_NAMES].to_numpy(float),dt=.025,scale=scale)[0]
            rows.append(dict(case=r['case'],dt_s=.025,scale=scale,period_s=.2,**s))
            print(r['case'],scale,s['E_aux_J'],s['max_ice_bulk'],flush=True)
    pd.DataFrame(rows).to_csv(DATA/'startup_convergence.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
    joint=[]
    for _,r in initial.iterrows():
        temp=r[[f'T{k}_C' for k in range(1,6)]+['TEL_C','TER_C']].to_numpy(float)
        for scale,dt in ((4,.0125),(8,.00625),(16,.003125)):
            s=m.simulate(temp,params=params.loc[r['case'],m.PARAM_NAMES].to_numpy(float),dt=dt,scale=scale)[0]
            joint.append(dict(case=r['case'],dt_s=dt,scale=scale,period_s=.2,**s))
    pd.DataFrame(joint).to_csv(DATA/'coupled_convergence.csv',index=False,encoding='utf-8-sig',float_format='%.12g')
if __name__=='__main__':main()
