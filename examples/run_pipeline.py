"""
run_pipeline.py — GATE 4/5: Integrasi Pipeline Penuh ARI Screening
==================================================================
(Gate 5 menambahkan schema kanonik `pipeline_output.csv` utk curve_extractor.)

Disertasi "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening".

Menggabungkan ketiga lapisan yang telah lulus di Gate 1-3 menjadi SATU
pipeline audit-ready:

    Lapisan 1  Solver referensi FE (Gate 1, truss_reference.solve_model)
               -> gaya batang awal, reaksi r^(0), utilisasi U*, umax.
    Lapisan 2  Mesin ARI murni-graf (Gate 2, ari_core.run_full_screening)
               -> S(G_M), RR_e(lambda), ARI_e(lambda), CI_e(lambda).
    Lapisan 3  Kinematic Guard observasional (Gate 3, kinematic_guard)
               -> rank intact->disrupted, rank_drop, label
                  CONSISTENT / MECHANISM / GRAPH_BLIND.

Prinsip desain (kontrak Gate 4):
  * TIDAK ADA perubahan formula/parameter — pipeline hanya mengorkestrasi
    modul Gate 1-3 apa adanya (regresi dijaga).
  * Guard bersifat OBSERVASIONAL: RR/ARI/CI tidak pernah dimodifikasi.
  * Grid penuh: lambda in {1, 0.75, 0.5, 0.25, 0} x setiap edge fisik
    (kontrol per-edge lambda=1 + 4 skenario disrupsi per edge) = 80 run
    untuk 16 edge kanonik, plus 4 kontrol utuh (per model).
  * abstain/uncertified => RR/ARI/CI kosong (None) di CSV — bukan angka
    sembarang.
  * Semua temuan deviasi tetap dicatat ke DEFERRED_FINDINGS.md (sprint
    mode); pipeline TIDAK berhenti untuk debug.

Output:
  results/verification/ari_screening_full.csv   (audit trail berkolom
                                                 kinematik, kolom `layer`)
  results/verification/screening_report.json    (ringkasan agregat +
                                                 konsistensi-check antar
                                                 lapisan vs Gate 2/3)

Pemakaian:
    python examples/run_pipeline.py
Exit code: 0 = pipeline selesai & semua konsistensi-check LULUS;
           1 = ada inkonsistensi antar-lapisan (butuh review).

Satuan: kN, mm, E = 200 kN/mm^2.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ari_core as ac                                   # noqa: E402 (Gate 2)
from truss_reference import load_models                 # noqa: E402 (Gate 1)
from kinematic_guard import (kinetic_snapshot,          # noqa: E402 (Gate 3)
                             guard_scenario, classify)

LAMBDAS = (1.0, 0.75, 0.5, 0.25, 0.0)     # grid penuh (kontrol + disrupsi)
OUT_CSV = ROOT / "results" / "verification" / "ari_screening_full.csv"
# Gate 5: schema KANONIK utk curve_extractor.py (spektra disertasi):
PIPE_CSV = ROOT / "results" / "verification" / "pipeline_output.csv"
OUT_JSON = ROOT / "results" / "verification" / "screening_report.json"

CSV_COLS = [
    "layer", "model", "edge_id", "lambda",
    # --- Lapisan 1: mekanik (solver Gate 1) ---
    "intact_rank", "intact_ndof", "U_star", "initial_force_kN",
    # --- Lapisan 2: ARI murni-graf (Gate 2) ---
    "status", "mechanical_status", "S_baseline", "S_scenario",
    "RR", "ARI", "CI",
    # --- Lapisan 3: kinematic guard (Gate 3) ---
    "disrupted_rank", "rank_drop", "solvable", "guard_label",
    # --- Gate 5: margin kinematik & keputusan guard kanonik ---
    "margin_m", "guard_decision",
    # --- audit tambahan ---
    "note",
    # --- Tabel 4.7 (Gate 9.3): kode status kanonik ---
    "status_code",
]

# Schema kanonik pipeline_output.csv (Gate 5 — kontrak curve_extractor):
PIPE_COLS = ["model_id", "edge_id", "lambda", "S_intact", "S_disrupted",
             "RR", "ARI", "CI", "rank_status", "margin_m",
             "guard_decision", "U_star", "status_code"]


def _margin_and_decision(diag: Optional[dict], intact: Optional[dict]):
    """Margin kinematik m_e(lambda) — definisi observasional Gate 5.

    m = rank_drop / ndof_free  (fraksi DOF bebas intak yang hilang akibat
    disrupsi). m = 0 <=> tidak ada mekanisme baru. Bukan pengganti analisis
    nullspace penuh; cukup utk deteksi perubahan status Clear->Forward.
    """
    if diag is None or intact is None:
        return "", ""
    ndof = int(intact["intact_ndof"]) or 1
    m = max(0, int(diag["rank_drop"])) / float(ndof)
    decision = "Clear" if (diag["solvable"] and m == 0.0) else "Forward"
    return round(m, 6), decision


def _f(x: Optional[float], nd: int = 12):
    return None if x is None else round(float(x), nd)


def run_pipeline(models_dir: Path = ROOT / "examples") -> dict:
    """Eksekusi pipeline penuh; return report struktur + daftar inkonsistensi."""
    models = load_models(str(models_dir / "verification_models.json"))
    by_id = {str(m["id"]): m for m in models}

    # ---- Gate 2 engine: baseline & cache per model (identik test_ari.py) --
    print("=" * 78)
    print("GATE 4 — PIPELINE PENUH (Solver -> ARI -> Kinematic Guard)")
    print("=" * 78)
    engines, baselines, caches = {}, {}, {}
    for mid, m in by_id.items():
        am = ac.build_ari_model(m)
        engines[mid] = am
        cache: dict = {}
        base_audit: dict = {}
        s_base, st_base = ac.compute_graph_score(am, None, cache, base_audit)
        baselines[mid] = (s_base, st_base)
        caches[mid] = cache
        print(f"[init] {mid:26s} S(G_M)={s_base:.9f} ({st_base})")

    rows = []
    inconsistencies = []
    agg = {}
    n_disruption_runs = 0
    n_control_runs = 0

    for mid, m in by_id.items():
        am = engines[mid]
        s_base, st_base = baselines[mid]
        caps = {int(k): float(v) for k, v in m["capacities"].items()}
        forces = {e["id"]: abs(float(am.result.element_forces[i]))
                  for i, e in enumerate(am.edges)}

        # Snapshot kinematik INTAK sekali per model (Lapisan 1/3)
        intact = kinetic_snapshot(m)

        summary = dict(
            model=mid, S_baseline=_f(s_base, 9), baseline_status=st_base,
            intact=dict(rank=intact["intact_rank"],
                        ndof=intact["intact_ndof"],
                        solvable=intact["intact_solvable"]),
            n_rows=0, counts={"CONSISTENT": 0, "MECHANISM": 0,
                              "GRAPH_BLIND": 0, "?": 0},
            graph_blind=[], utilization={},
        )
        summary["utilization"] = {
            str(eid): _f(min(forces[eid] / (caps[eid] + am.config["eps_R"]),
                             1.0), 6) for eid in sorted(forces)}

        # ---- Kontrol UTUH (tanpa edge): RR=1, ARI=1, CI=0 --------------
        ctrl = ac.compute_ari(am, None, baseline=baselines[mid],
                              pair_cache=caches[mid])
        rows.append(dict(
            layer="control_intact", model=mid, edge_id=None, lam=1.0,
            U_star=None, force=None, status=ctrl.status,
            mech=ctrl.detail.get("mechanical_status", "ok"),
            S_b=s_base, S=ctrl.S, RR=ctrl.RR, ARI=ctrl.ARI, CI=ctrl.CI,
            diag=None, label="?", margin=0.0, decision="Clear",
            code=ctrl.status_code,
            note="kontrol utuh tanpa edge"))
        n_control_runs += 1

        # ---- Per edge x lambda -------------------------------------------
        for e in sorted(am.edges, key=lambda x: x["id"]):
            eid = e["id"]
            # (a) kontrol per-edge lambda=1 (Lapisan 2 + snapshot intak)
            res1 = ac.compute_ari(am, (eid, 1.0), baseline=baselines[mid],
                                  pair_cache=caches[mid])
            rows.append(dict(
                layer="control_edge", model=mid, edge_id=eid, lam=1.0,
                U_star=res1.U_star, force=forces[eid], status=res1.status,
                mech=res1.detail.get("mechanical_status", "ok"),
                S_b=s_base, S=res1.S, RR=res1.RR, ARI=res1.ARI, CI=res1.CI,
                diag=None, label="?", margin=0.0, decision="Clear",
                code=res1.status_code,
                note="RR eksak 1; CI=eta*U*_e (kontrol Gate 2 blok [5])"))
            n_control_runs += 1
            # Konsistensi-check vs kontrak Gate 2: RR==1 eksak, CI==eta*U*
            exp_ci = am.config["eta"] * (res1.U_star or 0.0)
            if not (res1.RR == 1.0 and abs(res1.CI - exp_ci) < 1e-12):
                inconsistencies.append(
                    f"{mid} e{eid} lam=1: RR/CI kontrol salah "
                    f"(RR={res1.RR}, CI={res1.CI}, eta*U*={exp_ci})")

            # (b) skenario disrupsi lambda < 1 (Lapisan 2 + Lapisan 3)
            model_rows = []   # riwayat RR edge ini utk cek monotonic per-edge
            for lam in LAMBDAS:
                if lam == 1.0:
                    continue
                res = ac.compute_ari(am, (eid, lam), baseline=baselines[mid],
                                     pair_cache=caches[mid])
                diag = guard_scenario(m, eid, lam, intact)
                label = classify(diag, res.CI)
                margin, decision = _margin_and_decision(diag, intact)
                rows.append(dict(
                    layer="disruption", model=mid, edge_id=eid, lam=lam,
                    U_star=res.U_star, force=forces[eid], status=res.status,
                    mech=res.detail.get("mechanical_status", ""),
                    S_b=s_base, S=res.S, RR=res.RR, ARI=res.ARI, CI=res.CI,
                    diag=diag, label=label, margin=margin,
                    decision=decision,
                    code=res.status_code,
                    note=res.detail.get("note", "")))
                n_disruption_runs += 1
                summary["counts"][label] = summary["counts"].get(label, 0) + 1
                if label == "GRAPH_BLIND":
                    summary["graph_blind"].append(
                        dict(edge_id=eid, lambda_=lam, RR=_f(res.RR, 6),
                             CI=_f(res.CI, 6), rank_drop=diag["rank_drop"]))

                # Konsistensi-check Lapisan 2 vs 3 (kebijakan Gate 3/4):
                #   Mekanisme pada state terdisrupsi harus TERDETEKSI OLEH
                #   KEDUA lapisan dengan cara masing-masing, dan keduanya
                #   wajib sepakat:
                #     Lapisan 2 (ari_core.compute_graph_score -> solver
                #       Gate 1) -> detail["mechanical_status"] != "ok"
                #     Lapisan 3 (kinematic_guard.guard_scenario)
                #       -> diag["solvable"] == False  ATAU rank_drop > 0
                lay2_mech_bad = (res.detail.get("mechanical_status") != "ok")
                lay3_mech_bad = (not diag["solvable"]) or diag["rank_drop"] > 0
                if lay2_mech_bad != lay3_mech_bad:
                    inconsistencies.append(
                        f"{mid} e{eid} lam={lam}: Lapisan2 "
                        f"(mech={res.detail.get('mechanical_status')}) vs "
                        f"Lapisan3 (solvable={diag['solvable']}, "
                        f"rank_drop={diag['rank_drop']}) tidak sepakat")
                # GRAPH_BLIND hanya boleh terjadi pada skenario mekanisme.
                if label == "GRAPH_BLIND" and diag["solvable"]:
                    inconsistencies.append(
                        f"{mid} e{eid} lam={lam}: GRAPH_BLIND tanpa mekanisme")
                # Monotonisitas RR thd lambda (turunan dari monotonisitas S):
                # RR(1)=1 >= RR(0.75) >= RR(0.5) >= RR(0.25) >= RR(0)
                prev = model_rows[-1]["RR"] if model_rows else 1.0
                if prev is not None and res.RR is not None and \
                        res.RR > prev + 1e-12:
                    inconsistencies.append(
                        f"{mid} e{eid}: RR naik saat lambda turun "
                        f"({prev:.9f} -> {res.RR:.9f})")
                model_rows.append(dict(lam=lam, RR=res.RR))
                # catatan: urutan loop lambda menurun => prev adalah RR pada
                # lambda sebelumnya yang lebih besar.

        agg[mid] = summary

    # ---- Regresi cepat terhadap angka kunci Gate 2 -----------------------
    def get(mid, eid, lam):
        for r in rows:
            if r["model"] == mid and r["edge_id"] == eid and r["lam"] == lam:
                return r
        return None

    gate2_checks = []
    checks = [
        # (deskripsi, baris, field, nilai harapan, toleransi absolut)
        ("Tabel 4.11 remove bar0 RR=7/17",
         get("M1_parallel_bars_1d", 0, 0.0), "RR", 7 / 17, 1e-6),
        ("Tabel 4.11 remove bar1 RR=10/17",
         get("M1_parallel_bars_1d", 1, 0.0), "RR", 10 / 17, 1e-6),
        # Gate 9 (DF-01 ditutup): baris e1/e2/e5 kini tereproduksi <= 4e-7
        ("Tabel 4.3 e1(AB) RR=0.983152",
         get("M3_square_one_diagonal", 0, 0.0), "RR", 0.983152, 1e-5),
        ("Tabel 4.3 e1(AB) CI=0.016848",
         get("M3_square_one_diagonal", 0, 0.0), "CI", 0.016848, 1e-5),
        ("Tabel 4.3 e2(BC) RR=0.964724",
         get("M3_square_one_diagonal", 1, 0.0), "RR", 0.964724, 1e-5),
        ("Tabel 4.3 e2(BC) CI=0.216162",
         get("M3_square_one_diagonal", 1, 0.0), "CI", 0.216162, 1e-5),
        ("Tabel 4.3 e3(CD) KRITIS RR=1",
         get("M3_square_one_diagonal", 2, 0.0), "RR", 1.0, 1e-6),
        ("Tabel 4.3 e3(CD) KRITIS CI=0",
         get("M3_square_one_diagonal", 2, 0.0), "CI", 0.0, 1e-6),
        ("Tabel 4.3 e4(DA) KRITIS RR=1",
         get("M3_square_one_diagonal", 3, 0.0), "RR", 1.0, 1e-6),
        ("Tabel 4.3 e4(DA) KRITIS CI=0",
         get("M3_square_one_diagonal", 3, 0.0), "CI", 0.0, 1e-6),
        ("Tabel 4.3 e5(AC) RR=0.717285",
         get("M3_square_one_diagonal", 4, 0.0), "RR", 0.717285, 1e-5),
        ("Tabel 4.3 e5(AC) CI=0.472914",
         get("M3_square_one_diagonal", 4, 0.0), "CI", 0.472914, 1e-5),
    ]
    print("\n[konsistensi-regresi Gate 2]")
    for desc, r, fld, exp, tol in checks:
        got = r[fld.upper() if fld.islower() else fld] if r else None
        good = r is not None and got is not None and abs(got - exp) <= tol
        gate2_checks.append(dict(check=desc, expected=exp, actual=got,
                                 pass_=bool(good)))
        if not good:
            inconsistencies.append(f"Regresi Gate 2 gagal: {desc}")
        print(f"  {'PASS' if good else 'FAIL'}  {desc}"
              f"  (actual={got})")

    # GRAPH_BLIND harus terdeteksi utk M3 e2,e3 (menutup Finding #003)
    gb = agg["M3_square_one_diagonal"]["graph_blind"]
    gb_edges = sorted(g["edge_id"] for g in gb if g["lambda_"] == 0.0)
    good = gb_edges == [2, 3]
    gate2_checks.append(dict(check="Guard melabeli M3 e2,e3 GRAPH_BLIND",
                             expected=[2, 3], actual=gb_edges, pass_=good))
    if not good:
        inconsistencies.append("Kinematic guard tidak melabeli kasus #003")
    print(f"  {'PASS' if good else 'FAIL'}  GRAPH_BLIND M3@lam0 = {gb_edges}")

    # ---- Ringkasan agregat guard (semua lambda) ----------------------------
    print("\n[agregat Kinematic Guard — semua skenario disrupsi]")
    print(f"  {'model':26s} {'CONSISTENT':>10s} {'MECHANISM':>10s} "
          f"{'GRAPH_BLIND':>12s}")
    for mid, sm in agg.items():
        c = sm["counts"]
        print(f"  {mid:26s} {c.get('CONSISTENT',0):>10d} "
              f"{c.get('MECHANISM',0):>10d} {c.get('GRAPH_BLIND',0):>12d}")

    # ---- Tulis CSV (audit trail penuh Gate 4) -----------------------------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    _intact_by_model = {mid: agg[mid]["intact"]["rank"] for mid in agg}
    with open(OUT_CSV, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(CSV_COLS)
        for r in rows:
            diag = r["diag"] or {}
            wr.writerow([
                r["layer"], r["model"],
                "" if r["edge_id"] is None else r["edge_id"], r["lam"],
                _intact_by_model[r["model"]],
                _ndof_of(r["model"], agg),
                _num(r["U_star"]), _num(r["force"]),
                r["status"], r["mech"],
                _num(r["S_b"], 9), _num(r["S"], 9),
                _num(r["RR"]), _num(r["ARI"]), _num(r["CI"]),
                diag.get("disrupted_rank", ""), diag.get("rank_drop", ""),
                ("yes" if diag.get("solvable") else "no") if diag else "",
                r["label"],
                r["margin"], r["decision"],
                r["note"],
                r["code"],
            ])
    print(f"\n[CSV] {OUT_CSV} ({len(rows)} baris data + header)")

    # ---- Tulis pipeline_output.csv (Gate 5 — schema kanonik curve_extractor)
    # Baris yg dipakai extractor: SEMUA layer (kontrol utuh edge_id="" hanya
    # utk informasi; extractor mengelompokkan per (model_id, edge_id)).
    with open(PIPE_CSV, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(PIPE_COLS)
        for r in rows:
            if r["layer"] == "control_intact":
                continue          # bukan skenario per-edge
            diag = r["diag"] or {}
            rank_status = ("ok" if (r["layer"] != "disruption"
                                    or diag.get("solvable", True))
                           else "rank_deficient")
            wr.writerow([
                r["model"], r["edge_id"], r["lam"],
                _num(r["S_b"], 9), _num(r["S"], 9),
                _num(r["RR"]), _num(r["ARI"]), _num(r["CI"]),
                rank_status,
                r["margin"], r["decision"], _num(r["U_star"]),
                r["code"],
            ])
    print(f"[CSV] {PIPE_CSV} (schema Gate 5: {', '.join(PIPE_COLS)})")

    report = dict(
        generated="Gate 9 pipeline (run_pipeline.py)",
        date="2026-10-13",
        config=dict(alpha_k=0.5, alpha_R=0.5, q_e=1.0, K=2, gamma=1.0,
                    beta=0.1, eta=0.5, eps_w=1e-9, eps_d=1e-9, eps_R=1e-6,
                    baseline_tol=1e-12, lambdas=list(LAMBDAS)),
        n_rows=len(rows), n_disruption_runs=n_disruption_runs,
        n_control_runs=n_control_runs,
        per_model=agg,
        consistency_checks=gate2_checks,
        inconsistencies=inconsistencies,
        deferred_refs=["Finding #001 (DF-01) DITUTUP: b_jc per komponen reaksi (Gate 9)",
                       "Finding #002 (DF-03) invariansi asimtotik",
                       "Finding #003 kasus kritis GRAPH_BLIND (terdeteksi)",
                       "Finding #005 penamaan edge 1-based (tabel disertasi)",
                       "Finding #012 dikoreksi: identitas CI=1-RR(1-eta U*) terpenuhi"],
    )
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str))
    print(f"[JSON] {OUT_JSON}")

    return report


# helper kecil ------------------------------------------------------------
def _ndof_of(mid, agg):
    return agg[mid]["intact"]["ndof"]


def _num(x, nd=12):
    if x is None:
        return ""
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return x
    if xf != xf:      # nan
        return ""
    return round(xf, nd)


def main(argv) -> int:
    report = run_pipeline()
    inc = report["inconsistencies"]
    print("\n" + "=" * 78)
    print(f"RUN SELESAI: {report['n_rows']} baris "
          f"({report['n_disruption_runs']} skenario disrupsi + "
          f"{report['n_control_runs']} kontrol)")
    tot = {"CONSISTENT": 0, "MECHANISM": 0, "GRAPH_BLIND": 0}
    for s in report["per_model"].values():
        for k in tot:
            tot[k] += s["counts"].get(k, 0)
    print(f"Label guard (skenario disrupsi): {tot}")
    if inc:
        print("INKONSISTENSI TERDETEKSI:")
        for i in inc:
            print("  -", i)
        print("PIPELINE: FAIL")
        return 1
    print("Semua konsistensi-check antar-lapisan LULUS.")
    print("PIPELINE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
