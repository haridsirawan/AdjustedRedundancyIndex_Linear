"""
fine_grid_runner.py — GATE 6: Pipeline pada Grid Halus Delta-lambda = 0.05
==========================================================================
Disertasi "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening".

Sprint mode: TIDAK ADA perubahan formula/parameter ARI. Skrip ini hanya
menjalankan ORKESTRASI 3-LAPISAN yang sama dengan run_pipeline.py (Gate 4/5)
pada grid lambda yang lebih halus, untuk analisis visual plateau, guard-flip,
dan pola deviasi Finding #001.

Grid:
    lambda in {1.00, 0.95, 0.90, ..., 0.05, 0.00}   -> 21 titik per edge.

Per model x edge, setiap titik lambda menyimpan:
    S_intact, S_disrupted, RR, ARI, CI, rank_status, margin_m,
    guard_decision, U_star.

Output:
    results/verification/fine_grid_output.csv
    kolom PERSIS seperti pipeline_output.csv Gate 5 (PIPE_COLS), kecuali
    baris kontrol utuh tanpa edge-id DIKECUALIKAN (kontrak curve plotter:
    seluruh baris adalah skenario per-edge).

Konvensi abstain (spektra Gate 6):
    Jika sebuah skenario abstain (uncertified / baseline-tol), nilai
    numerik ditulis sebagai string "NaN" di CSV — BUKAN angka imputasi.
    (Catatan review: pipeline Gate 4/5 menulis kolom kosong utk abstain;
    gate 6 mengikuti instruksi eksplisit "catat sebagai NaN".)

Definisi margin & guard_decision identik Gate 5 (observasional):
    m_e(lambda) := rank_drop / ndof_free ; Clear jika solvable dan m == 0.

Pemakaian:
    python examples/fine_grid_runner.py
Exit code: 0 = semua skenario dieksekusi; 1 = ada error/kegagalan eksekusi.

Satuan: kN, mm, E = 200 kN/mm^2.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))

import ari_core as ac                                   # noqa: E402 (Gate 2)
from truss_reference import load_models                 # noqa: E402 (Gate 1)
from kinematic_guard import kinetic_snapshot, guard_scenario  # noqa: E402 (Gate 3)

# ---- Grid halus Gate 6 -----------------------------------------------------
LAMBDAS_FINE = [round(1.0 - 0.05 * i, 2) for i in range(21)]   # 1.00 .. 0.00
assert LAMBDAS_FINE[0] == 1.0 and LAMBDAS_FINE[-1] == 0.0 and len(LAMBDAS_FINE) == 21

OUT_CSV = ROOT / "results" / "verification" / "fine_grid_output.csv"

# Schema KANONIK Gate 5 — kolom sama persis dgn pipeline_output.csv
CSV_COLS = ["model_id", "edge_id", "lambda", "S_intact", "S_disrupted",
            "RR", "ARI", "CI", "rank_status", "margin_m",
            "guard_decision", "U_star"]


def _num(x: Optional[float], nd: int = 12) -> object:
    """Format angka; abstain/None -> 'NaN' (instruksi Gate 6, no imputasi)."""
    if x is None:
        return "NaN"
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return x
    if xf != xf:      # nan
        return "NaN"
    return round(xf, nd)


def _margin_and_decision(diag: Optional[dict], intact: Optional[dict]):
    """Identik definisi Gate 5 (observasional; bukan pengganti nullspace)."""
    if diag is None or intact is None:
        return "", ""
    ndof = int(intact["intact_ndof"]) or 1
    m = max(0, int(diag["rank_drop"])) / float(ndof)
    decision = "Clear" if (diag["solvable"] and m == 0.0) else "Forward"
    return round(m, 6), decision


def run_fine_grid(models_dir: Path = ROOT / "examples") -> dict:
    """Eksekusi grid halus penuh; return ringkasan + daftar kegagalan."""
    models = load_models(str(models_dir / "verification_models.json"))
    by_id = {str(m["id"]): m for m in models}

    print("=" * 78)
    print("GATE 6 — FINE GRID RUNNER (Delta-lambda = 0.05, 21 titik/edge)")
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
    failures = []
    n_abstain = 0
    expected_edges = {"M1_parallel_bars_1d": 2, "M2_planar_triangle": 3,
                      "M3_square_one_diagonal": 5, "M4_square_two_diagonals": 6}

    for mid, m in by_id.items():
        am = engines[mid]
        s_base, st_base = baselines[mid]
        intact = kinetic_snapshot(m)          # snapshot kinematik sekali/model

        for e in sorted(am.edges, key=lambda x: x["id"]):
            eid = e["id"]
            prev_rr = None                    # cek monotonisitas ringan
            for lam in LAMBDAS_FINE:
                res = ac.compute_ari(am, (eid, lam),
                                     baseline=baselines[mid],
                                     pair_cache=caches[mid])
                diag = guard_scenario(m, eid, lam, intact)
                margin, decision = _margin_and_decision(diag, intact)
                rank_status = ("ok" if diag.get("solvable", True)
                               else "rank_deficient")
                if res.RR is None:
                    n_abstain += 1
                    failures.append(f"{mid} e{eid} lam={lam}: abstain "
                                    f"(status={res.status}) — dicatat NaN")
                # Monotonisitas RR thd lambda menurun (sanity-check, bukan
                # penghenti sprint): pelanggaran dicatat sbg temuan.
                if prev_rr is not None and res.RR is not None and \
                        res.RR > prev_rr + 1e-12:
                    failures.append(f"{mid} e{eid}: RR naik saat lambda "
                                    f"turun ({prev_rr:.9f} -> {res.RR:.9f})")
                if res.RR is not None:
                    prev_rr = res.RR
                rows.append([mid, eid, lam,
                             _num(s_base, 9), _num(res.S, 9),
                             _num(res.RR), _num(res.ARI), _num(res.CI),
                             rank_status, margin, decision,
                             _num(res.U_star)])

        n_edge = len(am.edges)
        got = sum(1 for r in rows if r[0] == mid)
        exp = expected_edges[mid] * len(LAMBDAS_FINE)
        ok = (n_edge == expected_edges[mid] and got == exp)
        print(f"[grid] {mid:26s} edges={n_edge} rows={got}/{exp} "
              f"{'OK' if ok else 'MISMATCH'}")
        if not ok:
            failures.append(f"{mid}: jumlah baris tidak sesuai kontrak")

    # ---- Tulis CSV ---------------------------------------------------------
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(CSV_COLS)
        wr.writerows(rows)
    print(f"\n[CSV] {OUT_CSV} ({len(rows)} baris data + header; "
          f"abstain/NaN = {n_abstain})")

    return dict(n_rows=len(rows), n_abstain=n_abstain, failures=failures)


def main(argv) -> int:
    summary = run_fine_grid()
    print("=" * 78)
    hard_fail = [f for f in summary["failures"] if "abstain" not in f]
    print(f"SELESAI: {summary['n_rows']} baris, "
          f"{summary['n_abstain']} skenario abstain (dicatat NaN)")
    if summary["failures"]:
        print("CATATAN TEMUAN:")
        for f in summary["failures"]:
            print("  -", f)
    if hard_fail:
        print("FINE GRID: FAIL (kegagalan struktural/monotonisitas)")
        return 1
    print("FINE GRID: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
