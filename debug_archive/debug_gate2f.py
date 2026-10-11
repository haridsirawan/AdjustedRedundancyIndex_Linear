"""Inversi: cari (eps_removed, cost_floor) yang mereproduksi RR target Tabel 4.3 per-edge."""
import sys, itertools
sys.path.insert(0, "examples")
from truss_reference import load_models
import ari_core as A

T3 = {1: 0.983152, 2: 0.964724, 3: 1.0, 4: 1.0, 5: 0.717285}
mdl = next(m for m in load_models("examples/verification_models.json") if m["id"]=="M3_square_one_diagonal")
cfg = A.merged_config()
am = A.build_ari_model(mdl, cfg)
g = A.Multigraph([int(n["id"]) for n in mdl["nodes"]], am.edges)

def all_simple_paths(s,t):
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

base_w = A.base_weights_of(am)
print("intact weights:", {k: round(v,6) for k,v in base_w.items()})

def score(cost_map):
    om=A.rank_weights(2,cfg["gamma"]); eps_d=cfg["eps_d"]
    bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
    vt=len(am.support_nodes)
    b_map={nid: cfg["beta"]/vt+(1-cfg["beta"])*A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in am.support_nodes}
    total=0.0
    for case in A._load_cases(am):
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                ps=all_simple_paths(i,j); best=0.0
                for r in (1,2):
                    for subset in itertools.combinations(ps,r):
                        seen=set();ok=True
                        for p in subset:
                            for e in p:
                                if e in seen: ok=False;break
                                seen.add(e)
                            if not ok: break
                        if not ok: continue
                        ds=sorted(sum(cost_map[e] for e in p) for p in subset)
                        best=max(best,sum(om[k]/(d+eps_d) for k,d in enumerate(ds)))
                total+=a*b*best
    return total

def mk_cost(eps_rem, floor, mult):
    cost={}
    for eid,w in base_w.items():
        ww=w*mult.get(eid,1.0)
        if ww==0.0: cost[eid]=1.0/eps_rem
        elif floor is not None: cost[eid]=max(1.0/(ww+cfg["eps_w"]), 1.0/floor)
        else: cost[eid]=1.0/(ww+cfg["eps_w"])
    return cost

# floor sebagai nilai w efektif minimum (w_eff = max(w, floor)) -> cost = 1/(w_eff+eps)
for eps_rem in (1e-8,1e-9):
    s_base=score(mk_cost(eps_rem,None,{}))
    print(f"\neps_rem={eps_rem:.0e}: S_base={s_base:.6f}")
    for eid,tgt in sorted(T3.items()):
        # scan floor values
        best=None
        for f in [0.0,1e-6,1e-5,1e-4,3e-4,1e-3,3e-3,1e-2,3e-2,0.05,0.075,0.1,0.15,0.2,0.3,0.5]:
            sd=score(mk_cost(eps_rem,f,{eid:0.0}))
            rr=sd/s_base; dev=abs(rr-tgt)
            if best is None or dev<best[1]: best=(f,dev,rr)
        print(f"  e{eid}: tgt={tgt:.6f} best_floor={best[0]} -> RR={best[2]:.6f} dev={best[1]:.6f}")
