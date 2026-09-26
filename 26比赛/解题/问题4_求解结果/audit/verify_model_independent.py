"""Bounded independent Q4 model checks; no controller optimization is performed."""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
import bootstrap  # noqa: E402,F401
import numpy as np  # noqa: E402
import control_model as m  # noqa: E402
import q3_reference as reference  # noqa: E402


def main():
    checks=[]
    def check(name, value, expected, tolerance):
        checks.append(dict(check=name,passed=abs(value-expected)<=tolerance,
                           observed=value,expected=expected,tolerance=tolerance))
    cfg=m.make_config(scale=2,j0=m.J0)
    states=[m.initial_state(cfg,243.15) for _ in range(5)]
    c,g,h=m.network(cfg,states,m.THERMAL)
    check("initial_stack_areal_heat_capacity",c.sum(),97451.2976357623,1e-7)
    check("thermal_conductance_matrix_symmetry",np.max(np.abs(g-g.T)),0,1e-10)
    check("internal_conduction_row_sums_cancel",np.max(np.abs(g.sum(axis=1)-h)),0,1e-10)
    ns,nt,en,water,err=m.advance(cfg,states,np.full(7,-30.),0.,.1,np.ones(5),m.THERMAL)
    check("five_heaters_unit_conversion",en[0],12.5,1e-10)
    check("single_step_discrete_energy_balance",en[4]-en[0]-en[1]-en[2]+en[3],0,1e-8)
    _,d0=m.evaluate(cfg,states,np.full(7,-30.),0.,m.THERMAL)
    _,d1=m.evaluate(cfg,ns,nt,0.,m.THERMAL)
    check("single_step_independent_water_inventory",(d1[:,7].sum()-d0[:,7].sum()-water[0]+water[1])*.0025,0,1e-12)
    check("charge_budget_deadline",m.charge(m.Q_TIME),20,1e-12)
    p=m.DEFAULT.copy();p[5]=0.
    s,_,_,_=m.simulate(np.full(7,-30.),kind="constant",params=p,dt=.025,scale=2)
    r,_,_,_=reference.simulate("C",m.CONSTANT,m.Q_TIME,dt=.025,scale=2,stop=True)
    for key in ("first_success_s","E_aux_J","min_voltage_V","max_ice_bulk"):
        check("same_resolution_Q3_reproduction_"+key,s[key],r[key],1e-4 if key=="E_aux_J" else 1e-6)
    s,hist,_,_=m.simulate(np.full(7,-30.),kind="constant",power=[1,0,0,0,0],
                         horizon=1,dt=.05,scale=1,record=True)
    check("asymmetric_input_is_not_mirrored",float(hist[-1,4]>hist[-1,8]+.01),1,0)
    warm=np.array([.1,.1,.1,.1,.1,-30.,-30.])
    s,hist,_,_=m.simulate(warm,kind="dynamic",dt=.05,scale=1,post=1,record=True)
    check("initially_warm_success_time",s["first_success_s"],0,0)
    check("initially_warm_stop_time",s["stop_s"],0,0)
    check("initially_warm_total_energy",s["E_aux_J"],0,1e-12)
    check("shutdown_latches_even_after_temperature_rebound",np.max(np.abs(hist[:,11:16])),0,1e-12)
    check("rebound_probe_reaches_subzero_temperature",float(np.min(hist[-1,4:9])<0),1,0)
    destination=ROOT/"audit"/"independent_model_validation.csv"
    with destination.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)
    failed=[row for row in checks if not row["passed"]]
    print(f"Independent plant audit: {len(checks)-len(failed)}/{len(checks)} passed; {destination}")
    for row in failed:print(row)
    return bool(failed)


if __name__=="__main__":
    raise SystemExit(main())
