"""
bound_enhancement.py
====================

Pre-Analysis Enhancement — Section 4.5 disertasi "Adjusted Redundancy Index
(ARI) for Mechanics-Based Screening of Disruption Scenarios Before GNN
Prediction" (pages 131-136, Eq 4.9 - 4.12).

Tujuan
------
Membangun dua ANALYTICAL UPPER BOUNDS per skenario s = (element e, faktor
lambda) yang HANYA memerlukan state INTAK model (pre-analysis), sehingga
layar pra-GNN dapat mem-forward skenario berbahaya tanpa menyelesaikan model
terdisrupsi:

  A. Force-Redistribution Bound (Eq 4.9):
        alpha_s = 1 - lambda
        m_s     = m_e(lambda) = 1 - (1 - lambda) * h_e
        D_{j,s} = |N_{j,0}| + (alpha_s*|N_{e,0}|/m_s)*sqrt(k_j/k_e * h_j/h_e)
        D_{e,s} = lambda*|N_{e,0}|/m_s                    (bar melemah, lambda>0)
        U_s     = max_j D_{j,s}/R_{j,s};   g_C(s)=1 iff U_s >= 1

  B. Displacement-Amplification Bound (Eq 4.12):
        c_i = lambda_max(P_i K0^{-1} P_i^T)
        ||P_i du_s||_2 <= (alpha_s*|N_{e,0}|/m_s)*sqrt(c_i*h_e/k_e)
        d_s = max_i { ||P_i u_0|| + bound_i };  A_s = d_s/d_0
        g_D(s)=1 iff A_s >= A_lim or d_s >= d_lim

Strategi reuse cache (kontrak input Gate Pre-Analysis)
------------------------------------------------------
Kelas ``BoundCache`` MENGCOMPOSE ``kinematic_guard.GuardCache`` (getter publik
yang ditambahkan ke guard Gate 3) untuk status rank/solvabilitas state
terdisrupsi, dan memakai FAKTORISASI STATE INTAK dari ``truss_reference``
(assemble_global_stiffness + solve_model) yang sama yang dipakai solver Gate 1
— TIDAK ada reimplementasi SVD/rank-check di modul ini. Satu build cache per
model parent meng-amortisasi seluruh skenario (persyaratan waktu §4.5.6).

CATATAN OPERASIONAL (dipertahankan jujur untuk review):
  Guard Gate 3 menyimpan hasil faktorisasi kinematik sebagai dict diagnostik
  (rank/eigenvalue), bukan objek faktorisasi SVD mentah; karena itu BoundCache
  membaca ulang cache guard lewat getter publiknya dan membangun sendiri
  faktorisasi intak (sekali per model). Tidak ada logika guard yang diubah.

Referensi silang
----------------
* ari_core.py            -> utilitas _apply_stiffness_multiplier (konvensi
                            disrupsi identik Gate 2/4; TIDAK dimodifikasi)
* kinematic_guard.py     -> GuardCache (getter cache rank/solvabilitas)
* truss_reference.py     -> K0, u0, N0, reaksi, rank check (Gate 1)
* DIAGNOSIS.md           -> temuan Gate 2 (tidak ada regresi target M1/M3)

Satuan: kN, mm, E = 200 kN/mm^2.
Hanya numpy (+ scipy via numpy eigvalsh untuk subblok; tidak ada dep baru).
Semua ambang berada dalam satu config frozen (BOUND_CONFIG) — tidak ada
magic number di dalam logika.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss_reference import (assemble_global_stiffness, solve_model,
                             load_models)                       # Gate 1
from kinematic_guard import GuardCache                          # Gate 3 getter
from ari_core import _apply_stiffness_multiplier                # Gate 2 util


# -----------------------------------------------------------------------------
# Frozen configuration (§4.5.4 / instruksi Gate Pre-Analysis)
# Semua ambang & toleransi terpusat di sini; logika tidak boleh memuat angka.
# -----------------------------------------------------------------------------
def default_bound_config() -> dict:
    """Config beku bound enhancement. Nilai default sesuai Section 4.3.4/4.5.4."""
    return dict(
        A_lim=2.0,          # ambang amplifikasi perpindahan (diagnostik §4.3.4)
        d_lim=None,         # kriteria absolut (mm) — dinonaktifkan by default
        m_margin=1e-8,      # m_s < margin -> unusable (hindari pembagian ~0)
        d0_floor=1e-10,     # d_0 < floor  -> rasio A_s unusable
        h_floor=1e-12,      # h_e ~ 0      -> rasio h_j/h_e unusable utk j!=e
        near_zero_force=1e-12,   # |N_{e,0}| < eps -> tidak ada redistribusi
        eig_rel_tol=1e-10,  # toleransi relatif eigen (sinkron solver Gate 1)
    )


@dataclass
class IntactFacts:
    """Fakta mekanik state INTAK — SATU-SATUNYA sumber yang boleh dibaca bounds.

    (Section 4.5.6: pre-analysis hanya boleh memakai informasi pra-disrupsi.)
    Entri 'post_*' sengaja TIDAK ADA di struktur ini (leakage audit Task 3).
    """
    model_id: str
    dim: int
    node_ids: List[int]
    index_of: Dict[int, int]
    edge_ids: List[int]
    edge_nodes: Dict[int, Tuple[int, int]]       # eid -> (node_i, node_j) asli
    k_raw: Dict[int, float]                      # k_e = EA/L [kN/mm]
    capacity: Dict[int, float]                   # R_e [kN]
    N0: Dict[int, float]                         # gaya aksial intak [kN]
    W_e: Dict[int, float]                        # energi regangan per edge
    h: Dict[int, float]                          # h_e = W_e / sum(W) (fraksi)
    u0: np.ndarray                               # perpindahan intak penuh
    free_dofs: List[int]
    Kff_inv: np.ndarray                          # invers blok bebas K0
    min_eig_intact: float
    max_eig_intact: float
    solvable_intact: bool


class BoundCache:
    """Cache pre-analysis per model parent (Section 4.5.5: amortized cache).

    Membangun ``IntactFacts`` sekali (satu solve_model + satu inversi blok K_ff)
    dan mengkomposisi ``kinematic_guard.GuardCache`` untuk status rank/solvabel
    state terdisrupsi (reuse getter; tanpa reimplementasi SVD/rank-check).

    Parameters
    ----------
    model : dict
        Model kanonik (schema verification_models.json).
    config : dict, optional
        Override terhadap ``default_bound_config()``.

    Raises
    ------
    RuntimeError
        Jika model INTAK rank-deficient (mekanisme sejak awal) — bounds tidak
        terdefinisi; pemanggil harus abstain/forward.
    """

    def __init__(self, model: dict, config: Optional[dict] = None):
        self.model = copy.deepcopy(model)
        self.cfg = default_bound_config()
        if config:
            self.cfg.update(config)
        self.guard = GuardCache(self.model)          # REUSE guard Gate 3
        self.facts = self._build_intact_facts()
        self.c_i: Dict[int, float] = self._compute_c_i()

    # -- pembangunan cache ----------------------------------------------------
    def _build_intact_facts(self) -> IntactFacts:
        """Faktorisasi state INTAK (Eq 4.9: N_{j,0}, h_e; Eq 4.12: K0^{-1})."""
        cfg = self.cfg
        K, meta, dim, ndof, node_ids, index_of = \
            assemble_global_stiffness(self.model)
        res = solve_model(copy.deepcopy(self.model))
        if res.status != "ok":
            raise RuntimeError(
                f"Intact model {res.model_id} is rank-deficient "
                f"({res.status}); bounds unusable at source.")
        fixed = [d for d in range(ndof) if d not in set(
            _free_complement(ndof, res))]
        free = sorted(set(range(ndof)) - set(fixed))
        Kff = K[np.ix_(free, free)]
        Kff_inv = np.linalg.inv(Kff)               # intak => SPD pada free dofs
        # verifikasi numerik kondisi (upper-bound integrity, §4.5.5 rule):
        ev = np.linalg.eigvalsh(Kff)
        if ev.min() <= cfg["eig_rel_tol"] * max(ev.max(), 1e-30):
            raise RuntimeError("Intact K_ff ill-conditioned; bounds unusable.")

        edges = res.element_forces
        W = np.array([m["E"] * m["area"] / (2.0 * m["L"]) *
                      _axial_proj(res.displacements, m, dim) ** 2
                      for m in meta])
        tot_W = float(W.sum())
        h = {int(m["original_id"]): (float(W[e]) / tot_W if tot_W > 0 else 0.0)
             for e, m in enumerate(meta)}
        caps_in = self.model.get("capacities", {})
        capacity = {int(m["original_id"]):
                    float(caps_in.get(str(m["original_id"]),
                                      caps_in.get(m["original_id"], np.inf)))
                    for m in meta}
        N0 = {int(m["original_id"]): float(edges[e]) for e, m in enumerate(meta)}
        k_raw = {int(m["original_id"]): m["E"] * m["area"] / m["L"]
                 for m in meta}
        edge_nodes = {int(el["id"]): (int(el["nodes"][0]), int(el["nodes"][1]))
                      for el in self.model["elements"]}
        return IntactFacts(
            model_id=res.model_id, dim=dim, node_ids=list(node_ids),
            index_of=index_of, edge_ids=sorted(N0), edge_nodes=edge_nodes,
            k_raw=k_raw, capacity=capacity, N0=N0, 
            W_e={int(m["original_id"]): float(W[e])
                 for e, m in enumerate(meta)},
            h=h, u0=res.displacements, free_dofs=free, Kff_inv=Kff_inv,
            min_eig_intact=float(ev.min()), max_eig_intact=float(ev.max()),
            solvable_intact=True)

    def _compute_c_i(self) -> Dict[int, float]:
        """c_i = lambda_max(P_i K0^{-1} P_i^T) untuk setiap node translasi
        (Eq 4.12). P_i adalah matriks ekstraksi DOF node i."""
        f = self.facts
        inv_map = {d: p for p, d in enumerate(f.free_dofs)}
        c_i: Dict[int, float] = {}
        for nid in f.node_ids:
            dofs = [f.dim * nid + k for k in range(f.dim)]
            rows = [inv_map[d] for d in dofs if d in inv_map]
            if not rows:
                c_i[nid] = 0.0
                continue
            sub = f.Kff_inv[np.ix_(rows, rows)]
            sub = 0.5 * (sub + sub.T)              # simetriskan (numerik)
            c_i[nid] = float(np.linalg.eigvalsh(sub).max())
        return c_i

    # -- API publik ------------------------------------------------------------
    def m_factor(self, edge_id: int, lam: float) -> float:
        """m_e(lambda) = 1 - (1-lambda)*h_e  (Eq 4.9)."""
        h_e = self.facts.h[edge_id]
        return 1.0 - (1.0 - float(lam)) * h_e

    def compute_force_bound(self, e: int, lam: float) -> dict:
        """Force-Redistribution Bound (Eq 4.9).

        Returns dict dengan:
          D_j                : dict[edge_id -> bound gaya tarik-mutlak] [kN]
          U_s                : max_j D_{j,s}/R_{j,s} (tanpa batas atas; bisa >1)
          triggering_bar     : edge j yang mencapai utilisasi terbesar
          m_s, alpha_s, h_e  : intermediate
          g_C                : 1 iff U_s >= 1
          status             : 'ok' | 'unusable_m_near_zero' |
                               'unusable_capacity_missing' | 'no_redistribution'
        """
        f, cfg = self.facts, self.cfg
        if e not in f.N0:
            return dict(status="unusable_capacity_missing", reason="unknown edge")
        alpha_s = 1.0 - float(lam)
        m_s = self.m_factor(e, lam)
        if m_s < cfg["m_margin"]:
            # ordering policy: kinematik dulu — jangan bagi ~0 (Eq 4.13 step 1)
            return dict(status="unusable_m_near_zero", m_s=m_s, alpha_s=alpha_s)
        Ne0 = abs(f.N0[e])
        D: Dict[int, float] = {}
        he = f.h[e]
        if Ne0 <= cfg["near_zero_force"] or alpha_s == 0.0:
            # tidak ada gaya awal / tidak ada pelemahan -> tanpa redistribusi
            for j in f.edge_ids:
                D[j] = abs(f.N0[j]) * (lam if j == e else 1.0)
            status = ("no_redistribution" if Ne0 <= cfg["near_zero_force"]
                      else "ok")
        else:
            base = alpha_s * Ne0 / m_s
            for j in f.edge_ids:
                if j == e:
                    D[j] = float(lam) * Ne0 / m_s          # bar melemah (λ>0)
                else:
                    if he < cfg["h_floor"]:
                        return dict(status="unusable_capacity_missing",
                                    reason="h_e ~ 0: ratio h_j/h_e undefined")
                    D[j] = abs(f.N0[j]) + base * math.sqrt(
                        (f.k_raw[j] / f.k_raw[e]) * (f.h[j] / he))
        U_per_edge: Dict[int, float] = {}
        for j, Dj in D.items():
            Rj = f.capacity.get(j, np.inf)
            if not np.isfinite(Rj) or Rj <= 0.0:
                return dict(status="unusable_capacity_missing",
                            reason=f"capacity missing for edge {j}")
            U_per_edge[j] = Dj / Rj
        trig = max(U_per_edge, key=lambda j: U_per_edge[j])
        U_s = U_per_edge[trig]
        return dict(status="ok" if (Ne0 > cfg["near_zero_force"] and alpha_s > 0)
                    else ("no_redistribution"
                          if Ne0 <= cfg["near_zero_force"] else "control_ok"),
                    D_j=D, U_s=U_s, triggering_bar=int(trig),
                    U_per_edge=U_per_edge, m_s=m_s, alpha_s=alpha_s,
                    h_e=he, g_C=1 if U_s >= 1.0 else 0)

    def compute_displacement_bound(self, e: int, lam: float) -> dict:
        """Displacement-Amplification Bound (Eq 4.12).

        Returns dict dengan:
          c_i       : dict[node_id -> lambda_max(P_i K0^-1 P_i^T)]
          norm_u0_i : dict[node_id -> ||P_i u_0||]
          d_0, d_s  : max simpangan intak & bound atas simpangan terdisrupsi
          A_s       : d_s/d_0 (None jika d_0 < d0_floor -> unusable ratio)
          g_D       : 1 iff A_s >= A_lim OR d_s >= d_lim
          status    : 'ok' | 'unusable_d0_near_zero' | 'unusable_c_compute_failed'
                      | 'unusable_m_near_zero'
        """
        f, cfg = self.facts, self.cfg
        try:
            c_i = dict(self.c_i)
        except Exception:
            return dict(status="unusable_c_compute_failed")
        alpha_s = 1.0 - float(lam)
        m_s = self.m_factor(e, lam)
        if m_s < cfg["m_margin"]:
            return dict(status="unusable_m_near_zero", m_s=m_s)
        Ne0 = abs(f.N0[e])
        he, ke = f.h[e], f.k_raw[e]
        norm_u0 = {}
        for nid in f.node_ids:
            dofs = [f.dim * nid + k for k in range(f.dim)]
            norm_u0[nid] = float(np.linalg.norm(f.u0[dofs]))
        d_0 = max(norm_u0.values()) if norm_u0 else 0.0
        inc: Dict[int, float] = {}
        for nid in f.node_ids:
            if Ne0 <= cfg["near_zero_force"] or alpha_s == 0.0:
                inc[nid] = 0.0
            else:
                inc[nid] = (alpha_s * Ne0 / m_s) * math.sqrt(
                    max(c_i[nid], 0.0) * he / ke)
        d_s = max(norm_u0[i] + inc[i] for i in f.node_ids)
        A_s: Optional[float] = None
        status = "ok"
        if d_0 < cfg["d0_floor"]:
            status = "unusable_d0_near_zero"
        else:
            A_s = d_s / d_0
        gD = 0
        if A_s is not None and A_s >= cfg["A_lim"]:
            gD = 1
        if cfg["d_lim"] is not None and d_s >= cfg["d_lim"]:
            gD = 1
        return dict(status=status, c_i=c_i, norm_u0_i=norm_u0,
                    increment_i=inc, d_0=d_0, d_s=d_s, A_s=A_s,
                    m_s=m_s, alpha_s=alpha_s, g_D=gD)


# -----------------------------------------------------------------------------
# Helper internal
# -----------------------------------------------------------------------------
def _free_complement(ndof: int, res) -> List[int]:
    """DOF tertahan dari SolverResult (rekonstruksi: free = dof tak-reaksi)."""
    restrained = sorted({d for d in res.reactions})
    return restrained


def _axial_proj(u: np.ndarray, m: dict, dim: int) -> float:
    """Proyeksi perpindahan aksial elemen (sama dengan konvensi Gate 1)."""
    dofs = m["dofs"]
    if dim == 1:
        return float(u[dofs[1]] - u[dofs[0]])
    ui = u[dofs[0:2]]
    uj = u[dofs[2:4]]
    return float(np.dot(uj - ui, [m["c"], m["s"]]))


# -----------------------------------------------------------------------------
# CLI demo singkat (bukan test; test ada di test_bound_enhancement.py)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    models = load_models(here / "verification_models.json")
    for mdl in models:
        bc = BoundCache(mdl)
        print(f"\n[{bc.facts.model_id}] h_e =",
              {k: round(v, 4) for k, v in bc.facts.h.items()},
              " d_0 =", round(max(np.linalg.norm(
                  bc.facts.u0[bc.facts.dim * i:bc.facts.dim * (i + 1)])
                  for i in range(len(bc.facts.node_ids))), 6))
        for eid in bc.facts.edge_ids:
            fb = bc.compute_force_bound(eid, 0.0)
            db = bc.compute_displacement_bound(eid, 0.0)
            print(f"  e{eid} lam=0: force {fb.get('status')} "
                  f"U_s={fb.get('U_s', float('nan')):.4f} g_C={fb.get('g_C','-')}"
                  f" | disp {db.get('status')} A_s="
                  f"{(db.get('A_s') if db.get('A_s') is None else round(db['A_s'],4))}"
                  f" g_D={db.get('g_D','-')}")
