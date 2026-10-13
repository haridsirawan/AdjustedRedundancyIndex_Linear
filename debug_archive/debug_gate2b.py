"""Sweep H5/H6: arah edge vs pasangan (i,j) + definisi himpunan jalur P^K."""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
T1 = {0: 7/17, 1: 10/17}

def make_graph(edges, directed):
    nodes = sorted({e["i"] for e in edges} | {e["j"] for e in edges})
    g = A.Multigraph(nodes, edges)
    if directed:
        g.adj = {n: [] for n in nodes}
        for eid, (i, j) in g.edges.items():   # arah i->j sesuai urutan elemen
            g.adj[i].append(eid)
    return g

def dfs_directed(g, s, t, K, pathset):
    """pathset: 'all' semua jalur berarah; 'simple_shortest': per node hanya lanjut jika belum di jalur."""
    paths = []
    def dfs(node, used_e, used_n, acc):
        if node == t and acc:
            paths.append(tuple(acc)); return
        for eid in g.adj.get(node, []):
            if eid in used_e: continue
            nxt = g.other(eid, node)
            if nxt in used_n: continue
            used_e.add(eid); used_n.add(nxt); acc.append(eid)
            dfs(nxt, used_e, used_n, acc)
            acc.pop(); used_n.discard(nxt); used_e.discard(eid)
    dfs(s, set(), {s}, [])
    return paths

def phi(gsrc_edges, s, t, cost, cfg, mode):
    K = int(cfg["K"]); om = A.rank_weights(K, cfg["gamma"]); eps_d = cfg["eps_d"]
    g = make_graph(gsrc_edges, directed=(mode=="directed"))
    paths = dfs_directed(g, s, t, K, 'all')
    best = 0.0
    for r in range(1, min(K, len(paths))+1 if paths else 1):
        pass
    for rr in range(1, K+1):
        for subset in itertools.combinations(paths, rr):
            seen=set(); ok=True
            for p in subset:
                for e in p:
                    if e in seen: ok=False;break
                    seen.add(e)
                if not ok: break
            if not ok: continue
            ds = sorted(sum(cost[e] for e in p) for p in subset)
            v = sum(om[i]/(d+eps_d) for i,d in enumerate(ds))
            best = max(best, v)
    return best

def graph_score(am, wm, cfg, mode):
    base_w = A.base_weights_of(am)
    weights = {eid: w*wm.get(eid,1.0) for eid,w in base_w.items()}
    def _cost(w):
        if w==0.0: return 1.0/cfg["eps_removed"]
        return 1.0/(w+cfg["eps_w"])
    cost={eid:_cost(w) for eid,w in weights.items()}
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    vt=len(am.support_nodes); b_map={}
    for nid in am.support_nodes:
        mag=A._mag(am.reactions.get(nid,{}),am.dim)
        b_map[nid]=cfg["beta"]/vt+(1.0-cfg["beta"])*(mag/bc if bc>0 else 0.0)
    total=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i_node,a_w in ai.items():
            for j_node,b_w in b_map.items():
                total+=a_w*b_w*phi(am.edges,i_node,j_node,cost,cfg,mode)
    return total

models={m["id"]:m for m in load_models("examples/verification_models.json")}
for mid,target in (("M3_square_one_diagonal",T3),("M1_parallel_bars_1d",T1)):
    mdl=models[mid]; cfg=A.merged_config()
    print(f"\n##### {mid} : mode=directed (hanya jalur searah definisi elemen)")
    am=A.build_ari_model(mdl,cfg)
    s_base=graph_score(am,{},cfg,"directed")
    print(f"  S_base(directed)={s_base:.6f}")
    for eid in sorted(target):
        sd=graph_score(am,{eid:0.0},cfg,"directed")
        rr=sd/s_base
        print(f"  e{eid}: RR={rr:.6f} tgt={target[eid]:.6f} dev={abs(rr-target[eid]):.6f}")
