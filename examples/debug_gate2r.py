"""Sweep H20: b_jc dari reaksi state TERDISRUPSI (bisa None/rank-def) dengan agregasi penuh."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models, solve_model
import ari_core as A

T3={1:0.983152,2:0.964724,3:1.0,4:1.0,5:0.717285}
mdl=next(m for m in load_models("examples/verification_models.json") if m["id"]=="M3_square_one_diagonal")
cfg=A.merged_config()
am=A.build_ari_model(mdl,cfg)
base_w=A.base_weights_of(am)
g=A.Multigraph([int(n["id"]) for n in mdl["nodes"]],am.edges)

def phi(cost,s,t):
    om=A.rank_weights(2,cfg["gamma"]);eps_d=cfg["eps_d"]
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
    for r in (1,2):
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

def dis_reactions(eid):
    d=A._apply_stiffness_multiplier(mdl,{eid:0.0},drop_zero=True)
    res=solve_model(d)
    if res.status!="ok": return "RANK_DEF"
    comps=["ux","uy","uz"];dim=int(mdl.get("dimension",2));out={}
    for dof,val in res.reactions.items():
        out.setdefault(dof//dim,{})[comps[dof%dim]]=val
    return out

def score(mult,bsrc):
    weights={eid:w*mult.get(eid,1.0) for eid,w in base_w.items()}
    cost={eid:(1/cfg["eps_removed"] if w==0 else 1/(w+cfg["eps_w"])) for eid,w in weights.items()}
    reacts = am.reactions if bsrc=="intact" else bsrc  # bsrc can be dict or 'RANK_DEF'
    if reacts=="RANK_DEF": return "RANK_DEF"
    bc=sum(A._mag(rc,am.dim) for rc in reacts.values())
    vt=len(am.support_nodes)
    b_map={nid:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(reacts.get(nid,{}),am.dim)/bc for nid in am.support_nodes}
    tot=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                tot+=a*b*phi(cost,i,j)
    return tot

sb=score({},"intact")
for eid,tgt in sorted(T3.items()):
    dr=dis_reactions(eid)
    if dr=="RANK_DEF":
        print(f"e{eid}: RANK-DEF (solver gagal) -> tgt {tgt}")
        continue
    sd=score({eid:0.0},dr)
    rr=sd/sb
    print(f"e{eid}: RR_disr={rr:.6f} tgt={tgt:.6f} dev={abs(rr-tgt):.6f}")
