"""
kinematic_guard.py
==================

Gate 3 disertasi "Adjusted Redundancy Index (ARI) for Mechanics-Based
Screening" — KINEMATIC GUARD.

Motivasi (DEFERRED_FINDINGS Finding #003):
    Pada Square-One-Diagonal, penghapusan e3/e4 menurunkan rank K_ff dari 5
    menjadi 4 (struktur menjadi mekanisme), namun ARI murni-graf menghasilkan
    CI ~ 0 karena skor jalur optimal tidak berubah. Ini adalah BATAS
    REPRESENTASI ARI (skor graf tidak melihat kendala kinematik), bukan bug.

Solusi Gate 3:
    Lapisan diagnostik kinematik yang MEMPERKAYA hasil skrining ARI dengan
    bukti mekanik dari solver referensi Gate 1 (numpy.linalg.eigvals,
    toleransi relatif 1e-10 terhadap eigenvalue terbesar, TANPA pseudoinverse):

      * kinetic_snapshot(model)      -> status mekanik state INTAK
      * guard_scenario(model, eid, lam) -> diagnostik kinematik state terdisrupsi
      * annotate_screening(report)   -> memperkaya ScenarioResult ari_core
                                        dengan field kinematik (non-destruktif;
                                        nilai RR/ARI/CI TIDAK diubah)
      * classify(scenario_diag)      -> label review untuk sortasi tabel

Kebijakan desain (kontrak Gate 3):
    1. Guard TIDAK mengubah angka ARI — ia hanya menambahkan kolom audit
       ("guard flag"). Reviewer dapat menyaring baris berlabel:
         - "MECHANISM"      : rank-deficient pada lambda=0 (hapus-total)
         - "SOFTENING"      : rank-deficient parsial / degradasi kekekalan?
                              (tidak ada di model kanonik; didefinisikan utk
                              kelanjutan: lambda>0 tetap solvable tetapi
                              stiffness_ratio turun drastis)
         - "GRAPH_BLIND"    : CI_ARI < ci_blind_tol padahal rank turun
                              -> kasus Finding #003 (wajib masuk narasi
                              batas representasi)
         - "CONSISTENT"     : ARI dan kinematika sepakat (rank penuh).
    2. Deteksi rank memakai solver Gate 1 apa adanya (solve_model), sehingga
       tidak ada duplikasi logika K-assembly / rank-check.
    3. Edge lambda=0 diperlakukan sebagai PENGHAPUSAN FISIK (drop_zero),
       konsisten dengan konvensi Gate 2.

Satuan: kN, mm, E = 200 kN/mm^2.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from truss_reference import solve_model, load_models          # noqa: E402 (Gate 1)
from ari_core import (_apply_stiffness_multiplier,            # noqa: E402
                      build_ari_model, run_full_screening)

# -----------------------------------------------------------------------------
# Konstanta guard
# -----------------------------------------------------------------------------
CI_BLIND_TOL = 0.01        # ambang "CI kecil" utk klasifikasi GRAPH_BLIND
STIFF_WARN_RATIO = 0.25    # rasio lambda efektif total -> peringatan SOFTENING


def _intact_reference(model: dict):
    """Solver state INTAK -> (result, ndof_total). Dipanggil sekali per model."""
    res = solve_model(model)
    return res


def kinetic_snapshot(model: dict) -> dict:
    """Diagnostik kinematik state INTAK (dipakai juga oleh ari_core utk kontrol).

    Return dict berisi:
        intact_solvable, intact_rank, intact_ndof, intact_min_eig, intact_max_eig
    """
    res = solve_model(copy.deepcopy(model))
    return dict(
        intact_solvable=(res.status == "ok"),
        intact_rank=int(res.rank),
        intact_ndof=int(res.ndof),
        intact_min_eig=float(res.min_eig),
        intact_max_eig=float(res.max_eig),
    )


def guard_scenario(model: dict, edge_id: int, lambda_: float,
                   intact: Optional[dict] = None) -> dict:
    """Jalankan solver Gate 1 pada state terdisrupsi M_{e,lambda}.

    Return dict diagnostik:
        disrupted_status : "ok" | "rank_deficient"
        disrupted_rank   : rank K_ff state terdisrupsi
        rank_drop        : intact_free_dofs - disrupted_rank (>=0 berarti
                           mekanisme baru muncul; <0 tidak mungkin terjadi
                           utk pengurangan kekakuan, tapi dihitung jujur)
        solvable         : bool — apakah struktur masih dapat diselesaikan
                           TANPA pseudoinverse
        min_eig, max_eig : eigenvalue ekstrem K_ff (informasi kondisi)
    """
    if intact is None:
        intact = kinetic_snapshot(model)
    disrupted = _apply_stiffness_multiplier(model, {int(edge_id): float(lambda_)},
                                            drop_zero=True)
    res = solve_model(disrupted)
    diag = dict(
        edge_id=int(edge_id),
        lambda_=float(lambda_),
        disrupted_status=res.status,
        disrupted_rank=int(res.rank),
        intact_rank=intact["intact_rank"],
        solvable=(res.status == "ok"),
        min_eig=float(res.min_eig),
        max_eig=float(res.max_eig),
    )
    diag["rank_drop"] = int(intact["intact_rank"] - res.rank)
    return diag


def classify(diag: dict, ci_ari: Optional[float]) -> str:
    """Label review dari diagnostik + CI ARI (Finding #003 policy)."""
    if not diag.get("solvable", True):
        if ci_ari is not None and ci_ari < CI_BLIND_TOL and diag["rank_drop"] > 0:
            return "GRAPH_BLIND"     # mekanisme, tapi ARI melaporkan CI~0
        return "MECHANISM"
    return "CONSISTENT"


def annotate_screening(report: dict, models_by_id: Dict[str, dict],
                       lambdas: tuple = (0.0,), verbose: bool = False) -> dict:
    """Perkaya report run_full_screening() dgn kolom kinematik (non-destruktif).

    Untuk setiap skenario (eid, lam) ditambahkan:
        result.details["kinematic"] = guard_scenario(...)
        result.details["guard_label"] = classify(...)
    Nilai RR/ARI/CI TIDAK diubah — guard bersifat observasional.
    Return ringkasan agregat per model utk pencetakan tabel.
    """
    summary = {}
    for mid, rep in report.items():
        model = models_by_id[mid]
        intact = kinetic_snapshot(model)
        agg = dict(intact=intact, n_scenarios=0, n_mechanism=0,
                   n_graph_blind=0, n_consistent=0, graph_blind_rows=[])
        for (eid, lam), res in rep["scenarios"].items():
            if lam not in lambdas:
                continue
            diag = guard_scenario(model, eid, lam, intact)
            label = classify(diag, res.CI)
            res.detail["kinematic"] = diag
            res.detail["guard_label"] = label
            agg["n_scenarios"] += 1
            if label == "MECHANISM":
                agg["n_mechanism"] += 1
            elif label == "GRAPH_BLIND":
                agg["n_graph_blind"] += 1
                agg["graph_blind_rows"].append((eid, lam, res.CI, res.RR))
            else:
                agg["n_consistent"] += 1
            if verbose:
                print(f"  [{mid}] e{eid} lam={lam}: rank {diag['intact_rank']}"
                      f"->{diag['disrupted_rank']} ({diag['disrupted_status']})"
                      f" CI_ARI={res.CI:.6f} -> {label}")
        summary[mid] = agg
    return summary


# -----------------------------------------------------------------------------
# Self-test CLI
# -----------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    here = Path(__file__).resolve().parent
    models = load_models(here / "verification_models.json")
    by_id = {str(m["id"]): m for m in models}

    print("=" * 78)
    print("GATE 3 — KINEMATIC GUARD self-test")
    print("=" * 78)

    # Snapshot INTAK semua model
    print("\n[1] Snapshot kinematik state INTAK:")
    for mid, m in by_id.items():
        snap = kinetic_snapshot(m)
        print(f"    {mid:26s} rank={snap['intact_rank']:2d}/"
              f"{snap['intact_ndof']:2d} solvable={snap['intact_solvable']}"
              f" min_eig={snap['intact_min_eig']:.4e}")

    # Skrining ARI lalu anotasi guard (lambda=0 hapus-total)
    print("\n[2] Anotasi kinematik pada skenario hapus-total (lambda=0):")
    report = run_full_screening(models, lambdas=(0.0,))
    summary = annotate_screening(report, by_id, lambdas=(0.0,), verbose=False)

    hdr = (f"    {'model':26s} {'edge':>4s} {'lam':>4s} {'RR':>9s} "
           f"{'CI_ARI':>9s} {'rank':>7s} {'status':>15s} label")
    print(hdr)
    print("    " + "-" * (len(hdr) - 4))
    n_blind = 0
    for mid, rep in report.items():
        for (eid, lam), res in sorted(rep["scenarios"].items()):
            kin = res.detail.get("kinematic", {})
            label = res.detail.get("guard_label", "?")
            if label == "GRAPH_BLIND":
                n_blind += 1
            print(f"    {mid:26s} e{eid:<3d} {lam:4.2f} {res.RR:9.6f} "
                  f"{res.CI:9.6f} {kin.get('intact_rank','-')}->{kin.get('disrupted_rank','-'):<4}"
                  f" {kin.get('disrupted_status','?'):>15s} {label}")

    # Kasus kunci Finding #003: M3 e2 & e3 harus terlabel GRAPH_BLIND
    print("\n[3] Verifikasi kasus Finding #003 (M3_square_one_diagonal e2,e3):")
    ok = True
    for eid in (2, 3):
        res = report["M3_square_one_diagonal"]["scenarios"][(eid, 0.0)]
        lab = res.detail.get("guard_label")
        good = (lab == "GRAPH_BLIND" and abs(res.CI) < CI_BLIND_TOL
                and res.detail["kinematic"]["rank_drop"] > 0)
        ok = ok and good
        print(f"    e{eid}: CI={res.CI:.6f} rank_drop="
              f"{res.detail['kinematic']['rank_drop']} label={lab} "
              f"-> {'PASS' if good else 'FAIL'}")

    # Sanity: guard tidak mengubah angka ARI (non-destruktif) — dibandingkan
    # dengan baseline Gate 2 yang diketahui (Tabel 4.3 kasus kritis RR=1).
    print("\n[4] Sanity non-destruktif (RR/CI e2,e3 M3 tetap 1.0/0.0):")
    for eid in (2, 3):
        res = report["M3_square_one_diagonal"]["scenarios"][(eid, 0.0)]
        good = abs(res.RR - 1.0) < 1e-12 and abs(res.CI) < 1e-12
        ok = ok and good
        print(f"    e{eid}: RR={res.RR:.12f} CI={res.CI:.12f} "
              f"-> {'PASS' if good else 'FAIL'}")

    print(f"\nTotal skenario terlabel GRAPH_BLIND: {n_blind}")
    print("GATE 3 SELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
