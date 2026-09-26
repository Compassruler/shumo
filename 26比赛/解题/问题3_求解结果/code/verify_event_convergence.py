"""Fixed-power first-crossing convergence; no optimization or control overwrite.

Each discretization independently advances from -30 C with the saved powers,
then reintegrates/bisects the crossing step. P/R use j=0 until first crossing;
C uses the prescribed ramp. This event check allows constant heat to continue
until its own event, rather than ending every grid at the saved heat-off time.
"""
from pathlib import Path
import csv
import json
import numpy as np
from numba import njit
from aux_model import ROOT, J0, THERMAL, charge, advance, evaluate
from fast_cell import make_config, initial_state

DATA = ROOT / "data"
CROSSING_TOL_C = 1e-7
GRIDS = ((1,.1),(2,.05),(4,.025),(8,.025),(8,.0125),
         (8,.00625),(16,.00625),(16,.003125))

@njit(cache=True)
def locate(cfg, kind, power, dt):
    states = [initial_state(cfg,243.15) for _ in range(5)]
    temp = np.full(7,-30.)
    t = 0.
    en = np.zeros(5)
    vmin=1e9; imax=0.; satmax=0.; por=1e9; ratio=0.; kap=1e9
    inv=1e9; errmax=0.
    while t < 100.:
        step=min(dt,100.-t)
        if kind==1 and t<60.: step=min(step,60.-t)
        j=(charge(t+step)-charge(t))/step if kind==1 else 0.
        ns,nt,ne,nw,er=advance(cfg,states,temp,j,step,power,THERMAL)
        if np.min(temp[:5])<CROSSING_TOL_C and np.min(nt[:5])>=CROSSING_TOL_C:
            lo=0.;hi=step
            for _ in range(28):
                mid=(lo+hi)/2
                jm=(charge(t+mid)-charge(t))/mid if kind==1 else 0.
                ss,tt,ee,ww,rr=advance(cfg,states,temp,jm,mid,power,THERMAL)
                if np.min(tt[:5])>=CROSSING_TOL_C:hi=mid
                else:lo=mid
            step=hi
            j=(charge(t+step)-charge(t))/step if kind==1 else 0.
            ns,nt,ne,nw,er=advance(cfg,states,temp,j,step,power,THERMAL)
        t+=step;states=ns;temp=nt;en+=ne;errmax=max(errmax,er)
        current=min(.005*t,.3) if kind==1 else 0.
        e,d=evaluate(cfg,states,temp,current,THERMAL)
        vmin=min(vmin,np.min(e[:,0]));imax=max(imax,np.max(d[:,0]))
        satmax=max(satmax,np.max(d[:,3]));por=min(por,np.min(d[:,5]))
        ratio=max(ratio,np.max(e[:,6]));kap=min(kap,np.min(e[:,9]))
        inv=min(inv,np.min(d[:,6]))
        if np.min(temp[:5])>=CROSSING_TOL_C:
            return np.array([t,25.*np.sum(power)*t,np.min(temp[:5]),vmin,
                             imax,satmax,por,ratio,kap,inv,errmax,temp[5],
                             en[4]-en[0]-en[1]-en[2]+en[3]])
    raise RuntimeError("No first crossing within 100 seconds")

FIELDS=("first_crossing_s","E_aux_to_crossing_J","crossing_min_T_C",
        "min_voltage_V","max_local_ice_fraction","max_pore_ice_saturation",
        "min_porosity","max_j_jlim","min_kappa_S_m","min_inventory",
        "max_iteration_error_K","crossing_left_EP_C","energy_residual_J")

def main():
    controls=json.loads((DATA/"final_controls.json").read_text())
    rows=[]
    for strategy in ("P","C"):
        power=np.asarray(controls[strategy]["power"])
        for scale,dt in GRIDS:
            values=locate(make_config(scale=scale,j0=J0),int(strategy=="C"),power,dt)
            row=dict(strategy=strategy,scale=scale,dt_s=dt,
                     crossing_tolerance_C=CROSSING_TOL_C,**dict(zip(FIELDS,values.tolist())))
            row["passed"]=bool(row["min_voltage_V"]>=.3 and row["max_local_ice_fraction"]<.99
              and row["min_porosity"]>=0 and row["max_j_jlim"]<1
              and row["min_kappa_S_m"]>0 and row["min_inventory"]>=-1e-8
              and row["max_iteration_error_K"]<=1e-9)
            rows.append(row)
            print(strategy,scale,dt,row["first_crossing_s"],row["max_local_ice_fraction"],flush=True)
    with (DATA/"event_convergence.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    refresh_metadata(rows, controls)


def refresh_metadata(rows, controls):
    """Add event metadata while preserving original numerical fields."""
    # R has exactly P's powers and j=0 until its later heat-off time.
    formal=next(r for r in rows if r["strategy"]=="P" and r["scale"]==8 and r["dt_s"]==.00625)
    if controls["R"]["power"]!=controls["P"]["power"]:raise ValueError("R/P preheat inputs differ")
    metadata={
      "first_crossing_definition":"First min(T1,...,T5) >= 1e-7 C with continuous constant heating; full state reintegration in crossing step.",
      "controls":"final_controls.json; frozen powers, no reoptimization",
      "R_first_crossing_s":formal["first_crossing_s"],
      "R_heat_off_s":controls["R"]["th_s"],
      "R_first_crossing_basis":"R and P have identical initial state, power vector, and zero-current input before this crossing.",
      "legacy_first_success_s":"For preheat-kind simulations this field is gated until heat-off; use first_crossing_s for R physical first crossing.",
      "all_events_passed":all(r["passed"] is True or r["passed"]=="True" for r in rows),
      "main_P_legacy_startup_s":controls["P"]["th_s"],
      "main_P_legacy_temperature_tolerance_C":1e-4,
      "new_event_temperature_tolerance_C":CROSSING_TOL_C,
      "trajectory_note":"Trajectory CSV times and state fields retain the original main runs. No event timestamp is inferred from sparse output rows; independent events are stored separately.",
      "trajectory_field_definitions":{"cellN_ice_bulk":"maximum local control-volume ice fraction across one cell, including membrane; not volume average",
         "cellN_pore_ice_bulk":"maximum local ice fraction over porous layers",
         "cellN_pore_ice_saturation":"maximum local ice fraction divided by local dry porosity, porous layers only",
         "heater_on":"actual saved control, 1 before heat_off_s and 0 after"}}
    (DATA/"event_convergence_metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n")
    for name in ("summary_results.csv","postload_verification.csv","convergence.csv"):
        p=DATA/name
        with p.open(encoding="utf-8-sig",newline="") as f: old=list(csv.DictReader(f))
        for r in old:
            strategy=r["strategy"]
            scale=int(float(r.get("scale",8)));dt=float(r.get("dt_s",.00625))
            source=next(x for x in rows if x["strategy"]==("P" if strategy=="R" else strategy)
                        and x["scale"]==scale and x["dt_s"]==dt)
            r["first_crossing_s"]=source["first_crossing_s"]
            r["heat_off_s"]=controls[strategy]["th_s"]
            r["first_crossing_tolerance_C"]=CROSSING_TOL_C
            r["first_crossing_scope"]="constant_heater_event_check" if name=="convergence.csv" else "physical_first_crossing"
        with p.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(old[0]));w.writeheader();w.writerows(old)
    print(json.dumps(metadata,ensure_ascii=False),flush=True)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only",action="store_true",help="Refresh additive metadata from existing event CSV without simulation.")
    args=parser.parse_args()
    if args.metadata_only:
        with (DATA/"event_convergence.csv").open(encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f))
        for r in rows:
            r["scale"]=int(r["scale"])
            for key in ("dt_s","first_crossing_s"):
                r[key]=float(r[key])
        refresh_metadata(rows,json.loads((DATA/"final_controls.json").read_text()))
    else:
        main()
