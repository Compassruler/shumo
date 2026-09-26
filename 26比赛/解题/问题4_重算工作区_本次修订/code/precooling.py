"""Conservative Q4 precooling: 33 material layers, FVM and backward Euler.

Inputs and temperature outputs use deg C; SI is used for all other quantities.
The seven-node order is the Q3 plant order [T1,T2,T3,T4,T5,TEL,TER].
Run this file to regenerate precooling CSVs. No prior Q4 output is read.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np
try:
    from scipy.linalg import cholesky_banded, cho_solve_banded, eigh_tridiagonal
    LINEAR_ALGEBRA_BACKEND = "scipy.linalg"
except ImportError:
    # NumPy-only fallback keeps this independent precooling module reproducible
    # even when the full electrochemistry environment has not yet been installed.
    LINEAR_ALGEBRA_BACKEND = "numpy.linalg + explicit tridiagonal Cholesky"

    def cholesky_banded(ab, lower=True, check_finite=False):
        if not lower:
            raise ValueError("only lower band form is implemented")
        factor = ab.copy()
        factor[0,0] = np.sqrt(ab[0,0])
        for i in range(1, ab.shape[1]):
            factor[1,i-1] = ab[1,i-1]/factor[0,i-1]
            factor[0,i] = np.sqrt(ab[0,i]-factor[1,i-1]**2)
        return factor

    def cho_solve_banded(cb_and_lower, rhs, check_finite=False):
        factor, lower = cb_and_lower
        if not lower:
            raise ValueError("only lower band form is implemented")
        result = rhs.copy()
        result[0] /= factor[0,0]
        for i in range(1, len(result)):
            result[i] = (result[i]-factor[1,i-1]*result[i-1])/factor[0,i]
        result[-1] /= factor[0,-1]
        for i in range(len(result)-2, -1, -1):
            result[i] = (result[i]-factor[1,i]*result[i+1])/factor[0,i]
        return result

    def eigh_tridiagonal(diagonal, off_diagonal, check_finite=False):
        symmetric = np.diag(diagonal)+np.diag(off_diagonal,1)+np.diag(off_diagonal,-1)
        return np.linalg.eigh(symmetric)


AREA_M2 = 0.0025
T_INIT_C = 25.0
T_AMB_C = -30.0
NODE_NAMES = [f"T{k}_C" for k in range(1, 6)] + ["TEL_C", "TER_C"]


@dataclass(frozen=True)
class Material:
    thickness_m: float
    rho_kg_m3: float
    cp_J_kgK: float
    k_W_mK: float
    cells: int

    @property
    def capacity_J_m2K(self):
        return self.thickness_m * self.rho_kg_m3 * self.cp_J_kgK


# Attachment 1 original values, with no decimal rounding of rho*cp.
MATERIALS = {
    "EP": Material(.01, 7900., 500., 15., 20),
    "BP": Material(.002, 1980., 766., 95., 6),
    "aGDL": Material(.00015, 185., 545., .3, 4),
    "aCL": Material(.0000034, 970., 240., .27, 2),
    "PEM": Material(.000012, 2150., 1050., .24, 2),
    "cCL": Material(.0000113, 970., 240., .27, 2),
    "cGDL": Material(.00015, 185., 545., .3, 4),
}
MEA_ORDER = ("aGDL", "aCL", "PEM", "cCL", "cGDL")
MEA_CAPACITY = sum(MATERIALS[m].capacity_J_m2K for m in MEA_ORDER)
MEA_RESISTANCE = sum(MATERIALS[m].thickness_m / MATERIALS[m].k_W_mK for m in MEA_ORDER)
MEA_THICKNESS = sum(MATERIALS[m].thickness_m for m in MEA_ORDER)


class PrecoolModel:
    """Cell-centred multilayer FVM with exact half-cell Robin resistance.

    ``conductance_factor`` multiplies k in the BP/MEA assembly, preserving EP k.
    Thus G_eff = factor/(R_MEA + R_BP); it is a parametric effective-resistance
    sensitivity, not a claim that contact resistance was measured.
    ``effective_mea=True`` replaces each five-layer MEA by its equivalent k/C.
    """

    def __init__(self, scale=1, h=40., conductance_factor=1., effective_mea=False):
        if int(scale) != scale or scale < 1:
            raise ValueError("scale must be a positive integer")
        if h < 0 or conductance_factor <= 0:
            raise ValueError("h >= 0 and conductance_factor > 0 are required")
        self.scale = int(scale)
        self.h = float(h)
        self.conductance_factor = float(conductance_factor)
        self.effective_mea = bool(effective_mea)
        self.G_eff = self.conductance_factor / (MEA_RESISTANCE + .002 / 95.)
        self.Bi_stack = self.h*(.01/15. + (.006/95.+2.5*MEA_RESISTANCE)/self.conductance_factor)
        self.layers = []
        self._append_layer("EP_L", "EP", -1, None)
        for bp in range(6):
            self._append_layer(f"BP{bp}", "BP", -1, bp)
            if bp < 5:
                if effective_mea:
                    self._append_layer(f"cell{bp+1}_MEA", "MEA", bp, None)
                else:
                    for material in MEA_ORDER:
                        self._append_layer(f"cell{bp+1}_{material}", material, bp, None)
        self._append_layer("EP_R", "EP", -1, None)
        self._build()

    def _append_layer(self, name, material, cell, bp):
        if material == "MEA":
            mat = Material(MEA_THICKNESS, MEA_CAPACITY / MEA_THICKNESS, 1.,
                           MEA_THICKNESS / MEA_RESISTANCE, 14)
        else:
            mat = MATERIALS[material]
        self.layers.append((name, material, cell, bp, mat))

    def _build(self):
        widths, conductivities, capacities, names, materials, owners = [], [], [], [], [], []
        self.layer_rows = []
        xleft = 0.
        for index, (name, material, cell, bp, mat) in enumerate(self.layers):
            count = mat.cells * self.scale
            dx = mat.thickness_m / count
            k = mat.k_W_mK * (1. if material == "EP" else self.conductance_factor)
            for j in range(count):
                widths.append(dx)
                conductivities.append(k)
                capacities.append(mat.rho_kg_m3 * mat.cp_J_kgK * dx)
                names.append(name)
                materials.append(material)
                if material == "EP":
                    owner = 5 if name == "EP_L" else 6
                elif material == "BP":
                    # A shared BP is split at its actual mid-plane. No double count.
                    owner = 0 if bp == 0 else (4 if bp == 5 else bp - 1 if j < count // 2 else bp)
                else:
                    owner = cell
                owners.append(owner)
            self.layer_rows.append(dict(layer=index, name=name, material=material,
                x_left_mm=1000*xleft, x_right_mm=1000*(xleft+mat.thickness_m),
                thickness_m=mat.thickness_m, rho_kg_m3=mat.rho_kg_m3,
                cp_J_kgK=mat.cp_J_kgK, k_W_mK=k,
                capacity_J_m2K=mat.capacity_J_m2K, control_volumes=count))
            xleft += mat.thickness_m
        self.dx = np.asarray(widths)
        self.k = np.asarray(conductivities)
        self.C = np.asarray(capacities)
        self.region = np.asarray(names)
        self.material = np.asarray(materials)
        self.owner = np.asarray(owners)
        self.x = np.cumsum(self.dx) - self.dx / 2.
        self.Ls = float(np.sum(self.dx))
        self.g = 1. / (self.dx[:-1] / (2*self.k[:-1]) + self.dx[1:] / (2*self.k[1:]))
        self.boundary_g = np.zeros(2) if self.h == 0 else 1. / (1./self.h + self.dx[[0,-1]]/(2*self.k[[0,-1]]))
        self.diag_loss = np.zeros(len(self.dx))
        self.diag_loss[:-1] += self.g
        self.diag_loss[1:] += self.g
        self.diag_loss[[0,-1]] += self.boundary_g
        self.node_capacities = np.bincount(self.owner, weights=self.C, minlength=7)
        self._factors = {}
        self._eigen = None
        self.last_ledger = []

    def node_temps(self, field_C):
        """Energy-preserving mapping to Q3 [T1..T5,TEL,TER], in deg C."""
        field = self._field(field_C)
        return np.bincount(self.owner, weights=self.C*field, minlength=7) / self.node_capacities

    def spatial_node_temps(self, field_C):
        return self.node_temps(field_C)[[5, 0, 1, 2, 3, 4, 6]]

    def mean_temp(self, field_C):
        return float(np.dot(self.C, self._field(field_C)) / self.C.sum())

    def length_mean_temp(self, field_C):
        return float(np.dot(self.dx, self._field(field_C)) / self.dx.sum())

    def surface_temps(self, field_C, ambient_C=T_AMB_C):
        field = self._field(field_C)
        if self.h == 0:
            return field[[0, -1]].copy()
        return ambient_C + self.boundary_g / self.h * (field[[0,-1]] - ambient_C)

    def _field(self, field):
        a = np.asarray(field, dtype=float)
        if a.ndim == 0:
            a = np.full(len(self.dx), float(a))
        if a.shape != self.dx.shape or not np.all(np.isfinite(a)):
            raise ValueError("temperature must be finite and match the FVM mesh")
        return a

    def _be_step(self, deviation, dt):
        key = float(dt)
        if key not in self._factors:
            # Lower band form of symmetric positive-definite (C/dt + L).
            ab = np.zeros((2, len(self.C)))
            ab[0] = self.C / dt + self.diag_loss
            ab[1, :-1] = -self.g
            self._factors[key] = cholesky_banded(ab, lower=True, check_finite=False)
        return cho_solve_banded((self._factors[key], True), self.C/dt*deviation,
                               check_finite=False)

    def eigenmodes(self):
        """Mass-symmetric eigenpairs of d(C^1/2 u)/dt = S(C^1/2 u)."""
        if self._eigen is None:
            diagonal = -self.diag_loss / self.C
            off_diagonal = self.g / np.sqrt(self.C[:-1]*self.C[1:])
            self._eigen = eigh_tridiagonal(diagonal, off_diagonal, check_finite=False)
        return self._eigen

    def exact(self, seconds, initial_C=T_INIT_C, ambient_C=T_AMB_C):
        """Independent matrix-exponential solution of the spatial FVM ODE."""
        if seconds < 0:
            raise ValueError("seconds must be nonnegative")
        u0 = self._field(initial_C) - ambient_C
        if seconds == 0 or (self.h == 0 and np.ptp(u0) == 0):
            return u0 + ambient_C
        eigenvalues, eigenvectors = self.eigenmodes()
        coeff = eigenvectors.T @ (np.sqrt(self.C)*u0)
        return ambient_C + (eigenvectors @ (coeff*np.exp(eigenvalues*seconds))) / np.sqrt(self.C)

    def scan(self, tau_c_min_list, dt=.25, initial_C=T_INIT_C,
             ambient_C=T_AMB_C, method="be"):
        """Single sweep with exact landing on each requested time; dict minutes:field."""
        minutes = np.unique(np.asarray(list(tau_c_min_list), dtype=float))
        if not len(minutes) or np.any(minutes < 0) or dt <= 0:
            raise ValueError("nonempty nonnegative times and positive dt required")
        if method == "expm":
            return {float(m): self.exact(60.*m, initial_C, ambient_C) for m in minutes}
        if method != "be":
            raise ValueError("method must be 'be' or 'expm'")
        initial = self._field(initial_C)
        deviation = initial - ambient_C
        t = 0.
        loss = 0.
        initial_energy = float(np.dot(self.C, deviation))
        out = {}
        self.last_ledger = []
        for minute in minutes:
            end = 60.*minute
            while t < end - 1e-10:
                step = min(float(dt), end-t)
                deviation = self._be_step(deviation, step)
                # The same endpoint quadrature as backward Euler gives a discrete
                # energy identity. It is NOT compared to a different quadrature.
                loss += float(np.dot(self.boundary_g, deviation[[0,-1]]))*step
                t += step
            field = deviation + ambient_C
            energy_released = initial_energy - float(np.dot(self.C, deviation))
            surface = self.surface_temps(field, ambient_C)
            self.last_ledger.append(dict(cooling_min=float(minute),
                energy_released_J=AREA_M2*energy_released,
                convective_loss_J=AREA_M2*loss,
                residual_J=AREA_M2*(energy_released-loss),
                relative_residual=abs(energy_released-loss)/max(abs(energy_released),1.),
                surface_left_C=float(surface[0]), surface_right_C=float(surface[1]),
                mean_capacity_C=self.mean_temp(field)))
            out[float(minute)] = field.copy()
        return out

    def solve(self, tau_c_s, dt=.25, T0=None, method="be"):
        """Return full temperature in deg C; T0, if supplied, is also deg C."""
        initial = T_INIT_C if T0 is None else T0
        return self.scan([float(tau_c_s)/60.], dt=dt, initial_C=initial, method=method)[float(tau_c_s)/60.]


def _write_csv(path, rows, fields=None):
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summary_row(model, minute, field):
    nodes = model.node_temps(field)
    surface = model.surface_temps(field)
    field_range = float(field.max()-min(field.min(),surface.min()))
    mean_capacity = model.mean_temp(field)
    return dict(cooling_min=float(minute), **dict(zip(NODE_NAMES, nodes)),
        mean_capacity_C=mean_capacity, mean_length_C=model.length_mean_temp(field),
        mean_seven_nodes_C=float(nodes.mean()), field_min_C=float(min(field.min(),surface.min())),
        field_max_C=float(field.max()), field_range_K=field_range,
        cell_range_K=float(np.ptp(nodes[:5])), center_minus_left_EP_K=float(nodes[2]-nodes[5]),
        surface_left_C=float(surface[0]), surface_right_C=float(surface[1]),
        relative_field_range=field_range/max(abs(mean_capacity-T_AMB_C),1e-14),
        Bi_stack=model.Bi_stack)


def validation_rows(model, scan):
    """Meaningful discretization, energy, limit and mapping checks, no fake PASS."""
    rows = []
    def add(test, value, tolerance, unit, note):
        rows.append(dict(test=test, observed=float(value), tolerance=float(tolerance),
                         unit=unit, passed=bool(abs(value) <= tolerance), note=note))
    add("total_thickness", model.Ls-.0336335, 1e-13, "m", "2 EP + 6 BP + 25 MEA constituent layers")
    expected_C = 79000. + 6*.002*1980*766 + 5*MEA_CAPACITY
    add("total_capacity", model.C.sum()-expected_C, 1e-8, "J/m2/K", "Original material values, no rounded rho*cp")
    mapping_error = max(abs(np.dot(model.C, field) - np.dot(model.node_capacities, model.node_temps(field))) for field in scan.values())
    add("seven_node_energy_mapping", mapping_error, 1e-8, "J/m2", "All CVs belong to exactly one node; BP halves split geometrically")
    add("implicit_energy_balance", max(abs(z["residual_J"]) for z in model.last_ledger), 2e-5, "J", "Backward Euler loss quadrature matched to thermal equation")
    max_be_error = max(np.max(np.abs(field-model.exact(60*minute))) for minute,field in scan.items())
    add("BE_vs_matrix_exponential", max_be_error, .004, "K", "dt=0.25 s, 10:5:100 min")
    adiabatic = PrecoolModel(h=0.)
    add("adiabatic_uniform_limit", np.max(np.abs(adiabatic.solve(6000.)-25.)), 2e-6, "K", "h=0, initial 25 C")
    # Nonuniform insulated initial state additionally tests internal conservation.
    nonuniform = 25.+3.*np.cos(2*np.pi*adiabatic.x/adiabatic.Ls)
    insulated = adiabatic.solve(20., dt=.25, T0=nonuniform)
    add("adiabatic_nonuniform_conservation", AREA_M2*np.dot(adiabatic.C,insulated-nonuniform), 1e-6, "J", "h=0, nonuniform initial field")
    add("long_time_ambient_limit", np.max(np.abs(model.exact(24*3600.)+30.)), 1e-8, "K", "24 hours")
    add("maximum_principle", max(0.,max(float(f.max()-25.) for f in scan.values()),max(float(-30.-f.min()) for f in scan.values())), 1e-10, "K", "No new extrema under cooling")
    values = list(scan.values())
    add("pointwise_monotonic_cooling", max(0.,max(float(np.max(b-a)) for a,b in zip(values[:-1],values[1:]))), 1e-10, "K", "Every control volume cools over the sampled times")
    add("approximate_mirror_symmetry", max(np.max(np.abs(model.node_temps(f)[[0,1,5]]-model.node_temps(f)[[4,3,6]])) for f in values), .001, "K", "aCL and cCL thicknesses differ; actual oriented five-layer MEA is only approximately mirror symmetric")
    return rows


def convergence_rows():
    rows = []
    sample_minutes = (20.,40.,100.)
    mesh = PrecoolModel(scale=1)
    for dt in (2.,1.,.5,.25,.125):
        results = mesh.scan(sample_minutes, dt=dt)
        for minute, field in results.items():
            exact = mesh.exact(60*minute)
            rows.append(dict(study="time", scale=1, control_volumes=len(mesh.C), dt_s=dt,
                cooling_min=minute, max_field_error_K=float(np.max(np.abs(field-exact))),
                max_node_error_K=float(np.max(np.abs(mesh.node_temps(field)-mesh.node_temps(exact)))),
                reference="same mesh, matrix exponential"))
    reference = PrecoolModel(scale=8)
    target = {m: reference.node_temps(reference.exact(60*m)) for m in sample_minutes}
    for scale in (1,2,4):
        mesh = PrecoolModel(scale=scale)
        for minute in sample_minutes:
            field = mesh.exact(60*minute)
            # Compare same physical projection to avoid interpolation ambiguity.
            rows.append(dict(study="space", scale=scale, control_volumes=len(mesh.C), dt_s=0.,
                cooling_min=minute, max_field_error_K="",
                max_node_error_K=float(np.max(np.abs(mesh.node_temps(field)-target[minute]))),
                reference="scale=8 seven-node energy projection, matrix exponential"))
    return rows


def sensitivity_rows():
    rows = []
    for h in (20.,40.,80.,160.):
        for factor in (.1,.25,.5,1.,2.):
            mesh = PrecoolModel(h=h, conductance_factor=factor)
            for minute in (20.,40.):
                row = summary_row(mesh, minute, mesh.exact(60*minute))
                row.update(h_W_m2K=h, conductance_factor=factor, G_eff_W_m2K=mesh.G_eff,
                           note="k_BP and k_MEA scaled; k_EP fixed; illustrative effective-resistance perturbation")
                rows.append(row)
    return rows


def export_precooling(output_root, dt=.25, scale=1):
    """Regenerate all precooling CSV outputs, returning model and 19 sampled fields."""
    root = Path(output_root)
    data = root / "data"
    model = PrecoolModel(scale=scale)
    fields = model.scan(np.arange(10,101,5), dt=dt)
    ledger = list(model.last_ledger)
    _write_csv(data/"precooling_layers.csv", model.layer_rows)
    _write_csv(data/"precooling_nodes.csv", [summary_row(model,m,f) for m,f in fields.items()])
    rows = []
    for minute, field in fields.items():
        for i, temperature in enumerate(field):
            rows.append(dict(cooling_min=minute, cv=i, x_mm=1000*model.x[i],
                dx_mm=1000*model.dx[i], layer=model.region[i], material=model.material[i],
                node=NODE_NAMES[model.owner[i]], capacity_J_m2K=model.C[i],
                k_W_mK=model.k[i], temperature_C=temperature))
    _write_csv(data/"precooling_fields.csv", rows)
    _write_csv(data/"precooling_energy_balance.csv", ledger)
    checks = validation_rows(model, fields)
    _write_csv(data/"precooling_validation.csv", checks)
    _write_csv(data/"precooling_convergence.csv", convergence_rows())
    _write_csv(data/"precooling_sensitivity.csv", sensitivity_rows())
    initial_rows = []
    for name, minute in (("case1",None),("case2",20.),("case3",40.)):
        field = np.full(len(model.C),-30.) if minute is None else fields[minute]
        row = summary_row(model, -1. if minute is None else minute, field)
        row = dict(case=name, **row)
        initial_rows.append(row)
    _write_csv(data/"initial_temperature_cases.csv", initial_rows)
    node_capacity_rows = [dict(node=name, capacity_J_m2K=cap, capacity_J_K=AREA_M2*cap)
                          for name,cap in zip(NODE_NAMES,model.node_capacities)]
    _write_csv(data/"precooling_node_capacities.csv", node_capacity_rows)
    eigenvalues,eigenvectors = model.eigenmodes()
    initial_coefficients = eigenvectors.T @ (np.sqrt(model.C)*(T_INIT_C-T_AMB_C))
    mode_rows = []
    for i in range(10):
        idx = len(eigenvalues)-1-i
        modal_temperature = initial_coefficients[idx]*eigenvectors[:,idx]/np.sqrt(model.C)
        mode_rows.append(dict(mode=i+1,eigenvalue_per_s=eigenvalues[idx],
            time_constant_s=-1./eigenvalues[idx],
            max_initial_modal_amplitude_K=float(np.max(np.abs(modal_temperature)))))
    _write_csv(data/"precooling_slow_modes.csv", mode_rows)
    failures = [row["test"] for row in checks if not row["passed"]]
    if failures:
        raise AssertionError("Precooling validation failed: " + ", ".join(failures))
    return model, fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dt", type=float, default=.25)
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()
    model, fields = export_precooling(args.output, args.dt, args.scale)
    print(f"FVM: {len(model.C)} CVs, {len(model.layers)} layers, L={1000*model.Ls:.7f} mm, C={model.C.sum():.8f} J/m2/K, backend={LINEAR_ALGEBRA_BACKEND}")
    for minute in (20.,40.):
        print(minute, "min:", summary_row(model,minute,fields[minute]))


if __name__ == "__main__":
    main()
