"""Sweep H23: a_i dari REAKSI (|R_i|/Bc), b_j = |F_j|/Fc, J = semua simpul."""
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
dim=2
def _mag(d): return sum(v*v for v in d.values())**0.5 if d else 0.0

res=solve_model(mdl)
comps=["ux","uy","uz"]
react={}
for dof,val in res.reactions.items():
    react.setdefault(dof//dim,{})[comps[dof%dim]]=val
bc=sum(_mag(r) for r in react.values())
a_map={n:_mag(react.get(n,{}))/bc for n in g.nodes}   # reaksi utk i
loads=am.loads
fc=sum(abs(v) for d in loads.values() for v in d.values())
b_map={n:_mag(loads.get(n,{}))/fc for n in g.nodes}   # beban utk j

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

def score(mult):
    cost={eid:(1/cfg["eps_removed"] if w*mult.get(eid,1.0)==0 else 1/(w*mult.get(eid,1.0)+cfg["eps_w"])) for eid,w in base_w.items()}
    tot=0.0
    for i,a in a_map.items():
        if a<=0: continue
        for j,b in b_map.items():
            if b<=0 or j==i: continue
            tot+=a*b*phi(cost,i,j)
    return tot

sb=score({})
parts=[];devs=[]
for eid,tgt in sorted(T3.items()):
    rr=score({eid:0.0})/sb; devs.append(abs(rr-tgt)); parts.append(f"e{eid}:{rr:.6f}")
print(f"H23 a=R/b=F allnodes: "+" ".join(parts)+f" worst={max(devs):.6f}")
