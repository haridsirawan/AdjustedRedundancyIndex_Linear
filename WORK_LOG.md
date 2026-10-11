# WORK LOG - ARI Disertasi Implementation
**Date:** Sunday, October 11, 2026
**Current Gate:** Gate 1 - Reference Solver Verification
**Status:** 🟢 PASSED

## Actions Taken
- [x] Created `examples/verification_models.json` with 4 canonical models.
- [x] Created `examples/truss_reference.py` (FEM axial bar solver).
- [x] Ran verification script (`examples/test_truss_reference.py`, exit code 0 — semua PASS).

## Verification Results (vs Table 4.1)
Toleransi penerimaan: |Δ| < 5e-4. Nilai aktual di bawah adalah output riil dari rerun verifikasi pada 2026-10-11.

| Model       | Expected umax | Actual umax | Expected Umax | Actual Umax | Status |
|-------------|---------------|-------------|---------------|-------------|--------|
| Parallel    | 1.000000      | 1.000000    | 0.500000      | 0.500000    | ✅      |
| Triangle    | 1.154460      | 1.154460    | 0.442218      | 0.442218    | ✅      |
| 1-Diagonal  | 5.935311      | 5.935311    | 0.530330      | 0.530330    | ✅      |
| 2-Diagonal  | 3.582277      | 3.582277    | 0.320083      | 0.320083    | ✅      |

Deviasi maksimum aktual: Δumax = 4.98e-07 mm (Triangle), ΔUmax = 4.79e-07 (2-Diagonal).

### Data pendukung tambahan (regangan energi W, kN·mm)
| Model      | W (solver) |
|------------|------------|
| Parallel   | 15.000000  |
| Triangle   | 16.956287  |
| 1-Diagonal | 86.139610  |
| 2-Diagonal | 51.989854  |

## Notes for Reviewer (GenOffice)
- Solver menggunakan `numpy.linalg.solve`.
- Rank check menggunakan eigenvalue tolerance 1e-10 (relatif terhadap eigenvalue terbesar); struktur rank-deficient dicatat status `"rank_deficient"` dan TIDAK diselesaikan dengan pseudoinverse. Uji penolakan mekanisme juga PASS (rank = 1/4 terdeteksi).
- Konvensi penting: `umax` = norm resultan perpindahan per node √(ux²+uy²) — satu-satunya definisi yang mereproduksi seluruh baris Tabel 4.1. Roller "vertical only" = restraint uy = 0. Model Triangle menyertakan tie chord (0,0)-(1000,0); tanpa chord struktur menjadi mekanisme.
- Cara menjalankan: `python examples/truss_reference.py` atau `python examples/test_truss_reference.py`.

## Status Gate
🟢 **GATE 1 PASSED** — Menunggu persetujuan untuk lanjut ke Gate 2 (ARI Core).
