# README — results/verification
**Last updated:** 2026-10-11 (Gate 8). Semua artefak dihasilkan oleh kode di `examples/` pada commit yang tercatat di `ARCHITECTURE.md`. JANGAN mengedit file hasil secara manual — regenerasi lewat skrip.

| File | Dihasilkan oleh | Isi | Timestamp sumber |
|---|---|---|---|
| pipeline_output.csv | examples/run_pipeline.py (Gate 4/5) | Skema kanonik [model_id, edge_id, lambda, S_intact, S_disrupted, RR, ARI, CI, rank_status, margin_m, guard_decision, U_star]; grid coarse λ∈{1,.75,.5,.25,0}; 80 baris per-edge | 2026-10-11 |
| fine_grid_output.csv | examples/fine_grid_runner.py (Gate 6) | Kolom identik; grid halus Δλ=0.05 (21 titik/edge); 336 baris; abstain ditulis NaN (aktual: 0) | 2026-10-11 |
| ari_screening.csv | examples/test_ari.py (Gate 2) | Diagnostik + intermediate values (w_e^M, S, U*, RR/ARI/CI) | 2026-10-11 |
| ari_screening_full.csv | examples/run_pipeline.py (Gate 4) | Audit trail lengkap 84 run (64 disrupsi + 20 kontrol), kolom berjenjang per lapisan | 2026-10-11 |
| screening_report.json | examples/run_pipeline.py (Gate 4) | Agregat per model + daftar cek konsistensi lintas-lapisan | 2026-10-11 |
| critical_lambdas.json | examples/curve_extractor.py (Gate 5) | Kurva RR/CI terinterpolasi, lambda_crit_d_CI (ambang CI≥0.5, konvensi upper-bound zona kritis), lambda_guard_flip (transisi Clear→Forward), margins | 2026-10-11 |
| plots/curve_M1..M4*.pdf | examples/plot_curves.py (Gate 6) | Kurva halus RR(λ)/CI(λ) per model; 'x' merah = rank_deficient, '*' oranye = guard-flip | 2026-10-11 |

Regenerasi seluruh rantai: `python examples/run_pipeline.py && python examples/curve_extractor.py && python examples/fine_grid_runner.py && python examples/plot_curves.py`
Konfigurasi yang memproduksi angka di sini terkunci (lihat ARCHITECTURE.md §Konfigurasi).
