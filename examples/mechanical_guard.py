"""
mechanical_guard.py
===================

Pengaman kinematik berbasis redundansi mekanis — Bagian 4.2.2 disertasi
"Adjusted Redundancy Index (ARI)", Eq 4.1-4.5.

Definisi (naskah 4.2.2)
-----------------------
    a_e          = baris kompatibilitas pemanjangan batang e (dof bebas)
    k_e          = E_e A_e / L_e
    K0           = sum_e k_e a_e^T a_e                       (Eq 4.1)
    h_e          = k_e a_e K0^{-1} a_e^T                     (Eq 4.1)
    K_{e,lambda} = K0 - (1-lambda) k_e a_e^T a_e             (Eq 4.2)
    m_e(lambda)  = 1 - (1-lambda) h_e                        (Eq 4.2)
    rho0         = lambda_min(K0) / lambda_max(K0)

Implementasi numerik (4.2.2): matriks kompatibilitas berbobot A (baris
sqrt(k_e) a_e) difaktorkan dengan SVD; pada model utuh ber-rank penuh,
h_e = jumlah kuadrat entri baris matriks vektor singular kiri U.
Identitas h_e = k_e a_e K0^{-1} a_e^T = sum_k U[e,k]^2 (dipakai juga oleh
bound_enhancement.py — satu sumber kebenaran).

Validasi (Tabel 4.4): batang bergaya awal NOL (e3/e4 persegi satu diagonal)
tetap h_e = 1.000000 dan m_e(0) ~ 0 — definisi ini tidak boleh diganti
dengan fraksi energi regangan (yang akan memberi ~0 utk batang nol-gaya).

Margin & batas kondisi (Eq 4.4)
-------------------------------
    lambda_min(K_{e,lambda}) / lambda_max(K_{e,lambda}) >= m_e(lambda) * rho0
Toleransi beku (4.2.2): margin 1e-8; rank relatif 1e-10 (via solver Gate 1).

Kebijakan penerusan (Eq 4.5; berlapis Eq 4.13 di layered_policy.py)
-------------------------------------------------------------------
    g(s) = 1 bila margin ~0 (mekanisme), batas kondisi dilanggar, atau
    faktorisasi gagal -> skenario LANGSUNG diteruskan tanpa mengevaluasi
    rumus yang membagi dengan m_s.
    F(s) = 1{ CI(s) >= tau  atau  g(s) = 1  atau  ARI abstain/tidak sah }.

Satuan: kN, mm, E = 200 kN/mm^2.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from truss_reference import (assemble_global_stiffness, solve_model,   # noqa
                             load_models, _fixed_dofs, RANK_TOL_RELATIVE)

# --- Config beku (Bagian 4.2.2) ----------------------------------------------
MARGIN_TOL = 1e-8        # toleransi margin m_s ("margin kecil")
RANK_TOL = RANK_TOL_RELATIVE   # 1e-10, toleransi rank relatif solver Gate 1


# -----------------------------------------------------------------------------
# Faktorisasi state INTAK
# -----------------------------------------------------------------------------
def _arrays(model: dict):
    """(A, meta, free, ndof, dim) — A baris sqrt(k_e) a_e pada dof bebas."""
    K, meta, dim, ndof, node_ids, index_of = assemble_global_stiffness(model)
    fixed = set(_fixed_dofs(model))
    free = [d for d in range(ndof) if d not in fixed]
    A = np.zeros((len(meta), len(free)))
    for e, mm in enumerate(meta):
        row = np.zeros(ndof)
        dofs = mm["dofs"]
        if dim == 1:
            row[dofs[0]], row[dofs[1]] = -1.0, 1.0
        else:
            c, s = mm["c"], mm["s"]
            row[dofs[0]], row[dofs[1]] = -c, -s
            row[dofs[2]], row[dofs[3]] = c, s
        A[e, :] = math.sqrt(mm["E"] * mm["area"] / mm["L"]) * row[free]
    return A, meta, free, ndof, dim


def svd_redundancy_h(model: dict) -> Dict[int, float]:
    """h_e (Eq 4.1) = jumlah kuadrat entri baris U dari SVD A (4.2.2)."""
    A, meta, free, ndof, dim = _arrays(model)
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    return {int(meta[e]["original_id"]): float(np.sum(U[e, :] ** 2))
            for e in range(len(meta))}


def m_factor(h_e: float, lam: float) -> float:
    """m_e(lambda) = 1 - (1-lambda) h_e (Eq 4.2)."""
    return 1.0 - (1.0 - float(lam)) * float(h_e)


# -----------------------------------------------------------------------------
# Profil pengaman per model (dihitung sekali, dipakai seluruh skenario)
# -----------------------------------------------------------------------------
class MechanicalGuard:
    """h_e, m_e(lambda), margin & batas kondisi (Eq 4.1-4.4) utk satu model."""

    def __init__(self, model: dict):
        self.model = model
        self.A, self.meta, self.free, self.ndof, self.dim = _arrays(model)
        self.svd_ok = True
        U, S, Vt = None, None, None
        try:
            U, S, Vt = np.linalg.svd(self.A, full_matrices=False)
        except np.linalg.LinAlgError:
            self.svd_ok = False
        self.h: Dict[int, float] = {}
        for e in range(len(self.meta)):
            eid = int(self.meta[e]["original_id"])
            self.h[eid] = (float(np.sum(U[e, :] ** 2)) if self.svd_ok
                           else float("nan"))
        self._row_of = {int(m["original_id"]): i
                        for i, m in enumerate(self.meta)}
        K0 = self.A.T @ self.A
        self.K0 = 0.5 * (K0 + K0.T)
        ev = np.linalg.eigvalsh(self.K0)
        self.rho0 = float(ev.min() / ev.max()) if ev.max() > 0.0 else 0.0

    # -- per skenario ----------------------------------------------------------
    def m_e(self, eid: int, lam: float) -> float:
        return m_factor(self.h[eid], lam)

    def margin(self, eid: int, lam: float) -> dict:
        """Margin m_s + verifikasi batas kondisi Eq 4.4 utk K_{e,lambda}."""
        m_s = self.m_e(eid, lam)
        row = self.A[self._row_of[eid], :]
        Ke = self.K0 - (1.0 - float(lam)) * np.outer(row, row)
        Ke = 0.5 * (Ke + Ke.T)
        ev = np.linalg.eigvalsh(Ke)
        ratio = (float(max(ev.min(), 0.0) / ev.max())
                 if ev.max() > 0.0 else 0.0)
        bound = float(m_s * self.rho0)
        pad = 1e-8 * max(1.0, abs(bound))     # kelonggaran pembulatan (4.2.2)
        return dict(m_s=m_s, ratio=ratio, bound=bound, rho0=self.rho0,
                    bound_ok=bool(ratio + pad >= bound),
                    margin_small=bool(m_s <= MARGIN_TOL))

    def guard_flag(self, eid: int, lam: float) -> int:
        """g(s) Eq 4.5/4.13: 1 = teruskan (margin ~0 / batas dilanggar / SVD gagal)."""
        if not self.svd_ok:
            return 1
        info = self.margin(eid, lam)
        return 1 if (info["margin_small"] or not info["bound_ok"]) else 0

    # -- identitas Eq 4.7 (residual; verifikasi implementasi) ------------------
    def verify_update_identity(self, eid: int, lam: float) -> float:
        """max|K_{e,lambda}(u0+du_s) - p| utk du_s Eq 4.7 (harus ~0)."""
        model = self.model
        K, meta, dim, ndof, node_ids, index_of = \
            assemble_global_stiffness(model)
        fixed = set(_fixed_dofs(model))
        free = [d for d in range(ndof) if d not in fixed]
        res = solve_model(model)
        u0_full = res.displacements
        u0 = u0_full[free]
        p = np.zeros(ndof)
        for item in model.get("loads", []):
            nid = int(item["node"])
            for name, val in item.get("components", {}).items():
                idx = {"ux": 0, "uy": 1, "uz": 2}[name]
                if idx < dim:
                    p[dim * nid + idx] += float(val)
        p_free = p[free]
        row_idx = self._row_of[eid]
        mm = self.meta[row_idx]
        a_full = np.zeros(ndof)
        dofs = mm["dofs"]
        if dim == 1:
            a_full[dofs[0]], a_full[dofs[1]] = -1.0, 1.0
        else:
            c, s = mm["c"], mm["s"]
            a_full[dofs[0]], a_full[dofs[1]] = -c, -s
            a_full[dofs[2]], a_full[dofs[3]] = c, s
        k_e = mm["E"] * mm["area"] / mm["L"]
        N_e0 = k_e * float(a_full @ u0_full)
        m_s = self.m_e(eid, lam)
        if m_s <= 0.0:
            return float("nan")
        delta = (1.0 - float(lam)) * N_e0 / m_s * \
            np.linalg.solve(self.K0, a_full[free])
        Ke = self.K0 - (1.0 - float(lam)) * \
            np.outer(self.A[row_idx, :], self.A[row_idx, :])
        resid = Ke @ (u0 + delta) - p_free
        return float(np.max(np.abs(resid)))


# -----------------------------------------------------------------------------
# Self-test CLI (regresi Tabel 4.4 + Eq 4.4 + identitas Eq 4.7)
# -----------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    here = Path(__file__).resolve().parent
    models = {m["id"]: m for m in load_models(here / "verification_models.json")}
    fails: List[str] = []

    def check(name, cond, info=""):
        tag = "PASS" if cond else "FAIL"
        print(f"  [{tag}] {name} {info}")
        if not cond:
            fails.append(name)

    print("=" * 78)
    print("MECHANICAL GUARD — self-test (Bagian 4.2.2, Eq 4.1-4.4)")
    print("=" * 78)

    guards = {mid: MechanicalGuard(m) for mid, m in models.items()}

    # ---- (1) h_e vs teori -----------------------------------------------------
    print("\n[1] Profil h_e (Eq 4.1, metode SVD):")
    for mid, g in guards.items():
        print(f"    {mid:26s} h = " +
              str({k: round(v, 6) for k, v in sorted(g.h.items())}))
    g1 = guards["M1_parallel_bars_1d"]
    check("M1: h_e = (2/3, 1/3) (analitis: k_0/(k_0+k_1), k_1/(...))",
          abs(g1.h[0] - 2 / 3) < 1e-9 and abs(g1.h[1] - 1 / 3) < 1e-9)
    for mid in ("M2_planar_triangle", "M3_square_one_diagonal"):
        g = guards[mid]
        check(f"{mid}: semua h_e == 1 (isostatik, m = n_free)",
              all(abs(v - 1.0) < 1e-9 for v in g.h.values()))
    g4 = guards["M4_square_two_diagonals"]
    n_free4 = len(g4.free)
    check("M4: 0 < 1 - h_e utk semua edge (redundan; hapus tunggal tetap PD)",
          all((1.0 - v) > 0.0 for v in g4.h.values()),
          f"(min 1-h = {min(1.0 - v for v in g4.h.values()):.3e})")
    check("M4: sum h_e == n_free (jejak U orthonormal)",
          abs(sum(g4.h.values()) - n_free4) < 1e-9)

    # ---- (2) Tabel 4.4 — regresi e3/e4 (M3) -----------------------------------
    print("\n[2] Regresi Tabel 4.4 (M3 e3/e4, hapus-total lambda=0):")
    import ari_core as ac
    M3 = models["M3_square_one_diagonal"]
    g3 = guards["M3_square_one_diagonal"]
    am3 = ac.build_ari_model(M3)
    s3, st3 = ac.compute_graph_score(am3)
    for eid, label in ((2, "e3"), (3, "e4")):
        disrupted = ac._apply_stiffness_multiplier(M3, {eid: 0.0},
                                                   drop_zero=True)
        res = solve_model(disrupted)
        m0 = g3.m_e(eid, 0.0)
        r = ac.compute_ari(am3, (eid, 0.0), baseline=(s3, st3))
        check(f"Tabel 4.4 {label}: h_e = 1.000000",
              abs(g3.h[eid] - 1.0) < 1e-9, f"(h={g3.h[eid]:.6f})")
        check(f"Tabel 4.4 {label}: m_e(0) ~ 0",
              abs(m0) < 1e-12, f"(m={m0:.2e})")
        check(f"Tabel 4.4 {label}: rank 4/5",
              int(res.rank) == 4 and int(res.n_free) == 5,
              f"(rank={res.rank}/{res.n_free})")
        check(f"Tabel 4.4 {label}: guard g(s)=1 (diteruskan)",
              g3.guard_flag(eid, 0.0) == 1)
        check(f"Tabel 4.4 {label}: ARI absen (CI < 0.5)",
              r.CI is not None and r.CI < 0.5,
              f"(CI={r.CI:.6f})")

    # ---- (3) Batas kondisi Eq 4.4 di seluruh grid ------------------------------
    print("\n[3] Batas kondisi Eq 4.4 (lambda_min/lambda_max >= m_s * rho0):")
    n_ok = n_tot = 0
    for mid, g in guards.items():
        for eid in sorted(g.h):
            for lam in (1.0, 0.75, 0.5, 0.25, 0.0):
                info = g.margin(eid, lam)
                n_tot += 1
                n_ok += int(info["bound_ok"])
    check(f"Eq 4.4 terpenuhi di seluruh grid ({n_ok}/{n_tot})", n_ok == n_tot)

    # ---- (4) Identitas Eq 4.7 (residual numerik ~ 0) ---------------------------
    print("\n[4] Identitas pembaruan rank-1 Eq 4.7 (residual K_{e,lam}(u0+du)-p):")
    worst = 0.0
    for mid, eid, lam in (("M1_parallel_bars_1d", 0, 0.5),
                          ("M1_parallel_bars_1d", 0, 0.25),
                          ("M1_parallel_bars_1d", 1, 0.5),
                          ("M3_square_one_diagonal", 0, 0.5),
                          ("M3_square_one_diagonal", 4, 0.5)):
        r = guards[mid].verify_update_identity(eid, lam)
        worst = max(worst, r)
        print(f"    {mid:26s} e{eid} lam={lam}: residual={r:.3e}")
    check("Residual Eq 4.7 < 1e-8 di semua kasus uji", worst < 1e-8)

    print("\n" + "=" * 78)
    print("RESULT:", "ALL PASS" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
