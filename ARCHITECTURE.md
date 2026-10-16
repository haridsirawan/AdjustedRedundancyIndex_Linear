# ARCHITECTURE — Implementasi Disertasi ARI
> **Catatan lokasi (2026-10-13):** akar repo kode berada di folder `Coding/` (lokal), terpisah dari materi riset pribadi. Path yang disebut di dokumen ini (mis. `examples/…`, `results/…`) relatif terhadap akar repo itu.

**Status snapshot:** 2026-10-13 (Gate 9). Daftar file AKTUAL yang ada di repo (bukan rencana), dengan commit terakhir per file dan status.

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
        │
        └── mechanical_guard.py (Guard Eq 4.1–4.4, h_e SVD) ──► run_verification.py ──► kontrak Tabel 4.8
```

## File implementasi (examples/)
| File | Gate | Fungsi | Commit terakhir | Status |
|---|---|---|---|---|
| verification_models.json | 1 | Definisi 4 model kanonik + skala §4.1.2 + expected Tabel 4.1 | 71b1160 | ✅ selesai |
| truss_reference.py | 1 | Solver FE batang aksial 1D/2D (K global, BC, eigvals rank-check 1e-10, tanpa pseudoinverse) | 71b1160 | ✅ selesai |
| test_truss_reference.py | 1 | Acceptance test Tabel 4.1 + uji mekanisme | 71b1160 | ✅ selesai |
| ari_core.py | 2/9 | Mesin ARI Eq 2.5–2.18 (b_jc per KOMPONEN reaksi Eq 2.12; π_c ternormalisasi Eq 2.11; λ=0 hapus eksak; lintasan kosong i==j; status Tabel 4.7) | (Gate 9) | ✅ selesai |
| test_ari.py | 2 | Diagnostik: Tabel 4.11/4.3, monotonisitas, invariansi, intermediate values → ari_screening.csv | bf24b9c | ✅ selesai |
| kinematic_guard.py | 3 | Deteksi GRAPH_BLIND/MECHANISM; annotate hasil L2 | 9e4b402 | ✅ selesai |
| run_pipeline.py | 4/5 | Orkestrasi 3 lapisan; grid coarse {1,.75,.5,.25,0}; pipeline_output.csv (skema kanonik), ari_screening_full.csv, screening_report.json | c4791bb | ✅ selesai |
| curve_extractor.py | 5 | Interpolasi RR/CI λ; λ_crit(CI≥0.5) & λ_guard-flip → critical_lambdas.json | c4791bb | ✅ selesai |
| fine_grid_runner.py | 6 | Pipeline pada Δλ=0.05 (21 titik/edge) → fine_grid_output.csv (skema sama Gate 5) | df28ade | ✅ selesai |
| plot_curves.py | 6 | 4 PDF kurva RR/CI (Agg; marker x merah rank_deficient, * oranye guard-flip) | df28ade | ✅ selesai (flip-fix Gate 7) |
| mechanical_guard.py | 9 | h_e = k_e·a_e·K₀⁻¹·a_eᵀ via SVD (Eq 4.1); m_e(λ); batas kondisi Eq 4.4; identitas Eq 4.7 | (Gate 9) | ✅ selesai |
| run_verification.py | 9 | Runner verifikasi kanonik → baseline/scenarios/checks.csv, manifest.json, Tabel.tex, models.pdf, ci_by_damage.pdf (Tabel 4.8) | (Gate 9) | ✅ selesai |
| run_guard_verification.py | 9/9.2 | Paket verifikasi pengaman §4.2/§4.5.11 + diagnostik parametrik §4.2.4 (272 skenario; dua konvensi kritikalitas; decisions.csv + remaining_misses.csv) → guard_verification.json | (Gate 9.2) | ✅ selesai |
| ari_tutorial.py | 9 | Tutorial rantai ARI contoh dua batang (urutan reproduksi Kode 4.2) | (Gate 9) | ✅ selesai |

**Gate 9 (2026-10-13) — penyelarasan penuh dengan naskah:** b_jc per komponen reaksi (Eq 2.12) menutup DF-01 (Tabel 4.3 ≤ 4e-7); h_e SVD (Eq 4.1) menggantikan fraksi-energi di bound_enhancement (Tabel 4.4); λ=0 dihapus eksak; π_c ternormalisasi; status Tabel 4.7. Bukti: run_verification.py 65/65 LULUS + `results/review_prep/penyelarasan_disertasi_gate9.md`.

Catatan: gate 7 (agregasi laporan) dilaporkan selesai oleh peneliti (commit 93a824d) namun file agregatnya TIDAK terdapat pada branch sandbox ini — lihat ringkasan eksekusi Gate 8. Status gate 7 di workspace ini: 🟡 tidak tersedia untuk diverifikasi.

## Artefak hasil (results/)
| Path | Isi | Status |
|---|---|---|
| results/verification/pipeline_output.csv | 80 baris skema kanonik [model_id, edge_id, lambda, S_intact, S_disrupted, RR, ARI, CI, rank_status, margin_m, guard_decision, U_star, status_code] | ✅ |
| results/verification/fine_grid_output.csv | 336 baris grid halus Δλ=0.05, kolom identik | ✅ |
| results/verification/ari_screening.csv | diagnostik Gate 2 (test_ari.py) | ✅ |
| results/verification/ari_screening_full.csv + screening_report.json | audit Gate 4 (84 run) | ✅ |
| results/verification/critical_lambdas.json | ringkasan λ_kritis per edge (kunci: lambda_crit_d_CI, lambda_guard_flip) | ✅ |
| results/verification/plots/curve_M{1..4}_*.pdf | visualisasi kurva halus | ✅ |
| results/verification/README.md | penjelasan tiap file + timestamp | ✅ (Gate 8) |
| results/verification/baseline.csv, scenarios.csv, checks.csv, manifest.json, Tabel.tex, models.pdf, ci_by_damage.pdf | keluaran kontrak Tabel 4.8 (Gate 9) | ✅ |
| results/verification/guard_verification.json | verifikasi paket pengaman §4.2 + diagnostik parametrik §4.2.4 (Gate 9/9.2) | ✅ |
| results/revision/{models.json, decisions.csv, remaining_misses.csv, forwarded.csv} | paket parametrik 16 model (272 skenario); keputusan (+sha256), kasus terlewat & daftar diteruskan; bandingan draf A/B di guard_verification.json | ✅ (Gate 9.2/9.3) |
| results/review_prep/disertasi_numbers_audit.md | audit angka naskah vs kode | ✅ (Gate 8; dikoreksi Gate 9) |
| results/review_prep/review_checklist.md | checklist review manual | ✅ (Gate 8) |

## Log dokumentasi (root)
| File | Isi | Status |
|---|---|---|
| manifest_config_frozen.json | Paket protokol beku pra-validasi buta (Gate 14 — W5) | ✅ |
| results/dataset/{manifest.json, manifest.csv, models_s1..s5.json, dataset_stats.json} | Dataset induk 300 model S1–S5 (Gate 13 — W2e/W2f) | ✅ |
| results/screening/manifest_config_frozen.json | Salinan arsip protokol beku pada direktori penyaringan (Gate 14 — W5) | ✅ |
| examples/{structural_solvers.py, test_structural_solvers.py, generate_dataset_s1_s5.py, freeze_protocol_config.py} | Solver multi-keluarga S1–S5, generator 300 model, & pembekuan protokol (Gate 12–14) | ✅ |
| WORK_LOG.md | Entri sesi Gate 1–14 | ✅ |
| DEFERRED_FINDINGS.md | Finding #001–#012 + Last Checked | ✅ |
| ARCHITECTURE.md | File ini | ✅ (Gate 8) |

## Konfigurasi terkunci (jangan diubah tanpa keputusan review)
α_k=α_R=0.5, q_e=1, K=2, γ=1, η=0.5, β=0.1; ε_w=ε_d=1e-9, ε_R=1e-6 kN, baseline_tol=1e-12, max_search_nodes=200.000 (4.1.2); ε_removed=1e-8 (DEPRECATED — λ=0 kini dihapus eksak, Gate 9); skala per model §4.1.2 (M1 15/30, M2 20/40, M3/M4 20/80). Satuan: kN, mm, E=200 kN/mm².
