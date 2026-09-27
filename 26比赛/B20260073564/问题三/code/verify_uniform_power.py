"""Confirm that uniform full-power is the P-strategy optimum (not a search artifact).

The analytic derivation (3.5.5, ignoring inter-cell conduction) predicts
q_e > q_n > q_c.  The full coupled model instead returns q = (1,1,1,1,1).
This script fixes the end/near-end powers at 1.0, scans the centre power and
a few non-uniform allocations, and shows the energy is minimised at full power
because inter-cell conduction makes every cell's heat reach the bottleneck end
cells (see data/optimization_search_P.csv for the full search).

Run with the same Python as aux_model.py.  On Python 3.14 the frozen Q2
.python_deps (cp312) must be bypassed; importing the native libs first makes
the vendored sys.path insert a no-op, so we do that unconditionally.
"""
import sys
import numpy, scipy, numba, matplotlib  # noqa: F401  native-lib pre-import
from scipy.optimize import brentq

ROOT = __file__
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__)))
from aux_model import simulate  # noqa: E402


def th_for_crossing(power, tol=1e-4):
    """Preheat duration making min cell temperature just cross +tol degC."""
    def f(t):
        s, *_ = simulate("P", power, t, dt=0.025, scale=4)
        return s["final_min_T_C"] - tol

    lo, hi = 10.0, 90.0
    while f(hi) < 0:
        hi *= 1.5
        if hi > 400:
            return None
    return brentq(f, lo, hi, xtol=1e-7)


def main():
    allocs = {
        "uniform (1,1,1,1,1)":            [1, 1, 1, 1, 1],
        "center 0.5 (1,1,0.5,1,1)":       [1, 1, 0.5, 1, 1],
        "center 0.36 (1,1,0.36,1,1)":     [1, 1, 0.36, 1, 1],
        "center 0.1 (1,1,0.1,1,1)":       [1, 1, 0.1, 1, 1],
        "near+center (1,0.6,0.4,0.6,1)":  [1, 0.6, 0.4, 0.6, 1],
        "near+center (1,0.5,0.2,0.5,1)":  [1, 0.5, 0.2, 0.5, 1],
    }
    print(f"{'allocation':32s} {'th_s':>7s} {'sum_q':>6s} {'E_aux_J':>9s}")
    for name, p in allocs.items():
        th = th_for_crossing(p)
        if th is None:
            print(f"{name:32s}   no crossing within 400 s")
            continue
        print(f"{name:32s} {th:7.3f} {sum(p):6.3f} {25*th*sum(p):9.1f}")


if __name__ == "__main__":
    main()
