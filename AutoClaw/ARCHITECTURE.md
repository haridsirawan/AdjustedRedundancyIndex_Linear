# ARCHITECTURE — Implementasi Disertasi ARI
> **Catatan lokasi (2026-10-13):** seluruh suite verifikasi kini berada di folder `AutoClaw/`. Path yang disebut di dokumen ini (mis. `examples/…`, `results/…`) relatif terhadap folder `AutoClaw/`.

**Status snapshot:** 2026-10-11 (Gate 8). Daftar file AKTUAL yang ada di repo (bukan rencana), dengan commit terakhir per file dan status.

## Pipeline 3-lapisan
```
verification_models.json ──► truss_reference.py (L1 Solver FE)
                                   │ gaya awal, reaksi r^(0), U*, rank
                                   ▼
                              ari_core.py (L2 Mesin ARI, Eq 2.5–2.18)
                                   │ w_e^M, Φ^K_ij, S(G), RR, ARI, CI
                                   ▼
                            kinematic_guard.py (L3 Guard, rank/margin)
                                   │ guard_decision, margin_m
                                   ▼
 run_pipeline.py / fine_grid_runner.py ──► CSV audit ──► curve_extractor.py / plot_curves.py ──► JSON/PDF
```

## File implementasi (examples/)
| File | Gate | Fungsi | Commit terakhir | Status |
|---|---|---|---|---|
| verification_models.json | 1 | Definisi 4 model kanonik + skala §4.1.2 + expected Tabel 4.1 | 71b1160 | ✅ selesai |
| truss_reference.py | 1 | Solver FE batang aksial 1D/2D (K global, BC, eigvals rank-check 1e-10, tanpa pseudoinverse) | 71b1160 | ✅ selesai |
| test_truss_reference.py | 1 | Acceptance test Tabel 4.1 + uji mekanisme | 71b1160 | ✅ selesai |
| ari_core.py | 2 | Mesin ARI Eq 2.5–2.18 (exhaustive edge-disjoint paths, TANPA renormalisasi, abstain bila uncertified) | 9e4b402 | ✅ selesai |
| test_ari.py | 2 | Diagnostik: Tabel 4.11/4.3, monotonisitas, invariansi, intermediate values → ari_screening.csv | bf24b9c | ✅ selesai |
| kinematic_guard.py | 3 | Deteksi GRAPH_BLIND/MECHANISM; annotate hasil L2 | 9e4b402 | ✅ selesai |
| run_pipeline.py | 4/5 | Orkestrasi 3 lapisan; grid coarse {1,.75,.5,.25,0}; pipeline_output.csv (skema kanonik), ari_screening_full.csv, screening_report.json | c4791bb | ✅ selesai |
| curve_extractor.py | 5 | Interpolasi RR/CI λ; λ_crit(CI≥0.5) & λ_guard-flip → critical_lambdas.json | c4791bb | ✅ selesai |
| fine_grid_runner.py | 6 | Pipeline pada Δλ=0.05 (21 titik/edge) → fine_grid_output.csv (skema sama Gate 5) | df28ade | ✅ selesai |
| plot_curves.py | 6 | 4 PDF kurva RR/CI (Agg; marker x merah rank_deficient, * oranye guard-flip) | df28ade | ✅ selesai (flip-fix Gate 7) |

Catatan: gate 7 (agregasi laporan) dilaporkan selesai oleh peneliti (commit 93a824d) namun file agregatnya TIDAK terdapat pada branch sandbox ini — lihat ringkasan eksekusi Gate 8. Status gate 7 di workspace ini: 🟡 tidak tersedia untuk diverifikasi.

## Artefak hasil (results/)
| Path | Isi | Status |
|---|---|---|
| results/verification/pipeline_output.csv | 80 baris skema kanonik [model_id, edge_id, lambda, S_intact, S_disrupted, RR, ARI, CI, rank_status, margin_m, guard_decision, U_star] | ✅ |
| results/verification/fine_grid_output.csv | 336 baris grid halus Δλ=0.05, kolom identik | ✅ |
| results/verification/ari_screening.csv | diagnostik Gate 2 (test_ari.py) | ✅ |
| results/verification/ari_screening_full.csv + screening_report.json | audit Gate 4 (84 run) | ✅ |
| results/verification/critical_lambdas.json | ringkasan λ_kritis per edge (kunci: lambda_crit_d_CI, lambda_guard_flip) | ✅ |
| results/verification/plots/curve_M{1..4}_*.pdf | visualisasi kurva halus | ✅ |
| results/verification/README.md | penjelasan tiap file + timestamp | ✅ (Gate 8) |
| results/review_prep/disertasi_numbers_audit.md | audit angka naskah vs kode | ✅ (Gate 8) |
| results/review_prep/review_checklist.md | checklist review manual | ✅ (Gate 8) |

## Log dokumentasi (root)
| File | Isi | Status |
|---|---|---|
| WORK_LOG.md | Entri sesi Gate 1–8 | ✅ |
| DEFERRED_FINDINGS.md | Finding #001–#012 + Last Checked | ✅ |
| ARCHITECTURE.md | File ini | ✅ (Gate 8) |

## Konfigurasi terkunci (jangan diubah tanpa keputusan review)
α_k=α_R=0.5, q_e=1, K=2, γ=1, η=0.5, β=0.1; ε_w=ε_d=1e-9, ε_R=1e-6 kN, baseline_tol=1e-12, ε_removed=1e-8; skala per model §4.1.2 (M1 15/30, M2 20/40, M3/M4 20/80). Satuan: kN, mm, E=200 kN/mm².
