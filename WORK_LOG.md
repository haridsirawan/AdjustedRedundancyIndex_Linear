# WORK LOG — ARI Disertasi
**Researcher:** Harids Irawan
**Date:** Sunday, October 11, 2026
**Gate:** Gate 1 — Reference Solver Verification
**Status:** 🟢 PASSED

## Actions Taken
- [x] Created `examples/verification_models.json` with 4 canonical models (Bagian 4.1.2; satuan kN/mm, E = 200 kN/mm²).
- [x] Created `examples/truss_reference.py` (solver FE batang aksial 1D/2D sesuai Bagian 4.1.3 & 4.5.7).
- [x] Created `examples/test_truss_reference.py` (acceptance test vs Tabel 4.1 + uji penolakan mekanisme rank-deficient).
- [x] Ran verification script (`python examples/test_truss_reference.py`, exit code 0 — semua PASS).

## Verification Results
Toleransi penerimaan: |Δ| < 5e-4. Kolom "Actual" adalah output riil dari rerun verifikasi pada 2026-10-11.

| Model | Expected | Actual | Match? |
|-------|----------|--------|--------|
| Parallel bars | umax = 1.000000 mm, Umax = 0.500000 | umax = 1.000000, Umax = 0.500000 | ✅ |
| Triangle | umax = 1.154460 mm, Umax = 0.442218 | umax = 1.154460, Umax = 0.442218 | ✅ |
| 1-Diagonal | umax = 5.935311 mm, Umax = 0.530330 | umax = 5.935311, Umax = 0.530330 | ✅ |
| 2-Diagonal | umax = 3.582277 mm, Umax = 0.320083 | umax = 3.582277, Umax = 0.320083 | ✅ |
| Rank-deficient mechanism (uji penolakan) | status = `"rank_deficient"`, tanpa pseudoinverse | sesuai (rank = 1/4 terdeteksi) | ✅ |

Deviasi maksimum aktual: Δumax = 4.98e-07 mm (Triangle), ΔUmax = 4.79e-07 (2-Diagonal).

### Data pendukung tambahan (regangan energi W, kN·mm)
| Model      | W (solver) |
|------------|------------|
| Parallel   | 15.000000  |
| Triangle   | 16.956287  |
| 1-Diagonal | 86.139610  |
| 2-Diagonal | 51.989854  |

## Notes for Review
- Solver menggunakan `numpy.linalg.solve`.
- Rank check `K_ff` menggunakan `numpy.linalg.eigvals` dengan toleransi relatif 1e-10 terhadap eigenvalue terbesar; struktur rank-deficient dicatat status `"rank_deficient"` dan TIDAK diselesaikan dengan pseudoinverse. Uji penolakan mekanisme juga PASS (rank = 1/4 terdeteksi).
- Konvensi penting: `umax` = norm resultan perpindahan per node √(ux²+uy²) — satu-satunya definisi yang mereproduksi seluruh baris Tabel 4.1. Roller "vertical only" = restraint uy = 0. Model Triangle menyertakan tie chord (0,0)-(1000,0); tanpa chord struktur menjadi mekanisme.
- Cara menjalankan: `python examples/truss_reference.py` atau `python examples/test_truss_reference.py`.

## Status Gate
🟢 **GATE 1 PASSED** — Menunggu persetujuan untuk lanjut ke Gate 2 (ARI Core).
