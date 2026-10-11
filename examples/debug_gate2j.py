"""Inversi: untuk setiap edge e, cari nilai cost edge terhapus c_rem (edge lain intact)
sehingga RR_e = target Tabel 4.3. Jika solusi unik & konsisten -> konvensi teridentifikasi."""
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

def phi(g,s,t,cost):
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
cases=A._load_cases(am)

def score(cost):
    tot=0.0
    for case in cases:
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                tot+=a*b*phi(g,i,j,cost)
    return tot

cost_intact={eid:1.0/(w+cfg["eps_w"]) for eid,w in base_w.items()}
s_base=score(cost_intact)
print(f"S_base={s_base:.9f}; intact costs: "+", ".join(f"e{k}:{v:.3f}" for k,v in sorted(cost_intact.items())))

for eid,tgt in sorted(T3.items()):
    lo,hi=1.0,1e12
    # RR menurun thd c_rem? cek monotone dulu di dua titik
    def rr_for(c):
        cc=dict(cost_intact); cc[eid]=c
        return score(cc)/s_base
    f_lo=rr_for(lo)-tgt; f_hi=rr_for(hi)-tgt
    if f_lo*f_hi>0:
        print(f"e{eid}: tgt={tgt:.6f} rr(c=1)={rr_for(lo):.6f} rr(c=1e12)={rr_for(hi):.6f} -> TIDAK ADA AKAR (bracket gagal)")
        continue
    for _ in range(80):
        mid=(lo*hi)**0.5
        if (rr_for(mid)-tgt)*(f_lo)>0: hi=mid
        else: lo=mid
    c_star=(lo*hi)**0.5
    w_eff=1.0/c_star if c_star>1 else None
    print(f"e{eid}: tgt={tgt:.6f} -> c_rem*={c_star:.6g} (w_eff=1/c={1/c_star:.6g}) ; eps_equiv≈{1/c_star:.3e}")
