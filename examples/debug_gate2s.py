"""Sweep H21: a_i = |N_e|/R dari elemen insiden; b_j reaksi; edge terhapus -> cost 1e9."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models, solve_model
import ari_core as A

T3={1:0.983152,2:0.964724,3:1.0,4:1.0,5:0.717285}
mdl=next(m for m in load_models("examples/verification_models.json") if m["id"]=="M3_square_one_diagonal")
cfg=A.merged_config()
res=solve_model(mdl)
dim=int(mdl.get("dimension",2)); comps=["ux","uy","uz"]
pass
# node force map
fmap={}
for dof,val in res.loads.items():
    nid=dof//dim; fmap.setdefault(nid,{})[comps[dof%dim]]=val
# axial forces per element id
ax={}
for eid,N in res.forces.items():
    ax[mdl["elements"][eid]["id"]]=abs(N)
R=sum(abs(v) for v in res.reactions.values())
sup=set(int(s["node"]) for s in mdl["supports"])
bc=sum(A._mag(fmap.get(n,{}),dim) for n in sup)
vt=len(sup)
b_map={n:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(fmap.get(n,{}),dim)/bc for n in sup}
inc={}
for e in mdl["elements"]:
    inc.setdefault(e["i"],[]).append(e["id"]); inc.setdefault(e["j"],[]).append(e["id"])
a_intact={n:sum(ax[e] for e in inc.get(n,[]))/R for n in fmap}

g=A.Multigraph([n["id"] for n in mdl["nodes"]],
               [{"id":e["id"],"i":e["i"],"j":e["j"]} for e in mdl["elements"]])
wbase={e["id"]:0.5 for e in mdl["elements"]}; wbase[4]=0.457107  # cek ulang dari solver? pakai ari_core base
am=A.build_ari_model(mdl,cfg); wbase=A.base_weights_of(am)

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

def score(a_map,mult,epsr):
    cost={eid:(1/epsr if mult.get(eid,1)==0 else 1/(w+cfg["eps_w"])) for eid,w in wbase.items()}
    tot=0.0
    for i,a in a_map.items():
        if a<=0: continue
        for j,b in b_map.items():
            if j==i: continue
            tot+=a*b*phi(cost,i,j)
    return tot

for epsr in (1e-8,1e-9):
    sb=score(a_intact,{},epsr)
    parts=[];devs=[]
    for eid,tgt in sorted(T3.items()):
        rr=score(a_intact,{eid:0.0},epsr)/sb; devs.append(abs(rr-tgt)); parts.append(f"e{eid}:{rr:.6f}")
    print(f"H21 a=|N|/R epsr={epsr:.0e}: "+" ".join(parts)+f" worst={max(devs):.6f}")
