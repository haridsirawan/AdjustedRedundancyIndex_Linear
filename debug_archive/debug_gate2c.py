"""Sweep H6: pembatas himpunan jalur P^K_ij.
mode 'all_simple' : semua jalur simple (perilaku saat ini)
mode 'shortest'   : hanya jalur TERPENDEK (min hops); jika beberapa dengan hop sama -> semua
mode 'k_shortest' : K jalur distinct terpendek per panjang-hop unik (satu representative min-cost per hop)
"""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
T1 = {0: 7/17, 1: 10/17}

def all_simple_paths(g, s, t):
    out=[]
    def dfs(node, used_e, used_n, acc):
        if node==t and acc: out.append(tuple(acc))
        for eid in g.adj[node]:
            if eid in used_e: continue
            nxt=g.other(eid,node)
            if nxt in used_n: continue
            used_e.add(eid); used_n.add(nxt); acc.append(eid)
            dfs(nxt,used_e,used_n,acc)
            acc.pop(); used_n.discard(nxt); used_e.discard(eid)
    dfs(s,set(),{s},[])
    return out

def path_set(g, s, t, cost, K, mode):
    paths = all_simple_paths(g,s,t)
    if not paths: return []
    if mode=="all_simple": return paths
    hopmin = min(len(p) for p in paths)
    if mode=="shortest":
        return [p for p in paths if len(p)==hopmin]
    if mode=="k_rep_per_hop":
        # representative per jumlah-hop: jalur dengan cost terkecil; ambil max K
        by_len={}
        for p in paths:
            c=sum(cost[e] for e in p)
            L=len(p)
            if L not in by_len or c<by_len[L][1]: by_len[L]=(p,c)
        cand=sorted(by_len.values(), key=lambda x:x[1])
        return [p for p,_ in cand[:K]]
    raise ValueError(mode)

def phi(g,s,t,cost,cfg,mode):
    om=A.rank_weights(int(cfg["K"]),cfg["gamma"]); eps_d=cfg["eps_d"]
    K=int(cfg["K"])
    ps=path_set(g,s,t,cost,K,mode)
    best=0.0
    for r in range(1,K+1):
        for subset in itertools.combinations(ps,r):
            seen=set(); ok=True
            for p in subset:
                for e in p:
                    if e in seen: ok=False;break
                    seen.add(e)
                if not ok: break
            if not ok: continue
            ds=sorted(sum(cost[e] for e in p) for p in subset)
            v=sum(om[i]/(d+eps_d) for i,d in enumerate(ds))
            best=max(best,v)
    return best

def graph_score(am,wm,cfg,mode):
    base_w=A.base_weights_of(am)
    weights={eid:w*wm.get(eid,1.0) for eid,w in base_w.items()}
    def _cost(w):
        if w==0.0: return 1.0/cfg["eps_removed"]
        return 1.0/(w+cfg["eps_w"])
    cost={eid:_cost(w) for eid,w in weights.items()}
    g=A.Multigraph([int(n["id"]) for n in am.model["nodes"]],am.edges)
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
                total+=a_w*b_w*phi(g,i_node,j_node,cost,cfg,mode)
    return total

models={m["id"]:m for m in load_models("examples/verification_models.json")}
cfg=A.merged_config()
for mode in ("shortest","k_rep_per_hop"):
    print(f"\n=============== MODE {mode} ===============")
    for mid,target in (("M3_square_one_diagonal",T3),("M1_parallel_bars_1d",T1)):
        am=A.build_ari_model(models[mid],cfg)
        s_base=graph_score(am,{},cfg,mode)
        print(f"  [{mid}] S_base={s_base:.6f}")
        for eid in sorted(target):
            sd=graph_score(am,{eid:0.0},cfg,mode)
            rr=sd/s_base if s_base>0 else float('nan')
            print(f"    e{eid}: RR={rr:.6f} tgt={target[eid]:.6f} dev={abs(rr-target[eid]):.6f}")
