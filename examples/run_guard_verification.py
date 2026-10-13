"""
run_guard_verification.py — Verifikasi paket pengaman kinematik (Bagian 4.2 / 4.5.11)
=====================================================================================

Menjalankan pemeriksaan yang dilaporkan pada Bagian 4.2 disertasi:

  A. UJI ANALITIS  — identitas pembaruan rank-1 Eq 4.7 (residual ~ mesin)
     dan closed-form M1 (h_e = k_e / sum k -> 2/3, 1/3).
  B. REGRESI       — Tabel 4.3 (RR/CI), Tabel 4.4 (h_e = 1.000000; m_e(0) ~ 0;
     rank 4/5; guard meneruskan), Tabel 4.11 (7/17, 10/17), batas kondisi
     Eq 4.4 di seluruh grid lambda.
  C. DIAGNOSTIK    — Tabel 4.2/4.5 (kanonik): rank-turun 8; kritis 17;
     ARI diteruskan 5, pengaman 8, gabungan 11; terlewat 14/9/8.
  D. PARAMETRIK    — paket §4.2.4/§4.2.5 (272 skenario) HANYA dijalankan bila
     berkas results/revision/models.json tersedia; jika belum ada, ditandai
     "pending_material" (BUKAN kegagalan).

Keluaran: results/verification/guard_verification.json
Exit code 0 = kelompok A-C lulus semua.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ari_core as ac                                     # noqa: E402
from truss_reference import load_models, solve_model      # noqa: E402
from mechanical_guard import MechanicalGuard              # noqa: E402

OUT = ROOT / "results" / "verification" / "guard_verification.json"
LAMS = (0.0, 0.25, 0.5, 0.75)
TAU = 0.5
TOL_43 = 1e-5
TABEL_43 = {0: (0.983152, 0.016848), 1: (0.964724, 0.216162),
            2: (1.000000, 0.000000), 3: (1.000000, 0.000000),
            4: (0.717285, 0.472914)}
CHECKS: list = []


def check(group: str, name: str, expected, actual, tol: float = 0.0) -> bool:
    if actual is None:
        ok = False
    elif isinstance(expected, str):
        ok = (str(actual) == expected)
    else:
        ok = abs(float(actual) - float(expected)) <= float(tol)
    CHECKS.append(dict(group=group, check=name, expected=expected,
                       actual=("" if actual is None else actual),
                       tol=tol, pass_=bool(ok)))
    return ok


def run_parametric(models_path: Path) -> dict:
    """Diagnostik parametrik §4.2.4 (272 skenario) — kontrak §4.2.3/§4.2.5.

    Urutan audit (4.2.3): keputusan penerusan (hanya informasi INTAK) disimpan
    ke results/revision/decisions.csv + hash SEBELUM respons acuan
    pascagangguan dihitung. Kasus kritis yang TIDAK diteruskan kebijakan
    gabungan dicatat ke results/revision/remaining_misses.csv (4.2.5).

    Kriteria kritis: rank turun ATAU utilisasi maks > 1 ATAU perpindahan
    maks > 2xd0 — ketidaksamaan tegas polos. Konvensi UTAMA (A): utilisasi
    respons terdisrupsi vs kapasitas state saat itu (target x lambda, 4.1.5).
    Varian (B): vs kapasitas ASLI — dilaporkan berdampingan untuk rekonsiliasi
    dengan draf Tabel 4.5 peneliti. Daftar remaining_misses.csv mengikuti
    varian B (kritis = 71/39, cocok draf peneliti); forwarded.csv memuat
    seluruh skenario yang diteruskan salah satu kebijakan.
    """
    data = json.loads(models_path.read_text(encoding="utf-8"))
    models = data["models"]
    rev = models_path.parent

    engines = {}
    for m in models:
        scales = m.get("scales") or {"s_k": 20.0, "s_R": 80.0}
        am = ac.build_ari_model(m, None, scales)
        cache: dict = {}
        s_b, st_b = ac.compute_graph_score(am, None, cache)
        engines[m["id"]] = (am, (s_b, st_b), cache, MechanicalGuard(m))

    # ---- PASS 1: keputusan (intact-only) — disimpan SEBELUM respons acuan ----
    dec_rows = []
    for m in models:
        am, base, cache, g = engines[m["id"]]
        for e in sorted(am.edges, key=lambda x: x["id"]):
            eid = e["id"]
            for lam in LAMS:
                r = ac.compute_ari(am, (eid, lam), baseline=base,
                                   pair_cache=cache)
                dec_rows.append(dict(
                    model=m["id"], edge=eid, lam=lam,
                    CI=("" if r.CI is None else round(r.CI, 9)),
                    status=r.status_code,
                    ari_forward=int(r.CI is not None and r.CI >= TAU),
                    m_s=round(g.m_e(eid, lam), 12),
                    guard_flag=g.guard_flag(eid, lam)))
    dec_path = rev / "decisions.csv"
    with open(dec_path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(dec_rows[0].keys()))
        wr.writeheader()
        wr.writerows(dec_rows)
    dec_hash = hashlib.sha256(dec_path.read_bytes()).hexdigest()

    # ---- PASS 2: respons acuan pascagangguan + hitungan ----------------------
    counts = dict(n=0, rank_lost=0, critical=0, add_critical=0,
                  ari_fwd=0, guard_fwd=0, comb_fwd=0,
                  ari_missed=0, guard_missed=0, comb_missed=0,
                  ari_rank_missed=0, guard_rank_missed=0, comb_rank_missed=0)
    alt = dict(n=0, rank_lost=0, critical=0, add_critical=0,
               ari_fwd=0, guard_fwd=0, comb_fwd=0,
               ari_missed=0, guard_missed=0, comb_missed=0,
               ari_rank_missed=0, guard_rank_missed=0, comb_rank_missed=0)
    misses = []
    fwd_rows = []
    for m in models:
        am, base, cache, g = engines[m["id"]]
        u0 = float(am.result.umax)
        caps_o = {int(k): float(v) for k, v in m["capacities"].items()}
        for e in sorted(am.edges, key=lambda x: x["id"]):
            eid = e["id"]
            lab = f"e{eid+1}"
            for lam in LAMS:
                r = ac.compute_ari(am, (eid, lam), baseline=base,
                                   pair_cache=cache)
                disr = ac._apply_stiffness_multiplier(m, {eid: lam},
                                                      drop_zero=True)
                res = solve_model(disr)
                rank_lost = (res.status != "ok")
                # Konvensi UTAMA (A, sesuai 4.1.5): utilisasi respons
                # terdisrupsi vs kapasitas state saat itu (target x lambda).
                # Varian alternatif (B): vs kapasitas ASLI — dilaporkan untuk
                # rekonsiliasi dengan draf Tabel 4.5.
                Umax_B = None
                if not rank_lost:
                    Umax_B = max(
                        abs(float(res.element_forces[i])) /
                        caps_o[int(el["id"])]
                        for i, el in enumerate(disr["elements"]))
                uA = bool(res.Umax > 1.0) if not rank_lost else False
                uB = bool(Umax_B > 1.0) if Umax_B is not None else False
                d_over = (bool(res.umax > 2.0 * u0)
                          if not rank_lost else False)
                critA = rank_lost or uA or d_over
                critB = rank_lost or uB or d_over
                ari_f = bool(r.CI is not None and r.CI >= TAU)
                guard_f = (g.guard_flag(eid, lam) == 1)
                for cnt in (counts, alt):
                    cnt["n"] += 1
                    cnt["rank_lost"] += int(rank_lost)
                    cnt["ari_fwd"] += int(ari_f)
                    cnt["guard_fwd"] += int(guard_f)
                    cnt["comb_fwd"] += int(ari_f or guard_f)
                    if rank_lost:
                        cnt["ari_rank_missed"] += int(not ari_f)
                        cnt["guard_rank_missed"] += int(not guard_f)
                        cnt["comb_rank_missed"] += int(not (ari_f or guard_f))
                if critA:
                    counts["critical"] += 1
                    counts["add_critical"] += int(not rank_lost)
                    counts["ari_missed"] += int(not ari_f)
                    counts["guard_missed"] += int(not guard_f)
                    counts["comb_missed"] += int(not (ari_f or guard_f))
                if critB:
                    alt["critical"] += 1
                    alt["add_critical"] += int(not rank_lost)
                    alt["ari_missed"] += int(not ari_f)
                    alt["guard_missed"] += int(not guard_f)
                    alt["comb_missed"] += int(not (ari_f or guard_f))
                if critB and not (ari_f or guard_f):
                    cause = ("rank" if rank_lost else
                             ("utilisasi" if uB else "") +
                             ("+perpindahan" if d_over else ""))
                    misses.append(dict(model=m["id"], edge=lab,
                                       lambda_=lam, cause=cause,
                                       CI=("" if r.CI is None
                                           else round(r.CI, 9))))
                if ari_f or guard_f:
                    fwd_rows.append(dict(
                        model=m["id"], edge=lab, lambda_=lam,
                        CI=("" if r.CI is None else round(r.CI, 9)),
                        by=("both" if (ari_f and guard_f)
                            else ("ari" if ari_f else "guard")),
                        rank_lost=int(rank_lost), crit_A=int(critA),
                        crit_B=int(critB)))
    miss_path = rev / "remaining_misses.csv"
    with open(miss_path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["model", "edge", "lambda_",
                                            "cause", "CI"])
        wr.writeheader()
        wr.writerows(misses)
    fwd_path = rev / "forwarded.csv"
    with open(fwd_path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["model", "edge", "lambda_", "CI",
                                            "by", "rank_lost", "crit_A",
                                            "crit_B"])
        wr.writeheader()
        wr.writerows(fwd_rows)

    draft = data["meta"]["targets_tabel_45"]
    comparison = [
        ("N", draft["N"], counts["n"], alt["n"]),
        ("rank_kurang", draft["rank_kurang"], counts["rank_lost"],
         alt["rank_lost"]),
        ("kritis_total", draft["kritis_total"], counts["critical"],
         alt["critical"]),
        ("kritis_tambahan", draft["kritis_tambahan"], counts["add_critical"],
         alt["add_critical"]),
        ("ari_diteruskan", draft["ari_diteruskan"], counts["ari_fwd"],
         alt["ari_fwd"]),
        ("pengaman_diteruskan", draft["pengaman_diteruskan"],
         counts["guard_fwd"], alt["guard_fwd"]),
        ("gabungan_diteruskan", draft["gabungan_diteruskan"],
         counts["comb_fwd"], alt["comb_fwd"]),
        ("ari_rank_terlewat", draft["ari_rank_terlewat"],
         counts["ari_rank_missed"], alt["ari_rank_missed"]),
        ("pengaman_rank_terlewat", draft["pengaman_rank_terlewat"],
         counts["guard_rank_missed"], alt["guard_rank_missed"]),
        ("gabungan_rank_terlewat", draft["gabungan_rank_terlewat"],
         counts["comb_rank_missed"], alt["comb_rank_missed"]),
        ("ari_kritis_terlewat", draft["ari_kritis_terlewat"],
         counts["ari_missed"], alt["ari_missed"]),
        ("pengaman_kritis_terlewat", draft["pengaman_kritis_terlewat"],
         counts["guard_missed"], alt["guard_missed"]),
        ("gabungan_kritis_terlewat", draft["gabungan_kritis_terlewat"],
         counts["comb_missed"], alt["comb_missed"]),
    ]
    rows = []
    cocok_A: list = []
    cocok_B: list = []
    for m_, d_, a_, b_ in comparison:
        tag = ("A+B" if (d_ == a_ and d_ == b_)
               else ("A" if d_ == a_ else ("B" if d_ == b_ else "-")))
        rows.append(dict(metric=m_, draft=d_, aktual_A=a_, aktual_B=b_,
                         cocok=tag))
        if tag in ("A", "A+B"):
            cocok_A.append(m_)
        if tag in ("B", "A+B"):
            cocok_B.append(m_)
    return dict(
        status="available", counts=counts, counts_alt_B=alt,
        decisions_csv=str(dec_path.relative_to(ROOT)),
        decisions_sha256=dec_hash,
        remaining_misses_csv=str(miss_path.relative_to(ROOT)),
        forwarded_csv=str(fwd_path.relative_to(ROOT)),
        n_misses=len(misses),
        comparison_vs_draft=rows,
        cocok_A=cocok_A, cocok_B=cocok_B,
        selisih=[r["metric"] for r in rows if r["cocok"] == "-"])


def main() -> int:
    models = load_models(ROOT / "examples" / "verification_models.json")
    by_id = {str(m["id"]): m for m in models}
    guards = {mid: MechanicalGuard(m) for mid, m in by_id.items()}

    print("=" * 78)
    print("GUARD VERIFICATION — paket pengaman kinematik (Bagian 4.2)")
    print("=" * 78)

    # ------------------------------------------------------------- A. analitis
    print("\n[A] Uji analitis:")
    g1 = guards["M1_parallel_bars_1d"]
    ok_a = True
    ok_a &= check("A", "M1 h_0 = 2/3 (closed form)", 2 / 3, g1.h[0], 1e-9)
    ok_a &= check("A", "M1 h_1 = 1/3 (closed form)", 1 / 3, g1.h[1], 1e-9)
    resid = max(g1.verify_update_identity(0, lam) for lam in (0.5, 0.25))
    ok_a &= check("A", "Eq 4.7 residual M1-e0 (lam .5,.25) < 1e-8",
                  0.0, resid, 1e-8)
    g3 = guards["M3_square_one_diagonal"]
    resid3 = max(g3.verify_update_identity(eid, 0.5) for eid in (0, 4))
    ok_a &= check("A", "Eq 4.7 residual M3-e1/e5 (lam .5) < 1e-8",
                  0.0, resid3, 1e-8)
    print(f"    residual M1 = {resid:.2e} ; M3 = {resid3:.2e}")

    # ------------------------------------------------------------- B. regresi
    print("\n[B] Regresi kanonik:")
    engines, baselines, caches = {}, {}, {}
    for mid, m in by_id.items():
        am = ac.build_ari_model(m)
        c = {}
        s_b, st_b = ac.compute_graph_score(am, None, c)
        engines[mid], baselines[mid], caches[mid] = am, (s_b, st_b), c
    ok_b = True
    am3 = engines["M3_square_one_diagonal"]
    for eid, (t_rr, t_ci) in TABEL_43.items():
        r = ac.compute_ari(am3, (eid, 0.0), baseline=baselines
                           ["M3_square_one_diagonal"],
                           pair_cache=caches["M3_square_one_diagonal"])
        ok_b &= check("B", f"Tabel 4.3 e{eid+1} RR", t_rr, r.RR, TOL_43)
        ok_b &= check("B", f"Tabel 4.3 e{eid+1} CI", t_ci, r.CI, TOL_43)
    am1 = engines["M1_parallel_bars_1d"]
    for eid, t_rr in ((0, 7 / 17), (1, 10 / 17)):
        r = ac.compute_ari(am1, (eid, 0.0),
                           baseline=baselines["M1_parallel_bars_1d"],
                           pair_cache=caches["M1_parallel_bars_1d"])
        ok_b &= check("B", f"Tabel 4.11 bar{eid} RR", t_rr, r.RR, 1e-6)
    for eid, lab in ((2, "e3"), (3, "e4")):
        disr = ac._apply_stiffness_multiplier(
            by_id["M3_square_one_diagonal"], {eid: 0.0}, drop_zero=True)
        res = solve_model(disr)
        ok_b &= check("B", f"Tabel 4.4 {lab} h_e=1.000000", 1.0, g3.h[eid],
                      1e-9)
        ok_b &= check("B", f"Tabel 4.4 {lab} m_e(0)~0", 0.0,
                      g3.m_e(eid, 0.0), 1e-12)
        ok_b &= check("B", f"Tabel 4.4 {lab} rank 4/5", "4/5",
                      f"{int(res.rank)}/{int(res.n_free)}")
        ok_b &= check("B", f"Tabel 4.4 {lab} guard g=1", 1,
                      g3.guard_flag(eid, 0.0))
    n_eq44 = n_tot44 = 0
    for mid, g in guards.items():
        for eid in sorted(g.h):
            for lam in (1.0, 0.75, 0.5, 0.25, 0.0):
                n_tot44 += 1
                n_eq44 += int(g.margin(eid, lam)["bound_ok"])
    ok_b &= check("B", "Eq 4.4 batas kondisi seluruh grid", n_tot44, n_eq44)

    # ------------------------------------------------------------- C. diagnostik
    print("\n[C] Diagnostik kanonik (Tabel 4.2/4.5):")
    diag = dict(rank_lost=0, critical=0, ari_fwd=0, guard_fwd=0, comb_fwd=0,
                ari_missed=0, guard_missed=0, comb_missed=0)
    for mid, m in by_id.items():
        am = engines[mid]
        g = guards[mid]
        u0 = float(am.result.umax)
        for e in am.edges:
            eid = e["id"]
            for lam in LAMS:
                r = ac.compute_ari(am, (eid, lam), baseline=baselines[mid],
                                   pair_cache=caches[mid])
                disr = ac._apply_stiffness_multiplier(m, {eid: lam},
                                                      drop_zero=True)
                res = solve_model(disr)
                rank_lost = (res.status != "ok")
                u_over = d_over = False
                if not rank_lost:
                    # Kriteria (4.2.4): utilisasi respons terdisrupsi vs
                    # kapasitas state saat itu (target x lambda; 4.1.5) —
                    # `>` polos; mereproduksi hitungan kanonik naskah.
                    u_over = bool(res.Umax > 1.0)
                    d_over = bool(res.umax > 2.0 * u0)
                diag["rank_lost"] += int(rank_lost)
                ari_f = (r.CI is not None) and (r.CI >= TAU)
                guard_f = (g.guard_flag(eid, lam) == 1)
                diag["ari_fwd"] += int(ari_f)
                diag["guard_fwd"] += int(guard_f)
                diag["comb_fwd"] += int(ari_f or guard_f)
                if not (rank_lost or u_over or d_over):
                    continue
                diag["critical"] += 1
                diag["ari_missed"] += int(not ari_f)
                diag["guard_missed"] += int(not guard_f)
                diag["comb_missed"] += int(not (ari_f or guard_f))
    print(f"    rank-turun={diag['rank_lost']} kritis={diag['critical']} | "
          f"ARI fwd={diag['ari_fwd']} pengaman fwd={diag['guard_fwd']} "
          f"gabungan fwd={diag['comb_fwd']} | terlewat "
          f"{diag['ari_missed']}/{diag['guard_missed']}/"
          f"{diag['comb_missed']}")
    ok_c = True
    for key, target in (("rank_lost", 8), ("critical", 17), ("ari_fwd", 5),
                        ("guard_fwd", 8), ("comb_fwd", 11),
                        ("ari_missed", 14), ("guard_missed", 9),
                        ("comb_missed", 8)):
        ok_c &= check("C", f"Tabel 4.2/4.5 {key}", target, diag[key])

    # ------------------------------------------------------------- D. parametrik
    print("\n[D] Paket parametrik §4.2.4 (272 skenario):")
    models_rev = ROOT / "results" / "revision" / "models.json"
    if models_rev.exists():
        param = run_parametric(models_rev)
        c = param["counts"]
        print(f"    N={c['n']}  rank-turun={c['rank_lost']}  "
              f"kritis={c['critical']} (tambahan {c['add_critical']})")
        print(f"    diteruskan — ARI={c['ari_fwd']}  pengaman={c['guard_fwd']}  "
              f"gabungan={c['comb_fwd']}")
        print(f"    terlewat — rank {c['ari_rank_missed']}/"
              f"{c['guard_rank_missed']}/{c['comb_rank_missed']}; kritis "
              f"{c['ari_missed']}/{c['guard_missed']}/{c['comb_missed']}")
        b_ = param.get("counts_alt_B", {})
        if b_:
            print(f"    varian B (kapasitas asli): kritis={b_['critical']} "
                  f"tambahan={b_['add_critical']}; terlewat kritis "
                  f"{b_['ari_missed']}/{b_['guard_missed']}/"
                  f"{b_['comb_missed']}")
        print(f"    vs draf Tabel 4.5: cocok-A {len(param['cocok_A'])}/"
              f"{len(param['comparison_vs_draft'])}, cocok-B "
              f"{len(param['cocok_B'])}/{len(param['comparison_vs_draft'])}")
        print(f"    [berkas] {param['decisions_csv']} (sha256 "
              f"{param['decisions_sha256'][:16]}…) + "
              f"{param['remaining_misses_csv']} ({param['n_misses']} baris) "
              f"+ {param['forwarded_csv']}")
    else:
        param = dict(status="pending_material",
                     expected_path=str(models_rev.relative_to(ROOT)),
                     note="Berkas model parametrik §4.2.4 belum ada di repo.")
        print(f"    {param['status']} — {param['note']}")

    # ------------------------------------------------------------- keluaran
    n_pass = sum(1 for c in CHECKS if c["pass_"])
    n_fail = len(CHECKS) - n_pass
    result = dict(
        generated=datetime.now(timezone.utc).isoformat(),
        generator="examples/run_guard_verification.py (Bagian 4.2 / 4.5.11)",
        groups=dict(A_analitis=bool(ok_a), B_regresi=bool(ok_b),
                    C_diagnostik=bool(ok_c), D_parametrik=param),
        checks_total=len(CHECKS), checks_pass=n_pass, checks_fail=n_fail,
        checks=CHECKS,
    )
    OUT.write_text(json.dumps(result, indent=2, default=str),
                   encoding="utf-8")
    print(f"\n[berkas] {OUT.relative_to(ROOT)} "
          f"({n_pass}/{len(CHECKS)} LULUS)")
    print("=" * 78)
    print("GUARD VERIFICATION:", "PASS" if n_fail == 0 else f"FAIL ({n_fail})")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
