"""Sweep H14: (a) S = Phi^2 saja (tanpa bobot a,b); (b) b_jc ∝ panjang jalur terpendek."""
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

def paths_all(s,t):
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

def phi(cost,s,t):
    om=A.rank_weights(2,cfg["gamma"]);eps_d=cfg["eps_d"]
    ps=paths_all(s,t); best=0.0
    for r in (1,2):
        for subset in itertools.combinations(ps,r):
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

def hops(s,t):
    ps=paths_all(s,t)
    return min((len(p) for p in ps), default=None)

for mode in ("phi_only","pathlen_b"):
    print(f"\n===== {mode} =====")
    def score(mult):
        weights={eid:w*mult.get(eid,1.0) for eid,w in base_w.items()}
        cost={eid:(1/cfg["eps_removed"] if w==0 else 1/(w+cfg["eps_w"])) for eid,w in weights.items()}
        tot=0.0
        for case in A._load_cases(am):
            if mode=="phi_only":
                # S = sum over pairs (i in loaded, j in support) Phi(i,j) dinormalisasi jumlah pasangan? coba murni sum & rata2
                vals=[phi(cost,i,j) for i in case["f"] for j in am.support_nodes]
                tot+=sum(vals)/len(vals)
            else:
                # b_j ∝ 1/minhops ; a_i uniform
                sup=am.support_nodes
                bl={}
                for i_node in case["f"]:
                    for j in sup:
                        h=hops(i_node,j)
                        bl[(i_node,j)]=(1.0/h) if h else 0.0
                norm=sum(bl.values()) or 1.0
                for i_node in case["f"]:
                    for j in sup:
                        tot+=bl[(i_node,j)]/norm*phi(cost,i_node,j)
        return tot
    sb=score({})
    for eid,tgt in sorted(T3.items()):
        sd=score({eid:0.0}); rr=sd/sb
        print(f"  e{eid}: RR={rr:.6f} tgt={tgt:.6f} dev={abs(rr-tgt):.6f}")
