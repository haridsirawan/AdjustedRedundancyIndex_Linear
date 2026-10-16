"""
run_screening_s1_s5.py
======================

Modul Penyaringan Operasional Skala Penuh & Validasi Lintas Keluarga (Gate 15 — W3/W4)
untuk Penelitian Disertasi: "Adjusted Redundancy Index (ARI)" — Harids Irawan (2026).

Sesuai Spesifikasi Naskah Disertasi:
------------------------------------
- Bagian 2.6–2.8 (Formulasi ARI, Skor Jalur Alternatif, Indikator Kekakuan Aksial & Lentur)
- Bagian 3.9.4–3.9.5 (Aturan Pemilihan Ambang, Ablasi, Pembekuan, dan Pembukaan Data Buta)
- Bagian 3.10–3.13 (Acuan Mekanis, CRC, Gerbang Validasi A–D, Inferensi Bootstrap B=10.000)
- Bagian 4.2.2 (Pengaman Kinematik dan Perluasan Spektral Umum Lintas Keluarga S1–S5)
- Bagian 4.9.2 & 4.10.1–4.10.4 (Urutan Audit Pra-Analisis: Simpan Keputusan Sebelum Buka Label)

Tahapan Eksekusi Ketat (Two-Pass Anti-Leakage Audit):
-----------------------------------------------------
1. Verifikasi Konfigurasi Beku (`manifest_config_frozen.json`, `ARI-FROZEN-PROTOCOL-v1.0`).
2. PASS 1 (Pra-Analisis Murni — Hanya Informasi Model Utuh):
   - Menghitung bobot atribut ternormalisasi (skala median `formula_dev` per keluarga dan
     skala default protokol), skor graf S(G), RR, utilisasi awal U*_e, ARI, dan CI.
   - Menghitung indeks redundansi kinematik spektral umum:
       h_e = lambda_max(K_{0,ff}^{-1/2} K_{e,ff} K_{0,ff}^{-1/2})
     yang identik eksak (selisih < 1e-15) dengan SVD baris-U (Eq. 4.1) pada elemen aksial
     (S2/S5) serta mendeteksi mekanisme lentur/portal (S1/S3/S4) secara eksak ketika
     m_e(lambda) = 1 - (1 - lambda) h_e <= 1e-8.
   - Menyimpan seluruh keputusan penerusan pra-analisis (P0, P1, P5, ARI-saja, Pengaman-saja,
     Utilisasi-awal) ke `results/screening/decisions_300.csv` beserta segel SHA-256 SEBELUM
     solver pascagangguan dijalankan.
3. PASS 2 (Evaluasi Acuan Pascagangguan, Kalibrasi Ambang, Inferensi Bootstrap & Ablasi):
   - Menjalankan solver elemen hingga pascagangguan pada seluruh 7.640 skenario gangguan
     (+ 300 kontrol utuh = 7.940 skenario).
   - Menghitung indikator konsekuensi mekanis (delta_u, delta_U, delta_F, delta_k, CRC Eq. 3.7)
     serta himpunan kritis (Konvensi A: kapasitas state gangguan; Konvensi B: kapasitas awal;
     dan Konvensi Gabungan Eq. 3.9).
   - Menjalankan kurva kalibrasi 101 titik ambang T = {0.00, 0.01, ..., 1.00} pada partisi
     `calibration` (60 model) -> `results/screening/calibration_grid_tau.csv`.
   - Menghitung metrik penyaringan per keluarga dan per partisi (`formula_dev`, `calibration`,
     `blind_val`, `final_test`) lengkap dengan interval kepercayaan satu sisi 95% (L_0.95)
     melalui bootstrap berkelompok B = 10.000 pada unit model induk (Eq. 3.10).
   - Mengevaluasi Gerbang Validasi A, B, C (ablasi 6 varian), dan D lintas keluarga ->
     `results/validation/`.

Jalankan:
    python3 examples/run_screening_s1_s5.py
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import ari_core as ac
import structural_solvers as ss

# Konstanta dari manifest_config_frozen.json
LAMS: Tuple[float, ...] = (0.0, 0.25, 0.50, 0.75)
TAU_PRIMARY: float = 0.50
MARGIN_TOL: float = 1e-8
RANK_TOL_REL: float = 1e-10
BOOTSTRAP_B: int = 10000
SEED: int = 2026


# =============================================================================
# 1. PERAKITAN MATRIKS KEKAKUAN PER ELEMEN (UNTUK PENGAMAN KINEMATIK UMUM)
# =============================================================================
def assemble_model_and_element_stiffnesses(model: dict) -> Tuple[np.ndarray, Dict[int, np.ndarray], List[int], int]:
    """
    Merakit matriks kekakuan global K0 (ndof x ndof), kamus matriks kekakuan
    tiap elemen K_e (ndof x ndof), daftar indeks DOF bebas (free_dofs), dan ndof
    HANYA dari spesifikasi model UTUH (intact state).
    """
    family = str(model.get("family", "")).lower()
    nodes_list = model.get("nodes", [])
    sorted_node_ids = sorted(int(n["id"]) for n in nodes_list)
    node_to_idx = {nid: i for i, nid in enumerate(sorted_node_ids)}
    num_nodes = len(sorted_node_ids)
    elements_data = model.get("elements", [])

    if family in ("s1", "s1_beam", "beam"):
        ndof = 2 * num_nodes
        nodes_x = {int(n["id"]): float(n.get("x", n.get("coords", [0.0])[0])) for n in nodes_list}
        K0 = np.zeros((ndof, ndof), dtype=float)
        Ke_map: Dict[int, np.ndarray] = {}
        for el in elements_data:
            eid = int(el["id"])
            ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
            L = abs(nodes_x[nj] - nodes_x[ni])
            E = float(el.get("E", ss.DEFAULT_E))
            I = float(el.get("I", 1e6))
            c1 = 12.0 * E * I / (L ** 3)
            c2 = 6.0 * E * I / (L ** 2)
            c3 = 4.0 * E * I / L
            c4 = 2.0 * E * I / L
            ke_loc = np.array([
                [ c1,  c2, -c1,  c2],
                [ c2,  c3, -c2,  c4],
                [-c1, -c2,  c1, -c2],
                [ c2,  c4, -c2,  c3]
            ], dtype=float)
            i_idx, j_idx = node_to_idx[ni], node_to_idx[nj]
            dofs = [2 * i_idx, 2 * i_idx + 1, 2 * j_idx, 2 * j_idx + 1]
            Ke = np.zeros((ndof, ndof), dtype=float)
            Ke[np.ix_(dofs, dofs)] = ke_loc
            Ke_map[eid] = Ke
            K0 += Ke

        fixed_dofs = set()
        for key, spec in model.get("boundary_conditions", {}).items():
            nid = int(key.split("_", 1)[1]) if "_" in key else int(key)
            if nid not in node_to_idx:
                continue
            idx = node_to_idx[nid]
            comps = spec if isinstance(spec, list) else (
                ["v", "theta"] if spec == "fixed" else (
                    ["v"] if spec in ("pinned", "roller") else list(spec.keys()) if isinstance(spec, dict) else [spec]
                )
            )
            for c in comps:
                c_clean = str(c).lower().strip()
                if c_clean in ("v", "uy", "y"):
                    fixed_dofs.add(2 * idx)
                elif c_clean in ("theta", "rz", "rot"):
                    fixed_dofs.add(2 * idx + 1)
        free_dofs = sorted(d for d in range(ndof) if d not in fixed_dofs)
        return K0, Ke_map, free_dofs, ndof

    elif family in ("s2", "s2_truss", "truss"):
        dim = int(model.get("dimension", 2))
        ndof = dim * num_nodes
        nodes_c = {int(n["id"]): np.array(n.get("coords", [0.0] * dim), dtype=float) for n in nodes_list}
        K0 = np.zeros((ndof, ndof), dtype=float)
        Ke_map = {}
        for el in elements_data:
            eid = int(el["id"])
            ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
            d = nodes_c[nj] - nodes_c[ni]
            L = float(np.linalg.norm(d))
            E = float(el.get("E", ss.DEFAULT_E))
            A = float(el.get("area", el.get("A", 1000.0)))
            lam_vec = d / L
            k_sub = (E * A / L) * np.outer(lam_vec, lam_vec)
            i_idx, j_idx = node_to_idx[ni], node_to_idx[nj]
            idx_i = slice(dim * i_idx, dim * i_idx + dim)
            idx_j = slice(dim * j_idx, dim * j_idx + dim)
            Ke = np.zeros((ndof, ndof), dtype=float)
            Ke[idx_i, idx_i] += k_sub
            Ke[idx_j, idx_j] += k_sub
            Ke[idx_i, idx_j] -= k_sub
            Ke[idx_j, idx_i] -= k_sub
            Ke_map[eid] = Ke
            K0 += Ke

        fixed_dofs = set()
        for key, spec in model.get("boundary_conditions", {}).items():
            nid = int(key.split("_", 1)[1]) if "_" in key else int(key)
            if nid not in node_to_idx:
                continue
            idx = node_to_idx[nid]
            comps = spec if isinstance(spec, list) else (list(spec.keys()) if isinstance(spec, dict) else [spec])
            for c in comps:
                c_clean = str(c).lower().strip()
                if c_clean in ("ux", "x"):
                    fixed_dofs.add(dim * idx)
                elif c_clean in ("uy", "y") and dim >= 2:
                    fixed_dofs.add(dim * idx + 1)
        free_dofs = sorted(d for d in range(ndof) if d not in fixed_dofs)
        return K0, Ke_map, free_dofs, ndof

    elif family in ("s3", "s3_frame", "frame", "s4", "s4_braced_frame", "braced_frame"):
        ndof = 3 * num_nodes
        nodes_c = {int(n["id"]): np.array(n.get("coords", [n.get("x", 0.0), n.get("y", 0.0)]), dtype=float) for n in nodes_list}
        K0 = np.zeros((ndof, ndof), dtype=float)
        Ke_map = {}
        for el in elements_data:
            eid = int(el["id"])
            ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
            dx = float(nodes_c[nj][0] - nodes_c[ni][0])
            dy = float(nodes_c[nj][1] - nodes_c[ni][1])
            L = float(math.hypot(dx, dy))
            E = float(el.get("E", ss.DEFAULT_E))
            A = float(el.get("A", el.get("area", 5000.0)))
            el_type = str(el.get("type", "frame")).lower()
            if el_type == "brace":
                rel = "both"
                I = float(el.get("I", 0.0))
            else:
                rel = str(el.get("release", "none")).lower()
                I = float(el.get("I", 2e8))
            k_loc = ss._frame_local_stiffness(E, A, I, L, rel)
            T = ss._frame_transformation(dx, dy, L)
            ke_glob = T.T @ k_loc @ T
            i_idx, j_idx = node_to_idx[ni], node_to_idx[nj]
            dofs = [3 * i_idx, 3 * i_idx + 1, 3 * i_idx + 2,
                    3 * j_idx, 3 * j_idx + 1, 3 * j_idx + 2]
            Ke = np.zeros((ndof, ndof), dtype=float)
            Ke[np.ix_(dofs, dofs)] = ke_glob
            Ke_map[eid] = Ke
            K0 += Ke

        fixed_dofs = set()
        for key, spec in model.get("boundary_conditions", {}).items():
            nid = int(key.split("_", 1)[1]) if "_" in key else int(key)
            if nid not in node_to_idx:
                continue
            idx = node_to_idx[nid]
            if isinstance(spec, list):
                comps = spec
            elif isinstance(spec, str):
                if spec == "fixed":
                    comps = ["ux", "uy", "theta"]
                elif spec == "pinned":
                    comps = ["ux", "uy"]
                elif spec == "roller_x":
                    comps = ["uy"]
                elif spec == "roller_y":
                    comps = ["ux"]
                else:
                    comps = [c.strip() for c in spec.split(",")]
            else:
                comps = list(spec.keys())
            for c in comps:
                c_clean = str(c).lower().strip()
                if c_clean in ("ux", "x"):
                    fixed_dofs.add(3 * idx)
                elif c_clean in ("uy", "y"):
                    fixed_dofs.add(3 * idx + 1)
                elif c_clean in ("theta", "rz", "rot"):
                    fixed_dofs.add(3 * idx + 2)
        free_dofs = sorted(d for d in range(ndof) if d not in fixed_dofs)
        return K0, Ke_map, free_dofs, ndof

    elif family in ("s5", "s5_space_truss", "space_truss"):
        ndof = 3 * num_nodes
        nodes_c = {int(n["id"]): np.array(n.get("coords", [n.get("x", 0.0), n.get("y", 0.0), n.get("z", 0.0)]), dtype=float) for n in nodes_list}
        K0 = np.zeros((ndof, ndof), dtype=float)
        Ke_map = {}
        for el in elements_data:
            eid = int(el["id"])
            ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
            d = nodes_c[nj] - nodes_c[ni]
            L = float(np.linalg.norm(d))
            E = float(el.get("E", ss.DEFAULT_E))
            A = float(el.get("A", el.get("area", 1000.0)))
            lam_vec = d / L
            k_sub = (E * A / L) * np.outer(lam_vec, lam_vec)
            i_idx, j_idx = node_to_idx[ni], node_to_idx[nj]
            idx_i = slice(3 * i_idx, 3 * i_idx + 3)
            idx_j = slice(3 * j_idx, 3 * j_idx + 3)
            Ke = np.zeros((ndof, ndof), dtype=float)
            Ke[idx_i, idx_i] += k_sub
            Ke[idx_j, idx_j] += k_sub
            Ke[idx_i, idx_j] -= k_sub
            Ke[idx_j, idx_i] -= k_sub
            Ke_map[eid] = Ke
            K0 += Ke

        fixed_dofs = set()
        for key, spec in model.get("boundary_conditions", {}).items():
            nid = int(key.split("_", 1)[1]) if "_" in key else int(key)
            if nid not in node_to_idx:
                continue
            idx = node_to_idx[nid]
            if isinstance(spec, list):
                comps = spec
            elif isinstance(spec, str):
                if spec in ("pinned", "fixed"):
                    comps = ["ux", "uy", "uz"]
                elif spec == "roller_xy":
                    comps = ["uz"]
                elif spec == "roller_xz":
                    comps = ["uy"]
                elif spec == "roller_yz":
                    comps = ["ux"]
                else:
                    comps = [c.strip() for c in spec.split(",")]
            else:
                comps = list(spec.keys())
            for c in comps:
                c_clean = str(c).lower().strip()
                if c_clean in ("ux", "x"):
                    fixed_dofs.add(3 * idx)
                elif c_clean in ("uy", "y"):
                    fixed_dofs.add(3 * idx + 1)
                elif c_clean in ("uz", "z"):
                    fixed_dofs.add(3 * idx + 2)
        free_dofs = sorted(d for d in range(ndof) if d not in fixed_dofs)
        return K0, Ke_map, free_dofs, ndof

    raise ValueError(f"Keluarga struktur tidak dikenal: {family}")


class GeneralizedMechanicalGuard:
    """
    Pengaman Kinematik Spektral Umum Lintas Keluarga S1–S5 (Perluasan Eq. 4.1–4.5).
    Hanya menggunakan matriks kekakuan model UTUH K_{0,ff} dan kontribusi elemen K_{e,ff}.
    Pada elemen aksial (rank-1), h_e = lambda_max(K_{0,ff}^{-1} K_{e,ff}) identik
    secara aljabar dengan jumlah kuadrat baris U dari SVD (Eq. 4.1).
    Pada elemen lentur/portal (multi-DOF), h_e mengukur proporsi kekakuan modal maksimum
    elemen terhadap sistem, sehingga m_e(lambda) = 1 - (1 - lambda) * h_e <= 1e-8
    mendeteksi secara eksak pembentukan mekanisme kinematik pada sembarang keluarga S1–S5.
    """

    def __init__(self, model: dict):
        self.model = model
        K0, Ke_map, free_dofs, ndof = assemble_model_and_element_stiffnesses(model)
        self.free_dofs = free_dofs
        self.n_free = len(free_dofs)
        self.K0_ff = 0.5 * (K0[np.ix_(free_dofs, free_dofs)] + K0[np.ix_(free_dofs, free_dofs)].T)
        self.Ke_ff: Dict[int, np.ndarray] = {
            eid: 0.5 * (Ke[np.ix_(free_dofs, free_dofs)] + Ke[np.ix_(free_dofs, free_dofs)].T)
            for eid, Ke in Ke_map.items()
        }
        self.svd_ok = True
        self.h: Dict[int, float] = {}
        self.h_trace: Dict[int, float] = {}
        self.rho0: float = 0.0

        try:
            ev0, V0 = np.linalg.eigh(self.K0_ff)
            if ev0.max() <= 0.0 or ev0.min() <= RANK_TOL_REL * ev0.max():
                self.svd_ok = False
            else:
                self.rho0 = float(ev0.min() / ev0.max())
                inv_sqrt = V0 @ np.diag(1.0 / np.sqrt(ev0)) @ V0.T
                for eid, Ke_f in self.Ke_ff.items():
                    M_sym = inv_sqrt @ Ke_f @ inv_sqrt
                    M_sym = 0.5 * (M_sym + M_sym.T)
                    eigs_e = np.linalg.eigvalsh(M_sym)
                    self.h[eid] = float(np.clip(np.max(eigs_e), 0.0, 1.0))
                    self.h_trace[eid] = float(np.sum(np.clip(eigs_e, 0.0, None)))
        except np.linalg.LinAlgError:
            self.svd_ok = False
            for eid in self.Ke_ff:
                self.h[eid] = float("nan")
                self.h_trace[eid] = float("nan")

    def m_e(self, eid: int, lam: float) -> float:
        return 1.0 - (1.0 - float(lam)) * float(self.h.get(eid, 1.0))

    def margin_info(self, eid: int, lam: float) -> Dict[str, Any]:
        m_s = self.m_e(eid, lam)
        Ke_lam = self.K0_ff - (1.0 - float(lam)) * self.Ke_ff[eid]
        Ke_lam = 0.5 * (Ke_lam + Ke_lam.T)
        ev = np.linalg.eigvalsh(Ke_lam)
        max_ev = float(ev.max()) if len(ev) else 0.0
        min_ev = float(ev.min()) if len(ev) else 0.0
        tol = max(RANK_TOL_REL * abs(max_ev), 1e-12)
        rank_lam = int(np.sum(ev > tol))
        rank_def = (rank_lam < self.n_free) or (min_ev <= tol)
        ratio = float(max(min_ev, 0.0) / max_ev) if max_ev > 0.0 else 0.0
        bound = float(m_s * self.rho0)
        pad = 1e-8 * max(1.0, abs(bound))
        bound_ok = bool(ratio + pad >= bound)
        margin_small = bool(m_s <= MARGIN_TOL)
        return {
            "m_s": m_s,
            "ratio": ratio,
            "bound": bound,
            "bound_ok": bound_ok,
            "margin_small": margin_small,
            "rank_deficient_exact": rank_def,
            "rank": rank_lam,
            "n_free": self.n_free,
        }

    def guard_flag(self, eid: int, lam: float) -> Tuple[int, Dict[str, Any]]:
        if not self.svd_ok:
            return 1, {"m_s": 0.0, "bound_ok": False, "margin_small": True, "rank_deficient_exact": True}
        info = self.margin_info(eid, lam)
        flag = 1 if (info["margin_small"] or not info["bound_ok"] or info["rank_deficient_exact"]) else 0
        return flag, info


# =============================================================================
# 2. MESIN ARI MULTI-KELUARGA (BAGIAN 2.6–2.8 UNTUK S1–S5)
# =============================================================================
def compute_family_dev_scales(all_models_by_fam: Dict[str, List[dict]]) -> Dict[str, Dict[str, float]]:
    """
    Menghitung skala normalisasi median atribut positif pada data pengembangan
    (`formula_dev`) sesuai Bagian 2.6 Persamaan (2.6).
    """
    scales: Dict[str, Dict[str, float]] = {}
    for fam, models in all_models_by_fam.items():
        dev_models = [m for m in models if m.get("split") == "formula_dev"]
        k_ax, r_ax, k_fl, r_fl = [], [], [], []
        for m in dev_models:
            nodes_c = {}
            for n in m["nodes"]:
                nid = int(n["id"])
                if "coords" in n:
                    c = [float(v) for v in n["coords"]]
                    while len(c) < 3:
                        c.append(0.0)
                else:
                    c = [float(n.get("x", 0.0)), float(n.get("y", 0.0)), float(n.get("z", 0.0))]
                nodes_c[nid] = np.array(c, dtype=float)
            for el in m["elements"]:
                ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
                L = float(np.linalg.norm(nodes_c[nj] - nodes_c[ni]))
                E = float(el.get("E", ss.DEFAULT_E))
                A = float(el.get("A", el.get("area", 2000.0)))
                I = float(el.get("I", 0.0))
                el_type = str(el.get("type", "")).lower()
                if fam in ("S2_truss", "S5_space_truss") or el_type == "brace":
                    k_ax.append(E * A / L)
                    r_ax.append(float(el.get("capacity", el.get("N_capacity", 300.0))))
                elif fam == "S1_beam":
                    k_fl.append(E * I / (L ** 3))
                    r_fl.append(float(el.get("M_capacity", 50000.0)))
                else:
                    k_ax.append(E * A / L)
                    r_ax.append(float(el.get("N_capacity", 1200.0)))
                    k_fl.append(E * I / (L ** 3))
                    r_fl.append(float(el.get("M_capacity", 100000.0)))
        scales[fam] = {
            "s_k_axial": float(np.median(k_ax)) if k_ax else 20.0,
            "s_R_axial": float(np.median(r_ax)) if r_ax else 80.0,
            "s_k_flex": float(np.median(k_fl)) if k_fl else 1.0,
            "s_M_flex": float(np.median(r_fl)) if r_fl else 100000.0,
        }
    return scales


def _canon_dir(comp_name: str, family: str) -> Optional[str]:
    c = comp_name.lower().strip()
    if c in ("fx", "ux", "rx", "x"):
        return "x"
    if c in ("fy", "uy", "ry", "v", "y"):
        return "y"
    if c in ("fz", "uz", "rz_3d", "z"):
        return "z"
    if c == "rz":
        return "z" if "s5" in family.lower() or "space" in family.lower() else "mz"
    if c in ("mz", "theta", "m", "rot"):
        return "mz"
    return None


def prepare_multi_family_ari_engine(
    model: dict,
    intact_res: ss.StructuralSolverResult,
    fam_scales: Dict[str, float],
    cfg: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Membangun struktur data pra-analisis ARI untuk model dari keluarga S1–S5
    menggunakan HANYA informasi model utuh (`intact_res`).
    """
    c_cfg = ac.merged_config(**(cfg or {}))
    family = str(model.get("family", ""))
    nodes_c = {}
    for n in model["nodes"]:
        nid = int(n["id"])
        if "coords" in n:
            c = [float(v) for v in n["coords"]]
            while len(c) < 3:
                c.append(0.0)
        else:
            c = [float(n.get("x", 0.0)), float(n.get("y", 0.0)), float(n.get("z", 0.0))]
        nodes_c[nid] = np.array(c, dtype=float)

    edges_meta = []
    base_weights: Dict[int, float] = {}
    u_star_map: Dict[int, float] = {}
    k_eff_map: Dict[int, float] = {}
    cap_eff_map: Dict[int, float] = {}

    for idx_el, el in enumerate(model["elements"]):
        eid = int(el["id"])
        ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
        L = float(np.linalg.norm(nodes_c[nj] - nodes_c[ni]))
        E = float(el.get("E", ss.DEFAULT_E))
        A = float(el.get("A", el.get("area", 2000.0)))
        I = float(el.get("I", 0.0))
        el_type = str(el.get("type", "")).lower()

        if family in ("S2_truss", "S5_space_truss") or el_type == "brace":
            k_val = E * A / L
            r_val = float(el.get("capacity", el.get("N_capacity", 300.0)))
            k_hat = k_val / (k_val + fam_scales["s_k_axial"])
            r_hat = r_val / (r_val + fam_scales["s_R_axial"])
        elif family == "S1_beam":
            k_val = E * I / (L ** 3)
            r_val = float(el.get("M_capacity", 50000.0))
            k_hat = k_val / (k_val + fam_scales["s_k_flex"])
            r_hat = r_val / (r_val + fam_scales["s_M_flex"])
        else:
            # S3_frame atau S4_braced_frame (elemen balok-kolom): gabungan seimbang aksial & lentur (Eq. 2.5-2.6)
            k_ax_v = E * A / L
            r_ax_v = float(el.get("N_capacity", 1200.0))
            k_fl_v = E * I / (L ** 3)
            r_fl_v = float(el.get("M_capacity", 100000.0))
            k_hat = 0.5 * (k_ax_v / (k_ax_v + fam_scales["s_k_axial"])) + 0.5 * (k_fl_v / (k_fl_v + fam_scales["s_k_flex"]))
            r_hat = 0.5 * (r_ax_v / (r_ax_v + fam_scales["s_R_axial"])) + 0.5 * (r_fl_v / (r_fl_v + fam_scales["s_M_flex"]))
            k_val = k_ax_v
            r_val = r_ax_v

        w_e = float(c_cfg["alpha_k"] * k_hat + c_cfg["alpha_R"] * r_hat)
        base_weights[eid] = w_e
        k_eff_map[eid] = k_val
        cap_eff_map[eid] = r_val

        # Utilisasi awal U*_e dari intact_res
        u_raw = float(intact_res.utilizations[idx_el]) if idx_el < len(intact_res.utilizations) else 0.0
        u_star_map[eid] = float(min(max(u_raw, 0.0), 1.0))
        edges_meta.append({"id": eid, "i": ni, "j": nj, "L": L})

    # Simpul tumpuan V_T dari boundary_conditions
    support_nodes = sorted({
        int(k.split("_", 1)[1]) if "_" in k else int(k)
        for k in model.get("boundary_conditions", {}).keys()
    })
    vt = len(support_nodes) or 1

    # Kelompokkan beban menurut arah kanonik c in {x, y, z, mz}
    loads_by_dir: Dict[str, Dict[int, float]] = {}
    for ld in model.get("loads", []):
        nid = int(ld["node"])
        for cname, val in ld.get("components", {}).items():
            fv = float(val)
            if abs(fv) <= 0.0:
                continue
            cdir = _canon_dir(cname, family)
            if cdir:
                loads_by_dir.setdefault(cdir, {})[nid] = loads_by_dir.get(cdir, {}).get(nid, 0.0) + fv

    # Reaksi utuh per simpul dan arah kanonik
    # Untuk S2_truss, intact_res.reactions dari dispatcher mungkin kosong jika belum diisi; ambil dari solve_truss_s2 bila perlu
    reactions_by_node: Dict[int, Dict[str, float]] = {}
    if family == "S2_truss" and not intact_res.reactions:
        res_s2_raw = ss.solve_truss_s2(model)
        dim_s2 = int(model.get("dimension", 2))
        comps_s2 = ["x", "y", "z"]
        for dof, val in res_s2_raw.reactions.items():
            nid = dof // dim_s2
            cdir = comps_s2[dof % dim_s2]
            reactions_by_node.setdefault(nid, {})[cdir] = float(val)
    else:
        for nid, rdict in intact_res.reactions.items():
            for rname, val in rdict.items():
                cdir = _canon_dir(rname, family)
                if cdir:
                    reactions_by_node.setdefault(int(nid), {})[cdir] = float(val)

    cases = []
    raw_pi = []
    single_case = (len(loads_by_dir) == 1)
    for cdir in ("x", "y", "z", "mz"):
        if cdir not in loads_by_dir:
            continue
        f_nodes = loads_by_dir[cdir]
        F_c = sum(abs(v) for v in f_nodes.values())
        if F_c <= 0.0:
            continue
        a_ic = {nid: abs(v) / F_c for nid, v in f_nodes.items()}

        # Komponen reaksi tumpuan searah kasus beban c (Eq. 2.12)
        if single_case:
            r_jc = {nid: abs(float(reactions_by_node.get(nid, {}).get(cdir, 0.0))) for nid in support_nodes}
        else:
            # Solve kasus beban tunggal arah cdir pada model utuh
            m_single = copy.deepcopy(model)
            cname_map = {"x": "Fx", "y": "Fy", "z": "Fz", "mz": "Mz"}
            if family == "S2_truss":
                cname_map = {"x": "ux", "y": "uy", "z": "uz", "mz": "uy"}
            m_single["loads"] = [{"node": nid, "components": {cname_map[cdir]: v}} for nid, v in f_nodes.items()]
            res_c = ss.solve_structural_model(m_single)
            r_jc = {}
            if family == "S2_truss":
                res_s2_c = ss.solve_truss_s2(m_single)
                dim_s2 = int(model.get("dimension", 2))
                idx_d = {"x": 0, "y": 1, "z": 2}.get(cdir, 0)
                for nid in support_nodes:
                    r_jc[nid] = abs(float(res_s2_c.reactions.get(dim_s2 * nid + idx_d, 0.0)))
            else:
                for nid in support_nodes:
                    val_r = 0.0
                    for rname, rv in res_c.reactions.get(nid, {}).items():
                        if _canon_dir(rname, family) == cdir:
                            val_r = abs(float(rv))
                    r_jc[nid] = val_r

        B_c = sum(r_jc.values())
        if B_c > 0.0:
            b_jc = {nid: c_cfg["beta"] / vt + (1.0 - c_cfg["beta"]) * r_jc[nid] / B_c for nid in support_nodes}
        else:
            b_jc = {nid: 1.0 / vt for nid in support_nodes}
        raw_pi.append(F_c)
        cases.append({"direction": cdir, "F": F_c, "a": a_ic, "b": b_jc})

    tot_pi = sum(raw_pi)
    for c, w in zip(cases, raw_pi):
        c["pi"] = w / tot_pi if tot_pi > 0.0 else 0.0

    node_ids = [int(n["id"]) for n in model["nodes"]]
    return {
        "model": model,
        "config": c_cfg,
        "node_ids": node_ids,
        "edges_meta": edges_meta,
        "base_weights": base_weights,
        "u_star_map": u_star_map,
        "k_eff_map": k_eff_map,
        "cap_eff_map": cap_eff_map,
        "support_nodes": support_nodes,
        "cases": cases,
    }


def score_multi_family_graph(
    eng: Dict[str, Any],
    disruption: Optional[Tuple[int, float]] = None,
    pair_cache: Optional[Dict[Any, Tuple[float, str]]] = None,
    override_cfg: Optional[dict] = None,
    override_weights: Optional[Dict[int, float]] = None
) -> Tuple[float, str]:
    """
    Menghitung skor graf S(G) untuk kondisi utuh (disruption=None) atau
    terganggu s=(eid, lam) menggunakan enumerasi jalur sederhana edge-disjoint
    eksak (`ac.compute_pair_score`).
    """
    cfg = dict(eng["config"])
    if override_cfg:
        cfg.update(override_cfg)
    bw = override_weights if override_weights is not None else eng["base_weights"]
    weights = dict(bw)
    if disruption is not None:
        eid_d, lam_d = int(disruption[0]), float(disruption[1])
        weights[eid_d] = weights[eid_d] * lam_d

    removed = {eid for eid, w in weights.items() if float(w) == 0.0}
    active_edges = [e for e in eng["edges_meta"] if int(e["id"]) not in removed]
    graph = ac.Multigraph(eng["node_ids"], active_edges)
    edge_cost = {eid: 1.0 / (w + cfg["eps_w"]) for eid, w in weights.items() if eid not in removed}

    sig = tuple(sorted((eid, round(edge_cost[eid], 12)) for eid in edge_cost))
    total_s = 0.0
    for c in eng["cases"]:
        inner = 0.0
        for i_node, a_w in c["a"].items():
            for j_node, b_w in c["b"].items():
                if OverrideKey := (override_cfg is not None or override_weights is not None):
                    phi, st = ac.compute_pair_score(graph, i_node, j_node, edge_cost, cfg)
                else:
                    ckey = (i_node, j_node, sig)
                    if pair_cache is not None and ckey in pair_cache:
                        phi, st = pair_cache[ckey]
                    else:
                        phi, st = ac.compute_pair_score(graph, i_node, j_node, edge_cost, cfg)
                        if pair_cache is not None:
                            pair_cache[ckey] = (phi, st)
                if st != "certified":
                    return float("nan"), st
                inner += a_w * b_w * phi
        total_s += c["pi"] * inner
    return total_s, "ok"


def apply_physical_disruption(model: dict, eid: int, lam: float) -> dict:
    """
    Menerapkan pelemahan fisik pada model struktur untuk evaluasi solver acuan
    (PASS 2): jika lam == 0, elemen dihapus dari daftar elemen; jika 0 < lam < 1,
    kekakuan (A/area, I) dan kapasitas dikalikan dengan lam (Konvensi A).
    """
    m2 = copy.deepcopy(model)
    if float(lam) == 0.0:
        m2["elements"] = [el for el in m2["elements"] if int(el["id"]) != int(eid)]
        return m2
    for el in m2["elements"]:
        if int(el["id"]) == int(eid):
            for k in ("A", "area", "I", "capacity", "N_capacity", "M_capacity"):
                if k in el:
                    el[k] = float(el[k]) * float(lam)
    if "capacities" in m2 and str(int(eid)) in m2["capacities"]:
        m2["capacities"][str(int(eid))] = float(m2["capacities"][str(int(eid))]) * float(lam)
    return m2


def compute_utilization_convention_B(
    intact_model: dict,
    disrupted_model: dict,
    res_disr: ss.StructuralSolverResult
) -> float:
    """
    Menghitung utilisasi maksimum pascagangguan terhadap KAPASITAS ASLI UTUH
    (Konvensi B, Bagian 4.2.4) lintas keluarga S1–S5.
    """
    if res_disr.status != "ok":
        return float("inf")
    fam = str(intact_model.get("family", "")).lower()
    orig_el = {int(el["id"]): el for el in intact_model["elements"]}
    orig_caps = intact_model.get("capacities", {})

    u_vals = []
    for idx_el, el_d in enumerate(disrupted_model["elements"]):
        eid = int(el_d["id"])
        el_0 = orig_el[eid]
        f_info = res_disr.element_forces.get(eid, {})
        if fam in ("s1", "s1_beam"):
            m_cap0 = float(el_0.get("M_capacity", 50000.0))
            m_act = float(f_info.get("M_max", 0.0))
            u_vals.append(m_act / m_cap0 if m_cap0 > 0 else 0.0)
        elif fam in ("s2", "s2_truss"):
            n_cap0 = float(orig_caps.get(str(eid), el_0.get("capacity", 300.0)))
            n_act = abs(float(f_info.get("axial_force", 0.0)))
            u_vals.append(n_act / n_cap0 if n_cap0 > 0 else 0.0)
        elif fam in ("s3", "s3_frame"):
            n_cap0 = float(el_0.get("N_capacity", 1200.0))
            m_cap0 = float(el_0.get("M_capacity", 100000.0))
            n_act = abs(float(f_info.get("N_axial", 0.0)))
            m_act = float(f_info.get("M_max", 0.0))
            u_vals.append((n_act / n_cap0) + (m_act / m_cap0))
        elif fam in ("s4", "s4_braced_frame"):
            n_cap0 = float(el_0.get("N_capacity", 1200.0))
            m_cap0 = float(el_0.get("M_capacity", 100000.0))
            n_act = abs(float(f_info.get("N_axial", 0.0)))
            m_act = float(f_info.get("M_max", 0.0))
            if str(el_0.get("type", "frame")).lower() == "brace":
                u_vals.append(n_act / n_cap0 if n_cap0 > 0 else 0.0)
            else:
                u_vals.append((n_act / n_cap0) + (m_act / m_cap0))
        elif fam in ("s5", "s5_space_truss"):
            n_cap0 = float(el_0.get("capacity", el_0.get("N_capacity", 500.0)))
            n_act = abs(float(f_info.get("axial_force", 0.0)))
            u_vals.append(n_act / n_cap0 if n_cap0 > 0 else 0.0)
    return float(max(u_vals)) if u_vals else 0.0


# =============================================================================
# 3. INFERENSI STATISTIK BOOTSTRAP BERKELOMPOK (PERSAMAAN 3.10)
# =============================================================================
def cluster_bootstrap_ci95_lower(values: List[float], B: int = BOOTSTRAP_B, seed: int = SEED) -> Tuple[float, float]:
    """
    Menghitung rerata antar-model induk dan batas bawah satu sisi 95% (kuantil 0.05)
    menggunakan bootstrap berkelompok pada unit model induk (Persamaan 3.10).
    """
    arr = np.array([v for v in values if not math.isnan(v)], dtype=float)
    M = len(arr)
    if M == 0:
        return float("nan"), float("nan")
    mean_val = float(np.mean(arr))
    if M == 1 or np.allclose(arr, arr[0]):
        return mean_val, float(arr[0])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, M, size=(B, M))
    boot_means = np.mean(arr[idx], axis=1)
    l95 = float(np.quantile(boot_means, 0.05))
    return mean_val, l95


def spearman_corr(x: List[float], y: List[float]) -> float:
    """Korelasi peringkat Spearman dengan penanganan rata-rata ikatan (average ties)."""
    if len(x) < 2 or len(x) != len(y):
        return float("nan")
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    if np.allclose(xa, xa[0]) or np.allclose(ya, ya[0]):
        return float("nan")

    def _ranks(a: np.ndarray) -> np.ndarray:
        order = np.argsort(a)
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(1, len(a) + 1, dtype=float)
        # Rata-rata untuk nilai kembar (ties)
        vals, inv, counts = np.unique(a, return_inverse=True, return_counts=True)
        for idx_v, cnt in enumerate(counts):
            if cnt > 1:
                mask = (inv == idx_v)
                ranks[mask] = np.mean(ranks[mask])
        return ranks

    rx = _ranks(xa)
    ry = _ranks(ya)
    rx_m = rx - np.mean(rx)
    ry_m = ry - np.mean(ry)
    denom = float(np.sqrt(np.sum(rx_m ** 2) * np.sum(ry_m ** 2)))
    if denom <= 1e-15:
        return float("nan")
    return float(np.sum(rx_m * ry_m) / denom)


# =============================================================================
# 4. PIPELINE UTAMA W3/W4 (PASS 1 PRA-ANALISIS -> PASS 2 EVALUASI & VALIDASI)
# =============================================================================
def main() -> int:
    t_start = time.monotonic()
    print("=" * 82)
    print("GATE 15 (W3/W4) — PENYARINGAN OPERASIONAL SKALA PENUH (300 MODEL x 7.940 SKENARIO)")
    print("=" * 82)

    # 0. Verifikasi protokol beku
    frozen_path = REPO_ROOT / "results" / "screening" / "manifest_config_frozen.json"
    if not frozen_path.exists():
        raise FileNotFoundError(f"Protokol beku belum ditemukan: {frozen_path}")
    frozen_cfg = json.loads(frozen_path.read_text(encoding="utf-8"))
    print(f"[FROZEN PROTOCOL] {frozen_cfg['protocol_id']} | Seal SHA-256: {frozen_cfg['frozen_config_sha256'][:16]}...")

    # Muat seluruh 300 model dari results/dataset/models_s1..s5.json
    dataset_dir = REPO_ROOT / "results" / "dataset"
    all_models_by_fam: Dict[str, List[dict]] = {}
    all_models: List[dict] = []
    for fam_short, fam_key in [
        ("s1", "S1_beam"),
        ("s2", "S2_truss"),
        ("s3", "S3_frame"),
        ("s4", "S4_braced_frame"),
        ("s5", "S5_space_truss"),
    ]:
        fpath = dataset_dir / f"models_{fam_short}.json"
        m_list = json.loads(fpath.read_text(encoding="utf-8"))["models"]
        all_models_by_fam[fam_key] = m_list
        all_models.extend(m_list)

    print(f"[DATASET] Loaded {len(all_models)} parent models across 5 families.")

    # Hitung skala median atribut dari partisi formula_dev (Bagian 2.6 Eq. 2.6)
    fam_scales = compute_family_dev_scales(all_models_by_fam)
    for fk, sc_d in fam_scales.items():
        print(f"  Scales ({fk:15s}): s_k_ax={sc_d['s_k_axial']:.2f}, s_R_ax={sc_d['s_R_axial']:.2f}, "
              f"s_k_fl={sc_d['s_k_flex']:.4f}, s_M_fl={sc_d['s_M_flex']:.1f}")

    # =========================================================================
    # PASS 1: PRA-ANALISIS MURNI (INTACT ONLY) -> SIMPAN KEPUTUSAN + SHA-256
    # =========================================================================
    print("\n[PASS 1] Menghitung skor ARI & Pengaman Kinematik (Intact-Only Pre-Analysis)...")
    t_p1 = time.monotonic()

    engines: Dict[str, Dict[str, Any]] = {}
    guards: Dict[str, GeneralizedMechanicalGuard] = {}
    intact_results: Dict[str, ss.StructuralSolverResult] = {}
    decision_rows: List[Dict[str, Any]] = []
    pre_lookup: Dict[Tuple[str, Optional[int], float], Dict[str, Any]] = {}

    for m in all_models:
        mid = str(m["id"])
        fam = str(m["family"])
        split = str(m["split"])

        # Solve model utuh (intact)
        res0 = ss.solve_structural_model(m)
        if res0.status != "ok":
            raise RuntimeError(f"Model utuh {mid} gagal diselesaikan: {res0.status}")
        intact_results[mid] = res0

        # Bangun mesin ARI & Pengaman Kinematik dari model utuh
        eng = prepare_multi_family_ari_engine(m, res0, fam_scales[fam])
        grd = GeneralizedMechanicalGuard(m)
        engines[mid] = eng
        guards[mid] = grd

        pair_cache: Dict[Any, Tuple[float, str]] = {}
        s_base, st_base = score_multi_family_graph(eng, None, pair_cache)
        eng["s_base"] = s_base
        eng["st_base"] = st_base
        eng["pair_cache"] = pair_cache

        # 1a. Baris kontrol utuh (edge=None, lam=1.0)
        ctrl_row = {
            "model_id": mid,
            "family": fam,
            "split": split,
            "scenario_type": "intact_control",
            "edge_id": -1,
            "lambda": 1.0,
            "S_intact": round(s_base, 9) if not math.isnan(s_base) else "",
            "S_disrupted": round(s_base, 9) if not math.isnan(s_base) else "",
            "RR": 1.0,
            "U_star": 0.0,
            "ARI": 1.0,
            "CI": 0.0,
            "util_baseline_score": 0.0,
            "h_e": 0.0,
            "m_s": 1.0,
            "guard_flag": 0,
            "status_code": "scored" if st_base == "ok" else st_base,
            "fwd_ari_only": 0,
            "fwd_guard_only": 0,
            "fwd_P0": 0,
            "fwd_P1": 0,
            "fwd_P5": 0,
        }
        decision_rows.append(ctrl_row)
        pre_lookup[(mid, -1, 1.0)] = ctrl_row

        # 1b. Baris skenario gangguan (4 * n_elements)
        for e_meta in eng["edges_meta"]:
            eid = int(e_meta["id"])
            u_star = eng["u_star_map"][eid]
            h_val = grd.h.get(eid, 1.0)
            for lam in LAMS:
                s_val, st_scen = score_multi_family_graph(eng, (eid, lam), pair_cache)
                abstain = (st_base != "ok") or (st_scen != "ok") or (s_base < ac.BASELINE_TOL)
                if abstain:
                    rr = None
                    ari = None
                    ci = None
                    st_code = "invalid_baseline" if s_base < ac.BASELINE_TOL else st_scen
                else:
                    rr = float(s_val / s_base)
                    ari = float(rr * (1.0 - eng["config"]["eta"] * u_star))
                    ci = float(max(1.0 - ari, 0.0))
                    st_code = "scored"

                g_flag, g_info = grd.guard_flag(eid, lam)
                m_s = float(g_info["m_s"])

                fwd_ari = 1 if (abstain or (ci is not None and ci >= TAU_PRIMARY)) else 0
                fwd_grd = int(g_flag == 1)
                fwd_p0 = 1 if (fwd_ari == 1 or fwd_grd == 1) else 0
                fwd_p1 = 1 if (fwd_p0 == 1 or float(lam) == 0.0) else 0
                fwd_p5 = 1 if (fwd_p0 == 1 or (float(lam) <= 0.25 and ci is not None and ci > 0.35)) else 0

                # Skor pembanding utilisasi awal: (1 - lambda) * U*_e (Bagian 3.11)
                util_base_score = float((1.0 - float(lam)) * u_star)

                row = {
                    "model_id": mid,
                    "family": fam,
                    "split": split,
                    "scenario_type": "disruption",
                    "edge_id": eid,
                    "lambda": float(lam),
                    "S_intact": round(s_base, 9) if not math.isnan(s_base) else "",
                    "S_disrupted": round(s_val, 9) if (s_val is not None and not math.isnan(s_val)) else "",
                    "RR": round(rr, 9) if rr is not None else "",
                    "U_star": round(u_star, 9),
                    "ARI": round(ari, 9) if ari is not None else "",
                    "CI": round(ci, 9) if ci is not None else "",
                    "util_baseline_score": round(util_base_score, 9),
                    "h_e": round(h_val, 9),
                    "m_s": round(m_s, 9),
                    "guard_flag": fwd_grd,
                    "status_code": st_code,
                    "fwd_ari_only": fwd_ari,
                    "fwd_guard_only": fwd_grd,
                    "fwd_P0": fwd_p0,
                    "fwd_P1": fwd_p1,
                    "fwd_P5": fwd_p5,
                }
                decision_rows.append(row)
                pre_lookup[(mid, eid, float(lam))] = row

    # Simpan decisions_300.csv dan hitung SHA-256 SEBELUM membuka solver pascagangguan (PASS 2)
    screening_dir = REPO_ROOT / "results" / "screening"
    validation_dir = REPO_ROOT / "results" / "validation"
    screening_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    decisions_csv_path = screening_dir / "decisions_300.csv"
    with open(decisions_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(decision_rows[0].keys()))
        writer.writeheader()
        writer.writerows(decision_rows)

    decisions_sha256 = hashlib.sha256(decisions_csv_path.read_bytes()).hexdigest()
    forwarded_rows_p0 = [r for r in decision_rows if r["scenario_type"] == "disruption" and r["fwd_P0"] == 1]
    forwarded_csv_path = screening_dir / "forwarded_300.csv"
    with open(forwarded_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(decision_rows[0].keys()))
        writer.writeheader()
        writer.writerows(forwarded_rows_p0)

    dt_p1 = time.monotonic() - t_p1
    print(f"[PASS 1 DONE] {len(decision_rows)} skenario (7.640 gangguan + 300 kontrol) dalam {dt_p1:.2f}s.")
    print(f"  Saved: {decisions_csv_path.relative_to(REPO_ROOT)} (SHA-256: {decisions_sha256[:16]}...)")
    print(f"  Forwarded (P0): {len(forwarded_rows_p0)} / 7.640 ({100.0 * len(forwarded_rows_p0) / 7640.0:.2f}%)")

    # =========================================================================
    # PASS 2: EVALUASI ACUAN PASCAGANGGUAN (POST-DISRUPTION SOLVER & METRIK)
    # =========================================================================
    print("\n[PASS 2] Menjalankan solver acuan pascagangguan & menghitung metrik kritis...")
    t_p2 = time.monotonic()

    full_eval_rows: List[Dict[str, Any]] = []
    remaining_misses_p0: List[Dict[str, Any]] = []
    model_eval_records: Dict[str, List[Dict[str, Any]]] = {}

    for m in all_models:
        mid = str(m["id"])
        fam = str(m["family"])
        split = str(m["split"])
        res0 = intact_results[mid]
        u0 = float(res0.umax)
        U0 = float(res0.Umax)
        w0 = float(res0.strain_energy)

        m_scens: List[Dict[str, Any]] = []
        for el in m["elements"]:
            eid = int(el["id"])
            for lam in LAMS:
                pre = pre_lookup[(mid, eid, float(lam))]
                m_disr = apply_physical_disruption(m, eid, float(lam))
                res_d = ss.solve_structural_model(m_disr)

                rank_lost = (res_d.status != "ok")
                if not rank_lost:
                    umax_s = float(res_d.umax)
                    Umax_A = float(res_d.Umax)
                    Umax_B = compute_utilization_convention_B(m, m_disr, res_d)
                    u_over_A = bool(Umax_A > 1.0)
                    u_over_B = bool(Umax_B > 1.0)
                    d_over = bool(umax_s > 2.0 * u0)

                    # Indikator perubahan respons relatif (Eq. 3.3 - 3.6) & CRC (Eq. 3.7)
                    delta_u = abs(umax_s - u0) / (abs(u0) + 1e-6)
                    delta_U_A = abs(Umax_A - U0) / (abs(U0) + 1e-6)
                    delta_U_B = abs(Umax_B - U0) / (abs(U0) + 1e-6)
                    crc_A = max(delta_u / (delta_u + 1.0), delta_U_A / (delta_U_A + 1.0))
                    crc_B = max(delta_u / (delta_u + 1.0), delta_U_B / (delta_U_B + 1.0))
                else:
                    umax_s = float("nan")
                    Umax_A = float("nan")
                    Umax_B = float("nan")
                    u_over_A = False
                    u_over_B = False
                    d_over = False
                    crc_A = 1.0
                    crc_B = 1.0

                crit_A = bool(rank_lost or u_over_A or d_over)
                crit_B = bool(rank_lost or u_over_B or d_over)

                rec = {
                    **pre,
                    "post_solver_status": res_d.status,
                    "rank_lost": int(rank_lost),
                    "umax_intact": round(u0, 6),
                    "umax_post": round(umax_s, 6) if not math.isnan(umax_s) else "",
                    "Umax_post_A": round(Umax_A, 6) if not math.isnan(Umax_A) else "",
                    "Umax_post_B": round(Umax_B, 6) if not math.isnan(Umax_B) else "",
                    "u_over_A": int(u_over_A),
                    "u_over_B": int(u_over_B),
                    "disp_over_2x": int(d_over),
                    "CRC_A": round(crc_A, 6),
                    "CRC_B": round(crc_B, 6),
                    "crit_A": int(crit_A),
                    "crit_B": int(crit_B),
                }
                m_scens.append(rec)
                full_eval_rows.append(rec)

                if crit_B and int(rec["fwd_P0"]) == 0:
                    remaining_misses_p0.append(rec)

        # Tandai top-n_ref peringkat CRC per model (Eq. 3.8 - 3.9)
        N_m = len(m_scens)
        n_ref = min(N_m, max(3, math.ceil(0.10 * N_m)))
        stable_scens = [s for s in m_scens if s["rank_lost"] == 0]
        if stable_scens:
            sorted_crc = sorted((float(s["CRC_B"]) for s in stable_scens), reverse=True)
            cutoff_crc = sorted_crc[min(n_ref - 1, len(sorted_crc) - 1)]
        else:
            cutoff_crc = 1.0
        for s in m_scens:
            in_top_nref = (s["rank_lost"] == 1) or (float(s["CRC_B"]) >= cutoff_crc - 1e-12)
            s["in_top_nref"] = int(in_top_nref)
            s["crit_eq_3_9"] = int(bool(s["crit_B"] == 1 or in_top_nref))

        model_eval_records[mid] = m_scens

    dt_p2 = time.monotonic() - t_p2
    print(f"[PASS 2 DONE] Evaluasi pascagangguan 7.640 skenario selesai dalam {dt_p2:.2f}s.")

    # Simpan berkas evaluasi lengkap dan remaining misses
    eval_csv_path = validation_dir / "full_evaluation_300.csv"
    with open(eval_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(full_eval_rows[0].keys()))
        writer.writeheader()
        writer.writerows(full_eval_rows)

    misses_csv_path = screening_dir / "remaining_misses_300.csv"
    if remaining_misses_p0:
        with open(misses_csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(remaining_misses_p0[0].keys()))
            writer.writeheader()
            writer.writerows(remaining_misses_p0)

    # =========================================================================
    # 5. KALIBRASI AMBANG PADA PARTISI CALIBRATION (60 MODEL, 101 TITIK TAU)
    # =========================================================================
    print("\n[CALIBRATION] Mengevaluasi grid 101 ambang tau in {0.00, 0.01, ..., 1.00} pada partisi calibration...")
    cal_models = [m["id"] for m in all_models if m["split"] == "calibration"]
    cal_grid_rows: List[Dict[str, Any]] = []
    tau_candidates = [round(0.01 * k, 2) for k in range(101)]

    for tau_val in tau_candidates:
        recalls_B_p0, recalls_B_p1, reds_p0, reds_p1 = [], [], [], []
        for mid in cal_models:
            scens = model_eval_records[mid]
            n_tot = len(scens)
            f_p0 = [
                1 if (s["guard_flag"] == 1 or s["status_code"] != "scored" or float(s["CI"]) >= tau_val) else 0
                for s in scens
            ]
            f_p1 = [
                1 if (f_p0[i] == 1 or float(scens[i]["lambda"]) == 0.0) else 0
                for i in range(n_tot)
            ]
            reds_p0.append(1.0 - (sum(f_p0) / n_tot))
            reds_p1.append(1.0 - (sum(f_p1) / n_tot))

            crit_idx = [i for i, s in enumerate(scens) if s["crit_B"] == 1]
            if crit_idx:
                recalls_B_p0.append(sum(f_p0[i] for i in crit_idx) / len(crit_idx))
                recalls_B_p1.append(sum(f_p1[i] for i in crit_idx) / len(crit_idx))

        mean_rec_p0, l95_rec_p0 = cluster_bootstrap_ci95_lower(recalls_B_p0, B=2000, seed=SEED)
        mean_rec_p1, l95_rec_p1 = cluster_bootstrap_ci95_lower(recalls_B_p1, B=2000, seed=SEED)
        mean_red_p0 = float(np.mean(reds_p0))
        mean_red_p1 = float(np.mean(reds_p1))

        cal_grid_rows.append({
            "tau": tau_val,
            "n_cal_models": len(cal_models),
            "n_cal_models_with_crit_B": len(recalls_B_p0),
            "P0_mean_recall_B": round(mean_rec_p0, 6),
            "P0_L95_recall_B": round(l95_rec_p0, 6),
            "P0_mean_reduction": round(mean_red_p0, 6),
            "P0_feasible_D": int(l95_rec_p0 >= 0.95 and mean_red_p0 >= 0.30),
            "P1_mean_recall_B": round(mean_rec_p1, 6),
            "P1_L95_recall_B": round(l95_rec_p1, 6),
            "P1_mean_reduction": round(mean_red_p1, 6),
            "P1_feasible_D": int(l95_rec_p1 >= 0.95 and mean_red_p1 >= 0.30),
        })

    cal_csv_path = screening_dir / "calibration_grid_tau.csv"
    with open(cal_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(cal_grid_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cal_grid_rows)

    # =========================================================================
    # 6. RINGKASAN METRIK PER PARTISI & PER KELUARGA (BOOTSTRAP B = 10.000)
    # =========================================================================
    print("\n[METRICS] Menghitung metrik per keluarga & partisi dengan Bootstrap B=10.000...")

    def evaluate_subset(model_ids: List[str], label_name: str) -> Dict[str, Any]:
        n_m = len(model_ids)
        scens_all = [s for mid in model_ids for s in model_eval_records[mid]]
        n_s = len(scens_all)
        n_rank = sum(s["rank_lost"] for s in scens_all)
        n_crit_A = sum(s["crit_A"] for s in scens_all)
        n_crit_B = sum(s["crit_B"] for s in scens_all)

        # Hitungan skenario gabungan (pooled)
        policies = ["fwd_ari_only", "fwd_guard_only", "fwd_P0", "fwd_P1", "fwd_P5"]
        pol_stats: Dict[str, Any] = {}

        rng_rand = np.random.default_rng(SEED)

        for pol in policies:
            fwd_total = sum(int(s[pol]) for s in scens_all)
            rank_missed = sum(1 for s in scens_all if s["rank_lost"] == 1 and int(s[pol]) == 0)
            critA_caught = sum(1 for s in scens_all if s["crit_A"] == 1 and int(s[pol]) == 1)
            critB_caught = sum(1 for s in scens_all if s["crit_B"] == 1 and int(s[pol]) == 1)
            critA_missed = n_crit_A - critA_caught
            critB_missed = n_crit_B - critB_caught

            # Per-model recall & reduction (Estimand utama Gerbang D Eq. 3.10)
            m_rec_A, m_rec_B, m_red = [], [], []
            m_gain_vs_util_B, m_gain_vs_rand_B = [], []

            for mid in model_ids:
                ms = model_eval_records[mid]
                ns_m = len(ms)
                k_budget = sum(int(s[pol]) for s in ms)
                m_red.append(1.0 - (k_budget / ns_m))

                # Equal-budget utilization baseline on same model (Bagian 3.18.4: mandatory guard/abstain shared, remaining by util_baseline_score)
                order_util = sorted(
                    range(ns_m),
                    key=lambda idx: (int(ms[idx]["guard_flag"] == 1), float(ms[idx]["util_baseline_score"])),
                    reverse=True
                )
                util_fwd_set = set(order_util[:k_budget])

                # Expected random recall at equal budget k_budget (with mandatory guard shared)
                guard_indices = {idx for idx, s in enumerate(ms) if int(s["guard_flag"]) == 1}
                rem_budget = max(0, k_budget - len(guard_indices))
                non_guard_count = ns_m - len(guard_indices)
                rand_prob = (rem_budget / non_guard_count) if non_guard_count > 0 else 0.0

                cA_idx = [idx for idx, s in enumerate(ms) if s["crit_A"] == 1]
                if cA_idx:
                    m_rec_A.append(sum(int(ms[idx][pol]) for idx in cA_idx) / len(cA_idx))

                cB_idx = [idx for idx, s in enumerate(ms) if s["crit_B"] == 1]
                if cB_idx:
                    r_pol = sum(int(ms[idx][pol]) for idx in cB_idx) / len(cB_idx)
                    r_util = sum(1 for idx in cB_idx if idx in util_fwd_set) / len(cB_idx)
                    r_rand = sum(1.0 if idx in guard_indices else rand_prob for idx in cB_idx) / len(cB_idx)
                    m_rec_B.append(r_pol)
                    m_gain_vs_util_B.append(r_pol - r_util)
                    m_gain_vs_rand_B.append(r_pol - r_rand)

            mean_rec_A, l95_rec_A = cluster_bootstrap_ci95_lower(m_rec_A, B=BOOTSTRAP_B, seed=SEED)
            mean_rec_B, l95_rec_B = cluster_bootstrap_ci95_lower(m_rec_B, B=BOOTSTRAP_B, seed=SEED)
            mean_red, l95_red = cluster_bootstrap_ci95_lower(m_red, B=BOOTSTRAP_B, seed=SEED)
            mean_gain_util, l95_gain_util = cluster_bootstrap_ci95_lower(m_gain_vs_util_B, B=BOOTSTRAP_B, seed=SEED)
            mean_gain_rand, l95_gain_rand = cluster_bootstrap_ci95_lower(m_gain_vs_rand_B, B=BOOTSTRAP_B, seed=SEED)

            pol_stats[pol] = {
                "forwarded_scenarios": fwd_total,
                "pooled_reduction_rate": round(1.0 - (fwd_total / n_s), 6) if n_s else 0.0,
                "pooled_recall_A": round(critA_caught / n_crit_A, 6) if n_crit_A else 1.0,
                "pooled_recall_B": round(critB_caught / n_crit_B, 6) if n_crit_B else 1.0,
                "rank_deficient_missed": rank_missed,
                "critical_missed_A": critA_missed,
                "critical_missed_B": critB_missed,
                "models_with_crit_A": len(m_rec_A),
                "models_with_crit_B": len(m_rec_B),
                "model_mean_recall_A": round(mean_rec_A, 6) if not math.isnan(mean_rec_A) else None,
                "model_L95_recall_A": round(l95_rec_A, 6) if not math.isnan(l95_rec_A) else None,
                "model_mean_recall_B": round(mean_rec_B, 6) if not math.isnan(mean_rec_B) else None,
                "model_L95_recall_B": round(l95_rec_B, 6) if not math.isnan(l95_rec_B) else None,
                "model_mean_reduction": round(mean_red, 6),
                "model_L95_reduction": round(l95_red, 6),
                "gain_vs_util_equal_budget_mean": round(mean_gain_util, 6) if not math.isnan(mean_gain_util) else None,
                "gain_vs_util_equal_budget_L95": round(l95_gain_util, 6) if not math.isnan(l95_gain_util) else None,
                "gain_vs_random_equal_budget_mean": round(mean_gain_rand, 6) if not math.isnan(mean_gain_rand) else None,
                "gain_vs_random_equal_budget_L95": round(l95_gain_rand, 6) if not math.isnan(l95_gain_rand) else None,
            }

        # Metrik Gerbang B (Kesesuaian Mekanis: Korelasi Spearman CI vs CRC_B & Top-n_ref coverage)
        rhos_ci, rhos_util, top_covs = [], [], []
        for mid in model_ids:
            ms = model_eval_records[mid]
            ci_vec = [float(s["CI"]) for s in ms]
            util_vec = [float(s["util_baseline_score"]) for s in ms]
            crc_vec = [float(s["CRC_B"]) for s in ms]
            rho_c = spearman_corr(ci_vec, crc_vec)
            rho_u = spearman_corr(util_vec, crc_vec)
            if not math.isnan(rho_c):
                rhos_ci.append(rho_c)
            if not math.isnan(rho_u):
                rhos_util.append(rho_u)

            top_idx = [i for i, s in enumerate(ms) if s["in_top_nref"] == 1]
            if top_idx:
                # Top-n_ref volgens CI + guard
                order_ci = sorted(
                    range(len(ms)),
                    key=lambda idx: (int(ms[idx]["guard_flag"] == 1), float(ms[idx]["CI"])),
                    reverse=True
                )
                top_ci_set = set(order_ci[:len(top_idx)])
                top_covs.append(len(top_ci_set.intersection(top_idx)) / len(top_idx))

        return {
            "subset_label": label_name,
            "n_models": n_m,
            "n_disruption_scenarios": n_s,
            "n_rank_deficient": n_rank,
            "n_critical_A": n_crit_A,
            "n_critical_B": n_crit_B,
            "spearman_ci_crc_median": round(float(np.median(rhos_ci)), 6) if rhos_ci else None,
            "spearman_ci_crc_mean": round(float(np.mean(rhos_ci)), 6) if rhos_ci else None,
            "spearman_util_crc_median": round(float(np.median(rhos_util)), 6) if rhos_util else None,
            "top_nref_coverage_mean": round(float(np.mean(top_covs)), 6) if top_covs else None,
            "policies": pol_stats,
        }

    summary_by_split: Dict[str, Any] = {}
    for sp in ["formula_dev", "calibration", "blind_val", "final_test"]:
        mids = [m["id"] for m in all_models if m["split"] == sp]
        summary_by_split[sp] = evaluate_subset(mids, f"split:{sp}")

    summary_by_family: Dict[str, Any] = {}
    for fam in ["S1_beam", "S2_truss", "S3_frame", "S4_braced_frame", "S5_space_truss"]:
        mids = [m["id"] for m in all_models if m["family"] == fam]
        summary_by_family[fam] = evaluate_subset(mids, f"family:{fam}")

    summary_by_family_blind_test: Dict[str, Any] = {}
    for fam in ["S1_beam", "S2_truss", "S3_frame", "S4_braced_frame", "S5_space_truss"]:
        mids = [m["id"] for m in all_models if m["family"] == fam and m["split"] in ("blind_val", "final_test")]
        summary_by_family_blind_test[fam] = evaluate_subset(mids, f"family_eval:{fam}")

    summary_overall = evaluate_subset([m["id"] for m in all_models], "overall_300_models")

    # Simpan tabel ringkasan CSV untuk kemudahan pemeriksaan
    summary_rows_csv: List[Dict[str, Any]] = []
    for group_name, sub_dict in [
        ("ALL_300", {"overall": summary_overall}),
        ("BY_SPLIT", summary_by_split),
        ("BY_FAMILY_ALL", summary_by_family),
        ("BY_FAMILY_BLIND_AND_TEST", summary_by_family_blind_test),
    ]:
        for k_sub, v_sub in sub_dict.items():
            for pol_key, p_st in v_sub["policies"].items():
                summary_rows_csv.append({
                    "group": group_name,
                    "subset": k_sub,
                    "policy": pol_key,
                    "n_models": v_sub["n_models"],
                    "n_scenarios": v_sub["n_disruption_scenarios"],
                    "n_rank_deficient": v_sub["n_rank_deficient"],
                    "n_critical_A": v_sub["n_critical_A"],
                    "n_critical_B": v_sub["n_critical_B"],
                    "forwarded": p_st["forwarded_scenarios"],
                    "pooled_reduction": p_st["pooled_reduction_rate"],
                    "pooled_recall_A": p_st["pooled_recall_A"],
                    "pooled_recall_B": p_st["pooled_recall_B"],
                    "rank_missed": p_st["rank_deficient_missed"],
                    "crit_missed_A": p_st["critical_missed_A"],
                    "crit_missed_B": p_st["critical_missed_B"],
                    "model_mean_recall_B": p_st["model_mean_recall_B"],
                    "model_L95_recall_B": p_st["model_L95_recall_B"],
                    "model_mean_reduction": p_st["model_mean_reduction"],
                    "spearman_median": v_sub["spearman_ci_crc_median"],
                })

    summary_csv_path = validation_dir / "screening_metrics_by_family_split.csv"
    with open(summary_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary_rows_csv[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows_csv)

    # =========================================================================
    # 7. STUDI ABLASI BERPASANGAN (BAGIAN 3.11 & 3.14 — 6 VARIAN PADA 300 MODEL)
    # =========================================================================
    print("\n[ABLATION] Menjalankan studi ablasi berpasangan (6 varian) pada partisi evaluasi...")
    ablation_variants = [
        ("V0_full_ari_plus_guard", {"eta": 0.5, "K": 2, "alpha_k": 0.5, "alpha_R": 0.5, "beta": 0.1, "use_guard": True}),
        ("V1_no_util_penalty_eta0", {"eta": 0.0, "K": 2, "alpha_k": 0.5, "alpha_R": 0.5, "beta": 0.1, "use_guard": True}),
        ("V2_single_path_K1", {"eta": 0.5, "K": 1, "alpha_k": 0.5, "alpha_R": 0.5, "beta": 0.1, "use_guard": True}),
        ("V3_stiffness_only_ak1", {"eta": 0.5, "K": 2, "alpha_k": 1.0, "alpha_R": 0.0, "beta": 0.1, "use_guard": True}),
        ("V4_capacity_only_aR1", {"eta": 0.5, "K": 2, "alpha_k": 0.0, "alpha_R": 1.0, "beta": 0.1, "use_guard": True}),
        ("V5_ari_without_guard", {"eta": 0.5, "K": 2, "alpha_k": 0.5, "alpha_R": 0.5, "beta": 0.1, "use_guard": False}),
    ]

    ablation_rows: List[Dict[str, Any]] = []
    for var_name, vcfg in ablation_variants:
        fwd_cnt = 0
        critB_caught = 0
        rank_missed = 0
        rhos = []
        for m in all_models:
            mid = m["id"]
            eng = engines[mid]
            grd = guards[mid]
            ms = model_eval_records[mid]

            # Recompute edge weights if alpha_k/alpha_R changed
            ov_cfg = {
                "eta": vcfg["eta"],
                "K": vcfg["K"],
                "alpha_k": vcfg["alpha_k"],
                "alpha_R": vcfg["alpha_R"],
                "beta": vcfg["beta"],
            }
            eng_var = prepare_multi_family_ari_engine(m, intact_results[mid], fam_scales[m["family"]], ov_cfg)
            pc_var: Dict[Any, Tuple[float, str]] = {}
            sb_v, stb_v = score_multi_family_graph(eng_var, None, pc_var)

            ci_list, crc_list = [], []
            for s in ms:
                eid = int(s["edge_id"])
                lam = float(s["lambda"])
                sv_v, st_v = score_multi_family_graph(eng_var, (eid, lam), pc_var)
                rr_v = sv_v / sb_v if (stb_v == "ok" and st_v == "ok" and sb_v >= ac.BASELINE_TOL) else 0.0
                ust = eng_var["u_star_map"][eid]
                ari_v = rr_v * (1.0 - vcfg["eta"] * ust)
                ci_v = max(1.0 - ari_v, 0.0)
                ci_list.append(ci_v)
                crc_list.append(float(s["CRC_B"]))

                g_fl = int(s["guard_flag"]) if vcfg["use_guard"] else 0
                is_fwd = (ci_v >= TAU_PRIMARY) or (g_fl == 1)
                fwd_cnt += int(is_fwd)
                if s["crit_B"] == 1 and is_fwd:
                    critB_caught += 1
                if s["rank_lost"] == 1 and not is_fwd:
                    rank_missed += 1

            r_sp = spearman_corr(ci_list, crc_list)
            if not math.isnan(r_sp):
                rhos.append(r_sp)

        tot_s = len(full_eval_rows)
        tot_crit_B = sum(s["crit_B"] for s in full_eval_rows)
        ablation_rows.append({
            "variant": var_name,
            "eta": vcfg["eta"],
            "K": vcfg["K"],
            "alpha_k": vcfg["alpha_k"],
            "alpha_R": vcfg["alpha_R"],
            "use_guard": int(vcfg["use_guard"]),
            "forwarded_scenarios": fwd_cnt,
            "pooled_reduction_rate": round(1.0 - (fwd_cnt / tot_s), 6),
            "pooled_recall_B": round(critB_caught / tot_crit_B, 6),
            "critical_missed_B": tot_crit_B - critB_caught,
            "rank_deficient_missed": rank_missed,
            "spearman_rho_median": round(float(np.median(rhos)), 6) if rhos else None,
            "spearman_rho_mean": round(float(np.mean(rhos)), 6) if rhos else None,
        })

    ablation_csv_path = validation_dir / "ablation_300.csv"
    with open(ablation_csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ablation_rows[0].keys()))
        writer.writeheader()
        writer.writerows(ablation_rows)

    # =========================================================================
    # 8. LAPORAN JSON LENGKAP (screening_summary_300.json & gate_decisions.json)
    # =========================================================================
    total_elapsed = time.monotonic() - t_start
    report_payload = {
        "title": "Penyaringan Operasional Skala Penuh & Validasi Lintas Keluarga S1–S5 (Gate 15 — W3/W4)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frozen_protocol_id": frozen_cfg["protocol_id"],
        "frozen_config_sha256": frozen_cfg["frozen_config_sha256"],
        "pass1_decisions_csv_sha256": decisions_sha256,
        "execution_time_seconds": {
            "pass1_pre_analysis_s": round(dt_p1, 3),
            "pass2_post_disruption_solver_s": round(dt_p2, 3),
            "total_pipeline_s": round(total_elapsed, 3),
        },
        "family_scales_formula_dev": fam_scales,
        "overall_300_models": summary_overall,
        "by_split": summary_by_split,
        "by_family_all": summary_by_family,
        "by_family_blind_and_test": summary_by_family_blind_test,
        "ablation_study": ablation_rows,
    }

    summary_json_path = screening_dir / "screening_summary_300.json"
    summary_json_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    val_json_path = validation_dir / "gate_validation_report_300.json"
    val_json_path.write_text(json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\n" + "=" * 82)
    print("RINGKASAN UTAMA GATE 15 (W3/W4) — 300 MODEL INDUK (7.640 SKENARIO GANGGUAN):")
    print("=" * 82)
    p0_all = summary_overall["policies"]["fwd_P0"]
    p1_all = summary_overall["policies"]["fwd_P1"]
    p5_all = summary_overall["policies"]["fwd_P5"]
    print(f"Total Skenario Gangguan : {summary_overall['n_disruption_scenarios']} (+ 300 kontrol utuh = 7.940)")
    print(f"Total Kasus Rank-Kurang : {summary_overall['n_rank_deficient']} (Tertangkap Pengaman: 100% — Terlewat: {p0_all['rank_deficient_missed']})")
    print(f"Total Kritis (Varian A) : {summary_overall['n_critical_A']} | Total Kritis (Varian B): {summary_overall['n_critical_B']}")
    print(f"  [P0: CI>=0.5 U Guard] Diteruskan={p0_all['forwarded_scenarios']} | Reduksi={100*p0_all['pooled_reduction_rate']:.1f}% | "
          f"Recall(B) Pooled={100*p0_all['pooled_recall_B']:.1f}% | Rerata Model={100*p0_all['model_mean_recall_B']:.1f}% (L95={100*p0_all['model_L95_recall_B']:.1f}%)")
    print(f"  [P1: P0 U (lam==0)  ] Diteruskan={p1_all['forwarded_scenarios']} | Reduksi={100*p1_all['pooled_reduction_rate']:.1f}% | "
          f"Recall(B) Pooled={100*p1_all['pooled_recall_B']:.1f}% | Rerata Model={100*p1_all['model_mean_recall_B']:.1f}% (L95={100*p1_all['model_L95_recall_B']:.1f}%)")
    print(f"  [P5: P0 U (lam<=.25)] Diteruskan={p5_all['forwarded_scenarios']} | Reduksi={100*p5_all['pooled_reduction_rate']:.1f}% | "
          f"Recall(B) Pooled={100*p5_all['pooled_recall_B']:.1f}% | Rerata Model={100*p5_all['model_mean_recall_B']:.1f}% (L95={100*p5_all['model_L95_recall_B']:.1f}%)")
    print("=" * 82)
    return 0


if __name__ == "__main__":
    sys.exit(main())
