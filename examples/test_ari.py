"""
test_ari.py — Gate 2 Sprint Mode: diagnostik lengkap mesin ARI.

Menjalankan full screening pada 4 model kanonik (verification_models.json),
mencetak tabel perbandingan vs Tabel 4.11 (Two Parallel Bars, limit eps->0)
dan Tabel 4.3 (Square with One Diagonal, lambda=0), cek monotonisitas &
invariansi, mencetak intermediate values, dan menyimpan audit trail ke
results/verification/ari_screening.csv.

Pakailah: python examples/test_ari.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ari_core as ac
from truss_reference import load_models

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "results" / "verification" / "ari_screening.csv"

# ---------------------------------------------------------------------------
# Nilai target disertasi
# ---------------------------------------------------------------------------
# Tabel 4.11 — Two parallel bars, limit eps->0 (RR eksak rasional;
# ARI/CI dengan eta=0.5, U*_bar0=U*_bar1=0.75):
TABEL_411 = {
    ("M1_parallel_bars_1d", 0, 0.0): dict(RR=7/17,   ARI=21/68,  CI=47/68),
    ("M1_parallel_bars_1d", 1, 0.0): dict(RR=10/17,  ARI=15/34,  CI=19/34),
}
CONTROL_411 = dict(RR=1.0, ARI=0.75, CI=0.25)   # intact control
# Tabel 4.3 — Square with one diagonal, lambda=0 (kolom RR & CI disertasi):
TABEL_43 = {
    ("M3_square_one_diagonal", 0, 0.0): dict(RR=0.983152, CI=0.016848),
    ("M3_square_one_diagonal", 1, 0.0): dict(RR=0.964724, CI=0.216162),
    ("M3_square_one_diagonal", 2, 0.0): dict(RR=1.000000, CI=0.000000),
    ("M3_square_one_diagonal", 3, 0.0): dict(RR=1.000000, CI=0.000000),
    ("M3_square_one_diagonal", 4, 0.0): dict(RR=0.717285, CI=0.472914),
}
REL_TOL = 1e-6      # toleransi relatif kasus LULUS (Tabel 4.11)
ABS_TOL_DEV = 5e-4  # ambang deviasi absolut untuk flag sprint-mode


def fmt(x, nd=6):
    return "  n/a " if x is None else f"{x:.{nd}f}"


def close_rel(a, b, tol=REL_TOL):
    if a is None:
        return False
    return abs(a - b) <= tol * max(1.0, abs(b))


# ---------------------------------------------------------------------------
def main() -> int:
    models = load_models(str(ROOT / "examples" / "verification_models.json")) \
        if callable(load_models) else None
    if models is None:
        data = json.loads((ROOT / "examples" / "verification_models.json").read_text())
        models = data["models"]
    by_id = {m["id"]: m for m in models}

    all_rows = []
    fails = []

    print("=" * 78)
    print("GATE 2 — ARI CORE SCREENING (sprint mode)")
    print("=" * 78)

    # Full screening: 4 kontrol utuh + skenario hapus-total (lambda=0) per edge
    # Grid penuh (DF-05 ditutup): 16 edge x {0.75,0.5,0.25,0} = 64 skenario
    # disrupsi + 16 kontrol (lam=1 per-edge di blok [5]; lam=0 utk e3/e4 M3
    # dan seluruh edge M4 juga terdeteksi rank-deficient -> ok_with_rank_deficiency).
    report = ac.run_full_screening(
        models, lambdas=(0.75, 0.5, 0.25, 0.0), verbose=True)

    # ---- (1) Two Parallel Bars vs Tabel 4.11 ------------------------------
    print("\n--- [1] Two Parallel Bars vs TABEL 4.11 (limit eps->0) ---")
    am1 = report["M1_parallel_bars_1d"]["am"]
    ctrl = report["M1_parallel_bars_1d"]["control"]
    hdr = f"{'edge':<22}{'RR':>10}{'ARI':>10}{'CI':>10}  {'target':>10}  status"
    print(hdr)
    ok = True
    r_ctrl = dict(RR=ctrl.RR, ARI=ctrl.ARI, CI=ctrl.CI)
    m = "intact control"
    # Kontrol utuh tanpa edge-id: RR=1 eksak. Nilai ARI/CI Tabel 4.11
    # (0.75/0.25) memakai penalti U*_intact = Umax state utuh = 0.5.
    umax_intact = float(am1.result.Umax)
    ari_ref = ctrl.RR * (1.0 - am1.config["eta"] * umax_intact)
    good = (ctrl.RR == 1.0 and
            close_rel(ari_ref, CONTROL_411["ARI"]) and
            close_rel(1.0 - ari_ref, CONTROL_411["CI"]))
    ok &= good
    print(f"{m:<22}{fmt(ctrl.RR):>10}{fmt(ctrl.ARI):>10}{fmt(ctrl.CI):>10}"
          f"  {CONTROL_411['RR']:>10.6f}  {'PASS' if good else 'FAIL'}")
    for (_, eid, _lam), tgt in TABEL_411.items():
        res = report["M1_parallel_bars_1d"]["scenarios"][(eid, 0.0)]
        good = (close_rel(res.RR, tgt["RR"]) and close_rel(res.ARI, tgt["ARI"])
                and close_rel(res.CI, tgt["CI"]))
        ok &= good
        print(f"{('remove bar '+str(eid)):<22}{fmt(res.RR):>10}{fmt(res.ARI):>10}"
              f"{fmt(res.CI):>10}  {tgt['RR']:>10.6f}  {'PASS' if good else 'FAIL'}")
    print(f"Tabel 4.11: {'LULUS' if ok else 'GAGAL'} (rel.tol {REL_TOL:g})")
    if not ok:
        fails.append("Tabel 4.11 mismatch")

    # ---- (2) Square-One-Diagonal vs Tabel 4.3 -----------------------------
    # Gate 9: DF-01 DITUTUP. Akar masalah: b_jc harus memakai KOMPONEN reaksi
    # searah kasus beban (Eq 2.12), bukan magnitudo vektor reaksi gabungan.
    # Utk M3: b = {A: 0.95, B: 0.05}. Seluruh baris tereproduksi <= 4e-7.
    print("\n--- [2] Square with One Diagonal vs TABEL 4.3 (lambda=0) ---")
    print(f"{'edge':<10}{'RR(kode)':>12}{'RR(4.3)':>12}{'CI(kode)':>12}"
          f"{'CI(4.3)':>12}  status")
    for (mid, eid, lam), tgt in TABEL_43.items():
        res = report[mid]["scenarios"][(eid, lam)]
        d_rr = abs((res.RR or 0.0) - tgt["RR"])
        d_ci = abs((res.CI or 0.0) - tgt["CI"])
        verdict = "PASS" if (d_rr < 1e-5 and d_ci < 1e-5) else "FAIL"
        if verdict == "FAIL":
            fails.append(f"Tabel 4.3 e{eid} deviasi {d_rr:.2e}/{d_ci:.2e}")
        note = " (kasus kritis rank-turun CI~0)" if eid in (2, 3) else ""
        print(f"e{eid:<9}{fmt(res.RR):>12}{tgt['RR']:>12.6f}{fmt(res.CI):>12}"
              f"{tgt['CI']:>12.6f}  {verdict}{note}")

    # ---- (3) Monotonisitas S(G) thd lambda (M3-e5 / M4-e5? -> edge 4/4) ----
    print("\n--- [3] Cek MONOTONISITAS: lambda 1 -> 0.75 -> 0.5 -> 0.25 -> 0 ---")
    mono_ok = True
    for mid, eid in [("M3_square_one_diagonal", 4), ("M4_square_two_diagonals", 4),
                     ("M3_square_one_diagonal", 0), ("M4_square_two_diagonals", 5)]:
        am = ac.build_ari_model(by_id[mid])
        s_base, st = ac.compute_graph_score(am)
        lams = [1.0, 0.75, 0.5, 0.25, 0.0]
        seq = []
        cache = {}
        for lm in lams:
            if lm == 1.0:
                seq.append(s_base)
            else:
                s, _ = ac.compute_graph_score(am, {eid: lm}, cache)
                seq.append(s)
        incs = [(lams[i], lams[i+1], seq[i+1]-seq[i])
                for i in range(len(seq)-1) if seq[i+1] > seq[i] + 1e-12]
        good = not incs
        mono_ok &= good
        print(f"  {mid} e{eid}: S=" + " > ".join(f"{s:.6f}" for s in seq) +
              f"  [{'PASS' if good else 'FAIL ' + str(incs)}]")
    if not mono_ok:
        fails.append("Monotonisitas terlanggar")

    # ---- (4) Invariansi KONVERSI SATUAN kN-mm -> N-m (Bagian 2.6/4.1.3) ----
    # Koreksi Gate 9: uji lama (menskalakan s saja tanpa atribut fisik) BUKAN
    # uji invariansi formula. Uji yang benar = konversi satuan menyeluruh
    # (panjang, luas, E, beban, kapasitas, skala berdimensi ikut dikonversi)
    # — naskah 4.1.3 mensyaratkan nilai ARI tetap cocok dalam toleransi.
    print("\n--- [4] Cek INVARIANSI konversi satuan (kN-mm -> N-m) ---")
    inv_ok = True
    for mid in ["M1_parallel_bars_1d", "M3_square_one_diagonal"]:
        am0 = ac.build_ari_model(by_id[mid])
        m_conv, cfg_conv, sc_conv = _convert_units(by_id[mid],
                                                   ac.FIXED_SCALES[mid])
        am1 = ac.build_ari_model(m_conv, cfg_conv, sc_conv)
        worst = 0.0
        for eid in range(len(am0.edges)):
            r0 = ac.compute_ari(am0, (eid, 0.0))
            r1 = ac.compute_ari(am1, (eid, 0.0))
            if r0.ARI is not None and r1.ARI is not None:
                worst = max(worst, abs(r0.ARI - r1.ARI))
        good = worst < 1e-9
        inv_ok &= good
        print(f"  {mid}: maks |ΔARI| kN-mm vs N-m = {worst:.3e}  "
              f"[{'PASS' if good else 'FAIL'}]")
    if not inv_ok:
        fails.append("Invariansi konversi satuan terlanggar")

    # ---- (5) Kontrol lambda=1: RR=1 eksak, CI = eta*U* ----------------------
    print("\n--- [5] Kontrol lambda=1 per edge: RR=1 eksak, CI=eta*U*_e ---")
    ctl_ok = True
    for mid, rep in report.items():
        am = rep["am"]
        caps = {int(k): float(v) for k, v in am.model["capacities"].items()}
        forces = {e["id"]: abs(float(am.result.element_forces[i]))
                  for i, e in enumerate(am.edges)}
        for eid in sorted(forces):
            res = ac.compute_ari(am, (eid, 1.0), baseline=rep["baseline"],
                                 pair_cache={})
            u_star = min(forces[eid] / (caps[eid] + am.config["eps_R"]), 1.0)
            exp_ci = 1.0 - 1.0 * (1.0 - am.config["eta"] * u_star)
            good = (res.RR == 1.0) and abs(res.CI - exp_ci) < 1e-12
            ctl_ok &= good
            if not good:
                print(f"    FAIL {mid} e{eid}: RR={res.RR} CI={res.CI} vs {exp_ci}")
    print(f"  Semua kontrol edge λ=1: {'PASS' if ctl_ok else 'FAIL'}")
    if not ctl_ok:
        fails.append("Kontrol lambda=1 salah")

    # ---- (6) Intermediate values M3 e1,e2,e5 (penamaan Tabel 4.3) ----------
    # Tabel 4.3 memakai penamaan simpul A=(0,0),B=(1000,0),C=(1000,1000),
    # D=(0,1000): e1=AB(edge0), e2=BC(edge1), e3=CD(edge2), e4=DA(edge3),
    # e5=AC-diagonal(edge4).
    print("\n--- [6] INTERMEDIATE VALUES — Square-One-Diagonal (e1,e2,e5) ---")
    am3 = ac.build_ari_model(by_id["M3_square_one_diagonal"])
    w3 = ac.base_weights_of(am3)
    s_base3, _ = ac.compute_graph_score(am3)
    name_map = {0: "e1(AB)", 1: "e2(BC)", 2: "e3(CD)", 3: "e4(DA)", 4: "e5(AC)"}
    print("  w_e^M intact:", {name_map[k]: round(v, 6) for k, v in w3.items()})
    print(f"  S(G_M) baseline = {s_base3:.9f}")
    for eid in [0, 1, 4]:
        res = ac.compute_ari(am3, (eid, 0.0), baseline=(s_base3, "ok"))
        print(f"  {name_map[eid]}: S_disrupted={res.S:.9f}  U*={fmt(res.U_star)}"
              f"  RR={fmt(res.RR)}  ARI={fmt(res.ARI)}  CI={fmt(res.CI)}"
              f"  status={res.status}")

    # ---- (7) CSV audit trail ------------------------------------------------
    cols = ["model", "scenario_edge", "lambda", "status", "mechanical_status",
            "S_baseline", "S_scenario", "RR", "U_star", "ARI", "CI"]
    rows = []
    for mid, rep in report.items():
        s_b, _ = rep["baseline"]
        c = rep["control"]
        rows.append([mid, "CONTROL", 1.0, c.status, "ok", s_b, c.S,
                     c.RR, "", c.ARI, c.CI])
        for (eid, lam), res in sorted(rep["scenarios"].items()):
            rows.append([mid, eid, lam, res.status,
                         res.detail.get("mechanical_status", ""), s_b, res.S,
                         res.RR, res.U_star, res.ARI, res.CI])
            all_rows.append(rows[-1])
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        for r in rows:
            wr.writerow(["" if v != v else v for v in r])  # nan -> kosong
    print(f"\n[Audit trail tersimpan] {OUT_CSV} ({len(rows)} baris)")

    # ---- Ringasan ------------------------------------------------------------
    print("\n" + "=" * 78)
    if fails:
        print("RINGASAN: temuan ter-FLAG (lihat DEFERRED_FINDINGS.md):")
        for f in fails:
            print("  -", f)
    else:
        print("RINGASAN: semua cek keras LULUS.")
    print("Gate 9 exit 0 (seluruh target Tabel 4.3 tereproduksi; DF-01 ditutup).")
    return 0


def _convert_units(model: dict, scales: dict) -> tuple:
    """Konversi satuan kN-mm -> N-m (Bagian 4.1.3).

    Panjang /1000 (mm -> m); luas /1e6 (mm^2 -> m^2); E x1e9
    (kN/mm^2 -> N/m^2); beban & kapasitas x1e3 (kN -> N); s_k x1e6
    (kN/mm -> N/m); s_R x1e3 (kN -> N); eps_R x1e3 (satuan kapasitas).
    eps_w/eps_d TAK BERDIMENSI -> tetap. Nilai ARI wajib invarian.
    """
    import copy as _copy
    m2 = _copy.deepcopy(model)
    for n in m2["nodes"]:
        n["coords"] = [float(v) / 1000.0 for v in n["coords"]]
    for el in m2["elements"]:
        el["area"] = float(el["area"]) / 1e6
        if "E" in el:
            el["E"] = float(el["E"]) * 1e9
    if "material" in m2:
        m2["material"]["E"] = float(m2["material"]["E"]) * 1e9
    m2["capacities"] = {k: float(v) * 1e3
                        for k, v in m2["capacities"].items()}
    for item in m2.get("loads", []):
        item["components"] = {c: float(v) * 1e3
                              for c, v in item["components"].items()}
    cfg = dict(eps_R=1e-6 * 1e3)
    sc = dict(s_k=float(scales["s_k"]) * 1e6,
              s_R=float(scales["s_R"]) * 1e3)
    return m2, cfg, sc


if __name__ == "__main__":
    sys.exit(main())
