from pathlib import Path
import csv,json,hashlib
import numpy as np
import openpyxl
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'inputs') if (ROOT/'inputs'/'附件2.xlsx').exists() else ROOT.parent/'B题'/'氢燃料电池低温冷启动建模与控制策略研究  附件'
def read_data():
    book=openpyxl.load_workbook(SOURCE/'附件2.xlsx',data_only=True)
    out={}
    for name,T in [('minus20',-20.),('minus25',-25.)]:
        s=book[f'{int(T)}℃'];a=np.array(list(s.values)[2:],dtype=float)
        assert a.shape==(184,6) and np.isfinite(a).all()
        assert np.allclose(np.diff(a[:,0]),.2) and np.allclose(a[:,5],a[:,4]*10000)
        a=a[a[:,0]<=35+1e-9];assert len(a)==176
        out[name]=dict(t=a[:,0],I=a[:,1],V=a[:,2],T=a[:,3],j=a[:,5],T0=T)
    return out

def write_csv(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def json_write(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=lambda x: x.item() if isinstance(x,np.generic) else str(x)),encoding='utf-8')
def attach_observations(rows,d):
    for k,row in enumerate(rows):
        row.update(I_exp_A=d['I'][k],I_consistent_25cm2_A=d['j'][k]*.0025,
            V_exp_V=d['V'][k],T_exp_C=d['T'][k],V_rel_error_pct=abs(row['V_model_V']-d['V'][k])/abs(d['V'][k])*100,
            T_rel_error_pct=abs(row['T_model_C']-d['T'][k])/abs(d['T'][k])*100,
            T_rel_error_K_pct=abs(row['T_model_C']-d['T'][k])/(d['T'][k]+273.15)*100)
    return rows

def metrics(rows):
    a=lambda k:np.array([r[k] for r in rows])
    d={}
    for v in ['V','T']:
        unit='V' if v=='V' else 'C';err=a(f'{v}_model_{unit}')-a(f'{v}_exp_{unit}')
        d.update({f'{v}_RMSE':float(np.sqrt(np.mean(err**2))),f'{v}_MAE':float(np.mean(abs(err))),
            f'{v}_MAPE_pct':float(np.mean(a(f'{v}_rel_error_pct'))),f'{v}_max_relative_error_pct':float(np.max(a(f'{v}_rel_error_pct')))})
    for key in ['water_balance_kg_m2','energy_balance_J_m2','H2_balance_mol_m2','O2_balance_mol_m2']:
        d['max_abs_'+key]=float(np.max(abs(a(key))))
    d.update(valid_samples=int(a('model_valid').sum()),n_samples=len(rows),final=rows[-1],
        ice_peak_bulk=float(a('ice_max_bulk').max()),ice_peak_time_s=float(a('t_s')[a('ice_max_bulk').argmax()]),
        voltage_min_V=float(a('V_model_V').min()),voltage_min_time_s=float(a('t_s')[a('V_model_V').argmin()]))
    return d
