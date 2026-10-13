"""
test_bound_enhancement.py
=========================

Unit tests Gate Pre-Analysis (Task 4) pada model kanonik M1 & M3, sesuai
instruksi Section 4.9 (toleransi konservatisme bound).

Cakupan:
  (a) M1: pelemahan bar di lambda=0.25 -> solusi elastik eksak u=2 mm,
      gaya 10+20 kN, kedua utilisasi = 1; bound U_s WAJIB >= 1 (konservatif).
  (b) M3: penghapusan e3 (zero initial force) -> regresi Tabel 4.4:
      h_e = 1.000000, m_e(0) ~ 0, rank 4/5, guard kinematik yang meneruskan
      (per urutan Eq 4.13 langkah 1 — bound menjadi unusable_m_near_zero).
  (c) Kontrol lambda=1: semua bound = nilai intak, tanpa trigger.
  (d) lambda=0 hapus-total batang pemikul beban: m_e -> 1-h_e, bound harus
      memicu bila batang tersisa tak sanggup memikul.
  (+) Regresi target Gate 2: RR M1 7/17 & 10/17, RR M3 e3/e4 = 1 — bounds
      TIDAK BOLEH mengubah angka ARI (DIAGNOSIS.md constraint).

Exit code 0 = semua lulus.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss_reference import solve_model, load_models                 # noqa
from ari_core import build_ari_model, compute_ari                    # noqa
from bound_enhancement import BoundCache                             # noqa

FAILS = []


def check(name, cond, info=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name} {info}")
    if not cond:
        FAILS.append(name)


def main() -> int:
    here = Path(__file__).resolve().parent
    models = {m["id"]: m for m in load_models(here / "verification_models.json")}
    M1, M3 = models["M1_parallel_bars_1d"], models["M3_square_one_diagonal"]

    print("(a) M1 weakening bar at lambda=0.25 — elastic reference vs bound")
    bc1 = BoundCache(M1)
    # Verifikasi eksak (solver Gate 1, bukan asumsi): pada M1 kanonik
    # (A=[100,50] mm2, R=[40,20] kN, P=30 kN, L=1000 mm, E=200), pelemahan
    # BAR-0 pada lambda=0.25 menyamakan kekakuan (EA_eff=25000=kN keduanya)
    # sehingga gaya terbagi rata N=[10,20] kN PROPORTIONAL-KAPASITAS ->
    # utilisasi bar-1 TEPAT 1.0. Catatan: angka "u=2mm, forces 10+20" pada
    # brief task benar; klaim "both U=1" TIDAK konsisten dgn skala kanonik
    # (U_bar0=0.25) — dicatat jujur, kontrak yang diuji = KONSERVATISME:
    #   U_s(bound) >= max_j U(exact)  dan  D_j >= |N_j| exact utk semua j.
    import copy
    lam = 0.25
    weakened = copy.deepcopy(M1)
    for el in weakened["elements"]:
        if int(el["id"]) == 0:                 # bar-0 diperlemah
            el["area"] = float(el["area"]) * lam
    res_w = solve_model(weakened)
    check("elastic u_max == 2.0 mm", abs(res_w.umax - 2.0) < 1e-9,
          f"(actual {res_w.umax:.6f})")
    forces = list(np.abs(res_w.element_forces))
    check("elastic forces 10 & 20 kN",
          abs(forces[0] - 10.0) < 1e-8 and abs(forces[1] - 20.0) < 1e-8,
          f"(actual {forces})")
    utils = np.array([abs(n) / c for n, c in
                      zip(res_w.element_forces,
                          [M1["capacities"]["0"], M1["capacities"]["1"]])])
    check("elastic utilization bar-1 == 1.0 (bound must be >= 1)",
          abs(utils[1] - 1.0) < 1e-9, f"(actual {list(utils)})")
    # konservatisme bound terhadap solusi elastik EXACT yang sama:
    fb0 = bc1.compute_force_bound(0, lam)      # e = bar-0 (target task a)
    check("bound U_s(e0,lam=0.25) >= 1 (= exact max utilization)",
          fb0["U_s"] >= utils.max() - 1e-12 and fb0["U_s"] >= 1.0 - 1e-12,
          f"(U_s={fb0['U_s']:.4f} vs exact {utils.max():.4f})")
    check("bound D_j >= |N_j| exact utk SEMUA j (upper bound valid)",
          all(fb0["D_j"][j] >= abs(res_w.element_forces[j]) - 1e-9
              for j in range(2)),
          f"(D={[round(v,4) for v in fb0['D_j'].values()]})")
    # varian interpretasi task: pelemahan bar-1 juga harus bound >= 1? Tidak
    # otomatis; cek konservatisme thd exact saja + trigger utk bar-0 removal.
    for eb in (0, 1):
        fb = bc1.compute_force_bound(eb, lam)
        check(f"M1 bound U_s(e{eb},lam={lam}) >= exact-max ({utils.max():.3f})",
              fb["U_s"] >= utils.max() - 1e-12,
              f"(U_s={fb['U_s']:.4f}, status={fb['status']})")

    print("(b) M3 removal of e3 (zero initial force) — regresi Tabel 4.4")
    bc3 = BoundCache(M3)
    check("N0[e3] == 0", abs(bc3.facts.N0[3]) < 1e-12)
    check("h_e(e3) == 1.000000 (SVD; Tabel 4.4)",
          abs(bc3.facts.h[3] - 1.0) < 1e-9, f"(h={bc3.facts.h[3]:.6f})")
    m_e = bc3.m_factor(3, 0.0)
    check("m_e(lam=0) ~ 0 (Tabel 4.4: 1.11e-16)", abs(m_e) < 1e-12,
          f"(m={m_e:.2e})")
    fb = bc3.compute_force_bound(3, 0.0)
    check("force bound 'unusable_m_near_zero' (urutan Eq 4.13: kinematik dulu)",
          fb["status"] == "unusable_m_near_zero", f"(status={fb['status']})")
    db = bc3.compute_displacement_bound(3, 0.0)
    check("disp bound 'unusable_m_near_zero'",
          db["status"] == "unusable_m_near_zero", f"(status={db['status']})")

    print("(c) lambda=1 control — bounds equal intact values, no triggers")
    for bc, name in ((bc1, "M1"), (bc3, "M3")):
        for eid in bc.facts.edge_ids:
            fb = bc.compute_force_bound(eid, 1.0)
            db = bc.compute_displacement_bound(eid, 1.0)
            ok_f = fb["g_C"] == 0 and all(
                abs(fb["D_j"][j] - abs(bc.facts.N0[j])) < 1e-9
                for j in bc.facts.edge_ids)
            ok_d = db["g_D"] == 0 and abs(db["d_s"] - db["d_0"]) < 1e-9 \
                and abs(db["A_s"] - 1.0) < 1e-12
            check(f"{name} e{eid} lam=1 force==intact", ok_f)
            check(f"{name} e{eid} lam=1 disp==intact", ok_d)

    print("(d) lambda=0 complete removal of load-bearing bar — trigger")
    fb = bc1.compute_force_bound(1, 0.0)     # bar1 (pemikul) dihapus
    check("M1 remove bar1: g_C==1 (bar0 overloaded)", fb["g_C"] == 1,
          f"(U_s={fb['U_s']:.4f} on edge {fb['triggering_bar']})")
    fb0 = bc1.compute_force_bound(0, 0.0)
    check("M1 remove bar0: m_e -> 1-h_e", abs(fb0["m_s"] - (1 - fb0["h_e"]))
          < 1e-12, f"(m={fb0['m_s']:.4f})")
    check("M1 remove bar0: g_C==1 (bar1 overloaded)", fb0["g_C"] == 1,
          f"(U_s={fb0['U_s']:.4f})")

    print("(+) Regresi Gate 2 — bounds tidak mengubah angka ARI")
    am1 = build_ari_model(M1)
    base1 = compute_ari(am1)
    r0 = compute_ari(am1, (0, 0.0), baseline=(base1.S, base1.status))
    r1 = compute_ari(am1, (1, 0.0), baseline=(base1.S, base1.status))
    check("M1 RR(e0,0)==7/17", abs(r0.RR - 7 / 17) < 1e-6, f"({r0.RR:.9f})")
    check("M1 RR(e1,0)==10/17", abs(r1.RR - 10 / 17) < 1e-6, f"({r1.RR:.9f})")
    am3 = build_ari_model(M3)
    base3 = compute_ari(am3)
    r3 = compute_ari(am3, (3, 0.0), baseline=(base3.S, base3.status))
    check("M3 RR(e3,0)==1.0", abs(r3.RR - 1.0) < 1e-9, f"({r3.RR})")

    print("\nRESULT:", "ALL PASS" if not FAILS else f"FAILED: {FAILS}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    sys.exit(main())
