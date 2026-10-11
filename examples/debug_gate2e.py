"""Sweep H8: definisi himpunan target J (semua node, b dari reaksi; non-support -> beta/|V_T|)."""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
T1 = {0: 7/17, 1: 10/17}

def all_simple_paths(g,s,t):
    out=[]
    def dfs(node,ue,un,acc):
        if node==t and acc: out.append(tuple(acc))
        for eid in g.adj[node]:
            if eid in ue: continue
            nxt=g.other(eid,node)
            if nxt in un: continue
            ue.add(eid);un.add(nxt);acc.append(eid)
            dfs(nxt,ue,un,acc)
            acc.pop();un.discard(nxt);ue.discard(eid)
    dfs(s,set(),{s},[])
    return out

def phi(g,s,t,cost,cfg):
    om=A.rank_weights(int(cfg["K"]),cfg["gamma"]); eps_d=cfg["eps_d"]; K=int(cfg["K"])
    ps=all_simple_paths(g,s,t)
    best=0.0
    for r in range(1,K+1):
        for subset in itertools.combinations(ps,r):
            seen=set();ok=True
            for p in subset:
                for e in p:
                    if e in seen: ok=False;break
                    seen.add(e)
                if not ok: break
            if not ok: continue
            ds=sorted(sum(cost[e] for e in p) for p in subset)
            best=max(best,sum(om[i]/(d+eps_d) for i,d in enumerate(ds)))
    return best

def graph_score(am,wm,cfg,jmode):
    base_w=A.base_weights_of(am)
    weights={eid:w*wm.get(eid,1.0) for eid,w in base_w.items()}
    def _cost(w): return 1.0/cfg["eps_removed"] if w==0.0 else 1.0/(w+cfg["eps_w"])
    cost={eid:_cost(w) for eid,w in weights.items()}
    g=A.Multigraph([int(n["id"]) for n in am.model["nodes"]],am.edges)
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    vt=len(am.support_nodes); vn=len(g.nodes)
    floor = cfg["beta"]/vt
    b_map={}
    for nid in g.nodes:
        mag=A._mag(am.reactions.get(nid,{}),am.dim)
        if jmode=="allnodes_bfloor":   # non-support dapat floor, support dapat floor+(1-b)*r/Bc
            b_map[nid]= floor + ((1.0-cfg["beta"])*mag/bc if bc>0 and nid in am.reactions else 0.0)
        elif jmode=="allnodes_floor_only":  # non-support HANYA floor (tanpa (1-beta) utk support? tidak) -- skip
            pass
    total=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i_node,a_w in ai.items():
            for j_node,b_w in b_map.items():
                if j_node==i_node: continue
                total+=a_w*b_w*phi(g,i_node,j_node,cost,cfg)
    return total

models={m["id"]:m for m in load_models("examples/verification_models.json")}
cfg=A.merged_config()
for mid,target in (("M3_square_one_diagonal",T3),("M1_parallel_bars_1d",T1)):
    am=A.build_ari_model(models[mid],cfg)
    s_base=graph_score(am,{},cfg,"allnodes_bfloor")
    parts=[];devs=[]
    for eid in sorted(target):
        sd=graph_score(am,{eid:0.0},cfg,"allnodes_bfloor")
        rr=sd/s_base; devs.append(abs(rr-target[eid]))
        parts.append(f"e{eid}:RR={rr:.6f}(tgt{target[eid]:.6f})")
    print(f"[J=allnodes_bfloor] [{mid}] S_base={s_base:.6f} "+" ".join(parts)+f" || worst={max(devs):.6f}")
