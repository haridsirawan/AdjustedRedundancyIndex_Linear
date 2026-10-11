"""Sweep H18: a_i dari reaksi (support ∩ loaded), b_j = beta/|V_T| + (1-beta)|R_j|/Bc, J=tumpuan."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models
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

bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
vt=len(am.support_nodes)
b_map={nid:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in am.support_nodes}

def score(mult,anorm):
    weights={eid:w*mult.get(eid,1.0) for eid,w in base_w.items()}
    cost={eid:(1/cfg["eps_removed"] if w==0 else 1/(w+cfg["eps_w"])) for eid,w in weights.items()}
    tot=0.0
    for case in A._load_cases(am):
        ai={nid:A._mag(am.reactions.get(nid,{}),am.dim) for nid in case["f"]}
        ssum=sum(ai.values())
        if anorm=="global": ai={k:v/bc for k,v in ai.items()}
        else: ai={k:v/ssum for k,v in ai.items()}
        for i,a in ai.items():
            if a==0: continue
            for j,b in b_map.items():
                if j==i: continue
                tot+=a*b*phi(cost,i,j)
    return tot

for anorm in ("global","case"):
    sb=score({},anorm)
    parts=[];devs=[]
    for eid,tgt in sorted(T3.items()):
        rr=score({eid:0.0},anorm)/sb; devs.append(abs(rr-tgt)); parts.append(f"e{eid}:{rr:.6f}")
    print(f"a=reaction/{anorm}: "+" ".join(parts)+f" worst={max(devs):.6f}")
