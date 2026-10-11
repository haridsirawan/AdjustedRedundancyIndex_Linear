"""Diagnostik Gate 2 — sweep konvensi untuk mereproduksi Tabel 4.3 (M3) dan Tabel 4.11 (M1).

Hipotesis yang di-sweep:
  H1 eps_removed ∈ {1e-8, 1e-9}
  H2 b_jc dari reaksi INTAK vs DISRUPTED
  H4 penjumlahan jalur dalam Phi: rank-terurut vs posisi-independen (max over subsets)
Target M3 RR: e1=0.983152 e2=0.964724 e3=1.0 e4=1.0 e5=0.717285
Target M1 RR: bar0=7/17=0.411765 bar1=10/17=0.588235
"""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models, solve_model
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
T1 = {0: 7/17, 1: 10/17}

def combos_paths(graph, s, t, K):
    """Semua kombinasi <=K jalur edge-disjoint."""
    c, st = A.enumerate_edge_disjoint_paths(graph, s, t, K)
    return c, st

def phi_val(graph, s, t, cost, cfg, mode):
    K = int(cfg["K"]); om = A.rank_weights(K, cfg["gamma"]); eps_d = cfg["eps_d"]
    combos, st = combos_paths(graph, s, t, K)
    if st != "certified": return float("nan"), st
    best = 0.0; any_ = False
    for combo in combos:
        ds_all = [sum(cost[e] for e in p) for p in combo]
        r = len(ds_all)
        if mode == "ranked":          # omega per rank setelah sorting menaik
            cand = sum(om[i]/(d+eps_d) for i, d in enumerate(sorted(ds_all)))
        else:                          # posisi-independen: setiap subset dievaluasi dg om[:len]
            cand = 0.0
            for ksub in range(1, r+1):
                for sub in itertools.combinations(range(r), ksub):
                    v = sum(om[i]/(ds_all[j]+eps_d) for i, j in enumerate(sorted(sub, key=lambda x: ds_all[x])))
                    cand = max(cand, v)
        if cand > best: best, any_ = cand, True
    return (best if any_ else 0.0), st

def graph_score(am, wm, cfg, dis_react=None, mode="ranked"):
    base_w = A.base_weights_of(am)
    weights = {eid: w*wm.get(eid, 1.0) for eid, w in base_w.items()}
    graph = A.Multigraph([int(n["id"]) for n in am.model["nodes"]], am.edges)
    def _cost(w):
        if w == 0.0: return 1.0/cfg["eps_removed"]
        return 1.0/(w + cfg["eps_w"])
    cost = {eid: _cost(w) for eid, w in weights.items()}
    reacts = dis_react if dis_react is not None else am.reactions
    bc = sum(A._mag(rc, am.dim) for rc in reacts.values())
    vt = len(am.support_nodes); b_map = {}
    for nid in am.support_nodes:
        mag = A._mag(reacts.get(nid, {}), am.dim)
        b_map[nid] = cfg["beta"]/vt + (1.0-cfg["beta"])*(mag/bc if bc > 0 else 0.0)
    total = 0.0
    for case in A._load_cases(am):
        fc = sum(abs(v) for c in case["f"].values() for v in c.values())
        ai = {nid: A._mag(c, am.dim)/fc for nid, c in case["f"].items()}
        for i_node, a_w in ai.items():
            for j_node, b_w in b_map.items():
                p, st = phi_val(graph, i_node, j_node, cost, cfg, mode)
                if st != "certified": return float("nan"), st
                total += a_w*b_w*p
    return total, "ok"

def reactions_from(model):
    res = solve_model(model)
    if res.status != "ok": return None
    comps = ["ux","uy","uz"]; dim = int(model.get("dimension",2)); out = {}
    for dof, val in res.reactions.items():
        out.setdefault(dof//dim, {})[comps[dof%dim]] = val
    return out

models = {m["id"]: m for m in load_models("examples/verification_models.json")}
for mid, target in (("M3_square_one_diagonal", T3), ("M1_parallel_bars_1d", T1)):
    mdl = models[mid]
    print(f"\n########## {mid} ##########")
    for eps_rem in (1e-8, 1e-9):
        for mode in ("ranked", "posfree"):
            for use_dis in ((False, True) if mid.startswith("M3") else (False,)):
                cfg = A.merged_config(eps_removed=eps_rem)
                am = A.build_ari_model(mdl, cfg)
                s_base, st = graph_score(am, {}, cfg, mode=mode)
                rows = []
                for eid in sorted(target):
                    dr = reactions_from(A._apply_stiffness_multiplier(mdl, {eid: 0.0}, drop_zero=True)) if use_dis else None
                    if use_dis and dr is None:
                        rows.append((eid, None, target[eid], "rank_def")); continue
                    sd, st2 = graph_score(am, {eid: 0.0}, cfg, dis_react=dr, mode=mode)
                    rows.append((eid, sd/s_base, target[eid], st2))
                devs = [abs(r[1]-r[2]) for r in rows if r[1] is not None]
                worst = max(devs) if devs else float('inf')
                tag = f"eps_rem={eps_rem:.0e} mode={mode:8s} b={'DISR' if use_dis else 'INT'}"
                print(f"  [{tag}] S_base={s_base:.6f} worst_dev={worst:.6f}")
                for eid, rr, tg, stt in rows:
                    if rr is None: print(f"     e{eid}: {stt}")
                    else: print(f"     e{eid}: RR={rr:.6f} tgt={tg:.6f} dev={abs(rr-tg):.6f}")
