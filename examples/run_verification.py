"""
run_verification.py — Runner verifikasi kanonik (Bagian 4.1 & 4.5.6/4.5.10 disertasi)

Menghasilkan berkas keluaran yang dinyatakan naskah (Tabel 4.8):

    results/verification/baseline.csv     respons & skor 4 model utuh (Tabel 4.1)
    results/verification/scenarios.csv    64 gangguan + 16 kontrol edge + 4 kontrol utuh;
                                          status skor & status SOLVER dipisah kolom
    results/verification/checks.csv       pemeriksaan otomatis vs Tabel 4.1/4.2/4.3/
                                          4.4/4.5/4.11 + Eq 2.19 + monotonisitas
    results/verification/manifest.json    konfigurasi, versi, waktu, hash sumber
    results/verification/Tabel.tex        tabel LaTeX (reproduksi Tabel 4.1 & 4.3)
    results/verification/models.pdf       diagram 4 model kanonik
    results/verification/ci_by_damage.pdf kurva CI(lambda) + penanda rank acuan

Konvensi diagnostik Tabel 4.5 (kanonik, 64 gangguan):
  kejadian kritis = rank-turun  ATAU  utilisasi maks > 1  ATAU  perpindahan maks > 2xd0
  (ketidaksamaan TEGAS, "melampaui"; respons acuan tanpa pseudoinverse).
  Target naskah: kritis 17; ARI forward 5 (terlewat 14); pengaman 8 (terlewat 9);
  gabungan 11 (terlewat 8); rank-turun 8 (Tabel 4.2).

Pemakaian: python examples/run_verification.py      (exit 0 = semua LULUS)
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ari_core as ac                                 # noqa: E402
from truss_reference import load_models, solve_model  # noqa: E402
from mechanical_guard import MechanicalGuard          # noqa: E402

OUT = ROOT / "results" / "verification"
NODE_LETTERS = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}
LAMS_DISR = (0.0, 0.25, 0.5, 0.75)
TAU_CI = 0.5                       # ambang diagnostik (4.2.4), bukan ambang penerapan

# --- target naskah -----------------------------------------------------------
TABEL_41 = {
    "M1_parallel_bars_1d":     dict(batang=2, rank="1/1", umax=1.000000,
                                    Umax=0.500000, W=15.000000),
    "M2_planar_triangle":      dict(batang=3, rank="3/3", umax=1.154460,
                                    Umax=0.442218, W=16.956287),
    "M3_square_one_diagonal":  dict(batang=5, rank="5/5", umax=5.935311,
                                    Umax=0.530330, W=86.139610),
    "M4_square_two_diagonals": dict(batang=6, rank="5/5", umax=3.582277,
                                    Umax=0.320083, W=51.989854),
}
TOL_41 = 5e-4
TABEL_43 = {0: (0.983152, 0.016848), 1: (0.964724, 0.216162),
            2: (1.000000, 0.000000), 3: (1.000000, 0.000000),
            4: (0.717285, 0.472914)}
TOL_43 = 1e-5
TABEL_411 = dict(bar0=dict(RR=7 / 17, ARI=21 / 68, CI=47 / 68),
                 bar1=dict(RR=10 / 17, ARI=15 / 34, CI=19 / 34),
                 ctrl=dict(RR=1.0, ARI=0.75, CI=0.25))
TOL_411 = 1e-6
DIAG_TARGET = dict(rank_lost=8, critical=17, ari_fwd=5, guard_fwd=8,
                   comb_fwd=11, ari_missed=14, guard_missed=9, comb_missed=8)

CHECKS: list = []


def check(name: str, expected, actual, tol: float, note: str = "") -> bool:
    if actual is None:
        ok = False
    elif isinstance(expected, str):
        ok = (str(actual) == expected)
    else:
        ok = abs(float(actual) - float(expected)) <= float(tol)
    CHECKS.append(dict(check=name, expected=expected,
                       actual=("" if actual is None else actual),
                       tol=tol, pass_=bool(ok), note=note))
    return ok


def edge_label(e: dict) -> str:
    i, j = int(e["i"]), int(e["j"])
    return f"{NODE_LETTERS.get(i, i)}-{NODE_LETTERS.get(j, j)}"


def _connected_after(model: dict, removed_eid) -> bool:
    """Apakah graf tetap terhubung bila sisi `removed_eid` dihapus (Tabel 4.2)."""
    adj: dict = {}
    for el in model["elements"]:
        if removed_eid is not None and int(el["id"]) == int(removed_eid):
            continue
        i, j = int(el["nodes"][0]), int(el["nodes"][1])
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    nodes = [int(nd["id"]) for nd in model["nodes"]]
    seen = {nodes[0]}
    stack = [nodes[0]]
    while stack:
        u = stack.pop()
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == len(nodes)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    models = load_models(ROOT / "examples" / "verification_models.json")
    by_id = {str(m["id"]): m for m in models}

    print("=" * 78)
    print("RUN VERIFICATION — verifikasi kanonik ARI (Bagian 4.1 / 4.5.6)")
    print("=" * 78)

    # ------------------------------------------------------------------ 1. baseline
    print("\n[1] Baseline (model utuh) vs Tabel 4.1:")
    base_rows = []
    for m in models:
        mid = str(m["id"])
        res = solve_model(m)
        t = TABEL_41[mid]
        rank_str = f"{int(res.rank)}/{int(res.n_free)}"
        du = abs(res.umax - t["umax"])
        dU = abs(res.Umax - t["Umax"])
        dW = abs(res.strain_energy - t["W"])
        check(f"Tabel 4.1 {mid} umax", t["umax"], res.umax, TOL_41)
        check(f"Tabel 4.1 {mid} Umax", t["Umax"], res.Umax, TOL_41)
        check(f"Tabel 4.1 {mid} W", t["W"], res.strain_energy, TOL_41)
        check(f"Tabel 4.1 {mid} Rank/DOF", t["rank"], rank_str, 0.0)
        ok = (du < TOL_41 and dU < TOL_41 and dW < TOL_41)
        print(f"    {mid:26s} rank={rank_str} umax={res.umax:.6f} "
              f"Umax={res.Umax:.6f} W={res.strain_energy:.6f}  "
              f"{'PASS' if ok else 'FAIL'}")
        base_rows.append(dict(model=mid, batang=int(len(m["elements"])),
                              rank=rank_str, umax=res.umax, Umax=res.Umax,
                              W=res.strain_energy,
                              umax_target=t["umax"], Umax_target=t["Umax"],
                              W_target=t["W"],
                              status="PASS" if ok else "FAIL"))
    with open(OUT / "baseline.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(base_rows[0].keys()))
        wr.writeheader()
        wr.writerows(base_rows)

    # ------------------------------------------------------------------ 2. skenario
    print("\n[2] Skenario: kontrol utuh + 16 kontrol edge (lam=1) + 64 gangguan:")
    engines, baselines, caches, guards = {}, {}, {}, {}
    for mid, m in by_id.items():
        am = ac.build_ari_model(m)
        c = {}
        s_b, st_b = ac.compute_graph_score(am, None, c)
        engines[mid] = am
        baselines[mid] = (s_b, st_b)
        caches[mid] = c
        guards[mid] = MechanicalGuard(m)

    scen_rows = []
    for mid, m in by_id.items():
        am = engines[mid]
        s_b, st_b = baselines[mid]
        g = guards[mid]
        ctrl = ac.compute_ari(am, None, baseline=baselines[mid],
                              pair_cache=caches[mid])
        scen_rows.append(dict(model=mid, batang="", edge="", edge_label="",
                              lambda_=1.0, RR=ctrl.RR, ARI=ctrl.ARI, CI=ctrl.CI,
                              U_star="", rank=f"{int(am.result.rank)}/"
                              f"{int(am.result.n_free)}",
                              score_status=ctrl.status_code,
                              solver_status=ctrl.solver_status,
                              guard_flag="",
                              note="kontrol utuh tanpa edge"))
        for e in sorted(am.edges, key=lambda x: x["id"]):
            eid = e["id"]
            lab = edge_label(e)
            # kontrol edge lam=1
            r1 = ac.compute_ari(am, (eid, 1.0), baseline=baselines[mid],
                                pair_cache=caches[mid])
            check(f"Eq 2.19 {mid} e{eid+1} kontrol RR=1 eksak", 1.0, r1.RR, 0.0)
            ctl_ci = g.margin(eid, 1.0)  # noqa: F841 (dipakai utk dokumentasi)
            scen_rows.append(dict(model=mid, batang=f"e{eid+1}", edge=eid,
                                  edge_label=lab, lambda_=1.0, RR=r1.RR,
                                  ARI=r1.ARI, CI=r1.CI, U_star=r1.U_star,
                                  rank=f"{int(am.result.rank)}/"
                                  f"{int(am.result.n_free)}",
                                  score_status=r1.status_code,
                                  solver_status=r1.solver_status,
                                  guard_flag=g.guard_flag(eid, 1.0),
                                  note="kontrol edge lam=1; CI=eta*U*"))
            # 4 gangguan
            for lam in LAMS_DISR:
                r = ac.compute_ari(am, (eid, lam), baseline=baselines[mid],
                                   pair_cache=caches[mid])
                disr = ac._apply_stiffness_multiplier(m, {eid: lam},
                                                      drop_zero=True)
                res = solve_model(disr)
                scen_rows.append(dict(
                    model=mid, batang=f"e{eid+1}", edge=eid, edge_label=lab,
                    lambda_=lam, RR=r.RR, ARI=r.ARI, CI=r.CI, U_star=r.U_star,
                    rank=f"{int(res.rank)}/{int(res.n_free)}",
                    score_status=r.status_code,
                    solver_status=r.solver_status,
                    guard_flag=g.guard_flag(eid, lam),
                    note=r.detail.get("note", "")))
    with open(OUT / "scenarios.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(scen_rows[0].keys()))
        wr.writeheader()
        wr.writerows(scen_rows)
    print(f"    {len(scen_rows)} baris -> scenarios.csv")

    # ------------------------------------------------------------------ 3. diagnostik
    print("\n[3] Diagnostik kanonik (Tabel 4.2 & 4.5):")
    diag = dict(rank_lost=0, critical=0, ari_fwd=0, guard_fwd=0, comb_fwd=0,
                ari_missed=0, guard_missed=0, comb_missed=0,
                ari_rank_missed=0, guard_rank_missed=0, comb_rank_missed=0)
    diag_models: dict = {}
    for mid, m in by_id.items():
        am = engines[mid]
        s_b, st_b = baselines[mid]
        g = guards[mid]
        u0 = float(am.result.umax)
        dm = diag_models.setdefault(mid, dict(n=0, rank=0, connected=0))
        for e in am.edges:
            eid = e["id"]
            for lam in LAMS_DISR:
                dm["n"] += 1
                r = ac.compute_ari(am, (eid, lam), baseline=baselines[mid],
                                   pair_cache=caches[mid])
                disr = ac._apply_stiffness_multiplier(m, {eid: lam},
                                                      drop_zero=True)
                res = solve_model(disr)
                rank_lost = (res.status != "ok")
                dm["rank"] += int(rank_lost)
                if _connected_after(m, eid if lam == 0.0 else None):
                    dm["connected"] += 1
                u_over = d_over = False
                if not rank_lost:
                    # Kriteria diagnostik (4.2.4): utilisasi maksimum RESPONS
                    # TERDISRUPSI vs kapasitas state saat itu (target bar x
                    # lambda, Bagian 4.1.5) melampaui 1, atau perpindahan
                    # maksimum melampaui 2xd0 — ketidaksamaan TEGAS polos.
                    u_over = bool(res.Umax > 1.0)
                    d_over = bool(res.umax > 2.0 * u0)
                diag["rank_lost"] += int(rank_lost)
                # "Diteruskan" dihitung atas SELURUH 64 gangguan (Tabel 4.5)
                ari_f = (r.CI is not None) and (r.CI >= TAU_CI)
                guard_f = (g.guard_flag(eid, lam) == 1)
                diag["ari_fwd"] += int(ari_f)
                diag["guard_fwd"] += int(guard_f)
                diag["comb_fwd"] += int(ari_f or guard_f)
                if not (rank_lost or u_over or d_over):
                    continue
                # "Kritis terlewat" dihitung atas himpunan kritis saja
                diag["critical"] += 1
                diag["ari_missed"] += int(not ari_f)
                diag["guard_missed"] += int(not guard_f)
                diag["comb_missed"] += int(not (ari_f or guard_f))
                if rank_lost:
                    diag["ari_rank_missed"] += int(not ari_f)
                    diag["guard_rank_missed"] += int(not guard_f)
                    diag["comb_rank_missed"] += int(not (ari_f or guard_f))
    print(f"    rank-turun={diag['rank_lost']} kritis={diag['critical']} | "
          f"ARI fwd={diag['ari_fwd']} pengaman fwd={diag['guard_fwd']} "
          f"gabungan fwd={diag['comb_fwd']}")
    for key, target in (("rank_lost", 8), ("critical", 17), ("ari_fwd", 5),
                        ("guard_fwd", 8), ("comb_fwd", 11),
                        ("ari_missed", 14), ("guard_missed", 9),
                        ("comb_missed", 8), ("ari_rank_missed", 6),
                        ("guard_rank_missed", 0), ("comb_rank_missed", 0)):
        check(f"Tabel 4.2/4.5 kanonik: {key}", target, diag[key], 0.0)

    # ------------------------------------------------------------------ 4. regresi
    print("\n[4] Regresi angka tabel naskah:")
    for eid, (t_rr, t_ci) in TABEL_43.items():
        r = ac.compute_ari(engines["M3_square_one_diagonal"],
                           (eid, 0.0),
                           baseline=baselines["M3_square_one_diagonal"],
                           pair_cache=caches["M3_square_one_diagonal"])
        check(f"Tabel 4.3 e{eid+1} RR", t_rr, r.RR, TOL_43)
        check(f"Tabel 4.3 e{eid+1} CI", t_ci, r.CI, TOL_43)
    am1 = engines["M1_parallel_bars_1d"]
    for eid, keyname in ((0, "bar0"), (1, "bar1")):
        r = ac.compute_ari(am1, (eid, 0.0), baseline=baselines
                           ["M1_parallel_bars_1d"],
                           pair_cache=caches["M1_parallel_bars_1d"])
        t = TABEL_411[keyname]
        check(f"Tabel 4.11 {keyname} RR", t["RR"], r.RR, TOL_411)
        check(f"Tabel 4.11 {keyname} ARI", t["ARI"], r.ARI, TOL_411)
        check(f"Tabel 4.11 {keyname} CI", t["CI"], r.CI, TOL_411)
    # monotonicity per edge
    mono_bad = 0
    for mid, m in by_id.items():
        am = engines[mid]
        for e in am.edges:
            seq = []
            for lam in (1.0, 0.75, 0.5, 0.25, 0.0):
                if lam == 1.0:
                    seq.append(1.0)
                else:
                    r = ac.compute_ari(am, (e["id"], lam),
                                       baseline=baselines[mid],
                                       pair_cache=caches[mid])
                    seq.append(r.RR if r.RR is not None else float("nan"))
            for a_, b_ in zip(seq, seq[1:]):
                if b_ > a_ + 1e-12:
                    mono_bad += 1
    check("Monotonisitas RR(lambda) 16 edge (0 pelanggaran)", 0, mono_bad, 0.0)
    # Tabel 4.4
    g3 = guards["M3_square_one_diagonal"]
    for eid, lab in ((2, "e3"), (3, "e4")):
        disr = ac._apply_stiffness_multiplier(
            by_id["M3_square_one_diagonal"], {eid: 0.0}, drop_zero=True)
        res = solve_model(disr)
        check(f"Tabel 4.4 {lab} h_e=1.000000", 1.0, g3.h[eid], 1e-9)
        check(f"Tabel 4.4 {lab} m_e(0)~0", 0.0, g3.m_e(eid, 0.0), 1e-12)
        check(f"Tabel 4.4 {lab} rank 4/5", "4/5",
              f"{int(res.rank)}/{int(res.n_free)}", 0.0)
        check(f"Tabel 4.4 {lab} guard g=1", 1, g3.guard_flag(eid, 0.0), 0.0)
    n_pass = sum(1 for c in CHECKS if c["pass_"])
    n_fail = len(CHECKS) - n_pass
    print(f"    {n_pass}/{len(CHECKS)} pemeriksaan LULUS"
          + (f", {n_fail} GAGAL" if n_fail else ""))
    with open(OUT / "checks.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(CHECKS[0].keys()))
        wr.writeheader()
        wr.writerows(CHECKS)

    # ------------------------------------------------------------------ 5. LaTeX
    tex = []
    tex.append("% Dibangkitkan otomatis oleh examples/run_verification.py")
    tex.append("% (jangan mengedit manual — Bagian 4.9.2 aturan 2)\n")
    tex.append("\\begin{table}[htbp]\\centering")
    tex.append("\\caption{Reproduksi Tabel 4.1 (hasil solver, empat model utuh).}")
    tex.append("\\label{tab:repro41}")
    tex.append("\\begin{tabular}{lcccccc}\\hline")
    tex.append("Model & Batang & Rank/DOF & $u_{\\max}$ (mm) & $U_{\\max}$ "
               "& $W$ (kNmm) & Cek \\\\\\hline")
    for row in base_rows:
        tex.append(f"{row['model']} & {row['batang']} & {row['rank']} & "
                   f"{row['umax']:.6f} & {row['Umax']:.6f} & "
                   f"{row['W']:.6f} & {row['status']} \\\\")
    tex.append("\\hline\\end{tabular}\\end{table}\n")
    tex.append("\\begin{table}[htbp]\\centering")
    tex.append("\\caption{Reproduksi Tabel 4.3 (persegi satu diagonal, $\\lambda=0$).}")
    tex.append("\\label{tab:repro43}")
    tex.append("\\begin{tabular}{lcccc}\\hline")
    tex.append("Batang & RR & CI & Rank/DOF & Cek \\\\\\hline")
    for eid in range(5):
        r = ac.compute_ari(engines["M3_square_one_diagonal"], (eid, 0.0),
                           baseline=baselines["M3_square_one_diagonal"],
                           pair_cache=caches["M3_square_one_diagonal"])
        disr = ac._apply_stiffness_multiplier(
            by_id["M3_square_one_diagonal"], {eid: 0.0}, drop_zero=True)
        res = solve_model(disr)
        t_rr, t_ci = TABEL_43[eid]
        ok = (abs(r.RR - t_rr) <= TOL_43 and abs(r.CI - t_ci) <= TOL_43)
        tex.append(f"$e_{eid+1}$ & {r.RR:.6f} & {r.CI:.6f} & "
                   f"{int(res.rank)}/{int(res.n_free)} & "
                   f"{'PASS' if ok else 'FAIL'} \\\\")
    tex.append("\\hline\\end{tabular}\\end{table}")

    # --- Tabel 4.2: status gangguan (reproduksi) ---
    EXPECT_42 = {"M1_parallel_bars_1d": (8, 8, 0, 8),
                 "M2_planar_triangle": (12, 9, 3, 12),
                 "M3_square_one_diagonal": (20, 15, 5, 20),
                 "M4_square_two_diagonals": (24, 24, 0, 24)}
    tex.append("\n" + r"\begin{table}[htbp]\centering")
    tex.append(r"\caption{Reproduksi Tabel 4.2 (status gangguan; kontrol "
               r"tidak masuk jumlah gangguan).}")
    tex.append(r"\label{tab:repro42}")
    tex.append(r"\begin{tabular}{lcccc}\hline")
    tex.append("Model & Gangguan & Solusi unik & Rank kurang & Terhubung "
               r"\\" + r"\hline")
    for m_ in models:
        mid_ = str(m_["id"])
        dm_ = diag_models[mid_]
        uniq = dm_["n"] - dm_["rank"]
        cek = ("PASS" if (dm_["n"], uniq, dm_["rank"], dm_["connected"])
               == EXPECT_42[mid_] else "CEK")
        tex.append(f"{mid_} & {dm_['n']} & {uniq} & {dm_['rank']} & "
                   f"{dm_['connected']} ({cek}) " + r"\\")
    tex.append(r"\hline\end{tabular}\end{table}" + "\n")

    # --- Tabel 4.4: regresi e3/e4 (reproduksi) ---
    g3_ = guards["M3_square_one_diagonal"]
    tex.append(r"\begin{table}[htbp]\centering")
    tex.append(r"\caption{Reproduksi Tabel 4.4 (dua kehilangan elemen "
               r"bergaya awal nol).}")
    tex.append(r"\label{tab:repro44}")
    tex.append(r"\begin{tabular}{lccccc}\hline")
    tex.append("Elemen & CI & $h_e$ & $m_e(0)$ & Rank & Gabungan "
               r"\\")
    tex.append(r"\hline")
    for eid_ in (2, 3):
        r_ = ac.compute_ari(engines["M3_square_one_diagonal"], (eid_, 0.0),
                            baseline=baselines["M3_square_one_diagonal"],
                            pair_cache=caches["M3_square_one_diagonal"])
        disr_ = ac._apply_stiffness_multiplier(
            by_id["M3_square_one_diagonal"], {eid_: 0.0}, drop_zero=True)
        res_ = solve_model(disr_)
        gard = ("Teruskan" if g3_.guard_flag(eid_, 0.0) == 1 else "Tidak")
        tex.append(f"$e_{eid_ + 1}$ & {r_.CI:.2e} & {g3_.h[eid_]:.6f} & "
                   f"{g3_.m_e(eid_, 0.0):.2e} & "
                   f"{int(res_.rank)}/{int(res_.n_free)} & {gard} "
                   + r"\\")
    tex.append(r"\hline\end{tabular}\end{table}" + "\n")

    # --- Tabel 4.5 (paruh kanonik): diagnostik (reproduksi) ---
    tex.append(r"\begin{table}[htbp]\centering")
    tex.append(r"\caption{Reproduksi Tabel 4.5 (paruh kanonik; ambang "
               r"$\tau=0.5$, kontrol tidak dihitung).}")
    tex.append(r"\label{tab:repro45}")
    tex.append(r"\begin{tabular}{lcccc}\hline")
    tex.append("Kebijakan & $N$ & Diteruskan & Rank terlewat & Kritis "
               r"terlewat \\")
    tex.append(r"\hline")
    tex.append(f"ARI & 64 & {diag['ari_fwd']} & "
               f"{diag['ari_rank_missed']}/{diag['rank_lost']} & "
               f"{diag['ari_missed']}/{diag['critical']} " + r"\\")
    tex.append(f"Pengaman & 64 & {diag['guard_fwd']} & "
               f"{diag['guard_rank_missed']}/{diag['rank_lost']} & "
               f"{diag['guard_missed']}/{diag['critical']} " + r"\\")
    tex.append(f"Gabungan & 64 & {diag['comb_fwd']} & "
               f"{diag['comb_rank_missed']}/{diag['rank_lost']} & "
               f"{diag['comb_missed']}/{diag['critical']} " + r"\\")
    tex.append(r"\hline\end{tabular}\end{table}")
    (OUT / "Tabel.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ 6. figur
    fig, axes = plt.subplots(2, 2, figsize=(9, 8))
    def _xy(coords):
        return (coords[0], coords[1] if len(coords) > 1 else 0.0)
    for ax, m in zip(axes.ravel(), models):
        nodes = {int(n["id"]): [float(v) for v in n["coords"]]
                 for n in m["nodes"]}
        for el in m["elements"]:
            i, j = int(el["nodes"][0]), int(el["nodes"][1])
            xi, yi = _xy(nodes[i])
            xj, yj = _xy(nodes[j])
            ax.plot([xi, xj], [yi, yj], "-", color="0.4", lw=1.2)
        for nid, coords in nodes.items():
            x, y = _xy(coords)
            ax.plot(x, y, "o", color="C0", ms=6)
            ax.annotate(NODE_LETTERS.get(nid, str(nid)), (x, y),
                        textcoords="offset points", xytext=(6, 6), fontsize=9)
        for key, spec in m.get("boundary_conditions", {}).items():
            nid = int(key.split("_")[1])
            x, y = _xy(nodes[nid])
            ax.plot(x, y, "s", mfc="none", mec="C3", ms=12, mew=1.5)
        for item in m.get("loads", []):
            nid = int(item["node"])
            x, y = _xy(nodes[nid])
            for comp, val in item["components"].items():
                if abs(val) < 0.5:
                    continue
                dx, dy = (0.25, 0) if comp == "ux" else (0, 0.25)
                ax.arrow(x, y, dx * abs(val) / 30.0 * 0.6,
                         dy * abs(val) / 30.0 * 0.6,
                         head_width=60, head_length=100, fc="C2", ec="C2")
        ax.set_title(str(m["id"]), fontsize=10)
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(alpha=0.25)
    fig.suptitle("Empat model kanonik (kotak = tumpuan, panah = beban)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "models.pdf")
    plt.close(fig)

    # CI vs lambda (grid halus dlambda=0.05) + penanda rank acuan
    fig, axes = plt.subplots(2, 2, figsize=(9, 8), sharex=True)
    lams_fine = [round(1.0 - 0.05 * k, 10) for k in range(0, 21)]
    for ax, m in zip(axes.ravel(), models):
        mid = str(m["id"])
        am = engines[mid]
        cmap = plt.get_cmap("tab10")
        for k, e in enumerate(sorted(am.edges, key=lambda x: x["id"])):
            labs, cis, rankpts = [], [], []
            for lam in lams_fine:
                r = ac.compute_ari(am, (e["id"], lam),
                                   baseline=baselines[mid],
                                   pair_cache=caches[mid])
                labs.append(lam)
                cis.append(r.CI if r.CI is not None else float("nan"))
                if r.solver_status == "rank_deficient":
                    rankpts.append((lam, r.CI))
            ax.plot(labs, cis, "-", color=cmap(k % 10), lw=1.2,
                    label=f"e{e['id']+1}")
            if rankpts:
                ax.plot([p[0] for p in rankpts], [p[1] for p in rankpts],
                        "x", color=cmap(k % 10), ms=7, mew=1.6)
        ax.axhline(TAU_CI, color="0.5", ls="--", lw=0.8)
        ax.set_title(mid, fontsize=10)
        ax.set_xlabel("faktor tersisa $\\lambda$")
        ax.set_ylabel("CI")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
    fig.suptitle("CI terhadap faktor tersisa (x = rank acuan turun)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "ci_by_damage.pdf")
    plt.close(fig)

    # ------------------------------------------------------------------ 7. manifest
    src_files = sorted((ROOT / "examples").glob("*.py")) + \
        [ROOT / "examples" / "verification_models.json"]
    manifest = dict(
        title="Verifikasi kanonik ARI — keluaran terbangkitkan",
        generated=datetime.now(timezone.utc).isoformat(),
        generator="examples/run_verification.py",
        python=sys.version.split()[0],
        numpy=np.__version__,
        matplotlib=matplotlib.__version__,
        platform=platform.platform(),
        config=dict(alpha_k=0.5, alpha_R=0.5, q_e=1.0, K=2, gamma=1.0,
                    beta=0.1, eta=0.5, eps_w=1e-9, eps_d=1e-9, eps_R=1e-6,
                    baseline_tol=1e-12, max_search_nodes=ac.MAX_SEARCH_NODES,
                    lambdas_disrupsi=list(LAMS_DISR), tau_ci=TAU_CI),
        fixed_scales=ac.FIXED_SCALES,
        hashes={f.name: sha256_of(f) for f in src_files},
        outputs=["baseline.csv", "scenarios.csv", "checks.csv", "Tabel.tex",
                 "models.pdf", "ci_by_damage.pdf"],
        checks_total=len(CHECKS), checks_pass=n_pass,
        diagnostik=diag,
    )
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2,
                                                  default=str) + "\n",
                                       encoding="utf-8")

    print(f"\n[berkas] baseline.csv ({len(base_rows)}), "
          f"scenarios.csv ({len(scen_rows)}), checks.csv ({len(CHECKS)}), "
          f"Tabel.tex, models.pdf, ci_by_damage.pdf, manifest.json")
    print("\n" + "=" * 78)
    print(f"VERIFIKASI: {n_pass}/{len(CHECKS)} LULUS"
          + ("" if not n_fail else f" — {n_fail} GAGAL"))
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
