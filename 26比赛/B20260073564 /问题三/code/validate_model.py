"""Independent Q3/Q2 regression, heater accounting, and seven-node checks."""
import csv
import importlib.util
import os
import sys
from pathlib import Path

# Keep validation-only compilation products inside Q3, including the Q2 import.
os.environ.setdefault(
    "NUMBA_CACHE_DIR",
    str(Path(__file__).resolve().parent / "__pycache__" / "validation_numba_cache"))
import aux_model as aux

np = aux.np
ROOT = aux.ROOT
checks = []


def check(name, category, error, tolerance, note="", unit=""):
    error = float(error)
    tolerance = float(tolerance)
    checks.append({
        "check": name, "category": category, "error": error,
        "tolerance": tolerance, "unit": unit,
        "passed": bool(np.isfinite(error) and error <= tolerance), "note": note,
    })


def compare(name, category, actual, expected, tolerance, unit="", note=""):
    check(name, category, np.max(np.abs(np.asarray(actual)-np.asarray(expected))),
          tolerance, note, unit)


def require(name, category, condition, note=""):
    check(name, category, 0 if condition else 1, 0, note)


def main():
    q2_path = ROOT.parent / "问题2_求解结果" / "code" / "stack_model.py"
    spec = importlib.util.spec_from_file_location("q2_stack_reference", q2_path)
    q2 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = q2
    spec.loader.exec_module(q2)
    i3 = {name: n for n, name in enumerate(aux.HISTORY)}
    i2 = {name: n for n, name in enumerate(q2.HISTORY_NAMES)}

    # Same numerical scheme, time horizon and controls; only representation differs.
    old, h2, st2, t2 = q2.simulate(
        "ramp", [.005, .3], T0=-30., dt=.1, scale=1, tmax=30., record=True)
    new, h3, st3, t3 = aux.simulate(
        "C", np.zeros(5), 0., dt=.1, scale=1, post=30., record=True)
    compare("zero_aux_time_grid", "Q2 regression", h3[:, 0], h2[:, 0], 1e-11, "s")
    compare("zero_aux_charge_history", "Q2 regression",
            h3[:, i3["charge_C_cm2"]], h2[:, i2["charge_C_cm2"]], 1e-12, "C/cm2")
    compare("Q2_current_left_limit_convention", "Q2 regression",
            h2[:, i2["j_A_cm2"]], .005*np.maximum(h2[:, 0]-1e-9, 0.),
            1e-14, "A/cm2",
            "Q2 records current(t-1e-9) after each integration step.")
    compare("Q3_current_endpoint_convention", "Q2 regression",
            h3[:, i3["j_A_cm2"]], .005*h3[:, 0],
            1e-14, "A/cm2", "Q3 records current(t) at a continuous ramp endpoint.")
    for new_name, old_name in [
        ("T1_C", "T1_C"), ("T2_C", "T2_C"), ("T3_C", "T3_C"),
        ("T4_C", "T2_C"), ("T5_C", "T1_C"),
        ("TEL_C", "TEP_C"), ("TER_C", "TEP_C"),
    ]:
        compare("zero_aux_"+new_name, "Q2 regression",
                h3[:, i3[new_name]], h2[:, i2[old_name]], 1e-9, "K")
    for k, old_k in [(1, 1), (2, 2), (3, 3), (4, 2), (5, 1)]:
        for field, unit in [("V", "V"), ("ice_bulk", "1"),
                            ("pore_ice_saturation", "1")]:
            tolerance = 1e-8 if field == "V" else 1e-10
            note = ("Voltage histories use the documented left-limit/endpoint "
                    "current convention; allowed regression difference is 1e-8 V."
                    if field == "V" else "")
            compare(f"zero_aux_cell{k}_{field}", "Q2 regression",
                    h3[:, i3[f"cell{k}_{field}"]],
                    h2[:, i2[f"cell{old_k}_{field}"]], tolerance, unit, note)
    for new_name, old_name in [
        ("E_gen_J", "heat_gen_J_m2"), ("E_phase_J", "heat_phase_J_m2"),
        ("E_loss_J", "heat_loss_J_m2"),
        ("E_sensible_J", "heat_sensible_J_m2"),
    ]:
        compare("zero_aux_"+new_name, "Q2 regression",
                h3[:, i3[new_name]], aux.AREA*h2[:, i2[old_name]], 1e-8, "J")
    compare("zero_aux_final_temperatures", "Q2 regression",
            t3[[0, 1, 2, 5]], t2, 1e-9, "K")
    for k, old_k in [(0, 0), (1, 1), (2, 2), (3, 1), (4, 0)]:
        err = max(np.max(np.abs(a-b)) for a, b in zip(st3[k], st2[old_k]))
        check(f"zero_aux_state_{k+1}", "Q2 regression", err, 1e-9,
              "All five mass/gas state arrays, native units")
    compare("zero_aux_max_ice", "Q2 regression",
            new["max_ice_bulk"], old["max_ice_bulk"], 1e-11, "1")
    compare("zero_aux_min_voltage", "Q2 regression",
            new["min_voltage_V"], old["min_voltage_V"], 1e-11, "V")
    compare("zero_aux_energy", "heater accounting", new["E_aux_J"], 0., 0., "J")

    cfg = aux.make_config(scale=1, j0=aux.J0)
    states = [aux.initial_state(cfg, 243.15) for _ in range(5)]
    temp = np.full(7, -30.)
    c, g, h = aux.network(cfg, states, aux.THERMAL)
    compare("conductance_matrix_symmetric", "network",
            g, g.T, 1e-12, "W/(m2 K)")
    compare("internal_heat_flow_cancels", "network",
            g.sum(axis=0), h, 1e-12, "W/(m2 K)")
    bp_total = sum(c[k]-aux.properties(cfg, states[k])[0] for k in range(5))
    compare("six_shared_plate_heat_capacity", "network", bp_total,
            6*.002*1980*766, 1e-9, "J/(m2 K)")

    ns, nt, en, wa, er = aux.advance(
        cfg, states, temp, 0., 1., np.zeros(5), aux.THERMAL)
    compare("idle_zero_auxiliary_energy", "idle membrane exchange", en[0], 0., 0., "J")
    compare("idle_zero_electrochemical_energy", "idle membrane exchange", en[1], 0., 0., "J")
    require("idle_desorption_heat_is_negative", "idle membrane exchange", en[2] < 0.,
            f"Computed phase/desorption heat = {en[2]:.16g} J")
    membrane_change = sum(np.dot(ns[k][1][cfg.mem]-states[k][1][cfg.mem],
                                  cfg.dx[cfg.mem]) for k in range(5))*aux.AREA
    require("idle_membrane_water_decreases", "idle membrane exchange",
            membrane_change < 0.,
            f"Membrane liquid inventory change = {membrane_change:.16g} kg")
    compare("idle_no_reaction_water", "idle membrane exchange", wa[0], 0., 0., "kg/m2")
    check("idle_energy_balance", "idle membrane exchange",
          abs(en[4]-en[0]-en[1]-en[2]+en[3]), 1e-8, unit="J")
    initial_water = sum(aux.diagnostics(cfg, s)[7] for s in states)
    final_water = sum(aux.diagnostics(cfg, s)[7] for s in ns)
    check("idle_water_balance", "idle membrane exchange",
          abs((final_water-initial_water-wa[0]+wa[1])*aux.AREA), 1e-14, unit="kg")
    check("idle_thermal_iteration", "idle membrane exchange", er, 1e-9, unit="K")

    left, hl, sl, tl = aux.simulate(
        "P", [1, 0, 0, 0, 0], 5., dt=.1, scale=1, post=0., record=True)
    right, hr, sr, tr = aux.simulate(
        "P", [0, 0, 0, 0, 1], 5., dt=.1, scale=1, post=0., record=True)
    mirror = [4, 3, 2, 1, 0, 6, 5]
    compare("asymmetric_heaters_temperature_mirror", "independent heaters",
            hl[:, 4:11], hr[:, 4:11][:, mirror], 1e-10, "K")
    compare("asymmetric_heaters_voltage_mirror", "independent heaters",
            hl[:, 11:16], hr[:, 11:16][:, ::-1], 1e-10, "V")
    require("one_sided_heater_not_forced_symmetric", "independent heaters",
            tl[0]-tl[4] > .1,
            f"T1 minus T5 after 5 s = {tl[0]-tl[4]:.16g} K")
    for k in range(5):
        err = max(np.max(np.abs(a-b)) for a, b in zip(sl[k], sr[4-k]))
        check(f"asymmetric_state_mirror_{k+1}", "independent heaters",
              err, 1e-9, "All five mass/gas state arrays, native units")
    compare("one_heater_5s_energy", "heater accounting",
            left["E_aux_J"], 25.*5., 1e-10, "J")
    compare("mirrored_heater_energy", "heater accounting",
            left["E_aux_J"], right["E_aux_J"], 1e-12, "J")

    power = np.array([.8, .1, .4, 0., .3])
    th = 2.3
    mixed, hm, sm, tm = aux.simulate(
        "P", power, th, dt=.17, scale=1, post=1.7, record=True)
    expected_history = 25.*power.sum()*np.minimum(hm[:, 0], th)
    compare("non_grid_switch_energy_history", "heater accounting",
            hm[:, i3["E_aux_J"]], expected_history, 1e-9, "J")
    compare("non_grid_switch_total_energy", "heater accounting",
            mixed["E_aux_J"], 25.*power.sum()*th, 1e-9, "J")
    check("switch_event_recorded_exactly", "heater accounting",
          np.min(np.abs(hm[:, 0]-th)), 1e-12, unit="s")
    compare("shifted_loading_charge", "heater accounting",
            mixed["charge_C_cm2"], .0025*1.7**2, 1e-12, "C/cm2")
    for label, summary in [("zero_aux", new), ("left", left), ("right", right),
                           ("mixed", mixed)]:
        check(label+"_total_energy_balance", "conservation",
              abs(summary["energy_residual_J"]), 1e-8, unit="J")
        check(label+"_total_water_balance", "conservation",
              abs(summary["water_residual_kg"]), 1e-13, unit="kg")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        check("validation_runtime", "execution", 1., 0., repr(exc))
    path = ROOT / "data" / "model_validation.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checks[0]))
        writer.writeheader()
        writer.writerows(checks)
    failures = [row for row in checks if not row["passed"]]
    print(f"Model checks: {len(checks)-len(failures)}/{len(checks)} passed")
    print(path)
    for failure in failures:
        print(failure)
    sys.exit(bool(failures))
