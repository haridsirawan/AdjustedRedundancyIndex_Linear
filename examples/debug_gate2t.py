"""Sweep H22: w_e^M = (L_e/L0)^alpha ; alpha ∈ {-1,1,2}; cost=1/w; removed->1e9."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models
import ari_core as A

T3={1:0.983152,2:0.964724,3:1.0,4:1.0,5:0.717285}
mdl=next(m for m in load_models("examples/verification_models.json") if m["id"]=="M3_square_one_diagonal")
cfg=A.merged_config()
am=A.build_ari_model(mdl,cfg)
nodes={n["id"]:n for n in mdl["nodes"]}
def length(e):
    a,b=nodes[e["i"]]["c"],nodes[e["j"]]["c"]
    return ((a[0]-b[0])**2+(a[1]-b[1])**2)**0.5
L=[length(e) for e in mdl["elements"]]
L0=sum(L)/len(L)
g=A.Multigraph([n["id"] for n in mdl["nodes"]],[{"id":e["id"],"i":e["i"],"j":e["j"]} for e in mdl["elements"]])
sup=set(int(s["node"]) for s in mdl["supports"]); supn=sorted(sup)
loads={}
for item in mdl.get("loads",[]):
    nid=item["node"]; loads.setdefault(nid,{})
    for c,v in item["components"].items(): loads[nid][c]=loads[nid].get(c,0)+v
dim=2
def _mag(d): return sum(v*v for v in d.values())**0.5 if d else 0.0
bc=sum(_mag({k:v for k,v in loads.get(n,{}).items()}) for n in supn) or 1.0
vt=len(supn)
b_map={n:cfg["beta"]/vt+(1-cfg["beta"])*_mag(loads.get(n,{}))/bc for n in supn}

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

def score(alpha,mult):
    cost={}
    for e,l in zip(mdl["elements"],L):
        ww=(l/L0)**alpha*mult.get(e["id"],1.0)
        cost[e["id"]]=1e9 if ww==0 else 1/ww
    tot=0.0
    fc=sum(abs(v) for d in loads.values() for v in d.values())
    ai={n:_mag(d)/fc for n,d in loads.items()}
    for i,a in ai.items():
        for j,b in b_map.items():
            tot+=a*b*phi(cost,i,j)
    return tot

for alpha in (-1,1,2):
    sb=score(alpha,{})
    parts=[];devs=[]
    for eid,tgt in sorted(T3.items()):
        rr=score(alpha,{eid:0.0})/sb; devs.append(abs(rr-tgt)); parts.append(f"e{eid}:{rr:.6f}")
    print(f"H22 L-ratio^{alpha}: "+" ".join(parts)+f" worst={max(devs):.6f}")
