"""Sweep H10: w_eff = max(lambda*w, eps_removed); cost = 1/w_eff (atau /(w_eff+eps_w)); edge tetap di graf."""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
T1 = {0: 7/17, 1: 10/17}

def phi(g,s,t,cost,cfg):
    om=A.rank_weights(int(cfg["K"]),cfg["gamma"]); eps_d=cfg["eps_d"]; K=int(cfg["K"])
    paths=[]
    def dfs(node,ue,un,acc):
        if node==t and acc: paths.append(tuple(acc))
        for eid in g.adj[node]:
            if eid in ue: continue
            nxt=g.other(eid,node)
            if nxt in un: continue
            ue.add(eid);un.add(nxt);acc.append(eid)
            dfs(nxt,ue,un,acc)
            acc.pop();un.discard(nxt);ue.discard(eid)
    dfs(s,set(),{s},[])
    best=0.0
    for r in range(1,K+1):
        for subset in itertools.combinations(paths,r):
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

def graph_score(am,cfg,mult,eps_floor,use_eps_w):
    base_w=A.base_weights_of(am)
    g=A.Multigraph([int(n["id"]) for n in am.model["nodes"]],am.edges)
    cost={}
    for eid,w in base_w.items():
        ww=max(w*mult.get(eid,1.0), eps_floor)
        cost[eid]=1.0/(ww+(cfg["eps_w"] if use_eps_w else 0.0))
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    vt=len(am.support_nodes)
    b_map={nid:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in am.support_nodes}
    total=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                total+=a*b*phi(g,i,j,cost,cfg)
    return total

models={m["id"]:m for m in load_models("examples/verification_models.json")}
cfg=A.merged_config()
for eps_floor in (1e-8,1e-9,1e-10,1e-12):
  for use_eps_w in (True,False):
    print(f"\n===== eps_floor={eps_floor:.0e} +eps_w={use_eps_w} =====")
    for mid,target in (("M3_square_one_diagonal",T3),("M1_parallel_bars_1d",T1)):
        am=A.build_ari_model(models[mid],cfg)
        s_base=graph_score(am,cfg,{},eps_floor,use_eps_w)
        parts=[];devs=[]
        for eid in sorted(target):
            sd=graph_score(am,cfg,{eid:0.0},eps_floor,use_eps_w)
            rr=sd/s_base; devs.append(abs(rr-target[eid]))
            parts.append(f"e{eid}:RR={rr:.6f}")
        print(f"  [{mid}] S_base={s_base:.6f} "+" ".join(parts)+f" worst={max(devs):.6f}")
