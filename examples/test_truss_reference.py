"""
test_truss_reference.py
=======================

Skrip uji coba (acceptance test) untuk Solver Referensi Tabel 4.1.

Menjalankan `truss_reference.solve_model` pada keempat model kanonik
(examples/verification_models.json), lalu membandingkan umax dan Umax
dengan nilai "expected_results" (Tabel 4.1 disertasi, toleransi 5e-4).

Tambahan: uji perilaku rank-deficient (mekanisme) untuk memastikan solver
TIDAK memakai pseudoinverse dan mencatat status "rank_deficient".

Jalankan:
    python examples/test_truss_reference.py
Exit code 0 = semua lolos.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from truss_reference import load_models, solve_model  # noqa: E402

TOL = 5e-4


def test_table_4_1() -> bool:
    models = load_models(HERE / "verification_models.json")
    ok_all = True
    print("=" * 78)
    print("UJI 1 — Respon Model Intak vs Tabel 4.1")
    print("=" * 78)
    for m in models:
        res = solve_model(m)
        exp = m.get("expected_results", {})
        du = abs(res.umax - float(exp["umax_mm"]))
        dU = abs(res.Umax - float(exp["Umax"]))
        ok = res.status == "ok" and du < TOL and dU < TOL
        ok_all &= ok
        print(f"{m['id']:<28} status={res.status:<15} "
              f"umax={res.umax:.6f} (target {exp['umax_mm']:.6f}, Δ={du:.2e})  "
              f"Umax={res.Umax:.6f} (target {exp['Umax']:.6f}, Δ={dU:.2e})  "
              f"W={res.strain_energy:.6f} kN.mm  -> {'PASS' if ok else 'FAIL'}")
    return ok_all


def test_rank_deficient_no_pinv() -> bool:
    """Mekanisme: node bebas tanpa elemen -> Kff singular.

    Solver WAJIB menolak (status 'rank_deficient'), bukan memakai pseudoinverse.
    """
    broken = {
        "id": "X_mechanism",
        "dimension": 2,
        "nodes": [
            {"id": 0, "coords": [0.0, 0.0]},
            {"id": 1, "coords": [1000.0, 0.0]},
            {"id": 2, "coords": [500.0, 0.0]},  # node melayang, tak terhubung
        ],
        "elements": [{"id": 0, "nodes": [0, 1], "area": 100.0}],
        "material": {"E": 200.0},
        "capacities": {"0": 40.0},
        "boundary_conditions": {"node_0": {"ux": 0.0, "uy": 0.0}},
        "loads": [{"node": 1, "components": {"ux": 30.0}}],
    }
    res = solve_model(broken)
    ok = res.status == "rank_deficient" and res.rank < res.n_free
    print("-" * 78)
    print("UJI 2 — Rank-deficient (mekanisme): "
          f"status={res.status}, rank={res.rank}/{res.n_free} "
          f"(tanpa pseudoinverse) -> {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    results = [test_table_4_1(), test_rank_deficient_no_pinv()]
    print("=" * 78)
    if all(results):
        print("KESIMPULAN: SEMUA UJI LOLOS — output cocok dengan Tabel 4.1.")
        return 0
    print("KESIMPULAN: ADA UJI YANG GAGAL.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
