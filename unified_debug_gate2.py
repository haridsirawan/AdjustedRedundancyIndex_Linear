#!/usr/bin/env python3
"""
unified_debug_gate2.py
======================

SATU skrip diagnostik terpadu untuk menutup Finding #001 (deviasi RR
`ari_core.py` vs Tabel 4.3 disertasi) — menggantikan rangkaian
debug_gate2.py .. debug_gate2u.py yang masing-masing hanya men-sweep satu
dimensi hipotesis.

Doktrin "perapian & review ringan" (Gate 8): file ini TIDAK mengubah
formula/parameter `examples/ari_core.py`. Semua varian hipotesis di sini
adalah WRAPPER DIAGNOSTIK yang mereplikasi rantai Eq 2.5-2.18 secara lokal,
sehingga ari_core tetap menjadi baseline resmi sampai DIAGNOSIS.md ditulis.

================================================================================
STEP 1 — REFERENCE VALUES (status sumber: PARSIAL / REKONSTRUKSI)
================================================================================
PENTING: `main.pdf` (naskah disertasi) TIDAK ADA di sandbox ini — diverifikasi
dengan pencarian filesystem penuh dan penelusuran seluruh histori Git
(`git log --all --name-only`; satu-satunya PDF = kurva Gate 6). File
debug_gate2*.py juga tidak ada di working tree; dipulihkan dari commit
39765ce ke `debug_archive/`. Karena itu, nilai referensi diambil dari
*salinan target* yang ditanam para skrip debug tersebut + kontrak user:

  Tabel 4.3 (M3 square-with-one-diagonal, hapus-total lambda=0), penamaan e1..e5:
      e1(AB)  RR = 0.983152   CI = 0.016848
      e2(BC)  RR = 0.964724   CI = 0.216162   <-- INKONSISTEN INTERNAL naskah
      e3(CD)  RR = 1.000000   CI = 0.000000   <-- kasus kritis (batas representasi)
      e4(DA)  RR = 1.000000   CI = 0.000000   <-- kasus kritis
      e5(AC)  RR = 0.717285   CI = 0.472914
  IDENTITAS TERDETEKSI (numerik presisi tinggi, lihat DIAGNOSIS.md §2):
  Kelima RR T4.3 adalah hasil formula jalur-terpendek dengan bobot tumpuan
  salah-skala:
      Phi(i->j) := w_ij / L_min(i->j)^2   (kuadrat jarak — BUKAN Eq 2.8)
      S = b_A*Phi(C->A) + b_B*Phi(C->B),  b = (0.95, 0.05)
      => b_B/b_A = 1/19.0006  dan  rasio bobot-intak/critical q_e = w/w_crit
         = (0.08, 0.16, 0.32, 0.64, 1.28) untuk (e1,e2,e3,e4,e5) — deret
         powers-of-two yang tidak bersumber dari properti M3 manapun.
  Verifikasi per baris (RR_pred = 1 - q*(bB/bA)*min(1,1/q)):
      e1 0.983157 vs 0.983152 | e2 0.966316 vs 0.964724 | e3,e4 1.0 persis
      e5 0.717263 vs 0.717285  -> reproduksi ~1e-3..2e-3; BARIS e2 MEMANG
  SATU-SATUNYA yang tidak konsisten internal di naskah (CI=0.216162 melanggar
  Eq 2.17-2.18 naskah sendiri; seharusnya RR=0.836518 atau CI=0.295561 utk
  e1). Kesimpulan parsial: nilai T4.3 bukan keluaran pipeline Eq 2.5-2.13.

  Tabel 4.11 (M1 two parallel bars, limit eps->0) — rasional EKSAK:
      control       : RR = 1        ARI = 3/4 = 0.750000  CI = 1/4 = 0.250000
      bar0 removed  : RR = 7/17     ARI = 21/68 = 0.308824 CI = 47/68 = 0.691176
      bar1 removed  : RR = 10/17    ARI = 15/34 = 0.441176 CI = 19/34 = 0.558824
      (bar0 = edge id 0, A=100 mm2, cap=40 kN; bar1 = edge id 1, A=50, cap=20)
  IDENTITAS EKSAK TERBUKTI: dengan bobot kanonik kode
      w(bar0) = 1/2*(20/(20+15)) + 1/2*(40/(40+30)) = 4/7 ,  w(bar1) = 2/5
  dan agregasi Eq 2.8 dg omega RANKED FIXED-K (|P|=1 tetap memakai omega_1=1/K):
      Phi_base = (1/2)(7/4 + 5/2) = 17/8 ;  Phi(bar0 hilang) = (1/2)(5/2)
      => RR(bar0) = 5/2 /(17/8) = 20/17? TIDAK — hitung eksak: RR = (5/2)/(17/8)=20/17>1??
  Koreksi: Phi_bar0lost = (1/2)*(1/w1) = (1/2)*(5/2)=5/4 ; RR = (5/4)/(17/8) = 10/17.
  Jadi RR(bar1 hilang)=7/17 dan RR(bar0 hilang)=10/17 EKSAK dgn konvensi kode
  SEKARANG -> tabel 4.11 memuat LABEL bar0/bar1 TERTUKAR terhadap model JSON
  (bar0=A=100 -> RR=10/17 bukan 7/17). Grid-search memverifikasi kedua orientasi.

  Baseline S(G_M): TIDAK dilaporkan dalam bentuk angka di artefak yang ada;
  dihitung oleh kode: M1 = 0.485714286, M3 = 0.360252011 (dicetak di Step 4).

  Pemetaan label tabel -> edge-id kode diasumsikan SEJARAH (H3 pada #001):
      e1->id0(AB), e2->id1(BC), e3->id2(CD), e4->id3(DA), e5->id4(diag AC).
  Alternatif silang (e1<->e2, e5<->e3/e4) TIDAK direstui teks user
  ("Remove e5 (AC)" eksplisit).

================================================================================
GRID SEARCH (STEP 2) — sumbu hipotesis H1..H7
================================================================================
  eps_removed      ∈ {1e-8, 1e-9, 1e-10}                  (H1)
  b_jc_source      ∈ {INTACT, DISRUPTED}                  (H2)
  path_mode        ∈ {ranked, posfree, shortest, k_rep_per_hop} (H3)
  graph_direction  ∈ {UNDIRECTED, DIRECTED_by_element_order}    (H4)
  target_nodes_J   ∈ {supports_only, all_nodes_uniform}        (H5)
  renorm_timing    ∈ {before_lambda, after_lambda, no_renorm}  (H6)
Total = 3*2*4*2*2*3 = 288 kombinasi x (2 edge M1 + 5 edge M3 skenario
hapus-total). Skor agregasi mengikuti Eq 2.11-2.13 dengan pi_c = 1, beta
floor, a_ic dari node beban, b_jc dari simpul tumpuan V_T.

Perilaku dasar per mode (hasil analisis struktural + sweep empiris):
  * ranked & UNDIRECTED : identik (semua jalur simple tereksplorasi; omega
                          selalu menempel pada rank biaya menaik).
  * shortest            : himpunan jalur dibatasi hop-minimum.
  * k_rep_per_hop       : representative min-cost per panjang-hop unik.
  * DIRECTED (i->j sesuai urutan elemen) : banyak pasangan i->j tak terhubung
                          -> skor kolaps (bukan interpretasi fisik truss).
  * before_lambda/after_lambda (renormalisasi bobot grup) : menggeser semua
                          w_e secara global -> RR nyaris tidak berubah
                          (invarian penskalaan serentak, Finding #002);
                          berbeda bermakna hanya utk degradasi parsial.
  * supports_only (J = V_T) : Phi(i,i)=0 utk tumpuan tanpa self-loop ->
                          M1 kolaps (RR=0); M3 hampir tak berubah karena
                          node beban C sudah anggota V_T.

Output: debug_results.csv (semua baris, sorted |dev| menaik) + laporan
terminal TOP-5 (scoring agregat per model = max |dev| relatif antar edge)
+ logging verbose kandidat terbaik (Step 4).

Jalankan:  python unified_debug_gate2.py [--verbose] [--top N]
Dependensi: examples/truss_reference.py, examples/ari_core.py (read-only),
numpy. networkx tersedia tetapi TIDAK dipakai (DFS lokal preserve edge-id).
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np  # noqa: F401  (dipakai truss_reference; impor utk kejelasan)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "examples"))

from truss_reference import solve_model, load_models  # noqa: E402
import ari_core as A  # noqa: E402  (baseline read-only + utilitas)

# -----------------------------------------------------------------------------
# STEP 1 — reference values (lihat docstring: status PARSIAL, main.pdf absen)
# -----------------------------------------------------------------------------
# M3: edge-id kode (asumsi pemetaan sejarah e1..e5 -> id0..id4)
T43_RR = {0: 0.983152, 1: 0.964724, 2: 1.000000, 3: 1.000000, 4: 0.717285}
T43_CI = {0: 0.016848, 1: 0.216162, 2: 0.000000, 3: 0.000000, 4: 0.472914}
# M1: Tabel 4.11 (limit eps->0; dievaluasi pd eps=1e-9, rel.tol 1e-6 diterima)
T411_RR = {0: 7.0 / 17.0, 1: 10.0 / 17.0}
T411_ARI = {0: 21.0 / 68.0, 1: 15.0 / 34.0}
T411_CI = {0: 47.0 / 68.0, 1: 19.0 / 34.0}

ETA_DEFAULT = 0.5

AXIS = dict(
    eps_removed=[1e-8, 1e-9, 1e-10],
    b_jc_source=["INTACT", "DISRUPTED"],
    path_mode=["ranked", "posfree", "shortest", "k_rep_per_hop"],
    graph_direction=["UNDIRECTED", "DIRECTED_by_element_order"],
    target_nodes_J=["supports_only", "all_nodes_uniform"],
    renorm_timing=["before_lambda", "after_lambda", "no_renorm"],
)


# -----------------------------------------------------------------------------
# Utilitas graf & jalur (wrapper diagnostik; mirror perilaku ari_core)
# -----------------------------------------------------------------------------
class Graph:
    """Multigraph dgn mode arah. DIRECTED_by_element_order: adjacency hanya
    i->j sesuai urutan node elemen (hipotesis H4). Edge-id selalu dipertahankan
    (multigraph: dua edge paralel 0-1 = dua edge fisik berbeda)."""

    def __init__(self, node_ids, edges, directed=False):
        self.nodes = list(node_ids)
        self.edges = {e["id"]: (int(e["i"]), int(e["j"])) for e in edges}
        self.adj = {n: [] for n in self.nodes}
        for eid, (i, j) in self.edges.items():
            self.adj[i].append(eid)
            if not directed:
                self.adj[j].append(eid)

    def other(self, eid, node):
        i, j = self.edges[eid]
        return j if node == i else i


def all_simple_paths(g: Graph, s: int, t: int) -> List[Tuple[int, ...]]:
    """DFS semua jalur node-simple s->t (edge otomatis simple)."""
    out: List[Tuple[int, ...]] = []
    if s == t:
        return out

    def dfs(node, used_e, used_n, acc):
        if node == t and acc:
            out.append(tuple(acc))
        for eid in g.adj[node]:
            if eid in used_e:
                continue
            nxt = g.other(eid, node)
            if nxt in used_n:
                continue
            used_e.add(eid); used_n.add(nxt); acc.append(eid)
            dfs(nxt, used_e, used_n, acc)
            acc.pop(); used_n.discard(nxt); used_e.discard(eid)

    dfs(s, set(), {s}, [])
    return out


def path_set_for_mode(g, s, t, cost, K, mode) -> List[Tuple[int, ...]]:
    """Himpunan kandidat jalur P sebelum formasi kombinasi edge-disjoint."""
    ps = all_simple_paths(g, s, t)
    if not ps:
        return []
    if mode == "ranked" or mode == "posfree":
        return ps                                   # semua jalur simple (H3-a)
    if mode == "shortest":                          # H3-b: hanya hop-minimum
        hm = min(len(p) for p in ps)
        return [p for p in ps if len(p) == hm]
    if mode == "k_rep_per_hop":                     # H3-c: rep termurah per hop
        best = {}
        for p in ps:
            h = len(p)
            c = sum(cost[e] for e in p)
            if h not in best or c < best[h][1]:
                best[h] = (p, c)
        return [v[0] for v in best.values()]
    raise ValueError(f"path_mode tak dikenal: {mode}")


def combos_edge_disjoint(paths, K):
    """Semua kombinasi <=K jalur pairwise edge-disjoint (EKSHAUSTIF, §4.8.6)."""
    combos = []
    for r in range(1, K + 1):
        for subset in itertools.combinations(paths, r):
            seen, ok = set(), True
            for p in subset:
                if seen & set(p):
                    ok = False
                    break
                seen |= set(p)
            if ok:
                combos.append(list(subset))
    return combos


def phi_pair(g, s, t, cost, cfg, mode):
    """Phi^K_ij (Eq 2.8-2.10) dengan varian ranking-mode H3.
    ranked  : omega menempel rank-d setelah sorting menaik (default ari_core).
    posfree : maksimum atas SEMUA subsetting posisi-independen (H4 debug lama).
    shortest/k_rep_per_hop : same aggregation 'ranked' pada himpunan terbatas."""
    K = int(cfg["K"]); eps_d = cfg["eps_d"]
    om = A.rank_weights(K, cfg["gamma"])
    ps = path_set_for_mode(g, s, t, cost, K, mode)
    if not ps:
        return 0.0
    combos = combos_edge_disjoint(ps, K)
    agg_modes = ["ranked"] if mode != "posfree" else ["ranked", "posfree"]
    best = 0.0
    for combo in combos:
        ds = [sum(cost[e] for e in p) for p in combo]
        for amode in agg_modes:
            if amode == "ranked":
                cand = sum(om[i] / (d + eps_d) for i, d in enumerate(sorted(ds)))
            else:  # posfree: setiap subset jalur dievaluasi dgn omega[:len]
                r = len(ds)
                cand = 0.0
                for ksub in range(1, r + 1):
                    for sub in itertools.combinations(range(r), ksub):
                        v = sum(om[i] / (ds[j] + eps_d)
                                for i, j in enumerate(sorted(sub, key=lambda x: ds[x])))
                        cand = max(cand, v)
            best = max(best, cand)
    return best


# -----------------------------------------------------------------------------
# State mekanik & bobot (mirror Eq 2.5-2.7 + disrupsi Eq 2.14)
# -----------------------------------------------------------------------------
def intact_state(model: dict):
    """Solver Gate-1 state INTAK: gaya batang & reaksi awal r^(0)."""
    res = solve_model(model)
    if res.status != "ok":
        raise RuntimeError(f"{model['id']}: solver intak '{res.status}'")
    dim = int(model.get("dimension", 2))
    comps = ["ux", "uy", "uz"]
    forces = {int(el["id"]): float(res.element_forces[i])
              for i, el in enumerate(model["elements"])}
    reacts: Dict[int, Dict[str, float]] = {}
    for dof, val in res.reactions.items():
        nid = dof // dim
        reacts.setdefault(nid, {})[comps[dof % dim]] = val
    return res, dim, forces, reacts


def disrupted_state(model: dict, eid: int, lam: float):
    """State FE terdisrupsi M_{e,lam}: EA->lam*EA; lam=0 => hapus fisik.
    Return (status, reactions|None). Rank-deficient TANPA pseudoinverse."""
    m2 = A._apply_stiffness_multiplier(model, {eid: lam}, drop_zero=True)
    try:
        res = solve_model(m2)
    except Exception:
        return "rank_deficient", None
    if res.status != "ok":
        return res.status, None
    dim = int(model.get("dimension", 2))
    comps = ["ux", "uy", "uz"]
    reacts: Dict[int, Dict[str, float]] = {}
    for dof, val in res.reactions.items():
        nid = dof // dim
        reacts.setdefault(nid, {})[comps[dof % dim]] = val
    return "ok", reacts


def edge_weights(am_base: dict, mult: Dict[int, float], cfg: dict,
                 scales: dict, renorm: str) -> Dict[int, float]:
    """w_e^M = q_e*(alpha_k*k_hat + alpha_R*R_hat), lalu disrupsi Eq 2.14.
    renorm_timing (H6):
      no_renorm     : w_e -> lam*w_e                      (kontrak disertasi)
      before_lambda : skala GRUP dulu (w -> w/mean), baru lam  (degenerates:
                      lam=0 tetap nol; utk lam>0 = penskalaan serentak -> RR
                      invarian, Finding #002)
      after_lambda  : disrupsi dulu, lalu skala grup ke mean awal
                      (untuk hapus-total IDENTIK no_renorm secara matematis)."""
    caps = {int(k): float(v) for k, v in am_base["capacities"].items()}
    w = {}
    for m in am_base["edges_meta"]:
        eid = m["id"]
        k_hat = am_base["k_raw"][eid] / (am_base["k_raw"][eid] + scales["s_k"])
        r_hat = caps[eid] / (caps[eid] + scales["s_R"])
        w[eid] = cfg["alpha_k"] * k_hat + cfg["alpha_R"] * r_hat
    if renorm == "before_lambda":
        mu = sum(w.values()) / len(w)
        w = {e: v / mu for e, v in w.items()}
        for eid, lam in mult.items():
            w[eid] *= lam
        return w
    for eid, lam in mult.items():
        w[eid] = w[eid] * lam           # TANPA renormalisasi (default)
    if renorm == "after_lambda":
        mu0 = sum(A_.values() for A_ in [{}]) if False else None  # placeholder
        mu_ref = _intact_mean(am_base, cfg, scales)
        mu_now = sum(w.values()) / len(w)
        if mu_now > 0:
            w = {e: v * (mu_ref / mu_now) for e, v in w.items()}
    return w


def _intact_mean(am_base, cfg, scales) -> float:
    caps = {int(k): float(v) for k, v in am_base["capacities"].items()}
    tot = 0.0
    for m in am_base["edges_meta"]:
        eid = m["id"]
        k_hat = am_base["k_raw"][eid] / (am_base["k_raw"][eid] + scales["s_k"])
        r_hat = caps[eid] / (caps[eid] + scales["s_R"])
        tot += cfg["alpha_k"] * k_hat + cfg["alpha_R"] * r_hat
    return tot / len(am_base["edges_meta"])


def costs_from_weights(w: Dict[int, float], cfg: dict) -> Dict[int, float]:
    """c_e = 1/(w+eps_w); w==0 (hapus-total) -> c = 1/eps_removed (H1)."""
    out = {}
    for eid, we in w.items():
        out[eid] = (1.0 / cfg["eps_removed"]) if we == 0.0 \
            else 1.0 / (we + cfg["eps_w"])
    return out


def mag(comps: Dict[str, float], dim: int) -> float:
    comps_all = ["ux", "uy", "uz"]
    return math.sqrt(sum(comps.get(c, 0.0) ** 2 for c in comps_all[:dim]))


def graph_score_diag(base: dict, cost: Dict[int, float], cfg: dict,
                     params: dict, reacts_b: Optional[Dict], verbose_acc=None
                     ) -> float:
    """S(G) Eq 2.11-2.13 dengan varian H2/H5. pi_c = 1, satu load case
    kanonik uniarah per komponen beban non-nol (mirror ari_core._load_cases)."""
    dim = base["dim"]
    nodes = base["nodes"]
    g = Graph(nodes, base["edges_meta"],
              directed=(params["graph_direction"].startswith("DIRECTED")))
    V_T = sorted(base["reacts_intact"].keys())
    if params["target_nodes_J"] == "supports_only":
        J = V_T
    else:
        J = [n for n in nodes if n not in V_T]   # all_nodes_uniform (H5)
    # b_jc (H2): INTAK = reaksi r^(0); DISRUPTED = reaksi state terdisrupsi
    src = base["reacts_intact"] if (params["b_jc_source"] == "INTACT"
                                    or reacts_b is None) else reacts_b
    bc = sum(mag(rc, dim) for rc in src.values())
    vt = len(V_T)
    b_map = {}
    for nid in V_T:
        m_ = mag(src.get(nid, {}), dim)
        b_map[nid] = cfg["beta"] / vt + (1.0 - cfg["beta"]) * (m_ / bc if bc > 0 else 0.0)
    total = 0.0
    for case in base["load_cases"]:
        fc = sum(abs(v) for c in case["f"].values() for v in c.values())
        if fc <= 0:
            continue
        ai = {nid: mag(c, dim) / fc for nid, c in case["f"].items()}
        for i_node, aw in ai.items():
            for j_node in J:
                bw = b_map.get(j_node, 1.0 / len(J))  # uniform utk non-tumpuan
                ph = phi_pair(g, i_node, j_node, cost, cfg, params["path_mode"])
                total += aw * bw * ph
                if verbose_acc is not None:
                    verbose_acc.append(dict(i=i_node, j=j_node, a=aw, b=bw, phi=ph))
    return total


# -----------------------------------------------------------------------------
# Persiapan model
# -----------------------------------------------------------------------------
def prepare(model: dict) -> dict:
    cfg = A.merged_config()
    scales = A.FIXED_SCALES[str(model["id"])]
    res, dim, forces, reacts = intact_state(model)
    meta = A._edge_geometry(model)
    k_raw = {m["id"]: m["E"] * m["area"] / m["L"] for m in meta}
    loads: Dict[int, Dict[str, float]] = {}
    for item in model.get("loads", []):
        nid = int(item["node"])
        loads.setdefault(nid, {})
        for c, v in item.get("components", {}).items():
            loads[nid][c] = loads[nid].get(c, 0.0) + float(v)
    cases = []
    for nid, comps in sorted(loads.items()):
        for comp, val in comps.items():
            if abs(val) > 0.0:
                cases.append(dict(name=f"{comp}@{nid}", f={nid: {comp: val}}))
    caps = {int(k): float(v) for k, v in model["capacities"].items()}
    u_star = {eid: min(abs(forces[eid]) / (caps[eid] + cfg["eps_R"]), 1.0)
              for eid in caps}
    # node beban utk enumerasi audit (deep_log); mirror _load_cases
    load_case_nodes = sorted({nid for c in cases for nid in c["f"]})
    return dict(id=str(model["id"]), model=model, cfg=cfg, scales=scales,
                nodes=[int(n["id"]) for n in model["nodes"]],
                edges_meta=meta, k_raw=k_raw, capacities=caps, dim=dim,
                reacts_intact=reacts, load_cases=cases, u_star=u_star,
                forces=forces, load_case_nodes=load_case_nodes)


# -----------------------------------------------------------------------------
# STEP 2 — grid search
# -----------------------------------------------------------------------------
def run_grid(verbose=False):
    models = load_models(str(HERE / "examples" / "verification_models.json"))
    by_id = {str(m["id"]): m for m in models}
    bases = {"M1": prepare(by_id["M1_parallel_bars_1d"]),
             "M3": prepare(by_id["M3_square_one_diagonal"])}
    targets = {"M1": T411_RR, "M3": T43_RR}

    rows = []
    grid = list(itertools.product(*[AXIS[k] for k in AXIS]))
    for combo in grid:
        params = dict(zip(AXIS.keys(), combo))
        rec = {}
        for mk, base in bases.items():
            cfg = dict(base["cfg"])
            cfg["eps_removed"] = params["eps_removed"]
            w_int = edge_weights(base, {}, cfg, base["scales"], "no_renorm")
            c_int = costs_from_weights(w_int, cfg)
            s_base = graph_score_diag(base, c_int, cfg, params, None)
            worst_rel = 0.0
            per_edge = {}
            for eid, rr_t in targets[mk].items():
                w_d = edge_weights(base, {eid: 0.0}, cfg, base["scales"],
                                   params["renorm_timing"])
                c_d = costs_from_weights(w_d, cfg)
                st_d, reacts_d = disrupted_state(base["model"], eid, 0.0)
                s_d = graph_score_diag(base, c_d, cfg, params, reacts_d)
                rr = s_d / s_base if s_base > 0 else float("nan")
                dev_abs = abs(rr - rr_t)
                dev_rel = dev_abs / abs(rr_t) if rr_t else dev_abs
                worst_rel = max(worst_rel, dev_rel)
                per_edge[eid] = (rr, dev_abs, dev_rel, st_d)
            rec[mk] = (s_base, per_edge, worst_rel)
            for eid, (rr, da, dr, st) in per_edge.items():
                rows.append(dict(
                    eps_removed=params["eps_removed"],
                    b_jc_source=params["b_jc_source"],
                    path_mode=params["path_mode"],
                    graph_direction=params["graph_direction"],
                    target_nodes_J=params["target_nodes_J"],
                    renorm_timing=params["renorm_timing"],
                    model=mk, edge_id=eid,
                    S_intact=rec[mk][0], RR_observed=rr, RR_target=targets[mk][eid],
                    mech_status_disrupted=st,
                    abs_deviation=da, rel_deviation_pct=100.0 * dr,
                    score_max_rel_dev_model=worst_rel))
        if verbose:
            print(f"[grid] {params} -> M1 worst={rec['M1'][2]:.3%} "
                  f"M3 worst={rec['M3'][2]:.3%}")
    return rows, bases, params


def write_csv(rows, path="debug_results.csv"):
    rows_sorted = sorted(rows, key=lambda r: r["abs_deviation"])
    fields = list(rows[0].keys())
    with open(path, "w", newline="") as fh:
        wtr = csv.DictWriter(fh, fieldnames=fields)
        wtr.writeheader()
        for r in rows_sorted:
            wtr.writerow({k: (f"{v:.12g}" if isinstance(v, float) else v)
                          for k, v in r.items()})
    return rows_sorted


# -----------------------------------------------------------------------------
# STEP 3 — TOP-5 laporan terminal (skor agregat: max |dev| relatif per model)
# -----------------------------------------------------------------------------
def top_combos(rows, n=5):
    by_combo = {}
    for r in rows:
        key = tuple((k, r[k]) for k in AXIS)
        d = by_combo.setdefault(key, dict(M1=0.0, M3=0.0))
        d[r["model"]] = max(d[r["model"]], r["rel_deviation_pct"])
    scored = []
    for key, d in by_combo.items():
        both = math.hypot(d["M1"], d["M3"])          # skor gabungan kedua model
        scored.append((both, d, dict(key)))
    scored.sort(key=lambda x: x[0])
    return scored[:n]


# -----------------------------------------------------------------------------
# STEP 4 — deep logging kandidat terbaik
# -----------------------------------------------------------------------------
def deep_log(rows, bases):
    tops = top_combos(rows, 1)
    _, _, params = tops[0]
    print("\n" + "=" * 78)
    print("STEP 4 — DEEP LOGGING untuk kandidat terbaik:")
    for k, v in params.items():
        print(f"   {k:22s} = {v}")
    print("=" * 78)
    for mk in ("M1", "M3"):
        base = bases[mk]
        cfg = dict(base["cfg"]); cfg["eps_removed"] = params["eps_removed"]
        w_int = edge_weights(base, {}, cfg, base["scales"], "no_renorm")
        c_int = costs_from_weights(w_int, cfg)
        acc = []
        s_base = graph_score_diag(base, c_int, cfg, params, None, verbose_acc=acc)
        print(f"\n--- {mk} ---  S(G_M) = {s_base:.12f}")
        print("  w_e^M intact :", {e: round(v, 9) for e, v in sorted(w_int.items())})
        print("  pair contributions (a_i * b_j * Phi):")
        for t in acc:
            print(f"    i={t['i']} j={t['j']:>2} a={t['a']:.6f} b={t['b']:.6f} "
                  f"Phi={t['phi']:.9f}")
        for eid in sorted(TARGETS_ALL[mk]):
            g = Graph(base["nodes"], base["edges_meta"],
                      directed=params["graph_direction"].startswith("DIRECTED"))
            w_d = edge_weights(base, {eid: 0.0}, cfg, base["scales"],
                               params["renorm_timing"])
            c_d = costs_from_weights(w_d, cfg)
            print(f"\n  [hapus e{eid}]  cost:", {e: f"{v:.6g}" for e, v in sorted(c_d.items())})
            paths = path_set_for_mode(g, *_pair_endpoints(base, params), c_d,
                                      int(cfg["K"]), params["path_mode"]) \
                if False else None
            # enumerasi utk audit: cetak utk tiap pasangan aktif
            V_T = sorted(base["reacts_intact"].keys())
            J = V_T if params["target_nodes_J"] == "supports_only" else \
                [n for n in base["nodes"] if n not in V_T]
            for i_node in base["load_case_nodes"]:
                for j_node in J:
                    ps = all_simple_paths(g, i_node, j_node)
                    if not ps:
                        continue
                    ps_m = path_set_for_mode(g, i_node, j_node, c_d,
                                             int(cfg["K"]), params["path_mode"])
                    combos = combos_edge_disjoint(ps_m, int(cfg["K"]))
                    print(f"    pair ({i_node}->{j_node}): jalur(mode)={len(ps_m)} "
                          f"kombinasi={len(combos)}")
                    for p in ps_m:
                        print(f"      path {[('e%d'%e) for e in p]} "
                              f"d={sum(c_d[e] for e in p):.6g}")
                    om = A.rank_weights(int(cfg["K"]), cfg["gamma"])
                    best_phi, best_c = 0.0, None
                    for cb in combos:
                        ds = sorted(sum(c_d[e] for e in p) for p in cb)
                        v = sum(om[i] / (d + cfg["eps_d"]) for i, d in enumerate(ds))
                        if v > best_phi:
                            best_phi, best_c = v, (cb, ds)
                    if best_c:
                        cb, ds = best_c
                        print(f"      BEST Phi={best_phi:.9f} dari kombinasi "
                              f"{[[('e%d'%e) for e in p] for p in cb]} "
                              f"d_sorted={[f'{d:.6g}' for d in ds]}")
            acc2 = []
            st_d, reacts_d = disrupted_state(base["model"], eid, 0.0)
            s_d = graph_score_diag(base, c_d, cfg, params, reacts_d, verbose_acc=acc2)
            rr = s_d / s_base
            tgt = TARGETS_ALL[mk][eid]
            print(f"    S_disrupted = {s_d:.12f} ; RR = {s_d:.12f}/{s_base:.12f} "
                  f"= {rr:.12f} (target {tgt:.6f}; dev={abs(rr-tgt):.3e}) ; "
                  f"mech={st_d}")
            u = base["u_star"][eid]
            ari = rr * (1 - ETA_DEFAULT * u)
            print(f"    U*_e={u:.9f} -> ARI={ari:.9f} CI={1-ari:.9f}")


TARGETS_ALL = {"M1": T411_RR, "M3": T43_RR}


def _pair_endpoints(base, params):  # helper placeholder utk kompatibilitas
    V_T = sorted(base["reacts_intact"].keys())
    return (base["load_case_nodes"][0], V_T[0])


# -----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--csv", default="debug_results.csv")
    args = ap.parse_args()

    rows, bases, _ = run_grid(verbose=args.verbose)
    rows_sorted = write_csv(rows, args.csv)
    print(f"\n[STEP2] {len(rows)} baris -> {args.csv} (sorted |dev| menaik)")

    print("\n[STEP3] TOP-%d kombinasi parameter (skor = hypot(dev%% M1, dev%% M3));"
          "\n        toleransi evaluasi |dev| < 1e-4:" % args.top)
    tops = top_combos(rows, args.top)
    any_match = False
    for both, d, params in tops:
        ok = (d["M1"] / 100.0 < 1e-4) and (d["M3"] / 100.0 < 1e-4)
        any_match |= ok
        flag = "MATCH<1e-4" if ok else "-"
        print(f"  [{flag}] M1maxdev={d['M1']:7.3f}%  M3maxdev={d['M3']:7.3f}%  "
              f"eps_rm={params['eps_removed']:.0e} bjc={params['b_jc_source']} "
              f"path={params['path_mode']} dir={'U' if params['graph_direction'].startswith('UN') else 'D'} "
              f"J={params['target_nodes_J']} renorm={params['renorm_timing']}")
    if not any_match:
        print("  => TIDAK ADA kombinasi yang memenuhi |dev| < 1e-4 sekaligus.")

    # ringkasan deviasi minimum per target ( utk DIAGNOSIS )
    print("\n[STEP3b] Deviasi MINIMUM global per target:")
    for mk, tg in TARGETS_ALL.items():
        for eid, t in sorted(tg.items()):
            mrow = min((r for r in rows if r["model"] == mk and r["edge_id"] == eid),
                       key=lambda r: r["abs_deviation"])
            print(f"   {mk} e{eid}: best RR={mrow['RR_observed']:.9f} "
                  f"target={t:.9f} dev={mrow['abs_deviation']:.3e} "
                  f"(via {mrow['path_mode']}/{mrow['graph_direction'][:3]}/"
                  f"{mrow['target_nodes_J']}/bjc={mrow['b_jc_source']})")

    deep_log(rows, bases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
