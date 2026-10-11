"""Sweep H13: edge terhapus DIHILANGKAN dari graf (tanpa cost floor)."""
import sys, itertools
sys.path.insert(0,"examples")
from truss_reference import load_models
import ari_core as A

T3={1:0.983152,2:0.964724,3:1.0,4:1.0,5:0.717285}
T1={0:7/17,1:10/17}  # M1: id edge? cek di bawah
mdl3=next(m for m in load_models("examples/verification_models.json") if m["id"]=="M3_square_one_diagonal")
cfg=A.merged_config()

def phi_drop(edges_set, adj_full, s,t,cost,cfg):
    om=A.rank_weights(int(cfg["K"]),cfg["gamma"]);eps_d=cfg["eps_d"];K=int(cfg["K"])
    paths=[]
    def dfs(node,ue,un,acc):
        if node==t and acc: paths.append(tuple(acc))
        for eid in adj_full.get(node,[]):
            if eid not in edges_set or eid in ue: continue
            i,j=edges_map[eid]; nxt=j if node==i else i
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

am=A.build_ari_model(mdl3,cfg)
base_w=A.base_weights_of(am)
edges_map={e["id"]:(e["i"],e["j"]) for e in am.edges}
nodes=sorted({v for pr in edges_map.values() for v in pr})
adj_full={n:[eid for eid,(i,j) in edges_map.items() if n in (i,j)] for n in nodes}
cost_intact={eid:1.0/(w+cfg["eps_w"]) for eid,w in base_w.items()}
bc=sum(A._mag(rc,am.dim) for rc in am.reactions.values())
vt=len(am.support_nodes)
b_map={nid:cfg["beta"]/vt+(1-cfg["beta"])*A._mag(am.reactions.get(nid,{}),am.dim)/bc for nid in am.support_nodes}
cases=A._load_cases(am)

def score(active):
    tot=0.0
    for case in cases:
        fc=sum(abs(v) for c in case["f"].values() for v in c.values())
        ai={nid:A._mag(c,am.dim)/fc for nid,c in case["f"].items()}
        for i,a in ai.items():
            for j,b in b_map.items():
                tot+=a*b*phi_drop(active,adj_full,i,j,cost_intact,cfg)
    return tot

allE=set(base_w)
s_base=score(allE)
print(f"M3 drop-mode: S_base={s_base:.6f}")
for eid,tgt in sorted(T3.items()):
    sd=score(allE-{eid}); rr=sd/s_base
    print(f"  e{eid}: RR={rr:.6f} tgt={tgt:.6f} dev={abs(rr-tgt):.6f}")

# juga cek arah pasangan J->i vs i->J tidak relevan; dan cek target edge id M1 (0-based?)
