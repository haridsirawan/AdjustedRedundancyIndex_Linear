"""Sweep H16: a_i dari reaksi, b_j uniform 1/|V_T|."""
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

def score(mult,aweight,bset):
    weights={eid:w*mult.get(eid,1.0) for eid,w in base_w.items()}
    cost={eid:(1/cfg["eps_removed"] if w==0 else 1/(w+cfg["eps_w"])) for eid,w in weights.items()}
    Js = am.support_nodes if bset=="supports" else sorted(g.nodes)
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    tot=0.0
    for case in A._load_cases(am):
        if aweight=="uniform":
            ai={nid:1.0/len(case["f"]) for nid in case["f"]}
        elif aweight=="reaction":
            ai={nid:A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in case["f"]}
        elif aweight=="force_mag":
            fc=sum(abs(v) for c in case["f"].values() for v in c.values())
            ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        bw=1.0/len(Js)
        for i,a in ai.items():
            for j in Js:
                if j==i: continue
                tot+=a*bw*phi(cost,i,j)
    return tot

for aw in ("uniform","reaction","force_mag"):
  for bs in ("supports","allnodes"):
    sb=score({},aw,bs)
    parts=[];devs=[]
    for eid,tgt in sorted(T3.items()):
        rr=score({eid:0.0},aw,bs)/sb; devs.append(abs(rr-tgt))
        parts.append(f"e{eid}:{rr:.6f}")
    print(f"a={aw:10s} J={bs:9s}: "+" ".join(parts)+f" worst={max(devs):.6f}")
