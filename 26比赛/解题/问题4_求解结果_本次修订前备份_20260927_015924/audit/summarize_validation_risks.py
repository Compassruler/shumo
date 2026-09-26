"""Derive robustness and discretization risk tables from completed CSV files."""
from pathlib import Path
from collections import defaultdict
import csv

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
OUT=ROOT/"audit"
DEADLINE=60+11/.3


def read(name):
    with (DATA/name).open(encoding="utf-8-sig",newline="") as stream:
        return list(csv.DictReader(stream))


def save(rows,name):
    with (OUT/name).open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    robust=read("robustness.csv")
    grouped=defaultdict(list)
    for r in robust:grouped[(r["case"],float(r["initial_shift_K"]))].append(r)
    result=[];failures=[]
    for (case,shift),rows in sorted(grouped.items()):
        success=sum(r["feasible"]=="True" for r in rows)
        result.append(dict(case=case,initial_shift_K=shift,success=success,total=len(rows),
                      success_fraction=success/len(rows),min_voltage_V=min(float(r["min_voltage_V"]) for r in rows),
                      max_ice_bulk=max(float(r["max_ice_bulk"]) for r in rows),
                      minimum_first_success_s=min(float(r["first_success_s"]) for r in rows),
                      maximum_first_success_s=max(float(r["first_success_s"]) for r in rows)))
        for r in rows:
            if r["feasible"]=="True":continue
            first=float(r["first_success_s"])
            if float(r["min_voltage_V"])<.3:reason="voltage_constraint"
            elif float(r["max_ice_bulk"])>=.99:reason="ice_constraint"
            elif first<0:reason="did_not_reach_first_success"
            elif first+2>DEADLINE+1e-7:reason="first_success_leaves_less_than_2s_hold"
            else:reason="success_hold_interrupted_before_budget_deadline"
            failures.append(dict(case=case,seed=r["seed"],initial_shift_K=shift,
                            first_success_s=first,stop_s=r["stop_s"],remaining_s_after_first=DEADLINE-first,
                            final_min_T_C=r["final_min_T_C"],reason=reason))
    save(result,"robustness_independent_summary.csv")
    save(failures,"robustness_failure_classification.csv")
    conv=read("startup_convergence.csv")
    comparisons=[]
    for case in sorted({r["case"] for r in conv}):
        rows=[r for r in conv if r["case"]==case]
        base=next(r for r in rows if float(r["dt_s"])==.025 and float(r["scale"])==2 and float(r["period_s"])==.2)
        for label,dt,scale,period in (("time_step_halved",.0125,2,.2),("spatial_mesh_doubled",.025,4,.2),("control_period_halved",.025,2,.1)):
            new=next(r for r in rows if float(r["dt_s"])==dt and float(r["scale"])==scale and float(r["period_s"])==period)
            for metric in ("E_aux_J","first_success_s","stop_s","min_voltage_V","max_ice_bulk","dTmax_K"):
                b=float(base[metric]);v=float(new[metric])
                comparisons.append(dict(case=case,comparison=label,metric=metric,base=b,refined=v,
                      absolute_change=v-b,relative_change_percent=100*(v-b)/abs(b) if b else "undefined_zero_baseline"))
    save(comparisons,"convergence_independent_comparison.csv")
    nominal=[]
    for r in read("main_results.csv"):
        if r["strategy"]!="dynamic":continue
        nominal.append(dict(case=r["case"],first_success_s=r["first_success_s"],stop_s=r["stop_s"],
                       margin_until_deadline_s=DEADLINE-float(r["stop_s"]),E_aux_J=r["E_aux_J"],
                       post_min_T_C=r["post_min_T_C"],remains_above_freezing_after_shutdown=float(r["post_min_T_C"])>=0))
    save(nominal,"nominal_deadline_and_poststop_risks.csv")
    sensitivity=[r for r in read("sensitivity.csv") if r["feasible"]!="True"]
    save(sensitivity,"sensitivity_failure_rows.csv")
    print("Robustness groups:",result)
    print("Failed robustness trials:",len(failures),"/",len(robust))
    print("Failed sensitivity trials:",len(sensitivity))


if __name__=="__main__":main()
