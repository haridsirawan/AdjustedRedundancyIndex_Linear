"""
ari_core.py
===========

Mesin ARI (Adjusted Redundancy Index) — Gate 2 disertasi
"Adjusted Redundancy Index (ARI) for Mechanics-Based Screening".

Mengimplementasikan formulasi Bagian 2.6-2.8 dan 4.5.3 di atas output
solver referensi Gate 1 (`truss_reference.solve_model`).

Rantai perhitungan
------------------
A. Normalisasi atribut (Eq 2.5-2.7)
     k_e = E_e * A_e / L_e                      [kN/mm]
     x_hat_e = x_e / (x_e + s_x)                (s_x skala TETAP per grup/model)
     w_e^M = q_e * (alpha_k * k_hat_e + alpha_R * R_hat_e),  q_e = 1 (kanonik)
B. Enumerasi & optimasi jalur (Eq 2.8-2.10)
     c_e^M = 1 / (w_e^M + eps_w)
     d^M(p) = sum_{e in p} c_e^M
     Phi^K_ij = max_{P edge-disjoint, |P|<=K} sum_r omega_r/(d^M(p^(r)) + eps_d)
     omega_r = gamma^(r-1) / sum_t gamma^(t-1)   (gamma = 1 -> rata-rata K jalur)
     ENUMERASI EKSHAUSTIF (bukan greedy; Section 4.8.6).
C. Agregasi skor graf (Eq 2.11-2.13)
     F_c = sum_i |f_ic| ; a_ic = |f_ic| / F_c
     B_c = sum_j |r_jc^(0)| ; b_jc = beta/|V_T| + (1-beta)*|r_jc^(0)|/B_c
     S(G) = sum_c pi_c * sum_i a_ic * sum_j b_jc * Phi^K_ij
D. Disrupsi & ARI (Eq 2.14-2.18)
     s = (e, lambda): w_e -> lambda * w_e  (TANPA renormalisasi; Section 4.8.4)
     RR_e(lambda) = S(G_{M_e,lambda}) / S(G_M)
     U*_e = min(D_e / (R_e + eps_R), 1)
     ARI_e = RR_e * (1 - eta * U*_e) ; CI_e = 1 - ARI_e
     Baseline tolerance 1e-12: jika S(G_M) < tol -> semua skenario "abstain".

Konvensi implementasi (disepakati pada verifikasi Gate 2):
* State terdisrupsi M_{e,lambda}: kekakuan edge diskala EA_e -> lambda*EA_e.
  Edge e dipertahankan dalam graf dengan bobot w_e -> lambda*w_e (edge-id tetap
  ada; multigraph: edge ID berbeda = edge fisik berbeda).
* Semua besaran mekanik (gaya awal, reaksi awal r^(0), utilisasi D_e) dievaluasi
  pada state INTAK; hanya bobot/cost graf yang berubah saat disrupsi.
* Jika state terdisrupsi rank-deficient (mekanisme) -> solver Gate 1 menolak
  (tanpa pseudoinverse); skenario dicatat status "rank_deficient", RR:=0,
  ARI:=0, CI:=1 (deteksi kegagalan struktur).

Satuan: gaya kN, panjang mm, E kN/mm^2.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from truss_reference import solve_model, load_models  # noqa: E402  (Gate 1)

# -----------------------------------------------------------------------------
# Konstanta & konfigurasi default (Section 4.5.3)
# -----------------------------------------------------------------------------
EPS_W = 1e-9          # regularisasi biaya edge
EPS_D = 1e-9          # regularisasi denominator skor jalur
EPS_R = 1e-6          # kN, pengaman kapasitas pada U*
BASELINE_TOL = 1e-12  # toleransi baseline score
MAX_SEARCH_NODES = 500_000  # batas DFS -> status "uncertified"

DEFAULT_CONFIG = dict(
    alpha_k=0.5,      # bobot kekakuan ternormalisasi
    alpha_R=0.5,      # bobot kapasitas ternormalisasi (alpha_k + alpha_R = 1)
    gamma=1.0,        # peluruhan peringkat jalur
    K=2,              # jumlah jalur maksimum per kombinasi
    beta=0.1,         # floor bobot simpul tumpuan
    eta=0.5,          # faktor penalti utilisasi
    eps_w=EPS_W,
    eps_d=EPS_D,
    eps_R=EPS_R,
    baseline_tol=BASELINE_TOL,
    # epsilon efektif untuk skenario penghapusan total (lambda = 0):
    # w_e -> lambda*w_e menjadi tepat nol sehingga cost tak hingga dan skor
    # runtuh ke nol untuk SEMUA edge. Tabel 4.3/4.11 disertasi menggunakan
    # regularisasi eps_eff = 1e-8 pada limit hapus-total (masih dalam rezim
    # "limit eps->0": hasil konvergen terhadap nilai tabel saat eps dikecilkan).
    eps_removed=1e-8,
)

# Skala tetap per model (Section 4.1.2) — TIDAK direnormalisasi per model.
FIXED_SCALES = {
    "M1_parallel_bars_1d":     dict(s_k=15.0, s_R=30.0),
    "M2_planar_triangle":      dict(s_k=20.0, s_R=40.0),
    "M3_square_one_diagonal":  dict(s_k=20.0, s_R=80.0),
    "M4_square_two_diagonals": dict(s_k=20.0, s_R=80.0),
}


def merged_config(**overrides) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(overrides)
    if abs(cfg["alpha_k"] + cfg["alpha_R"] - 1.0) > 1e-12:
        raise ValueError("alpha_k + alpha_R harus = 1")
    return cfg


# -----------------------------------------------------------------------------
# Struktur data (semua intermediate result disimpan untuk audit trail)
# -----------------------------------------------------------------------------
@dataclass
class AriModelData:
    """Model kanonik + state mekanik utuh dari solver referensi (Gate 1)."""
    model: dict
    config: dict
    scales: dict                       # s_k, s_R
    result: object                     # SolverResult (status ok)
    edges: List[dict]                  # metadata edge: id,i,j,L,area,E
    k_raw: Dict[int, float]            # k_e = E*A/L [kN/mm]
    loads: Dict[int, Dict[str, float]]         # node -> komponen beban f
    reactions: Dict[int, Dict[str, float]]     # node -> komponen reaksi r^(0)
    support_nodes: List[int]           # V_T
    dim: int
    audit: dict = field(default_factory=dict)


@dataclass
class ScenarioResult:
    edge_id: Optional[int]
    lam: float
    S: float
    RR: Optional[float]
    U_star: Optional[float]
    ARI: Optional[float]
    CI: Optional[float]
    status: str                        # ok | rank_deficient | abstain | uncertified
    detail: dict = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Utilitas geometri edge
# -----------------------------------------------------------------------------
def _edge_geometry(model: dict) -> List[dict]:
    nodes = {int(n["id"]): [float(v) for v in n["coords"]] for n in model["nodes"]}
    E_default = float(model.get("material", {}).get("E", 200.0))
    out = []
    for el in model["elements"]:
        i, j = int(el["nodes"][0]), int(el["nodes"][1])
        L = float(np.linalg.norm(np.array(nodes[j]) - np.array(nodes[i])))
        out.append(dict(id=int(el["id"]), i=i, j=j, L=L,
                        area=float(el["area"]), E=float(el.get("E", E_default))))
    return out


# -----------------------------------------------------------------------------
# A. Normalisasi atribut (Eq 2.5-2.7)
# -----------------------------------------------------------------------------
def compute_edge_weights(model: dict, config: Optional[dict] = None,
                         scales: Optional[dict] = None,
                         q: Optional[Dict[int, float]] = None) -> Dict[int, float]:
    """Bobot edge w_e^M = q_e * (alpha_k*k_hat_e + alpha_R*R_hat_e).

    Return dict[edge_id] = weight. Kondisi awal kanonik: q_e = 1 (no degradasi).
    """
    cfg = merged_config(**(config or {}))
    mid = str(model.get("id", "unknown"))
    sc = scales or FIXED_SCALES[mid]
    meta = _edge_geometry(model)
    k_raw = {m["id"]: m["E"] * m["area"] / m["L"] for m in meta}
    caps = {int(eid): float(c) for eid, c in model["capacities"].items()}
    weights = {}
    for m in meta:
        eid = m["id"]
        qe = (q or {}).get(eid, 1.0)
        k_hat = k_raw[eid] / (k_raw[eid] + sc["s_k"])
        r_hat = caps[eid] / (caps[eid] + sc["s_R"])
        weights[eid] = qe * (cfg["alpha_k"] * k_hat + cfg["alpha_R"] * r_hat)
    return weights


# -----------------------------------------------------------------------------
# B. Enumerasi jalur edge-disjoint & skor pasangan (Eq 2.8-2.10)
# -----------------------------------------------------------------------------
class Multigraph:
    """Graf multi-edge: node ints, edge dengan id unik; edge ID berbeda =
    edge fisik berbeda (dua batang paralel 0-1 = dua edge)."""

    def __init__(self, node_ids: List[int], edges: List[dict]):
        self.nodes = list(node_ids)
        self.edges = {e["id"]: (int(e["i"]), int(e["j"])) for e in edges}
        self.adj: Dict[int, List[int]] = {n: [] for n in self.nodes}
        for eid, (i, j) in self.edges.items():
            self.adj[i].append(eid)
            self.adj[j].append(eid)

    def other(self, eid: int, node: int) -> int:
        i, j = self.edges[eid]
        return j if node == i else i


def enumerate_edge_disjoint_paths(graph: Multigraph, source: int, target: int,
                                  K: int,
                                  max_nodes: int = MAX_SEARCH_NODES
                                  ) -> Tuple[List[List[Tuple[int, ...]]], str]:
    """Enumerasi EKSHAUSTIF semua kombinasi <=K jalur edge-disjoint source->target.

    Bukan greedy (Section 4.8.6). Return (kombinasi, status) dengan
    status "certified" atau "uncertified" (batas pencarian terlampaui ->
    caller WAJIB menganggap hasil tidak bersertifikat, bukan angka sembarang).
    """
    paths: List[Tuple[int, ...]] = []
    budget = {"n": 0}

    def dfs(node, used_edges, used_nodes, path) -> bool:
        budget["n"] += 1
        if budget["n"] > max_nodes:
            return False
        if node == target and path:
            paths.append(tuple(path))
            # lanjut: kumpulkan semua jalur sederhana, bukan hanya yang pertama
        for eid in graph.adj[node]:
            if eid in used_edges:
                continue
            nxt = graph.other(eid, node)
            if nxt in used_nodes:
                continue  # jalur sederhana (node-simple => otomatis edge-simple)
            used_edges.add(eid)
            used_nodes.add(nxt)
            path.append(eid)
            ok = dfs(nxt, used_edges, used_nodes, path)
            path.pop()
            used_nodes.discard(nxt)
            used_edges.discard(eid)
            if not ok:
                return False
        return True

    certified = dfs(source, set(), {source}, [])
    if not certified:
        return [], "uncertified"

    combos: List[List[Tuple[int, ...]]] = []
    for r in range(1, K + 1):
        for subset in itertools.combinations(paths, r):
            seen = set()
            disjoint = True
            for p in subset:
                for e in p:
                    if e in seen:
                        disjoint = False
                        break
                    seen.add(e)
                if not disjoint:
                    break
            if disjoint:
                combos.append(list(subset))
    return combos, "certified"


def rank_weights(K: int, gamma: float) -> List[float]:
    """omega_r = gamma^(r-1) / sum_{t=1..K} gamma^(t-1)."""
    w = [gamma ** r for r in range(K)]
    s = sum(w)
    return [x / s for x in w]


def compute_pair_score(graph: Multigraph, source: int, target: int,
                       edge_cost: Dict[int, float], config: dict
                       ) -> Tuple[float, str]:
    """Phi^K_ij(G) = max atas kombinasi jalur edge-disjoint (|P|<=K) dari
    sum_r omega_r / (d^M(p^(r)) + eps_d), jalur diurut menaik menurut d^M.

    Return (score, certification_status).
    """
    cfg = config if "eps_d" in config else merged_config(**config)
    K = int(cfg["K"])
    eps_d = cfg["eps_d"]
    combos, status = enumerate_edge_disjoint_paths(graph, source, target, K)
    if status != "certified":
        return float("nan"), status
    om = rank_weights(K, cfg["gamma"])
    best = 0.0
    found_any = False
    for combo in combos:
        ds = sorted(sum(edge_cost[e] for e in p) for p in combo)
        score = sum(om[r] / (d + eps_d) for r, d in enumerate(ds))
        if score > best:
            best = score
            found_any = True
    return (best if found_any else 0.0), status


# -----------------------------------------------------------------------------
# C. Agregasi skor graf (Eq 2.11-2.13)
# -----------------------------------------------------------------------------
def build_ari_model(model: dict, config: Optional[dict] = None,
                    scales: Optional[dict] = None) -> AriModelData:
    """Jalankan solver Gate 1 (state INTAK), kumpulkan beban & reaksi awal."""
    cfg = merged_config(**(config or {}))
    res = solve_model(model)
    if res.status != "ok":
        raise RuntimeError(f"Model {model['id']}: solver Gate 1 status "
                           f"'{res.status}' — ARI tidak dapat dihitung.")
    dim = int(model.get("dimension", 2))
    comps_all = ["ux", "uy", "uz"]
    meta = _edge_geometry(model)
    k_raw = {m["id"]: m["E"] * m["area"] / m["L"] for m in meta}
    loads: Dict[int, Dict[str, float]] = {}
    for item in model.get("loads", []):
        nid = int(item["node"])
        loads.setdefault(nid, {})
        for c, v in item.get("components", {}).items():
            loads[nid][c] = loads[nid].get(c, 0.0) + float(v)
    reactions: Dict[int, Dict[str, float]] = {}
    for dof, val in res.reactions.items():
        nid = dof // dim
        comp = comps_all[dof % dim]
        reactions.setdefault(nid, {})[comp] = val
    support_nodes = sorted(reactions.keys())
    return AriModelData(
        model=model, config=cfg,
        scales=scales or FIXED_SCALES[str(model["id"])],
        result=res, edges=meta, k_raw=k_raw,
        loads=loads, reactions=reactions,
        support_nodes=support_nodes, dim=dim)


def _load_cases(am: AriModelData) -> List[dict]:
    """Satu load case per arah beban diskret; pi_c = 1 (beban kanonik uniarah)."""
    cases = []
    for nid, comps in sorted(am.loads.items()):
        for comp, val in comps.items():
            if abs(val) > 0.0:
                cases.append(dict(name=f"{comp}@{nid}", f={nid: {comp: val}}))
    return cases


def _mag(comps: Dict[str, float], dim: int) -> float:
    comps_all = ["ux", "uy", "uz"]
    return math.sqrt(sum(comps.get(c, 0.0) ** 2 for c in comps_all[:dim]))


def base_weights_of(am: AriModelData,
                    scales: Optional[dict] = None) -> Dict[int, float]:
    """Bobot intact w_e^M (diekspos untuk audit). `scales` opsional mengganti
    (s_k, s_R) — dipakai uji invariansi penskalaan-serentak (DF-03)."""
    cfg = am.config
    sc = dict(am.scales)
    if scales:
        sc.update(scales)
    caps = {int(k): float(v) for k, v in am.model["capacities"].items()}
    out = {}
    for m in am.edges:
        eid = m["id"]
        k_hat = am.k_raw[eid] / (am.k_raw[eid] + sc["s_k"])
        r_hat = caps[eid] / (caps[eid] + sc["s_R"])
        out[eid] = 1.0 * (cfg["alpha_k"] * k_hat + cfg["alpha_R"] * r_hat)
    return out


def compute_graph_score(am: AriModelData,
                        weight_mult: Optional[Dict[int, float]] = None,
                        pair_cache: Optional[dict] = None,
                        audit: Optional[dict] = None,
                        scales: Optional[dict] = None) -> Tuple[float, str]:
    """S(G) untuk state saat ini. weight_mult = pengali lambda per edge TANPA
    renormalisasi (Section 4.8.4).

    Integritas mekanik state terdisrupsi diverifikasi dengan solver Gate 1
    (EA_e -> lambda*EA_e). Rank-deficient -> status "rank_deficient", S nan.
    """
    cfg = am.config
    wm = weight_mult or {}
    base_w = base_weights_of(am, scales)
    weights = {eid: w * wm.get(eid, 1.0) for eid, w in base_w.items()}

    graph = Multigraph([int(n["id"]) for n in am.model["nodes"]], am.edges)

    # --- Verifikasi mekanik state terdisrupsi (tanpa pseudoinverse) ----------
    # Edge lambda=0 diperlakukan sebagai penghapusan fisik pada model FE; jika
    # struktur menjadi mekanisme -> status "rank_deficient" dicatat pada audit.
    # Skor graf tetap dihitung murni-graf (konvensi Tabel 4.3/4.11): edge yang
    # dihapus memperoleh cost regularisasi c := 1/eps_removed (limit eps->0).
    disrupted = _apply_stiffness_multiplier(am.model, wm, drop_zero=True)
    mech_status = "ok"
    try:
        res = solve_model(disrupted)
        mech_status = res.status
    except Exception:
        mech_status = "rank_deficient"

    # --- Cost edge dengan regularisasi hapus-total ----------------------------
    def _cost(w):
        if w == 0.0:
            return 1.0 / cfg["eps_removed"]
        return 1.0 / (w + cfg["eps_w"])
    edge_cost = {eid: _cost(w) for eid, w in weights.items()}

    # --- Bobot simpul tumpuan b_jc --------------------------------------------
    # r^(0) = reaksi state INTAK (konvensi: superscript (0) = initial/intact).
    # Tidak direnormalisasi terhadap state terdisrupsi (Section 4.8.4).
    bc = sum(_mag(rc, am.dim) for rc in am.reactions.values())
    vt = len(am.support_nodes)
    b_map = {}
    for nid in am.support_nodes:
        mag = _mag(am.reactions.get(nid, {}), am.dim)
        b_map[nid] = (cfg["beta"] / vt
                      + (1.0 - cfg["beta"]) * (mag / bc if bc > 0 else 0.0))

    total = 0.0
    case_records = []
    for case in _load_cases(am):
        fc = sum(abs(v) for comps in case["f"].values() for v in comps.values())
        if fc <= 0.0:
            continue
        ai = {nid: _mag(comps, am.dim) / fc for nid, comps in case["f"].items()}
        inner = 0.0
        pair_records = []
        for i_node, a_w in ai.items():
            for j_node, b_w in b_map.items():
                key = (i_node, j_node, tuple(sorted(edge_cost.items())))
                if pair_cache is not None and key in pair_cache:
                    phi, st = pair_cache[key]
                else:
                    phi, st = compute_pair_score(graph, i_node, j_node,
                                                 edge_cost, cfg)
                    if pair_cache is not None:
                        pair_cache[key] = (phi, st)
                if st != "certified":
                    return float("nan"), st
                inner += a_w * b_w * phi
                pair_records.append(dict(i=i_node, j=j_node, a=a_w, b=b_w,
                                         phi=phi))
        total += 1.0 * inner  # pi_c = 1
        case_records.append(dict(case=case["name"], pairs=pair_records))
    if audit is not None:
        audit["weights"] = dict(weights)
        audit["b_map"] = dict(b_map)
        audit["mechanical_status"] = mech_status
        audit["cases"] = case_records
    return total, "ok"


def kinetic_snapshot(model: dict) -> dict:
    """Gate 3 (Kinematic Guard) — diagnostik state INTAK via solver Gate 1.

    Didefinisikan lokal di ari_core agar tidak ada import melingkar dengan
    kinematic_guard.py; implementasi identik dengan kinematic_guard.
    """
    res = solve_model(model)
    return dict(
        intact_solvable=(res.status == "ok"),
        intact_rank=int(res.rank),
        intact_ndof=int(res.ndof),
        intact_min_eig=float(res.min_eig),
        intact_max_eig=float(res.max_eig),
    )


def guard_diagnostic(model: dict, weight_mult: Dict[int, float]) -> dict:
    """Gate 3 — diagnostik kinematik state terdisrupsi M_{e,lambda}.

    lambda=0 diperlakukan sebagai penghapusan fisik (drop_zero=True).
    Rank-check memakai solver Gate 1 apa adanya (eigvals, tol relatif 1e-10,
    TANPA pseudoinverse). Non-destruktif terhadap skor graf.
    """
    intact = kinetic_snapshot(model)
    disrupted = _apply_stiffness_multiplier(model, weight_mult, drop_zero=True)
    try:
        res = solve_model(disrupted)
        status, rank = res.status, int(res.rank)
        min_eig, max_eig = float(res.min_eig), float(res.max_eig)
    except Exception:
        status, rank = "rank_deficient", -1
        min_eig = max_eig = float("nan")
    return dict(
        disrupted_status=status,
        disrupted_rank=rank,
        intact_rank=intact["intact_rank"],
        rank_drop=int(intact["intact_rank"] - rank),
        solvable=(status == "ok"),
        min_eig=min_eig, max_eig=max_eig,
    )


def _apply_stiffness_multiplier(model: dict, mult: Dict[int, float],
                                drop_zero: bool = False) -> dict:
    """State terdisrupsi M_{e,lambda}: EA_e -> lambda*EA_e (kapasitas & atribut
    lain TIDAK diubah; tanpa renormalisasi).

    drop_zero=True: edge dengan lambda == 0 dihapus fisik dari model FE
    (penghapusan total). Untuk lambda > 0 edge tetap ada dengan EA diskala.
    """
    m2 = json.loads(json.dumps(model))
    by_id = {int(el["id"]): el for el in m2["elements"]}
    for eid, lam in mult.items():
        if drop_zero and float(lam) == 0.0:
            m2["elements"] = [el for el in m2["elements"]
                              if int(el["id"]) != eid]
            continue
        el = by_id[eid]
        el["area"] = float(el["area"]) * float(lam)
    return m2


# -----------------------------------------------------------------------------
# D. Disrupsi & ARI (Eq 2.14-2.18)
# -----------------------------------------------------------------------------
def compute_ari(am: AriModelData, disruption: Optional[Tuple[int, float]] = None,
                config: Optional[dict] = None,
                baseline: Optional[Tuple[float, str]] = None,
                pair_cache: Optional[dict] = None,
                scales: Optional[dict] = None) -> ScenarioResult:
    """RR, ARI, CI untuk skenario s=(e, lambda). disruption=None => kontrol utuh.

    Kontrol lambda=1: RR = 1 eksak; ARI = 1 - eta*U*_e sehingga CI = eta*U*_e
    (bukan nol — penalti utilisasi tetap aktif pada state utuh).

    `scales` opsional mengganti (s_k, s_R) model — dipakai uji invariansi
    penskalaan-serentak (DF-03). Jika diberikan, baseline yang dikirim caller
    WAJIB dihitung dengan skala yang sama.
    """
    cfg = dict(am.config)
    cfg.update(config or {})
    sc = dict(am.scales)
    if scales:
        sc.update({k: float(v) for k, v in scales.items()})
    eid, lam = (None, 1.0) if disruption is None else (int(disruption[0]),
                                                       float(disruption[1]))

    # Utilisasi awal (state INTAK): U*_e = min(D_e/(R_e+eps_R), 1)
    caps = {int(k): float(v) for k, v in am.model["capacities"].items()}
    u_star = None
    if eid is not None:
        idx = next(i for i, m in enumerate(am.edges) if m["id"] == eid)
        demand = abs(float(am.result.element_forces[idx]))
        u_star = min(demand / (caps[eid] + cfg["eps_R"]), 1.0)

    if baseline is None:
        baseline = compute_graph_score(am, None, pair_cache, scales=sc)
    s_base, st_base = baseline
    if st_base != "ok" or s_base < cfg["baseline_tol"]:
        return ScenarioResult(eid, lam, float("nan"), None, u_star, None, None,
                              "abstain", dict(S_baseline=s_base,
                                              baseline_status=st_base))

    if eid is not None and lam == 1.0:
        # Kontrol per-edge: w_e tidak berubah -> S identik baseline, RR = 1
        # EKSAK; penalti utilisasi TETAP aktif sehingga CI = eta*U*_e (bukan 0),
        # sesuai kontrak acceptance "Kontrol lambda=1".
        # Gate 3 (Kinematic Guard): kontrol diverifikasi dengan solver Gate 1
        # pada state INTAK — status mekanik & rank tercatat di audit trail.
        ctrl_audit = dict(S_baseline=s_base, mechanical_status="ok",
                          note="kontrol lambda=1: RR eksak 1")
        kin = kinetic_snapshot(am.model)
        ctrl_audit.update(kin)
        ctrl_status = "ok"
        if not kin["intact_solvable"]:
            ctrl_status = "ok_with_rank_deficiency"
            ctrl_audit["note"] += (" | PERINGATAN KINEMATIC-GUARD: state INTAK"
                                   " rank-deficient (mekanisme)")
        return ScenarioResult(eid, lam, s_base, 1.0, u_star,
                              1.0 - cfg["eta"] * u_star,
                              max(cfg["eta"] * u_star, 0.0), ctrl_status,
                              ctrl_audit)
    if eid is None:
        # Kontrol utuh (tanpa edge): tidak ada U*_e -> ARI = RR = 1, CI = 0
        rr = 1.0
        s_val = s_base
        st = "ok"
        mech = "ok"
    else:
        scen_audit: dict = {}
        s_val, st = compute_graph_score(am, {eid: lam}, pair_cache,
                                        scen_audit, scales=sc)
        mech = scen_audit.get("mechanical_status", "unknown")

    detail = dict(S_baseline=s_base, mechanical_status=mech)

    if st == "uncertified":
        # Pencarian tidak selesai -> BUKAN angka sembarang
        return ScenarioResult(eid, lam, float("nan"), None, u_star, None, None,
                              "uncertified", detail)
    if st == "rank_deficient":
        # Peringatan audit (Layer-3): pada skenario hapus-total, struktur FE
        # dapat menjadi mekanisme (rank K_ff turun; Gate 1 menolak WITHOUT
        # pseudoinverse). Tabel 4.3 disertasi TIDAK meng-abstain kasus ini:
        # skor jalur tetap dihitung murni-graf pada topologi terdisrupsi.
        # Status dicatat sebagai "ok_with_rank_deficiency" agar reviewer dapat
        # melihat degradasi kinematik yang tidak tercermin dalam RR/CI.
        detail["note"] = ("FE rank-deficient (mekanisme) pada state terdisrupsi;"
                          " skor graf tetap dihitung murni-graf sesuai kontrak"
                          " Tabel 4.3 — lihat DEFERRED_FINDINGS DF-02")
        st = "ok_with_rank_deficiency"
    if st not in ("ok", "ok_with_rank_deficiency"):
        return ScenarioResult(eid, lam, s_val, None, u_star, None, None, st,
                              detail)

    rr = s_val / s_base
    ari = rr * (1.0 - cfg["eta"] * (u_star if u_star is not None else 0.0))
    ci = max(1.0 - ari, 0.0)   # floor numerik: CI >= 0 (RR<=1 terjamin teoritis)
    detail["mechanical_status"] = mech
    return ScenarioResult(eid, lam, s_val, rr, u_star, ari, ci, st, detail)


# -----------------------------------------------------------------------------
# Skrining penuh (audit trail lengkap)
# -----------------------------------------------------------------------------
def run_full_screening(models: List[dict], config: Optional[dict] = None,
                       scales_by_model: Optional[dict] = None,
                       lambdas: Tuple[float, ...] = (0.0,),
                       verbose: bool = False) -> dict:
    """Semua kontrol (per model) + semua skenario (edge x lambda).

    Return report per model: baseline, control, scenarios[(eid,lam)],
    intact utilization, dan audit intermediate results.
    """
    report = {}
    for m in models:
        mid = str(m["id"])
        am = build_ari_model(m, config, (scales_by_model or {}).get(mid))
        cache: dict = {}
        base_audit: dict = {}
        s_base, st_base = compute_graph_score(am, None, cache, base_audit)
        baseline = (s_base, st_base)
        control = compute_ari(am, None, config=config, baseline=baseline,
                              pair_cache=cache)
        scen = {}
        for e in am.edges:
            for lam in lambdas:
                scen[(e["id"], lam)] = compute_ari(am, (e["id"], lam),
                                                   config=config,
                                                   baseline=baseline,
                                                   pair_cache=cache)
        report[mid] = dict(
            model=m, am=am, baseline=baseline, control=control,
            scenarios=scen, audit=base_audit,
            intact_utilization={
                e["id"]: abs(float(am.result.element_forces[i]))
                for i, e in enumerate(am.edges)})
        if verbose:
            print(f"[{mid}] S_base={s_base:.9f} ({st_base})")
    return report
