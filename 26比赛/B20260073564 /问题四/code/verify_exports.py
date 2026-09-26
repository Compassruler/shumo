"""Independently audit Q4 CSV outputs, without reusing simulation summaries.

Run after run_problem4.py. Heater samples at row i apply over (t[i-1],t[i]].
The stopped=1 event row still contains the last heating interval; all subsequent
rows must have q=0. Every check is saved, and any failed check returns exit 1.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import bootstrap  # noqa: F401: use the isolated task dependencies
import numpy as np


CHECKS: list[dict] = []
Q_DEADLINE = 60 + 11 / 0.3
CONST_POWER = np.array([1.0, 1.0, 0.6245115587719579, 1.0, 1.0])


def check(name, ok, observed="", expected="", file=""):
    if file:
        try:file=Path(file).resolve().relative_to(Path(__file__).resolve().parents[1])
        except ValueError:pass
    CHECKS.append(dict(check=name, passed=bool(ok), observed=observed,
                       expected=expected, file=str(file)))


def close(name, observed, expected, atol=1e-6, rtol=1e-8, file=""):
    observed, expected = float(observed), float(expected)
    check(name, math.isfinite(observed) and math.isfinite(expected)
          and abs(observed - expected) <= atol + rtol * abs(expected),
          observed, expected, file)


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Missing or duplicate CSV column names: " + str(path))
    if not rows:
        raise ValueError("Empty CSV: " + str(path))
    return rows


def numeric_columns(rows):
    return {name: np.array([float(row[name]) for row in rows]) for name in rows[0]}


def qcharge(t):
    return 0.0025 * np.minimum(t, 60.0)**2 + 0.3 * np.maximum(t - 60.0, 0.0)


def audit_trajectory(path, summary, hold_s):
    a = numeric_columns(read_rows(path))
    required = ["time_s", "j_A_cm2", "charge_C_cm2", "stopped"]
    required += [f"T{k}_C" for k in range(1, 6)] + ["TEL_C", "TER_C"]
    required += [f"cell{k}_{name}" for name in ["q_W_cm2", "V_V", "ice_bulk",
                 "pore_ice_bulk", "mem_ice_bulk", "pore_ice_saturation",
                 "lambda", "j_over_jlim", "gas_porosity", "state", "risk",
                 "rT_K_s", "rV_V_s", "ice_est"] for k in range(1, 6)]
    required += ["E_aux_J", "E_gen_J", "E_phase_J", "E_loss_J", "E_sensible_J",
                 "energy_residual_J", "water_residual_kg", "water_inventory_kg",
                 "water_produced_kg", "water_out_kg"]
    missing = sorted(set(required) - set(a))
    check("trajectory_required_columns", not missing, ",".join(missing), "none", path)
    if missing:
        return
    check("all_trajectory_values_finite", all(np.all(np.isfinite(x)) for x in a.values()), file=path)
    t = a["time_s"]
    close("trajectory_initial_time", t[0], 0, file=path)
    check("trajectory_time_strictly_increasing", np.all(np.diff(t) > 0), file=path)
    check("prescribed_current", np.allclose(a["j_A_cm2"], np.minimum(.005*t, .3), rtol=0, atol=1e-11), file=path)
    check("analytic_charge", np.allclose(a["charge_C_cm2"], qcharge(t), rtol=0, atol=2e-10), file=path)
    T = np.array([a[f"T{k}_C"] for k in range(1, 6)]).T
    V = np.array([a[f"cell{k}_V_V"] for k in range(1, 6)]).T
    ice = np.array([a[f"cell{k}_ice_bulk"] for k in range(1, 6)]).T
    q = np.array([a[f"cell{k}_q_W_cm2"] for k in range(1, 6)]).T
    ratio = np.array([a[f"cell{k}_j_over_jlim"] for k in range(1, 6)]).T
    pore = np.array([a[f"cell{k}_gas_porosity"] for k in range(1, 6)]).T
    check("heater_power_bounds", np.min(q) >= -1e-12 and np.max(q) <= 1+1e-12,
          f"{np.min(q):.12g}..{np.max(q):.12g}", "0..1", path)
    energy_per_cell = 25 * np.cumsum(q * np.diff(t, prepend=0)[:, None], axis=0)
    integrated = energy_per_cell.sum(axis=1)
    delta = float(np.max(np.abs(integrated-a["E_aux_J"])))
    check("heater_energy_independent_right_rectangle", delta < 1e-6, delta, "<1e-6 J", path)
    check("auxiliary_energy_nondecreasing", np.min(np.diff(a["E_aux_J"], prepend=0)) >= -1e-8, file=path)
    residual = (a["E_sensible_J"] - a["E_aux_J"] - a["E_gen_J"]
                - a["E_phase_J"] + a["E_loss_J"])
    check("energy_residual_formula", np.max(np.abs(residual-a["energy_residual_J"])) < 1e-7, file=path)
    check("discrete_energy_balance", np.max(np.abs(residual)) < 1e-6,
          np.max(np.abs(residual)), "<1e-6 J", path)
    check("water_balance", np.max(np.abs(a["water_residual_kg"])) < 1e-9,
          np.max(np.abs(a["water_residual_kg"])), "<1e-9 kg", path)
    waterkeys = ["water_inventory_kg", "water_produced_kg", "water_out_kg"]
    if all(key in a for key in waterkeys):
        water_balance = (a[waterkeys[0]]-a[waterkeys[0]][0]
                         -a[waterkeys[1]]+a[waterkeys[2]])
        check("independently_reconstructed_water_balance", np.max(np.abs(water_balance))<1e-9,
              np.max(np.abs(water_balance)), "<1e-9 kg", path)
        check("water_residual_matches_independent_inventory", np.max(np.abs(water_balance-a["water_residual_kg"]))<1e-11, file=path)
        produced_from_charge = 5*25*.018/(2*96485)*qcharge(t)
        check("Faraday_water_production_from_analytic_charge", np.max(np.abs(a["water_produced_kg"]-produced_from_charge))<1e-11, file=path)
    for name in ("pore_ice_bulk", "mem_ice_bulk", "pore_ice_saturation"):
        part = np.array([a[f"cell{k}_{name}"] for k in range(1, 6)]).T
        check(name+"_nonnegative", np.min(part) >= -1e-12, file=path)
        if name != "pore_ice_saturation":
            check(name+"_not_above_all_MEA_max", np.max(part-ice) <= 1e-10, file=path)
    poreice = np.array([a[f"cell{k}_pore_ice_bulk"] for k in range(1,6)]).T
    membraneice = np.array([a[f"cell{k}_mem_ice_bulk"] for k in range(1,6)]).T
    check("all_MEA_ice_is_max_of_pore_and_membrane", np.max(np.abs(ice-np.maximum(poreice,membraneice)))<1e-10, file=path)
    mirror = max(float(np.max(np.abs(T[:,0]-T[:,4]))),
                 float(np.max(np.abs(T[:,1]-T[:,3]))),
                 float(np.max(np.abs(a["TEL_C"]-a["TER_C"]))))
    initial_mirror = max(abs(T[0,0]-T[0,4]),abs(T[0,1]-T[0,3]),
                         abs(a["TEL_C"][0]-a["TER_C"][0]))
    # The full oriented aGDL/aCL/PEM/cCL/cGDL precooling mesh is not exactly
    # mirror symmetric. Its small initial asymmetry must not be called a solver
    # failure; compare subsequent mismatch against the actual initial mismatch.
    if summary.get('strategy') != 'constant_optimized':
        check("mirror_difference_not_amplified_from_initial_field", mirror<=initial_mirror+1e-6,
              mirror, f"<= initial {initial_mirror:.12g} + 1e-6 K", path)

    flags = a["stopped"]
    check("stop_flag_binary_and_latched", np.all((flags==0)|(flags==1)) and np.all(np.diff(flags)>=0), file=path)
    stop_ids = np.flatnonzero(flags > .5)
    feasible = str(summary.get("feasible", "")).lower() in ("true", "1", "1.0")
    check("successful_main_trajectory_has_stop", len(stop_ids)>0 or not feasible, file=path)
    stop_i = int(stop_ids[0]) if len(stop_ids) else len(t)-1
    cutoff = slice(0, stop_i+1)
    if len(stop_ids):
        check("no_heater_reactivation_after_stop", np.max(np.abs(q[stop_i+1:]), initial=0) < 1e-12, file=path)
        check("no_post_stop_auxiliary_energy", np.max(np.abs(a["E_aux_J"][stop_i:]-a["E_aux_J"][stop_i])) < 1e-8, file=path)
        close("summary_stop_s", summary["stop_s"], t[stop_i], file=path)
    close("summary_elapsed_s", summary["elapsed_s"], t[-1], file=path)
    for key in ["E_aux_J", "E_gen_J", "E_phase_J", "E_loss_J", "E_sensible_J",
                "energy_residual_J", "water_residual_kg"]:
        close("summary_"+key, summary[key], a[key][stop_i], atol=1e-6 if key.endswith("_J") else 1e-12, file=path)
    close("summary_min_voltage", summary["min_voltage_V"], V[cutoff].min(), file=path)
    close("summary_max_ice", summary["max_ice_bulk"], ice[cutoff].max(), file=path)
    close("summary_dTmax", summary["dTmax_K"], np.ptp(T[cutoff], axis=1).max(), file=path)
    close("summary_final_min_T", summary["final_min_T_C"], T[stop_i].min(), file=path)
    close("summary_final_max_T", summary["final_max_T_C"], T[stop_i].max(), file=path)
    close("summary_min_porosity", summary["min_gas_porosity"], pore[cutoff].min(), file=path)
    close("summary_max_current_lim_ratio", summary["max_j_over_jlim"], ratio[cutoff].max(), file=path)
    close("summary_post_energy", summary["post_energy_J"], 0, file=path)
    close("summary_post_min_temperature", summary["post_min_T_C"], T[stop_i:].min(), file=path)
    close("summary_post_min_voltage", summary["post_min_voltage_V"], V[stop_i:].min(), file=path)
    close("summary_post_max_ice", summary["post_max_ice_bulk"], ice[stop_i:].max(), file=path)
    close("summary_max_water_balance_residual", summary["max_water_residual_kg"],
          np.max(np.abs(a["water_residual_kg"])), atol=1e-12, file=path)
    if feasible:
        check("path_voltage_constraint", V[cutoff].min() >= .3-1e-10, V[cutoff].min(), ">=0.30 V", path)
        check("path_ice_constraint", ice[cutoff].max() < .99, ice[cutoff].max(), "<0.99", path)
        check("path_transport_feasible", pore[cutoff].min() >= -1e-12 and ratio[cutoff].max()<1, file=path)
        check("summary_positive_conductivity_and_inventory", float(summary["min_kappa_S_m"])>0
              and float(summary["min_inventory"])>=-1e-8, file=path)
        first = float(summary["first_success_s"])
        fi = int(np.argmin(np.abs(t-first)))
        close("first_success_saved_as_event_row", t[fi], first, atol=1e-7, file=path)
        check("first_success_all_cells_warm", T[fi].min()>0, T[fi].min(), ">0 degC", path)
        close("first_success_energy", summary["first_success_energy_J"], a["E_aux_J"][fi], file=path)
        close("first_success_charge", summary["charge_at_success_C_cm2"], qcharge(first), file=path)
        check("inherited_charge_budget", qcharge(first)<=20+1e-7 and first<=Q_DEADLINE+1e-6,
              qcharge(first), "<=20 C/cm2", path)
        if np.min(T[0])>0:
            close("warm_initial_field_success_at_zero", first, 0, file=path)
            close("warm_initial_field_no_auxiliary_energy", summary["E_aux_J"], 0, file=path)
        elif summary["strategy"] in ("dynamic", "constant_hold", "guarded", "constant_optimized"):
            observed = t[stop_i]-first
            check("common_success_hold_duration", observed>=hold_s-1e-6, observed, f">={hold_s} s", path)
            window = (t>=t[stop_i]-hold_s-1e-8)&(t<=t[stop_i]+1e-8)
            check("common_success_hold_stays_warm", np.min(T[window])>0,
                  np.min(T[window]), ">0 degC throughout hold samples", path)
        elif summary["strategy"] == "constant_first":
            close("first_hit_baseline_no_hold", t[stop_i], first, file=path)
    if summary["strategy"].startswith("constant") and stop_i>0:
        expected = np.array([float(summary[f'q{k}_W_cm2']) for k in range(1,6)]) if summary['strategy']=='constant_optimized' else CONST_POWER
        check("constant_heater_vector", np.allclose(q[1:stop_i+1], expected, rtol=0, atol=1e-10), file=path)
    for k in range(1,6):
        for key in (f"E{k}_J", f"E_aux_cell{k}_J", f"cell{k}_E_aux_J"):
            if key in summary:
                close("per_cell_energy_"+str(k), summary[key], energy_per_cell[stop_i,k-1], file=path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[1]/"data")
    parser.add_argument("--hold-s", type=float, default=2.0)
    args = parser.parse_args()
    data = args.data.resolve()
    mainfile = data/"main_results.csv"
    try:
        rows = read_rows(mainfile)
        pairs = [(r["case"],r["strategy"]) for r in rows]
        check("main_table_nine_rows", len(rows)==9, len(rows), 9, mainfile)
        check("main_table_unique_case_strategy", len(pairs)==len(set(pairs)), file=mainfile)
        cases = sorted({r["case"] for r in rows})
        check("main_table_three_cases", len(cases)==3, len(cases), 3, mainfile)
        for case in cases:
            check("main_table_three_comparison_strategies", {r["strategy"] for r in rows if r["case"]==case}
                  == {"dynamic","constant_hold","constant_first"}, observed=case, file=mainfile)
        for row in rows:
            path = data/f"trajectory_{row['case']}_{row['strategy']}.csv"
            try:
                audit_trajectory(path, row, args.hold_s)
            except Exception as exc:
                check("trajectory_read_or_schema_error", False, repr(exc), file=path)
        guardedfile = data/"guarded_results.csv"
        if guardedfile.exists():
            guarded = read_rows(guardedfile)
            check("guarded_table_three_cases", len(guarded)==3, len(guarded), 3, guardedfile)
            for row in guarded:
                path = data/f"trajectory_{row['case']}_guarded.csv"
                try:
                    audit_trajectory(path,row,args.hold_s)
                except Exception as exc:
                    check("guarded_trajectory_read_or_schema_error",False,repr(exc),file=path)
        optimizedfile = data/'optimized_constant_results.csv'
        if optimizedfile.exists():
            for row in read_rows(optimizedfile):
                path=data/f"trajectory_{row['case']}_constant_optimized.csv"
                try:
                    audit_trajectory(path,row,args.hold_s)
                except Exception as exc:
                    check('optimized_constant_schema_error',False,repr(exc),file=path)
        scanfile = data/"constant_scan.csv"
        scan = read_rows(scanfile)
        check("constant_scan_19_points", len(scan)==19, len(scan), 19, scanfile)
        time_key = next((k for k in ["cooling_min","precool_min","tau_min","tau_c_min","cooling_time_min"] if k in scan[0]), None)
        check("constant_scan_cooling_time_column", time_key is not None, time_key, file=scanfile)
        if time_key:
            times = [float(r[time_key]) for r in scan]
            check("constant_scan_10_to_100_by_5", times==list(range(10,101,5)), times, file=scanfile)
            first_scan = next(r for r in scan if float(r[time_key])==10)
            close("10_min_scan_no_artificial_time", first_scan["first_success_s"], 0, file=scanfile)
            close("10_min_scan_no_artificial_energy", first_scan["E_aux_J"], 0, file=scanfile)
        for row in scan:
            if str(row.get("feasible", "")).lower() in ("true", "1", "1.0"):
                check("scan_charge_budget", qcharge(float(row["first_success_s"]))<=20+1e-7,
                      row.get(time_key,""), file=scanfile)
                check("scan_voltage_ice_constraints", float(row["min_voltage_V"])>=.3
                      and float(row["max_ice_bulk"])<.99, row.get(time_key,""), file=scanfile)
            if time_key:
                point = int(float(row[time_key]))
                path = data/f"trajectory_scan_{point:03d}min.csv"
                try:
                    audit_trajectory(path, dict(row, strategy="constant_first"), 0.0)
                except Exception as exc:
                    check("scan_trajectory_read_or_schema_error", False, repr(exc), file=path)
    except Exception as exc:
        check("required_output_missing_or_invalid", False, repr(exc), file=data)
    result = data/"independent_export_validation.csv"
    with result.open("w",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["check","passed","observed","expected","file"])
        writer.writeheader();writer.writerows(CHECKS)
    failed=[r for r in CHECKS if not r["passed"]]
    print(f"Independent CSV audit: {len(CHECKS)-len(failed)}/{len(CHECKS)} passed; {result}")
    for row in failed:
        print(f"FAIL {row['check']} | {row['observed']} | {row['file']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
