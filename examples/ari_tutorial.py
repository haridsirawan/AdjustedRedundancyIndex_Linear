"""
ari_tutorial.py — Tutorial langkah-demi-langkah rantai ARI (contoh dua batang)
==============================================================================

Rujukan naskah: Bagian 4.5.6/4.5.9 (Kode 4.2) — paket prototipe "memperluas
contoh dua batang menjadi enumerasi graf kecil dan solver batang aksial
1D/2D". Skrip ini mendemonstrasikan SELURUH rantai perhitungan pada model
kanonik M1 (dua batang paralel) dengan angka antara dicetak, ditutup
verifikasi nilai analitis Tabel 4.11 (limit regularisasi nol):
RR = 7/17 dan 10/17.

Jalankan: python examples/ari_tutorial.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ari_core as ac                                   # noqa: E402
from truss_reference import load_models                 # noqa: E402

EXACT = {                                # Tabel 4.11 (limit epsilon -> 0)
    "bar0": dict(RR=7 / 17, ARI=21 / 68, CI=47 / 68),
    "bar1": dict(RR=10 / 17, ARI=15 / 34, CI=19 / 34),
}


def main() -> int:
    print("=" * 78)
    print("TUTORIAL ARI — model M1 (dua batang paralel 1D)")
    print("=" * 78)

    model = load_models(ROOT / "examples" / "verification_models.json")[0]
    am = ac.build_ari_model(model)
    cfg = am.config
    res = am.result

    print("\n[0] Solver referensi, state utuh (Bagian 4.1.3):")
    print(f"    u      = {res.displacements} mm")
    print(f"    N_e    = {res.element_forces} kN  (batang 0: 100 mm^2; "
          f"batang 1: 50 mm^2)")
    print(f"    reaksi = {res.reactions} kN (utk gaya 30 kN di ujung bebas)")
    print(f"    U_max  = {res.Umax:.6f} ; W = {res.strain_energy:.6f} kN.mm")

    print("\n[1] Bobot edge  w_e = q_e (alpha_k k_hat_e + alpha_R r_hat_e)  "
          "(Eq 2.5-2.7):")
    w = ac.base_weights_of(am)
    s = am.scales
    for eid, val in sorted(w.items()):
        k = am.k_raw[eid]
        cap = float(model["capacities"][str(eid)])
        k_hat = k / (k + s["s_k"])
        r_hat = cap / (cap + s["s_R"])
        print(f"    e{eid}: k_e = {k:.4f} (k_hat = {k_hat:.6f}) | "
              f"R_e = {cap:.1f} (r_hat = {r_hat:.6f})")
        print(f"          w_{eid} = 0.5*{k_hat:.6f} + 0.5*{r_hat:.6f} "
              f"= {val:.6f}   (tak berdimensi)")

    print("\n[2] Biaya sisi & skor pasangan  (Eq 2.8-2.10):")
    edge_cost = {eid: 1.0 / (v + cfg["eps_w"]) for eid, v in w.items()}
    for eid, cval in sorted(edge_cost.items()):
        print(f"    c_{eid} = 1/(w_{eid} + eps_w) = {cval:.6f}")
    graph = ac.Multigraph([int(n["id"]) for n in model["nodes"]], am.edges)
    phi, st = ac.compute_pair_score(graph, 1, 0, edge_cost, cfg)
    print(f"    Lintasan 1->0: {{e0}}, {{e1}}, dan kombinasi bebas-sisi "
          f"{{e0,e1}}")
    print(f"    Phi^(2)_(1,0) = max = {phi:.6f}   (status: {st})")

    print("\n[3] Agregasi S(G)  (Eq 2.11-2.13):")
    c0 = ac._prepare_cases(am)[0]
    print(f"    Kasus beban {c0['name']}: F_c = {c0['F']:.3f} kN ; "
          f"a_ic = {c0['a']}")
    print(f"    Reaksi komponen searah c: r_jc = {c0['r']} ; "
          f"B_c = {c0['B']:.3f}")
    print(f"    b_jc = {({k: round(v, 6) for k, v in c0['b'].items()})} ; "
          f"pi_c = {c0['pi']:.6f}")
    s_base, st_b = ac.compute_graph_score(am)
    print(f"    S(G_M) = {s_base:.9f}  ({st_b})")

    print("\n[4] Skenario s = (e, lambda)  ->  RR / ARI / CI  (Eq 2.14-2.19):")
    ok = True
    hdr = (f"    {'skenario':<18}{'S(s)':>11}{'RR':>11}{'ARI':>11}"
           f"{'CI':>11}   cek analitis")
    print(hdr)
    for eid, key in ((0, "bar0"), (1, "bar1")):
        r = ac.compute_ari(am, (eid, 0.0), baseline=(s_base, st_b))
        t = EXACT[key]
        good = (abs(r.RR - t["RR"]) < 1e-6 and abs(r.ARI - t["ARI"]) < 1e-6
                and abs(r.CI - t["CI"]) < 1e-6)
        ok &= good
        print(f"    {'hapus batang ' + str(eid):<18}{r.S:>11.6f}"
              f"{r.RR:>11.6f}{r.ARI:>11.6f}{r.CI:>11.6f}   "
              f"{t['RR']:.6f} -> {'PASS' if good else 'FAIL'}")
    ctrl = ac.compute_ari(am, None, baseline=(s_base, st_b))
    print(f"    {'kontrol utuh':<18}{ctrl.S:>11.6f}{ctrl.RR:>11.6f}"
          f"{ctrl.ARI:>11.6f}{ctrl.CI:>11.6f}   RR=1 eksak, CI=0")
    r1 = ac.compute_ari(am, (0, 1.0), baseline=(s_base, st_b))
    print(f"    {'kontrol e0 lam=1':<18}{r1.S:>11.6f}{r1.RR:>11.6f}"
          f"{r1.ARI:>11.6f}{r1.CI:>11.6f}   CI = eta*U*_e (Eq 2.19)")

    print("\n[5] Catatan:")
    print("    * 7/17, 10/17, 21/68, 15/34 adalah nilai EKSAK limit "
          "regularisasi nol (Tabel 4.11); kode memakai eps_w = eps_d = 1e-9.")
    print("    * lambda = 0 pada graf = PENGHAPUSAN sisi (Bagian 2.8); "
          "0 < lambda <= 1 -> w_e := lambda*w_e tanpa renormalisasi.")
    print("    * Verifikasi penuh 4 model: python examples/run_verification.py")
    print("\nTUTORIAL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
