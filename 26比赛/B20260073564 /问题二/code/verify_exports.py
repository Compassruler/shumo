"""Final file-level consistency checks, independent of the solver's status string."""
from pathlib import Path
import csv,json
from stack_model import charge,simulate
import numpy as np
from run_question2 import write_csv

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'
def read(name):
    with (DATA/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))

rows=[]
def record(check,value,tolerance):
    rows.append({'check':check,'value':float(value),'tolerance':tolerance,'passed':bool(value<=tolerance)})
    assert value<=tolerance,(check,value,tolerance)

for summary in read('strategy_summary.csv'):
    kind=summary['strategy'];p=np.asarray(json.loads(summary['parameters']),dtype=float)
    code={'constant':0,'ramp':1,'step':2}[kind]
    tr=read(f'trajectory_{kind}.csv')
    qerr=max(abs(float(r['charge_C_cm2'])-charge(float(r['time_s']),code,p)) for r in tr)
    vmin=min(float(r[f'cell{k}_V']) for r in tr for k in (1,2,3))
    imax=max(float(r[f'cell{k}_ice_bulk']) for r in tr for k in (1,2,3))
    record(kind+'_analytic_charge',qerr,1e-9)
    record(kind+'_summary_voltage_extremum',abs(vmin-float(summary['min_voltage_V'])),1e-9)
    record(kind+'_summary_ice_extremum',abs(imax-float(summary['max_ice_bulk'])),1e-9)
    record(kind+'_voltage_path_violation',max(0.,.30-vmin),1e-10)
    record(kind+'_terminal_temperature_violation',max(0.,1e-12-min(float(tr[-1][f'T{k}_C']) for k in (1,2,3))),1e-12)
    record(kind+'_budget_violation',max(0.,float(tr[-1]['charge_C_cm2'])-20),1e-10)
    record(kind+'_terminal_time_match',abs(float(tr[-1]['time_s'])-float(summary['end_time_s'])),1e-9)
    cells=read(f'cells_{kind}.csv')
    symmetry=0.
    for i in range(0,len(cells),5):
        block=cells[i:i+5]
        for a,b in ((0,4),(1,3)):
            for key in ('temperature_C','V','ice_bulk'):
                symmetry=max(symmetry,abs(float(block[a][key])-float(block[b][key])))
    record(kind+'_five_cell_export_symmetry',symmetry,1e-12)
boundary=json.loads((DATA/'critical_temperature.json').read_text(encoding='utf-8'))
record('critical_success_status',float(boundary['critical_success']['status']!='success'),0)
record('critical_failure_status',float(boundary['critical_failure']['status']!='charge_exhausted'),0)
for key,value in boundary.items():
    if key.startswith('finest_check_'):
        expected='charge_exhausted' if value['T0_C']==boundary['critical_failure']['T0_C'] else 'success'
        record(key+'_bracket_confirm',float(value['status']!=expected),0)
write_csv('最终CSV独立核验.csv',rows)

# Recompute slope-limit sequence on the SAME grid as the final table.
limits=[]
for tp in (60.,30.,10.,5.,1.,.5,.2,.1,.05,.02,.01):
    s,*_=simulate('ramp',[.5/tp,.5],dt=.003125,scale=8)
    limits.append({'plateau_time_s':tp,'slope_A_cm2_s':.5/tp,'dt_s':.003125,'grid_scale':8,**s})
write_csv('ramp_slope_limit.csv',limits)
print(f'{len(rows)} exported-result checks passed; slope sequence updated',flush=True)
