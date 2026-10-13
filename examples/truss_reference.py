"""
truss_reference.py
==================

Solver referensi elemen hingga untuk model kanonik "screening" berbasis mekanika
(Bagian 3.1.3, 4.1.3, dan 4.5.7 disertasi "Adjusted Redundancy Index (ARI)").

Cakupan
-------
* Elemen batang aksial 1D (bar) dan rangka planar 2D (truss).
* Perakitan matriks kekakuan global K dari elemen-elemen batang.
* Penerapan kondisi batas perletakan (zero-displacement constraints):
    - "pinned": ux = uy = 0 (2D) atau ux = 0 (1D)
    - "roller_vertical":       uy = 0 (roler hanya menahan gaya vertikal)
    - "roller_horizontal":     ux = 0
* Penyelesaian sistem K_ff * u_f = p_f dengan `numpy.linalg.solve`.
* Pemeriksaan rangking (rank) matriks K_ff via `numpy.linalg.eigvals`
  dengan toleransi RELATIF 1e-10 terhadap nilai eigen terbesar.
  JIKA RANK DEFICIENT -> TIDAK menggunakan pseudoinverse; hasil dicatat
  sebagai status "rank_deficient".
* Output: perpindahan nodal, gaya batang (aksial, +tarik/-tarik),
  utilisasi U = |Gaya| / Capacity per elemen, Umax, umax, dan
  regangan energi (strain energy) W = 1/2 u^T K u = sum N^2 L / (2 E A).

Satuan (Strict Constraints)
---------------------------
* Gaya   : kN
* Panjang: mm
* Area   : mm^2
* E      : kN/mm^2  (default 200 kN/mm^2)

Definisi umax (konsisten dengan Tabel 4.1 disertasi)
----------------------------------------------------
umax adalah NORM RESULTAN perpindahan maksimum pada node bebas
(magnitudo vektor perpindahan per node, bukan komponen tunggal).
Untuk model 1D ini identik dengan |ux| maksimum.

Pemakaian
---------
python truss_reference.py [path/ke/verification_models.json]

atau sebagai modul:

    from truss_reference import solve_model, load_models
    result = solve_model(model_dict)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import numpy as np

# -----------------------------------------------------------------------------
# Konstanta global (satuan disertasi)
# -----------------------------------------------------------------------------
DEFAULT_E = 200.0          # kN/mm^2
RANK_TOL_RELATIVE = 1e-10  # toleransi relatif rank-check thd eigenvalue terbesar


@dataclass
class SolverResult:
    """Hasil penyelesaian satu model kanonik."""
    model_id: str
    status: str                          # "ok" | "rank_deficient"
    ndof: int
    n_free: int
    rank: int
    displacements: np.ndarray            # vektor perpindahan penuh (semua dof)
    node_displacement_norm: np.ndarray   # norm resultant per node
    element_forces: np.ndarray           # gaya aksial per elemen (+ = tarik)
    utilizations: np.ndarray             # U_i = |N_i| / capacity_i
    umax: float                          # max norm resultant simpangan node
    u_max_component: float               # max |komponen| dof (informasi)
    Umax: float                          # max utilisasi
    strain_energy: float                 # W = 1/2 p.u (kN.mm)
    reactions: Dict[int, float] = field(default_factory=dict)
    min_eig: float = 0.0
    max_eig: float = 0.0


# -----------------------------------------------------------------------------
# Utilitas
# -----------------------------------------------------------------------------
def _dof_indices(node_id: int, dim: int) -> List[int]:
    return [dim * node_id + k for k in range(dim)]


def _dir_components(dof_name: str) -> List[str]:
    """'ux' -> ['ux']; 'xy' -> ['ux','uy'] ; dst."""
    mapping = {"x": "ux", "y": "uy", "z": "uz"}
    return [mapping[c.lower()] for c in dof_name if c.lower() in mapping]


def _fixed_dofs(model: dict) -> List[int]:
    """Kumpulkan daftar dof yang tertahan (zero-displacement constraints)."""
    dim = int(model.get("dimension", 2))
    fixed: List[int] = []
    for key, spec in model.get("boundary_conditions", {}).items():
        node_id = int(key.split("_", 1)[1])
        if isinstance(spec, dict):
            comps = list(spec.keys())
        else:
            comps = _dir_components(str(spec))
        for comp in comps:
            idx = {"ux": 0, "uy": 1, "uz": 2}[comp]
            if idx < dim:
                fixed.append(dim * node_id + idx)
    return sorted(set(fixed))


def _load_vector(model: dict, ndof: int) -> np.ndarray:
    p = np.zeros(ndof)
    dim = int(model.get("dimension", 2))
    for item in model.get("loads", []):
        node_id = int(item["node"])
        comps = item.get("components", {})
        for name, value in comps.items():
            idx = {"ux": 0, "uy": 1, "uz": 2}[name]
            if idx < dim:
                p[dim * node_id + idx] += float(value)
    return p


# -----------------------------------------------------------------------------
# Kekakuan elemen
# -----------------------------------------------------------------------------
def element_stiffness_1d(area: float, length: float, E: float) -> np.ndarray:
    """Matriks kekakuan batang aksial 1D (2 dof: ux_i, ux_j)."""
    k = E * area / length
    return k * np.array([[1.0, -1.0], [-1.0, 1.0]])


def element_stiffness_2d(xi, yi, xj, yj, area: float, E: float):
    """Matriks kekakuan batang planar 2D (4 dof) + metadata geometri."""
    dx, dy = xj - xi, yj - yi
    length = float(np.hypot(dx, dy))
    if length <= 0.0:
        raise ValueError("Elemen dengan panjang nol tidak diizinkan.")
    c, s = dx / length, dy / length
    k = E * area / length
    m = np.array([
        [ c * c,  c * s, -c * c, -c * s],
        [ c * s,  s * s, -c * s, -s * s],
        [-c * c, -c * s,  c * c,  c * s],
        [-c * s, -s * s,  c * s,  s * s],
    ])
    return k * m, length, c, s


# -----------------------------------------------------------------------------
# Rank check & solver inti
# -----------------------------------------------------------------------------
def check_rank(Kff: np.ndarray, tol_rel: float = RANK_TOL_RELATIVE):
    """Rank Kff via eigvals; toleransi relatif thd |eigenvalue| terbesar.

    Mengembalikan (is_full_rank, rank, lambda_max, lambda_min_abs).
    """
    if Kff.size == 0:
        return True, 0, 0.0, 0.0
    eigvals = np.linalg.eigvals(Kff)
    abs_eig = np.abs(eigvals)
    lam_max = float(abs_eig.max())
    lam_min = float(abs_eig.min())
    tol = tol_rel * lam_max
    rank = int(np.sum(abs_eig > tol))
    is_full_rank = rank == Kff.shape[0]
    return is_full_rank, rank, lam_max, lam_min


def assemble_global_stiffness(model: dict):
    """Rakit K global dan metadata elemen.

    Mengembalikan (K, elem_meta) dengan elem_meta[i] = (i_node, j_node, L, c, s, area, E_elem)
    Untuk 1D: c = 1, s = 0.
    """
    nodes = {int(n["id"]): [float(v) for v in n["coords"]] for n in model["nodes"]}
    dim = int(model.get("dimension", 2))
    E_default = float(model.get("material", {}).get("E", DEFAULT_E))
    node_ids = sorted(nodes)
    index_of = {nid: k for k, nid in enumerate(node_ids)}
    ndof = dim * len(node_ids)
    K = np.zeros((ndof, ndof))
    meta = []
    for el in model["elements"]:
        i, j = int(el["nodes"][0]), int(el["nodes"][1])
        ni, nj = index_of[i], index_of[j]
        coords_i, coords_j = nodes[i], nodes[j]
        area = float(el["area"])
        E_el = float(el.get("E", E_default))
        if dim == 1:
            length = abs(coords_j[0] - coords_i[0])
            kloc = element_stiffness_1d(area, length, E_el)
            dofs = [ni, nj]
            c, s = 1.0, 0.0
        else:
            kloc, length, c, s = element_stiffness_2d(
                coords_i[0], coords_i[1], coords_j[0], coords_j[1], area, E_el)
            dofs = [2 * ni, 2 * ni + 1, 2 * nj, 2 * nj + 1]
        K[np.ix_(dofs, dofs)] += kloc
        meta.append(dict(i=ni, j=nj, L=length, c=c, s=s, area=area, E=E_el,
                         original_id=int(el["id"]), dofs=dofs))
    return K, meta, dim, ndof, node_ids, index_of


def solve_model(model: dict) -> SolverResult:
    """Selesaikan satu model kanonik sesuai aturan Bagian 4.1.3 / 4.5.7."""
    mid = str(model.get("id", "unknown"))
    K, meta, dim, ndof, node_ids, index_of = assemble_global_stiffness(model)

    fixed = _fixed_dofs(model)
    free = [d for d in range(ndof) if d not in set(fixed)]
    Kff = K[np.ix_(free, free)]
    p = _load_vector(model, ndof)
    pf = p[free]

    # --- Rank check (WAJIB sebelum solve; tanpa pseudoinverse) -------------
    full_rank, rank, lam_max, lam_min = check_rank(Kff)
    if not full_rank:
        z = np.zeros(ndof)
        return SolverResult(
            model_id=mid, status="rank_deficient", ndof=ndof, n_free=len(free),
            rank=rank, displacements=z, node_displacement_norm=np.zeros(len(node_ids)),
            element_forces=np.zeros(len(meta)), utilizations=np.zeros(len(meta)),
            umax=float("nan"), u_max_component=float("nan"), Umax=float("nan"),
            strain_energy=float("nan"), min_eig=lam_min, max_eig=lam_max)

    # --- Penyelesaian K_ff u_f = p_f ----------------------------------------
    uf = np.linalg.solve(Kff, pf)
    u = np.zeros(ndof)
    u[free] = uf

    # --- Gaya batang & utilisasi --------------------------------------------
    capacities = model.get("capacities", {})
    forces = np.zeros(len(meta))
    utils = np.zeros(len(meta))
    strain_energy = 0.0
    for e, m in enumerate(meta):
        dofs = m["dofs"]
        if dim == 1:
            ui, uj = u[dofs[0]], u[dofs[1]]
            axial_proj = uj - ui
        else:
            ui = u[dofs[0:2]]
            uj = u[dofs[2:4]]
            axial_proj = float(np.dot(uj - ui, [m["c"], m["s"]]))
        N = m["E"] * m["area"] / m["L"] * axial_proj
        forces[e] = N
        cap_key = str(m["original_id"])
        cap = float(capacities.get(cap_key, capacities.get(e, np.inf)))
        utils[e] = abs(N) / cap if np.isfinite(cap) and cap > 0 else 0.0
        strain_energy += N * N * m["L"] / (2.0 * m["E"] * m["area"])

    # --- Ukuran respons -------------------------------------------------------
    if dim == 1:
        node_norm = np.abs(u)
    else:
        node_norm = np.array([np.hypot(u[2 * k], u[2 * k + 1]) for k in range(len(node_ids))])
    umax = float(node_norm.max()) if node_norm.size else 0.0
    Umax = float(utils.max()) if utils.size else 0.0

    # --- Reaksi (di dof tertahan): r = K u - p -------------------------------
    reactions = {}
    r_full = K @ u - p
    for d in fixed:
        reactions[int(d)] = float(r_full[d])

    return SolverResult(
        model_id=mid, status="ok", ndof=ndof, n_free=len(free), rank=rank,
        displacements=u, node_displacement_norm=node_norm,
        element_forces=forces, utilizations=utils,
        umax=umax, u_max_component=float(np.abs(u).max()), Umax=Umax,
        strain_energy=strain_energy, reactions=reactions,
        min_eig=lam_min, max_eig=lam_max)


# -----------------------------------------------------------------------------
# Loader & pelaporan
# -----------------------------------------------------------------------------
def load_models(path: Path) -> List[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["models"]


def format_table(results: List[SolverResult], models: List[dict]) -> str:
    lines = []
    header = (f"{'Model':<28} {'Status':<16} {'rank/free':>10} "
              f"{'umax [mm]':>12} {'Umax [-]':>10} {'W [kN.mm]':>12}")
    lines.append(header)
    lines.append("-" * len(header))
    exp = {m["id"]: m.get("expected_results", {}) for m in models}
    for res in results:
        e = exp.get(res.model_id, {})
        tag = res.model_id
        lines.append(
            f"{tag:<28} {res.status:<16} {res.rank:>4}/{res.n_free:<5} "
            f"{res.umax:>12.6f} {res.Umax:>10.6f} {res.strain_energy:>12.6f}")
        if e:
            du = res.umax - float(e["umax_mm"])
            dU = res.Umax - float(e["Umax"])
            ok = "PASS" if (abs(du) < 5e-4 and abs(dU) < 5e-4) else "FAIL"
            lines.append(
                f"{'':<28} vs Tabel 4.1: umax={e['umax_mm']:.6f} "
                f"(Δ={du:+.6f}), Umax={e['Umax']:.6f} (Δ={dU:+.6f}) -> {ok}")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    here = Path(__file__).resolve().parent
    path = Path(argv[1]) if len(argv) > 1 else here / "verification_models.json"
    models = load_models(path)
    results = [solve_model(m) for m in models]
    print(format_table(results, models))
    # Detail gaya batang tiap model
    for res, m in zip(results, models):
        if res.status != "ok":
            continue
        caps = m.get("capacities", {})
        det = ", ".join(
            f"E{e}: N={res.element_forces[e]:+.4f} kN (cap {caps.get(str(e), '?')} kN, "
            f"U={res.utilizations[e]:.6f})"
            for e in range(len(res.element_forces)))
        print(f"\n[{res.model_id}] {det}")
    all_ok = all(
        r.status == "ok"
        and abs(r.umax - float(m.get("expected_results", {}).get("umax_mm", r.umax))) < 5e-4
        and abs(r.Umax - float(m.get("expected_results", {}).get("Umax", r.Umax))) < 5e-4
        for r, m in zip(results, models))
    print("\nVERIFIKASI TABEL 4.1:", "SEMUA COCOK (PASS)" if all_ok else "ADA YANG TIDAK COCOK (FAIL)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
