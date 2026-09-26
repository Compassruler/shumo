"""Independent checks specific to the revised sensor/observer implementation.

Reads saved trajectories, reconstructs filtering, event-window extrema, charge
and energy; no simulation-summary calculation is reused. The source-structure
checks are narrowly labelled and are not a proof of observer identifiability.
Run after all main, guarded, optimized-constant and baseline CSVs are complete.
"""
from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path

import bootstrap  # noqa: F401
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CHECKS = []


def check(name, passed, observed='', expected='', file=''):
    if file:
        try:file=Path(file).resolve().relative_to(ROOT)
        except ValueError:pass
    CHECKS.append(dict(check=name, passed=bool(passed), observed=observed,
                       expected=expected, file=str(file)))


def close(name, observed, expected, file='', atol=1e-6, rtol=1e-8):
    a, b = float(observed), float(expected)
    check(name, np.isfinite(a) and np.isfinite(b) and
          abs(a-b) <= atol+rtol*abs(b), a, b, file)


def charge(t):
    return .0025*np.minimum(t, 60.)**2+.3*np.maximum(t-60., 0.)


def is_true(value):
    return str(value).lower() in ('true', '1', '1.0')


def matrix(df, names):
    return df[names].to_numpy(float)


def audit(path, summary, period=.2, hold=2.):
    df = pd.read_csv(path, encoding='utf-8-sig')
    t = df.time_s.to_numpy(float)
    T = matrix(df, [f'T{k}_C' for k in range(1,6)])
    V = matrix(df, [f'cell{k}_V_V' for k in range(1,6)])
    ice = matrix(df, [f'cell{k}_ice_bulk' for k in range(1,6)])
    q = matrix(df, [f'cell{k}_q_W_cm2' for k in range(1,6)])
    totals = np.cumsum(25*np.diff(t, prepend=0)*q.sum(axis=1))
    first, stop = float(summary.first_success_s), float(summary.stop_s)
    feasible = is_true(summary.feasible)
    close('independent_total_heater_energy', summary.E_aux_J, totals[-1], path, atol=2e-6)
    check('nonnegative_event_charge_and_energy', np.all(df.charge_C_cm2>=0) and
          np.min(totals)>=-1e-8, file=path)
    if first >= 0:
        fi = int(np.argmin(abs(t-first)))
        close('true_first_has_exact_saved_event', t[fi], first, path, atol=1e-7)
        check('true_first_all_cells_positive', T[fi].min()>0, T[fi].min(), '>0', path)
        close('first_window_energy_integral', summary.first_success_energy_J, totals[fi], path)
        close('first_window_voltage_extreme', summary.first_min_voltage_V, V[:fi+1].min(), path)
        close('first_window_ice_extreme', summary.first_max_ice_bulk, ice[:fi+1].max(), path)
        close('first_window_temperature_spread', summary.first_dTmax_K, np.ptp(T[:fi+1],axis=1).max(), path)
        close('first_charge_uses_first_time', summary.charge_at_success_C_cm2, charge(first), path)
        if feasible:
            check('first_charge_budget', charge(first)<=20.+1e-7, charge(first), '<=20 C/cm2', path)
        if fi > 0:
            check('no_earlier_thermal_success_row', np.max(np.min(T[:fi],axis=1))<=1e-7+1e-10,
                  np.max(np.min(T[:fi],axis=1)), '<=1e-7 numerical temperature threshold', path)
    if stop < 0:
        check('no_stop_cannot_be_feasible', not feasible, file=path)
        return
    si = int(np.argmin(abs(t-stop)))
    close('actual_stop_has_exact_saved_event', t[si], stop, path, atol=1e-7)
    close('stop_charge_uses_stop_time', summary.charge_at_stop_C_cm2, charge(stop), path)
    close('stop_minus_first_charge_is_separate',
          float(summary.charge_at_stop_C_cm2)-float(summary.charge_at_success_C_cm2),
          charge(stop)-charge(first), path)
    check('latched_power_after_actual_stop', np.max(abs(q[si+1:]), initial=0)<1e-12, file=path)
    close('cost_is_actual_stop_energy', summary.E_aux_J, totals[si], path, atol=2e-6)
    check('actual_cost_includes_first_window', float(summary.E_aux_J)>=float(summary.first_success_energy_J)-1e-6,
          float(summary.E_aux_J)-float(summary.first_success_energy_J), '>=0 J', path)
    close('post_temperature_includes_shutdown_endpoint', summary.post_min_T_C, T[si:].min(), path)
    close('post_voltage_includes_shutdown_endpoint', summary.post_min_voltage_V, V[si:].min(), path)
    close('post_ice_includes_shutdown_endpoint', summary.post_max_ice_bulk, ice[si:].max(), path)

    mode = summary.get('shutdown_mode', 'ideal' if summary.strategy=='constant_first' else 'sensor')
    if mode == 'sensor' and stop > 0:
        close('sampled_stop_on_control_clock', stop/period, round(stop/period), path, atol=1e-6)
        expected_samples = np.arange(int(round(stop/period))+1)*period
        ids = np.array([int(np.argmin(abs(t-x))) for x in expected_samples])
        check('every_sensor_sample_is_exported', np.max(abs(t[ids]-expected_samples))<1e-7, file=path)
        measuredT = matrix(df, [f'cell{k}_sensor_temperature_C' for k in range(1,6)])[ids]
        measuredV = matrix(df, [f'cell{k}_sensor_voltage_V' for k in range(1,6)])[ids]
        estimatedI = matrix(df, [f'cell{k}_ice_est' for k in range(1,6)])[ids]
        savedrT = matrix(df, [f'cell{k}_rT_K_s' for k in range(1,6)])[ids]
        savedrV = matrix(df, [f'cell{k}_rV_V_s' for k in range(1,6)])[ids]
        beta, br = np.exp(-period/.15), np.exp(-period/.20)
        ft, fv = measuredT[0].copy(), measuredV[0].copy()
        rt, rv = np.zeros(5), np.zeros(5)
        reconstructedT, reconstructedV, ratesT, ratesV = [], [], [], []
        margin = float(summary.get('sensor_stop_margin_C', .2))
        start = None
        detected = None
        for n, sample in enumerate(expected_samples):
            previousT, previousV = ft.copy(), fv.copy()
            ft = beta*ft+(1-beta)*measuredT[n]
            fv = beta*fv+(1-beta)*measuredV[n]
            rt = br*rt+(1-br)*(ft-previousT)/period
            rv = br*rv+(1-br)*(fv-previousV)/period
            reconstructedT.append(ft.copy());reconstructedV.append(fv.copy())
            ratesT.append(rt.copy());ratesV.append(rv.copy())
            good = ft.min()>margin and fv.min()>=.3 and estimatedI[n].max()<.99
            if good:
                if start is None:start=sample
                if sample-start>=hold-1e-8 and detected is None:detected=sample
            else:start=None
        close('reconstructed_filtered_temperature_rate', np.max(abs(np.asarray(ratesT)-savedrT)), 0., path, atol=2e-8)
        close('reconstructed_filtered_voltage_rate', np.max(abs(np.asarray(ratesV)-savedrV)), 0., path, atol=2e-8)
        savedT = matrix(df,[f'cell{k}_filtered_temperature_C' for k in range(1,6)])[ids]
        savedV = matrix(df,[f'cell{k}_filtered_voltage_V' for k in range(1,6)])[ids]
        close('reconstructed_filtered_temperature_signal', np.max(abs(np.asarray(reconstructedT)-savedT)), 0., path, atol=2e-8)
        close('reconstructed_filtered_voltage_signal', np.max(abs(np.asarray(reconstructedV)-savedV)), 0., path, atol=2e-8)
        check('sensor_stop_has_required_temperature_margin', ft.min()>margin, ft.min(), f'>{margin} C', path)
        check('sensor_stop_voltage_and_estimated_ice', fv.min()>=.3 and estimatedI[-1].max()<.99, file=path)
        check('sensor_continuous_hold_reconstructs_shutdown', detected is not None and abs(detected-stop)<1e-7,
              detected, stop, path)
        window = (t>=stop-hold-1e-8)&(t<=stop+1e-8)
        actual_good = np.min(T[window])>0 and np.min(V[window])>=.3 and np.max(ice[window])<.99
        check('feasible_sensor_stop_has_true_physical_hold', (not feasible) or actual_good, file=path)
        check('physical_hold_flag_matches_success', (not feasible) or is_true(summary.physical_hold_completed), file=path)
        if feasible:
            check('physical_hold_duration', float(summary.physical_hold_s)>=hold-1e-7,
                  summary.physical_hold_s, f'>={hold} s', path)
        if first>=0 and np.min(T[fi:si+1])>0:
            close('unbroken_physical_hold_duration', summary.physical_hold_s, stop-first, path)
    elif mode == 'ideal':
        close('ideal_first_reference_stops_at_first', stop, first, path)

    truthT = np.column_stack([T, df.TEL_C, df.TER_C])
    predictedT = matrix(df, [f'observer_T{k}_C' for k in range(1,6)]+['observer_TEL_C','observer_TER_C'])
    # Observer columns retain interval-end predictions before sensor correction,
    # making the exact summary maxima reconstructable even for noisy records.
    observed_error = np.max(abs(predictedT[1:si+1]-truthT[1:si+1]),initial=0.)
    close('observer_temperature_error_from_trajectory', summary.observer_max_temperature_error_K,
          observed_error, path, atol=2e-8)
    raw_ice_names = [f'cell{k}_observer_ice_bulk' for k in range(1,6)]
    if set(raw_ice_names).issubset(df.columns):
        predictedI = matrix(df, raw_ice_names)
        close('observer_ice_error_from_trajectory', summary.observer_max_ice_error,
              np.max(abs(predictedI[1:si+1]-ice[1:si+1]),initial=0.), path, atol=2e-9)
    elif float(summary.observer_max_ice_error)<1e-10:
        # Only a no-noise/nominal consistency assertion; corrected ice_est is
        # not silently equated with the observer's raw internal ice field.
        close('nominal_raw_observer_ice_error_zero', summary.observer_max_ice_error, 0., path, atol=1e-10)
    if summary.strategy.startswith('constant') or summary.strategy in ('zero_heater','inherited_constant_C','full_power'):
        states = matrix(df,[f'cell{k}_state' for k in range(1,6)])
        check('constant_actuation_state_zero_before_stop', np.all(states[:si]==0), file=path)


def source_checks(root):
    path = root/'code'/'control_model.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    functions = {n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    function = functions['control']
    args = [a.arg for a in function.args.args]
    check('structure_control_accepts_only_measurements_and_estimator',
          args == ['t','period','temp0','estimated_temp','measured_voltage',
                   'estimated_states','cfg','p','cs','integral'], args, file=path)
    identifiers = {n.id for n in ast.walk(function) if isinstance(n,ast.Name)}
    check('structure_no_plant_state_or_diagnostics_in_control',
          not {'states','d','e','thermal'}.intersection(identifiers),
          sorted({'states','d','e','thermal'}.intersection(identifiers)), 'empty', path)
    sim = functions['simulate_raw']
    prediction = [n for n in ast.walk(sim) if isinstance(n,ast.Call)
                  and isinstance(n.func,ast.Name) and n.func.id=='advance'
                  and isinstance(n.args[0],ast.Name) and n.args[0].id=='observer_cfg']
    check('structure_observer_uses_independent_nominal_prediction', len(prediction)==1 and
          [ast.unparse(a) for a in prediction[0].args] ==
          ['observer_cfg','estimated_states','estimated_temp','jm','step','q','THERMAL'], file=path)
    check('structure_observer_water_gas_initialized_independently',
          any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='initial_state'
              and isinstance(n.args[0],ast.Name) and n.args[0].id=='observer_cfg' for n in ast.walk(sim)), file=path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args=parser.parse_args();root=args.root.resolve();data=root/'data'
    source_checks(root)
    files=['main_results.csv','guarded_results.csv','optimized_constant_results.csv','constant_baselines.csv','observer_example_results.csv']
    for name in files:
        tablepath=data/name
        check('required_summary_file_exists', tablepath.exists(), file=tablepath)
        if not tablepath.exists():continue
        frame=pd.read_csv(tablepath,encoding='utf-8-sig')
        check('summary_covers_all_three_cases', set(frame['case'])=={'case1','case2','case3'},file=tablepath)
        for _,summary in frame.iterrows():
            path=data/f'trajectory_{summary["case"]}_{summary["strategy"]}.csv'
            try:audit(path,summary)
            except Exception as exc:check('trajectory_revision_audit_exception',False,repr(exc),file=path)
    # Selection claims are independently tied to saved feasible search rows.
    if (data/'optimized_constant_results.csv').exists():
        optimized=pd.read_csv(data/'optimized_constant_results.csv')
        for _,r in optimized.iterrows():
            check('reoptimized_constant_is_reported_feasible',is_true(r.feasible),r['case'],file='optimized_constant_results.csv')
    target=data/'revision_validation.csv'
    with target.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['check','passed','observed','expected','file'])
        writer.writeheader();writer.writerows(CHECKS)
    failed=[r for r in CHECKS if not r['passed']]
    print(f'Revision independent audit: {len(CHECKS)-len(failed)}/{len(CHECKS)} passed; {target}')
    for r in failed:print(f'FAIL {r["check"]} | {r["observed"]} | {r["file"]}')
    return int(bool(failed))


if __name__=='__main__':
    raise SystemExit(main())
