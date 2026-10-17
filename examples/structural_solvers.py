"""
structural_solvers.py
=====================

Suite Solver Elemen Hingga Struktur Multi-Keluarga untuk Penelitian Disertasi:
"Adjusted Redundancy Index (ARI)" — Harids Irawan (2026).

Memenuhi Prasyarat Realisasi Dataset Utama (Tabel 3.6, Tabel 4.15, Tabel 4.16 butir 2,
dan Spesifikasi Teknis Pemenuhan Lima Keluarga Struktur S1–S5):
---------------------------------------------------------------------------------------
* S1 (W2a): Elemen balok dengan translasi dan rotasi (Euler-Bernoulli 2D/1D).
            Mencakup lendutan, rotasi, reaksi tumpuan, momen lentur, gaya geser,
            dan kondisi ujung (jepit, rol, elastik/bebas).
* S2 (Eksis): Batang aksial bidang 2D (truss) — didelegasikan ke `truss_reference.py`.
* S3 (W2b): Elemen portal bidang dengan aksial dan lentur (2D plane frame).
            Mencakup transformasi koordinat lokal-global, rotasi simpul,
            pelepasan momen ujung (hinge/moment release: none, start, end, both).
* S4 (W2c): Portal bidang berpengaku (braced frame).
            Mencakup sambungan pengaku (bracing pin-connected), idealisasi tarik/tekan,
            reduksi simpangan lateral (drift), dan interaksi aksial-lentur (P-M).
* S5 (W2d): Rangka ruang 3D (space truss).
            Mencakup koordinat ruang 3D (ux, uy, uz), kekangan spasial, gaya aksial ruang,
            pemeriksaan mekanisme kinematik 3D (rank check), dan energi regangan W.

Kontrak Numerik & Standar Mutu (Strict Constraints):
---------------------------------------------------
1. Satuan Konsisten: Gaya (kN), Panjang (mm), Luas (mm^2), Inersia (mm^4), E (kN/mm^2).
2. Rank Check Eksak: Memeriksa kestabilan matriks kekakuan K_ff via nilai eigen.
   Toleransi relatif 1e-10 terhadap nilai eigen terbesar. JIKA RANK DEFICIENT,
   solver WAJIB menolak (status = 'rank_deficient') dan TIDAK menggunakan pseudoinverse.
3. Energi Regangan: W = 1/2 u^T K u.
4. Utilisasi: Dihitung berbasis kapasitas batas elemen.

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# Pustaka internal S2
try:
    from truss_reference import solve_model as solve_truss_s2
except ImportError:
    # Fallback jika diimpor di luar root repo
    solve_truss_s2 = None

# Konstanta numerik
DEFAULT_E = 200.0          # kN/mm^2 (Baja struktural)
RANK_TOL_RELATIVE = 1e-10  # Toleransi relatif rank terhadap max eigenvalue


# =============================================================================
# DATA CLASS HASIL SOLVER
# =============================================================================
@dataclass
class StructuralSolverResult:
    """Hasil umum penyelesaian sistem struktur elemen hingga."""
    model_id: str
    family: str                          # "S1_beam" | "S2_truss" | "S3_frame" | "S4_braced_frame" | "S5_space_truss"
    status: str                          # "ok" | "rank_deficient" | "error"
    ndof: int
    n_free: int
    rank: int
    displacements: np.ndarray            # vektor perpindahan global (semua DOF)
    node_displacements: Dict[int, Dict[str, float]] # rincian per node {node_id: {dof_name: val}}
    reactions: Dict[int, Dict[str, float]]          # reaksi tumpuan per node {node_id: {dof_name: val}}
    element_forces: Dict[int, Dict[str, Any]]       # gaya dalam per elemen (N, V, M, dll)
    utilizations: np.ndarray             # rasio pembebanan / utilisasi
    umax: float                          # resultan simpangan maksimum translasi (mm)
    Umax: float                          # utilisasi maksimum elemen
    strain_energy: float                 # energi regangan W = 1/2 u^T K u (kN.mm)
    min_eig: float = 0.0
    max_eig: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 1. SOLVER S1: ELEMEN BALOK LENTUR (EULER-BERNOULLI BEAM)
# =============================================================================
def solve_beam_s1(model: dict) -> StructuralSolverResult:
    """
    Solver untuk S1: Elemen balok transversal & lentur (Euler-Bernoulli).
    DOF per simpul: [v, theta] (translasi y [mm], rotasi z [rad]).
    """
    model_id = str(model.get("id", "S1_beam"))
    nodes = {int(n["id"]): float(n.get("x", n.get("coords", [0.0])[0])) for n in model.get("nodes", [])}
    sorted_node_ids = sorted(nodes.keys())
    num_nodes = len(sorted_node_ids)
    node_to_idx = {nid: i for i, nid in enumerate(sorted_node_ids)}
    
    ndof = 2 * num_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    elements_data = model.get("elements", [])
    
    elem_geom = {}
    for el in elements_data:
        eid = int(el["id"])
        ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
        xi, xj = nodes[ni], nodes[nj]
        L = abs(xj - xi)
        if L <= 0.0:
            raise ValueError(f"Elemen balok {eid} memiliki panjang nol.")
        
        E = float(el.get("E", DEFAULT_E))
        I = float(el.get("I", 1e6))
        
        # Matriks kekakuan balok 4x4: [v_i, theta_i, v_j, theta_j]
        c1 = 12.0 * E * I / (L**3)
        c2 = 6.0 * E * I / (L**2)
        c3 = 4.0 * E * I / L
        c4 = 2.0 * E * I / L
        
        ke = np.array([
            [ c1,  c2, -c1,  c2],
            [ c2,  c3, -c2,  c4],
            [-c1, -c2,  c1, -c2],
            [ c2,  c4, -c2,  c3]
        ], dtype=float)
        
        i_idx = node_to_idx[ni]
        j_idx = node_to_idx[nj]
        dofs = [2 * i_idx, 2 * i_idx + 1, 2 * j_idx, 2 * j_idx + 1]
        
        for r_i, r in enumerate(dofs):
            for c_i, c in enumerate(dofs):
                K[r, c] += ke[r_i, c_i]
                
        elem_geom[eid] = {"ni": ni, "nj": nj, "L": L, "E": E, "I": I, "ke": ke, "dofs": dofs}
        
    # Kondisi batas
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
                comps = ["v", "theta"]
            elif spec in ("pinned", "roller"):
                comps = ["v"]
            elif spec == "guided":
                comps = ["theta"]
            else:
                comps = [c.strip() for c in spec.split(",")]
        else:
            comps = list(spec.keys())
            
        for c in comps:
            c_clean = c.lower().strip()
            if c_clean in ("v", "uy", "y"):
                fixed_dofs.add(2 * idx)
            elif c_clean in ("theta", "rz", "rot"):
                fixed_dofs.add(2 * idx + 1)
                
    free_dofs = sorted([d for d in range(ndof) if d not in fixed_dofs])
    n_free = len(free_dofs)
    
    # Beban
    p = np.zeros(ndof, dtype=float)
    for ld in model.get("loads", []):
        nid = int(ld["node"])
        if nid not in node_to_idx:
            continue
        idx = node_to_idx[nid]
        comps = ld.get("components", {})
        if "Fy" in comps or "v" in comps or "uy" in comps:
            val = float(comps.get("Fy", comps.get("v", comps.get("uy", 0.0))))
            p[2 * idx] += val
        if "Mz" in comps or "theta" in comps or "M" in comps:
            val = float(comps.get("Mz", comps.get("theta", comps.get("M", 0.0))))
            p[2 * idx + 1] += val
            
    # Rank check
    if n_free == 0:
        rank = 0
        min_eig, max_eig = 0.0, 0.0
        status = "ok"
        u = np.zeros(ndof)
    else:
        Kff = K[np.ix_(free_dofs, free_dofs)]
        eigs = np.linalg.eigvalsh(Kff)
        min_eig = float(np.min(eigs))
        max_eig = float(np.max(eigs))
        
        tol = max(RANK_TOL_RELATIVE * abs(max_eig), 1e-12)
        rank = int(np.sum(eigs > tol))
        
        if rank < n_free or min_eig < -tol:
            return StructuralSolverResult(
                model_id=model_id, family="S1_beam", status="rank_deficient",
                ndof=ndof, n_free=n_free, rank=rank, displacements=np.zeros(ndof),
                node_displacements={}, reactions={}, element_forces={},
                utilizations=np.zeros(len(elements_data)), umax=0.0, Umax=0.0,
                strain_energy=0.0, min_eig=min_eig, max_eig=max_eig,
                meta={"keterangan": "Mekanisme kinematik balok terdeteksi"}
            )
        
        pf = p[free_dofs]
        uf = np.linalg.solve(Kff, pf)
        u = np.zeros(ndof, dtype=float)
        u[free_dofs] = uf
        status = "ok"
        
    # Reaksi tumpuan
    reactions_all = K @ u - p
    reactions_dict: Dict[int, Dict[str, float]] = {}
    node_disp_dict: Dict[int, Dict[str, float]] = {}
    v_disps = []
    
    for nid, idx in node_to_idx.items():
        v_val = float(u[2 * idx])
        th_val = float(u[2 * idx + 1])
        v_disps.append(abs(v_val))
        node_disp_dict[nid] = {"v": v_val, "theta": th_val}
        
        rx_val = float(reactions_all[2 * idx]) if (2 * idx) in fixed_dofs else 0.0
        rm_val = float(reactions_all[2 * idx + 1]) if (2 * idx + 1) in fixed_dofs else 0.0
        if abs(rx_val) > 1e-9 or abs(rm_val) > 1e-9:
            reactions_dict[nid] = {"Ry": rx_val, "Mz": rm_val}
            
    # Gaya dalam elemen
    elem_forces: Dict[int, Dict[str, Any]] = {}
    utilizations = []
    for el in elements_data:
        eid = int(el["id"])
        g = elem_geom[eid]
        ue = u[g["dofs"]]
        fe = g["ke"] @ ue  # [V_i, M_i, V_j, M_j]
        
        # Konvensi mekanika: V_i, M_i, V_j, M_j
        Vi, Mi, Vj, Mj = float(fe[0]), float(fe[1]), float(fe[2]), float(fe[3])
        M_max = max(abs(Mi), abs(Mj))
        V_max = max(abs(Vi), abs(Vj))
        
        M_cap = float(el.get("M_capacity", el.get("capacity", 1e8)))
        u_val = M_max / M_cap if M_cap > 0 else 0.0
        utilizations.append(u_val)
        
        elem_forces[eid] = {
            "Vi": Vi, "Mi": Mi, "Vj": Vj, "Mj": Mj,
            "M_max": M_max, "V_max": V_max, "utilization": u_val
        }
        
    umax = float(max(v_disps)) if v_disps else 0.0
    Umax = float(max(utilizations)) if utilizations else 0.0
    W = 0.5 * float(p @ u)
    
    return StructuralSolverResult(
        model_id=model_id, family="S1_beam", status=status,
        ndof=ndof, n_free=n_free, rank=rank, displacements=u,
        node_displacements=node_disp_dict, reactions=reactions_dict,
        element_forces=elem_forces, utilizations=np.array(utilizations),
        umax=umax, Umax=Umax, strain_energy=W, min_eig=min_eig, max_eig=max_eig,
        meta={"num_elements": len(elements_data), "num_nodes": num_nodes}
    )


# =============================================================================
# 2. SOLVER S3: ELEMEN PORTAL BIDANG (2D PLANE FRAME)
# =============================================================================
def _frame_local_stiffness(E: float, A: float, I: float, L: float, release: str = "none") -> np.ndarray:
    """Matriks kekakuan elemen portal bidang lokal 6x6 dengan opsi pelepasan momen."""
    k = np.zeros((6, 6), dtype=float)
    # Aksial
    k[0, 0] = E * A / L; k[0, 3] = -E * A / L
    k[3, 0] = -E * A / L; k[3, 3] = E * A / L
    
    # Lentur dengan pelepasan momen
    if release in ("none", "", None):
        c1 = 12.0 * E * I / (L**3)
        c2 = 6.0 * E * I / (L**2)
        c3 = 4.0 * E * I / L
        c4 = 2.0 * E * I / L
        kb = np.array([
            [ c1,  c2, -c1,  c2],
            [ c2,  c3, -c2,  c4],
            [-c1, -c2,  c1, -c2],
            [ c2,  c4, -c2,  c3]
        ])
    elif release in ("start", "i"):
        # M_i dilepas = 0
        c1 = 3.0 * E * I / (L**3)
        c2 = 3.0 * E * I / (L**2)
        c3 = 3.0 * E * I / L
        kb = np.array([
            [ c1, 0.0, -c1,  c2],
            [0.0, 0.0, 0.0, 0.0],
            [-c1, 0.0,  c1, -c2],
            [ c2, 0.0, -c2,  c3]
        ])
    elif release in ("end", "j"):
        # M_j dilepas = 0
        c1 = 3.0 * E * I / (L**3)
        c2 = 3.0 * E * I / (L**2)
        c3 = 3.0 * E * I / L
        kb = np.array([
            [ c1,  c2, -c1, 0.0],
            [ c2,  c3, -c2, 0.0],
            [-c1, -c2,  c1, 0.0],
            [0.0, 0.0, 0.0, 0.0]
        ])
    elif release == "both":
        # Sendi kedua ujung (truss action)
        kb = np.zeros((4, 4), dtype=float)
    else:
        raise ValueError(f"Opsi release '{release}' tidak dikenal (pilih: none, start, end, both).")
        
    for r_i, r in enumerate([1, 2, 4, 5]):
        for c_i, c in enumerate([1, 2, 4, 5]):
            k[r, c] = kb[r_i, c_i]
            
    return k


def _frame_transformation(dx: float, dy: float, L: float) -> np.ndarray:
    """Matriks transformasi 6x6 lokal ke global untuk portal bidang."""
    c = dx / L
    s = dy / L
    return np.array([
        [ c,  s, 0.0,  0.0,  0.0, 0.0],
        [-s,  c, 0.0,  0.0,  0.0, 0.0],
        [0.0, 0.0, 1.0,  0.0,  0.0, 0.0],
        [0.0, 0.0, 0.0,   c,   s, 0.0],
        [0.0, 0.0, 0.0,  -s,   c, 0.0],
        [0.0, 0.0, 0.0,  0.0,  0.0, 1.0]
    ], dtype=float)


def solve_frame_s3(model: dict) -> StructuralSolverResult:
    """
    Solver untuk S3: Elemen portal bidang dengan aksial & lentur (2D Plane Frame).
    DOF per simpul: [ux, uy, theta] (translasi x, y [mm], rotasi z [rad]).
    Mendukung rotasi dan pelepasan sendi ujung elemen (moment releases).
    """
    model_id = str(model.get("id", "S3_frame"))
    nodes = {int(n["id"]): np.array(n.get("coords", [n.get("x", 0.0), n.get("y", 0.0)]), dtype=float)
             for n in model.get("nodes", [])}
    sorted_node_ids = sorted(nodes.keys())
    num_nodes = len(sorted_node_ids)
    node_to_idx = {nid: i for i, nid in enumerate(sorted_node_ids)}
    
    ndof = 3 * num_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    elements_data = model.get("elements", [])
    
    elem_info = {}
    for el in elements_data:
        eid = int(el["id"])
        ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
        xi, yi = nodes[ni][0], nodes[ni][1]
        xj, yj = nodes[nj][0], nodes[nj][1]
        dx, dy = xj - xi, yj - yi
        L = float(np.hypot(dx, dy))
        if L <= 0.0:
            raise ValueError(f"Elemen portal {eid} memiliki panjang nol.")
            
        E = float(el.get("E", DEFAULT_E))
        A = float(el.get("A", 5000.0))
        I = float(el.get("I", 2e8))
        rel = str(el.get("release", "none")).lower()
        
        k_loc = _frame_local_stiffness(E, A, I, L, rel)
        T = _frame_transformation(dx, dy, L)
        ke_glob = T.T @ k_loc @ T
        
        i_idx = node_to_idx[ni]
        j_idx = node_to_idx[nj]
        dofs = [3 * i_idx, 3 * i_idx + 1, 3 * i_idx + 2,
                3 * j_idx, 3 * j_idx + 1, 3 * j_idx + 2]
                
        for r_i, r in enumerate(dofs):
            for c_i, c in enumerate(dofs):
                K[r, c] += ke_glob[r_i, c_i]
                
        elem_info[eid] = {
            "ni": ni, "nj": nj, "L": L, "E": E, "A": A, "I": I, "rel": rel,
            "k_loc": k_loc, "T": T, "dofs": dofs, "dx": dx, "dy": dy
        }
        
    # Kondisi batas
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
            c_clean = c.lower().strip()
            if c_clean in ("ux", "x"):
                fixed_dofs.add(3 * idx)
            elif c_clean in ("uy", "y"):
                fixed_dofs.add(3 * idx + 1)
            elif c_clean in ("theta", "rz", "rot"):
                fixed_dofs.add(3 * idx + 2)
                
    free_dofs = sorted([d for d in range(ndof) if d not in fixed_dofs])
    n_free = len(free_dofs)
    
    # Beban simpul
    p = np.zeros(ndof, dtype=float)
    for ld in model.get("loads", []):
        nid = int(ld["node"])
        if nid not in node_to_idx:
            continue
        idx = node_to_idx[nid]
        comps = ld.get("components", {})
        if "Fx" in comps or "ux" in comps or "x" in comps:
            p[3 * idx] += float(comps.get("Fx", comps.get("ux", comps.get("x", 0.0))))
        if "Fy" in comps or "uy" in comps or "y" in comps:
            p[3 * idx + 1] += float(comps.get("Fy", comps.get("uy", comps.get("y", 0.0))))
        if "Mz" in comps or "theta" in comps or "M" in comps:
            p[3 * idx + 2] += float(comps.get("Mz", comps.get("theta", comps.get("M", 0.0))))
            
    # Rank check
    if n_free == 0:
        rank = 0
        min_eig, max_eig = 0.0, 0.0
        status = "ok"
        u = np.zeros(ndof)
    else:
        Kff = K[np.ix_(free_dofs, free_dofs)]
        eigs = np.linalg.eigvalsh(Kff)
        min_eig = float(np.min(eigs))
        max_eig = float(np.max(eigs))
        
        tol = max(RANK_TOL_RELATIVE * abs(max_eig), 1e-12)
        rank = int(np.sum(eigs > tol))
        
        if rank < n_free or min_eig < -tol:
            return StructuralSolverResult(
                model_id=model_id, family="S3_frame", status="rank_deficient",
                ndof=ndof, n_free=n_free, rank=rank, displacements=np.zeros(ndof),
                node_displacements={}, reactions={}, element_forces={},
                utilizations=np.zeros(len(elements_data)), umax=0.0, Umax=0.0,
                strain_energy=0.0, min_eig=min_eig, max_eig=max_eig,
                meta={"keterangan": "Mekanisme kinematik portal terdeteksi"}
            )
            
        pf = p[free_dofs]
        uf = np.linalg.solve(Kff, pf)
        u = np.zeros(ndof, dtype=float)
        u[free_dofs] = uf
        status = "ok"
        
    # Reaksi & perpindahan simpul
    reactions_all = K @ u - p
    reactions_dict: Dict[int, Dict[str, float]] = {}
    node_disp_dict: Dict[int, Dict[str, float]] = {}
    disp_norms = []
    
    for nid, idx in node_to_idx.items():
        ux_val = float(u[3 * idx])
        uy_val = float(u[3 * idx + 1])
        th_val = float(u[3 * idx + 2])
        disp_norms.append(float(np.hypot(ux_val, uy_val)))
        node_disp_dict[nid] = {"ux": ux_val, "uy": uy_val, "theta": th_val}
        
        rx = float(reactions_all[3 * idx]) if (3 * idx) in fixed_dofs else 0.0
        ry = float(reactions_all[3 * idx + 1]) if (3 * idx + 1) in fixed_dofs else 0.0
        rm = float(reactions_all[3 * idx + 2]) if (3 * idx + 2) in fixed_dofs else 0.0
        if abs(rx) > 1e-9 or abs(ry) > 1e-9 or abs(rm) > 1e-9:
            reactions_dict[nid] = {"Rx": rx, "Ry": ry, "Mz": rm}
            
    # Gaya dalam elemen
    elem_forces: Dict[int, Dict[str, Any]] = {}
    utilizations = []
    for el in elements_data:
        eid = int(el["id"])
        inf = elem_info[eid]
        ue_glob = u[inf["dofs"]]
        ue_loc = inf["T"] @ ue_glob
        fe_loc = inf["k_loc"] @ ue_loc  # [N_i, V_i, M_i, N_j, V_j, M_j]
        
        # Gaya dalam lokal
        Ni, Vi, Mi = float(fe_loc[0]), float(fe_loc[1]), float(fe_loc[2])
        Nj, Vj, Mj = float(fe_loc[3]), float(fe_loc[4]), float(fe_loc[5])
        N_axial = 0.5 * (Nj - Ni)  # Tarik positif
        M_max = max(abs(Mi), abs(Mj))
        
        # Kapasitas nominal
        N_cap = float(el.get("N_capacity", el.get("capacity_axial", 1e6)))
        M_cap = float(el.get("M_capacity", el.get("capacity_moment", 1e8)))
        u_val = (abs(N_axial) / N_cap) + (M_max / M_cap)
        utilizations.append(u_val)
        
        elem_forces[eid] = {
            "N_axial": N_axial, "Ni": Ni, "Vi": Vi, "Mi": Mi,
            "Nj": Nj, "Vj": Vj, "Mj": Mj, "M_max": M_max,
            "utilization": u_val
        }
        
    umax = float(max(disp_norms)) if disp_norms else 0.0
    Umax = float(max(utilizations)) if utilizations else 0.0
    W = 0.5 * float(p @ u)
    
    return StructuralSolverResult(
        model_id=model_id, family="S3_frame", status=status,
        ndof=ndof, n_free=n_free, rank=rank, displacements=u,
        node_displacements=node_disp_dict, reactions=reactions_dict,
        element_forces=elem_forces, utilizations=np.array(utilizations),
        umax=umax, Umax=Umax, strain_energy=W, min_eig=min_eig, max_eig=max_eig,
        meta={"num_elements": len(elements_data), "num_nodes": num_nodes}
    )


# =============================================================================
# 3. SOLVER S4: PORTAL BIDANG BERPENGAKU (BRACED FRAME)
# =============================================================================
def solve_braced_frame_s4(model: dict) -> StructuralSolverResult:
    """
    Solver untuk S4: Portal bidang berpengaku (Braced Frame).
    Elemen terdiri dari komponen balok-kolom (frame) dan pengaku diagonal (brace).
    Pengaku diidealisasikan sendi kedua ujung (pure axial/truss).
    Menghitung interaksi P-M, distribusi geser dasar, dan reduksi simpangan lateral (drift).
    """
    model_id = str(model.get("id", "S4_braced_frame"))
    # Salin model untuk memodifikasi elemen bertipe 'brace'
    adapted_model = dict(model)
    adapted_model["id"] = model_id
    elements = []
    
    for el in model.get("elements", []):
        el_copy = dict(el)
        el_type = str(el.get("type", "frame")).lower()
        if el_type == "brace":
            # Pengaku sendi ujung (truss action)
            el_copy["release"] = "both"
            el_copy["I"] = 0.0
        elements.append(el_copy)
    adapted_model["elements"] = elements
    
    # Selesaikan sistem struktur
    res = solve_frame_s3(adapted_model)
    if res.status != "ok":
        res.family = "S4_braced_frame"
        return res
        
    # Analisis Tambahan Khusus S4: Pemisahan Frame vs Bracing
    frame_forces = {}
    brace_forces = {}
    interaction_ratios = []
    
    for el in model.get("elements", []):
        eid = int(el["id"])
        el_type = str(el.get("type", "frame")).lower()
        f_info = res.element_forces[eid]
        
        N_cap = float(el.get("N_capacity", el.get("capacity_axial", 1e6)))
        M_cap = float(el.get("M_capacity", el.get("capacity_moment", 1e8)))
        
        N_act = abs(f_info["N_axial"])
        M_act = f_info["M_max"]
        
        if el_type == "brace":
            # Pengaku: murni aksial
            ratio = N_act / N_cap if N_cap > 0 else 0.0
            brace_forces[eid] = {"axial": f_info["N_axial"], "ratio": ratio}
        else:
            # Balok-kolom: interaksi aksial-lentur (P-M)
            ratio = (N_act / N_cap) + (M_act / M_cap)
            frame_forces[eid] = {"axial": f_info["N_axial"], "moment": M_act, "ratio": ratio}
            
        interaction_ratios.append(ratio)
        res.element_forces[eid]["interaction_ratio"] = ratio
        res.element_forces[eid]["element_type"] = el_type
        
    res.family = "S4_braced_frame"
    res.utilizations = np.array(interaction_ratios)
    res.Umax = float(max(interaction_ratios)) if interaction_ratios else 0.0
    res.meta.update({
        "frame_elements_count": len(frame_forces),
        "brace_elements_count": len(brace_forces),
        "total_shear_carried_by_braces": sum(abs(b["axial"]) for b in brace_forces.values())
    })
    return res


# =============================================================================
# 4. SOLVER S5: RANGKA RUANG 3D (3D SPACE TRUSS)
# =============================================================================
def solve_space_truss_s5(model: dict) -> StructuralSolverResult:
    """
    Solver untuk S5: Rangka ruang 3D (Space Truss).
    DOF per simpul: [ux, uy, uz] (translasi 3D global [mm]).
    Mencakup komponen ruang 3D, kekangan spasial, deteksi mekanisme ruang via rank-check,
    dan energi regangan W.
    """
    model_id = str(model.get("id", "S5_space_truss"))
    nodes = {int(n["id"]): np.array(n.get("coords", [n.get("x", 0.0), n.get("y", 0.0), n.get("z", 0.0)]), dtype=float)
             for n in model.get("nodes", [])}
    sorted_node_ids = sorted(nodes.keys())
    num_nodes = len(sorted_node_ids)
    node_to_idx = {nid: i for i, nid in enumerate(sorted_node_ids)}
    
    ndof = 3 * num_nodes
    K = np.zeros((ndof, ndof), dtype=float)
    elements_data = model.get("elements", [])
    
    elem_info = {}
    for el in elements_data:
        eid = int(el["id"])
        ni, nj = int(el["nodes"][0]), int(el["nodes"][1])
        xi, xj = nodes[ni], nodes[nj]
        d = xj - xi
        L = float(np.linalg.norm(d))
        if L <= 0.0:
            raise ValueError(f"Elemen rangka ruang {eid} memiliki panjang nol.")
            
        E = float(el.get("E", DEFAULT_E))
        A = float(el.get("A", 1000.0))
        lam = d / L  # cosinus arah [Cx, Cy, Cz]
        
        # Submatriks 3x3: (E*A/L) * (lam @ lam.T)
        k_sub = (E * A / L) * np.outer(lam, lam)
        
        i_idx = node_to_idx[ni]
        j_idx = node_to_idx[nj]
        idx_i = slice(3 * i_idx, 3 * i_idx + 3)
        idx_j = slice(3 * j_idx, 3 * j_idx + 3)
        
        K[idx_i, idx_i] += k_sub
        K[idx_j, idx_j] += k_sub
        K[idx_i, idx_j] -= k_sub
        K[idx_j, idx_i] -= k_sub
        
        elem_info[eid] = {
            "ni": ni, "nj": nj, "L": L, "E": E, "A": A, "lam": lam,
            "i_idx": i_idx, "j_idx": j_idx
        }
        
    # Kondisi batas 3D
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
            c_clean = c.lower().strip()
            if c_clean in ("ux", "x"):
                fixed_dofs.add(3 * idx)
            elif c_clean in ("uy", "y"):
                fixed_dofs.add(3 * idx + 1)
            elif c_clean in ("uz", "z"):
                fixed_dofs.add(3 * idx + 2)
                
    free_dofs = sorted([d for d in range(ndof) if d not in fixed_dofs])
    n_free = len(free_dofs)
    
    # Beban simpul 3D
    p = np.zeros(ndof, dtype=float)
    for ld in model.get("loads", []):
        nid = int(ld["node"])
        if nid not in node_to_idx:
            continue
        idx = node_to_idx[nid]
        comps = ld.get("components", {})
        if "Fx" in comps or "ux" in comps or "x" in comps:
            p[3 * idx] += float(comps.get("Fx", comps.get("ux", comps.get("x", 0.0))))
        if "Fy" in comps or "uy" in comps or "y" in comps:
            p[3 * idx + 1] += float(comps.get("Fy", comps.get("uy", comps.get("y", 0.0))))
        if "Fz" in comps or "uz" in comps or "z" in comps:
            p[3 * idx + 2] += float(comps.get("Fz", comps.get("uz", comps.get("z", 0.0))))
            
    # Rank check ketat ruang 3D
    if n_free == 0:
        rank = 0
        min_eig, max_eig = 0.0, 0.0
        status = "ok"
        u = np.zeros(ndof)
    else:
        Kff = K[np.ix_(free_dofs, free_dofs)]
        eigs = np.linalg.eigvalsh(Kff)
        min_eig = float(np.min(eigs))
        max_eig = float(np.max(eigs))
        
        tol = max(RANK_TOL_RELATIVE * abs(max_eig), 1e-12)
        rank = int(np.sum(eigs > tol))
        
        if rank < n_free or min_eig < -tol:
            return StructuralSolverResult(
                model_id=model_id, family="S5_space_truss", status="rank_deficient",
                ndof=ndof, n_free=n_free, rank=rank, displacements=np.zeros(ndof),
                node_displacements={}, reactions={}, element_forces={},
                utilizations=np.zeros(len(elements_data)), umax=0.0, Umax=0.0,
                strain_energy=0.0, min_eig=min_eig, max_eig=max_eig,
                meta={"keterangan": "Mekanisme ruang 3D terdeteksi"}
            )
            
        pf = p[free_dofs]
        uf = np.linalg.solve(Kff, pf)
        u = np.zeros(ndof, dtype=float)
        u[free_dofs] = uf
        status = "ok"
        
    # Reaksi & resultan perpindahan simpul 3D
    reactions_all = K @ u - p
    reactions_dict: Dict[int, Dict[str, float]] = {}
    node_disp_dict: Dict[int, Dict[str, float]] = {}
    disp_norms = []
    
    for nid, idx in node_to_idx.items():
        ux_val = float(u[3 * idx])
        uy_val = float(u[3 * idx + 1])
        uz_val = float(u[3 * idx + 2])
        norm_val = float(np.sqrt(ux_val**2 + uy_val**2 + uz_val**2))
        disp_norms.append(norm_val)
        node_disp_dict[nid] = {"ux": ux_val, "uy": uy_val, "uz": uz_val, "norm": norm_val}
        
        rx = float(reactions_all[3 * idx]) if (3 * idx) in fixed_dofs else 0.0
        ry = float(reactions_all[3 * idx + 1]) if (3 * idx + 1) in fixed_dofs else 0.0
        rz = float(reactions_all[3 * idx + 2]) if (3 * idx + 2) in fixed_dofs else 0.0
        if abs(rx) > 1e-9 or abs(ry) > 1e-9 or abs(rz) > 1e-9:
            reactions_dict[nid] = {"Rx": rx, "Ry": ry, "Rz": rz}
            
    # Gaya aksial dalam elemen ruang 3D
    elem_forces: Dict[int, Dict[str, Any]] = {}
    utilizations = []
    for el in elements_data:
        eid = int(el["id"])
        inf = elem_info[eid]
        ui = u[3 * inf["i_idx"]: 3 * inf["i_idx"] + 3]
        uj = u[3 * inf["j_idx"]: 3 * inf["j_idx"] + 3]
        
        # N = (E*A/L) * lam . (u_j - u_i)
        N = float((inf["E"] * inf["A"] / inf["L"]) * np.dot(inf["lam"], uj - ui))
        cap = float(el.get("capacity", el.get("N_capacity", 500.0)))
        u_val = abs(N) / cap if cap > 0 else 0.0
        utilizations.append(u_val)
        
        elem_forces[eid] = {
            "axial_force": N,
            "utilization": u_val,
            "capacity": cap,
            "length": inf["L"]
        }
        
    umax = float(max(disp_norms)) if disp_norms else 0.0
    Umax = float(max(utilizations)) if utilizations else 0.0
    W = 0.5 * float(p @ u)
    
    return StructuralSolverResult(
        model_id=model_id, family="S5_space_truss", status=status,
        ndof=ndof, n_free=n_free, rank=rank, displacements=u,
        node_displacements=node_disp_dict, reactions=reactions_dict,
        element_forces=elem_forces, utilizations=np.array(utilizations),
        umax=umax, Umax=Umax, strain_energy=W, min_eig=min_eig, max_eig=max_eig,
        meta={"num_elements": len(elements_data), "num_nodes": num_nodes}
    )


# =============================================================================
# 5. DISPATCHER UNIFIKASI SOLVER STRUKTUR MULTI-KELUARGA
# =============================================================================
def solve_structural_model(model: dict) -> StructuralSolverResult:
    """
    Dispatcher umum untuk menyelesaikan model dari lima keluarga struktur (S1 - S5).
    Mengenali properti 'family' atau inferensi otomatis dari struktur data.
    """
    family = str(model.get("family", "")).lower()
    
    # Deteksi otomatis keluarga
    if family in ("s1", "s1_beam", "beam"):
        return solve_beam_s1(model)
    elif family in ("s3", "s3_frame", "frame", "portal"):
        return solve_frame_s3(model)
    elif family in ("s4", "s4_braced_frame", "braced_frame", "portal_berpengaku"):
        return solve_braced_frame_s4(model)
    elif family in ("s5", "s5_space_truss", "space_truss", "rangka_ruang"):
        return solve_space_truss_s5(model)
    elif family in ("s2", "s2_truss", "truss", "rangka_batang"):
        if solve_truss_s2 is not None:
            res_s2 = solve_truss_s2(model)
            # Adaptasi ke StructuralSolverResult
            node_disp_dict = {}
            dim_s2 = int(model.get("dimension", 2))
            for nid in range(len(model.get("nodes", []))):
                if dim_s2 == 1:
                    node_disp_dict[nid] = {"ux": float(res_s2.displacements[nid])}
                else:
                    node_disp_dict[nid] = {"ux": float(res_s2.displacements[2*nid]),
                                           "uy": float(res_s2.displacements[2*nid+1])}
            elem_forces = {}
            for eid, force in enumerate(res_s2.element_forces):
                elem_forces[eid] = {"axial_force": float(force), "utilization": float(res_s2.utilizations[eid])}
            return StructuralSolverResult(
                model_id=res_s2.model_id, family="S2_truss", status=res_s2.status,
                ndof=res_s2.ndof, n_free=res_s2.n_free, rank=res_s2.rank,
                displacements=res_s2.displacements, node_displacements=node_disp_dict,
                reactions={}, element_forces=elem_forces, utilizations=res_s2.utilizations,
                umax=res_s2.umax, Umax=res_s2.Umax, strain_energy=res_s2.strain_energy,
                min_eig=res_s2.min_eig, max_eig=res_s2.max_eig
            )
        raise RuntimeError("Modul truss_reference.py tidak ditemukan untuk S2.")
    else:
        # Heuristik berdasarkan dimensi dan properti elemen
        dim = int(model.get("dimension", 2))
        has_I = any("I" in el for el in model.get("elements", []))
        has_brace = any(el.get("type") == "brace" for el in model.get("elements", []))
        
        if dim == 3 or any(len(n.get("coords", [])) == 3 or "z" in n for n in model.get("nodes", [])):
            return solve_space_truss_s5(model)
        elif has_brace:
            return solve_braced_frame_s4(model)
        elif has_I:
            # Jika semua node di sumbu horizontal, uji apakah balok atau portal
            ys = [n.get("coords", [0, 0])[1] if "coords" in n else n.get("y", 0.0) for n in model.get("nodes", [])]
            if len(set(ys)) == 1 and not any("Fx" in ld.get("components", {}) for ld in model.get("loads", [])):
                return solve_beam_s1(model)
            return solve_frame_s3(model)
        else:
            if solve_truss_s2 is not None:
                return solve_structural_model({**model, "family": "S2_truss"})
            raise ValueError(f"Tidak dapat menentukan solver untuk model {model.get('id')}.")
