"""Sweep H11: p_s = 0.5, eps_w ∈ {1e-9, 1e-8}, eps_removed ∈ {1e-8,1e-9}."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models
import ari_core as A

T3={1:0.983152,2:0.964724,3:1.0,4:1.0,5:0.717285}
T1={0:7/17,1:10/17}

def phi(g,s,t,cost,cfg):
    om=A.rank_weights(int(cfg["K"]),cfg["gamma"]);eps_d=cfg["eps_d"];K=int(cfg["K"])
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

def gs(am,cfg,mult):
    base_w=A.base_weights_of(am)
    g=A.Multigraph([int(n["id"]) for n in am.model["nodes"]],am.edges)
    cost={}
    for eid,w in base_w.items():
        ww=w*mult.get(eid,1.0)
        cost[eid]=1.0/cfg["eps_removed"] if ww==0.0 else 1.0/(ww+cfg["eps_w"])
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    vt=len(am.support_nodes)
    b_map={nid:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in am.support_nodes}
    tot=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                tot+=a*b*phi(g,i,j,cost,cfg)
    return tot

models={m["id"]:m for m in load_models("examples/verification_models.json")}
for ps in (0.5,):
  for epsw in (1e-9,1e-8,1e-6):
    for epsr in (1e-8,1e-9):
      cfg=A.merged_config(alpha_k=ps,alpha_R=1-ps,eps_w=epsw,eps_removed=epsr)
      out=[]
      for mid,target in (("M3_square_one_diagonal",T3),("M1_parallel_bars_1d",T1)):
        am=A.build_ari_model(models[mid],cfg)
        sb=gs(am,cfg,{})
        devs=[];parts=[]
        for eid in sorted(target):
            sd=gs(am,cfg,{eid:0.0});rr=sd/sb;devs.append(abs(rr-target[eid]))
            parts.append(f"e{eid}:{rr:.6f}")
        out.append(f"[{mid[:2]}] "+" ".join(parts)+f" worst={max(devs):.6f}")
      print(f"ps={ps} eps_w={epsw:.0e} eps_rem={epsr:.0e}\n   "+"\n   ".join(out))
