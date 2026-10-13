# README — results/verification
**Last updated:** 2026-10-13 (Gate 9). Semua artefak dihasilkan oleh kode di `examples/`; JANGAN mengedit file hasil secara manual — regenerasi lewat skrip. Hash sumber & konfigurasi tercatat di `manifest.json`.

## Keluaran kontrak Tabel 4.8 (Gate 9 — `run_verification.py`)
| File | Isi |
|---|---|
| baseline.csv | Respons & skor 4 model utuh vs Tabel 4.1 (umax, Umax, W, Rank/DOF, status) |
| scenarios.csv | Kontrol utuh + 16 kontrol edge (λ=1) + 64 gangguan (λ∈{0,.25,.5,.75}); status skor & status SOLVER dipisah kolom |
| checks.csv | Pemeriksaan otomatis vs Tabel 4.1/4.2/4.3/4.4/4.5/4.11 + Eq 2.19 + monotonisitas (**65/65 LULUS**) |
| manifest.json | Konfigurasi, versi pustaka, waktu, hash sumber |
| Tabel.tex | Tabel LaTeX reproduksi Tabel 4.1 & 4.3 (siap dimasukkan ke naskah) |
| models.pdf | Diagram 4 model kanonik |
| ci_by_damage.pdf | Kurva CI(λ) 4 model + penanda rank acuan (padanan Gambar 4.3) |
| guard_verification.json | Verifikasi paket pengaman §4.2 (analitis/regresi/diagnostik; parametrik pending) |

## Artefak pipeline (Gate 4–6, diregenerasi Gate 9)
| File | Dihasilkan oleh | Isi |
|---|---|---|
| pipeline_output.csv | run_pipeline.py | Skema kanonik 12 kolom; grid coarse λ∈{1,.75,.5,.25,0}; per-edge |
| fine_grid_output.csv | fine_grid_runner.py | Kolom identik; Δλ=0.05 (21 titik/edge); 336 baris |
| ari_screening.csv | test_ari.py | Diagnostik + intermediate values (w_e, S, U*, RR/ARI/CI) |
| ari_screening_full.csv | run_pipeline.py | Audit trail 84 run (64 disrupsi + 20 kontrol, kolom berjenjang) |
| screening_report.json | run_pipeline.py | Agregat per model + cek konsistensi lintas-lapisan |
| critical_lambdas.json | curve_extractor.py | λ_kritis (CI≥0.5) & λ_guard-flip per edge |
| plots/curve_M1..M4*.pdf | plot_curves.py | Kurva halus RR(λ)/CI(λ); 'x' = rank_deficient, '*' = guard-flip |

## Regenerasi seluruh rantai
```bash
cd examples
python3 ari_tutorial.py && python3 run_verification.py && python3 run_guard_verification.py
python3 run_pipeline.py && python3 fine_grid_runner.py && python3 curve_extractor.py && python3 plot_curves.py
```
Konfigurasi terkunci (lihat ARCHITECTURE.md §Konfigurasi); λ=0 = penghapusan sisi eksak (ε_removed deprecated).
