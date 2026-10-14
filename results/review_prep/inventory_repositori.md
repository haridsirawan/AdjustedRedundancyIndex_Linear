# Inventaris Repositori — Adjusted Redundancy Index (ARI)
**Dibuat:** 13 Oktober 2026 · oleh AutoClaw · untuk pemeriksaan manual oleh peneliti (Harids Irawan).
**Koneksi GenOffice:** ✅ terhubung (GenOffice v0.11.505; menulis/membaca docx, xlsx, pptx).
Salinan Word: `Inventaris Repositori ARI.docx` (folder riset) — versi Markdown ini ada di repo.

## 1. Ringkasan repositori
| Item | Nilai |
|---|---|
| Repo GitHub | https://github.com/haridsirawan/Adjusted-Redundancy-Index (privat) |
| Folder lokal | `…/Research/Adjusted Redudancy Index/Coding/` |
| Branch / HEAD | `main` @ `416093e` |
| `e79bd17` | **Gate 10**: audit naskah revisi (193 hal) — seluruh klaim paket Gate 9 terverifikasi persis |
| `02a43f2` | **Gate 11 (K6)**: rekonsiliasi draf 17/32/41 vs kode 30/32/52 — selisih terlokalisasi |
| `6f2b95e` | **Gate 11 (W1)**: diagnosa 28 kasus kritis terlewat + evaluasi kandidat kebijakan (P1..P7) |
| `eeabcb4` | **Gate 12 (W2a–W2d)**: solver multi-keluarga S1, S3, S4, S5 + uji analitis 100% PASS |
| File terlacak | **66 file** (≈11 MB; `examples/` = 5.418 baris Python + JSON) |
| Status | Semua runner HIJAU — kanonik 68/68, guard 33/33, pipeline PASS, grid halus PASS, plot PASS |

## 2. Riwayat commit (pekerjaan sesi ini)
| Commit | Isi singkat |
|---|---|
| `6399cef` | Impor materi riset; tambah README + .gitignore; setop melacak .DS_Store |
| `79ba0e3` | Merge cabang verifikasi (ARI Gate 1–8 milik kerja sebelumnya) |
| `90e6462` | Berhenti melacak `__pycache__` |
| `cb0fe40` | Reorganisasi: pindahkan suite verifikasi ke folder `AutoClaw/` |
| `87241ce` | Pisahkan repo kode ke folder `Coding/` (repo = kode saja, materi riset keluar) |
| `7753f63` | **Gate 9**: selaraskan kode dengan naskah — Tabel 4.3 tereproduksi ≤ 4e-7; h_e SVD; mekanisme lain |
| `f5b7bbe` | **Gate 9.1**: `ari_tutorial.py` (Kode 4.2) + `run_guard_verification.py` (§4.5.11) |
| `ab2628d` | **Gate 9.2**: paket parametrik §4.2.4 — 16 model, 272 skenario, decisions/remaining_misses |
| `416093e` | **Gate 9.3**: `status_code` di semua CSV; Tabel.tex diperluas; `forwarded.csv`; panduan revisi |
| `e79bd17` | **Gate 10**: audit naskah revisi (193 hal) — seluruh klaim paket Gate 9 terverifikasi persis |
| `02a43f2` | **Gate 11 (K6)**: rekonsiliasi draf 17/32/41 vs kode 30/32/52 — selisih terlokalisasi |
| `6f2b95e` | **Gate 11 (W1)**: diagnosa 28 kasus kritis terlewat + evaluasi kandidat kebijakan (P1..P7) |
| `eeabcb4` | **Gate 12 (W2a–W2d)**: solver multi-keluarga S1, S3, S4, S5 + uji analitis 100% PASS |

## 3. Daftar lengkap isi repositori (66 file)

### 3.1 `examples/` — kode & model (19 file)
| File | Fungsi |
|---|---|
| `verification_models.json` | 4 model kanonik §4.1.2 (geometri, beban, kapasitas, skala) |
| `structural_solvers.py` | Solver FE struktur multi-keluarga: S1 Balok, S3 Portal, S4 Berpengaku, S5 Rangka Ruang 3D |
| `test_structural_solvers.py` | Suite uji analitis dan acceptance test untuk S1, S3, S4, S5 (100% PASS) |
| `verification_solvers_s1_s5.json` | Model acuan kanonik untuk solver multi-keluarga S1, S3, S4, S5 |
| `truss_reference.py` | Solver FE batang aksial (rank-check eig 1e-10, tanpa pseudoinverse) |
| `ari_core.py` | Mesin ARI Eq 2.5–2.18 (b_jc per komponen reaksi; λ=0 hapus eksak; status Tabel 4.7) |
| `ari_tutorial.py` | Tutorial rantai ARI contoh dua batang (urutan reproduksi Kode 4.2) |
| `mechanical_guard.py` | Pengaman kinematik Eq 4.1–4.4 (h_e = k_e·a_e·K₀⁻¹·a_eᵀ via SVD; m_e(λ); batas κ) |
| `kinematic_guard.py` | Guard observasional lama (rank/solvabilitas; dipertahankan sebagai audit) |
| `bound_enhancement.py` | Bound praanalisis §4.4 (h_e SVD — dikoreksi Gate 9) |
| `layered_policy.py` | Kebijakan berlapis F⁺ (Eq 4.13; urutan: guard → bound → ARI) |
| `run_pipeline.py` | Pipeline 3 lapisan → CSV kanonik 13 kolom + laporan konsistensi |
| `fine_grid_runner.py` | Grid halus Δλ=0.05 (21 titik × 16 edge = 336 baris) |
| `curve_extractor.py` | Ekstraksi λ_kritis & λ_guard-flip → `critical_lambdas.json` |
| `plot_curves.py` | 4 PDF kurva RR(λ)/CI(λ) |
| `test_ari.py` | Diagnostik inti: Tabel 4.3/4.11, monotonisitas, konversi satuan |
| `test_bound_enhancement.py` | Regresi bound (Tabel 4.4 + konservatisme) |
| `test_leakage_audit.py` | Audit kebocoran §4.5.6 (4 pemeriksaan) |
| `test_truss_reference.py` | Acceptance solver vs Tabel 4.1 |
| `run_verification.py` | Runner verifikasi kanonik (kontrak Tabel 4.8) — 68/68 pemeriksaan |
| `run_guard_verification.py` | Paket pengaman §4.2 + diagnostik parametrik §4.2.4 |
| `run_ablation_bounds.py` | Ablasi bound praanalisis (peninggalan sesi sebelumnya) |

### 3.2 `results/verification/` — keluaran kontrak naskah (20 item)
| File | Isi |
|---|---|
| `README.md` | Penjelasan tiap file |
| `Tabel.tex` | **Reproduksi Tabel 4.1, 4.2, 4.3, 4.4, 4.5-kanonik (LaTeX, siap tempel)** |
| `baseline.csv` | Respons 4 model utuh vs Tabel 4.1 (umax, Umax, W) |
| `scenarios.csv` | 4 kontrol utuh + 16 kontrol edge + 64 gangguan; status skor & solver terpisah |
| `checks.csv` | **68/68 pemeriksaan LULUS** (semua tabel + Eq 2.19 + monotonisitas) |
| `manifest.json` | Konfigurasi, versi pustaka, waktu, hash sumber |
| `guard_verification.json` | §A analitis, §B regresi, §C diagnostik kanonik, **§D parametrik + bandingan draf** |
| `models.pdf` / `ci_by_damage.pdf` | Diagram 4 model / kurva CI + penanda rank |
| `pipeline_output.csv` | 80 baris, skema kanonik **13 kolom** (termasuk `status_code`) |
| `fine_grid_output.csv` | 336 baris grid halus, kolom identik |
| `ari_screening.csv` / `ari_screening_full.csv` | Diagnostik test_ari / audit 84 run |
| `screening_report.json` | Agregat pipeline + konsistensi antar-lapisan |
| `critical_lambdas.json` | λ_kritis (CI≥0.5) & λ_guard-flip per edge |
| `plots/curve_M1…M4*.pdf` | 4 kurva halus RR/CI |

### 3.3 `results/revision/` — paket parametrik §4.2.4 (5 file)
| File | Isi |
|---|---|
| `models.json` | 16 model parametrik (4 grup × 4 konfigurasi) + target draf |
| `decisions.csv` | Keputusan penerusan 272 skenario (disimpan sebelum respons acuan; sha256 dicatat) |
| `remaining_misses.csv` | 28 kasus kritis tak diteruskan (varian B) |
| `forwarded.csv` | 52 skenario diteruskan (kolom `by`: ari/guard/both; kritikalitas A/B) |
| `README.md` | Hasil & catatan rekonsiliasi draf vs kode |

### 3.4 `results/review_prep/` — bahan review (5 file)
| File | Isi |
|---|---|
| `penyelarasan_disertasi_gate9.md` | **Laporan lengkap pemetaan naskah → kode → bukti** |
| `revision_guide.md` | **Panduan revisi akhir naskah** (apa yang harus diubah, apa yang tidak) |
| `disertasi_numbers_audit.md` | Audit angka naskah vs kode (dengan koreksi Gate 9) |
| `review_checklist.md` | Checklist review manual (status terbaru) |
| `inventory_repositori.md` | Dokumen ini |

### 3.5 `results/bounds/` (2) · Root (8) · `debug_archive/` (8)
- `results/bounds/`: `ablation_report.csv`, `leakage_audit.log` — audit bound praanalisis.
- Root: `README.md` (peta repo), `ARCHITECTURE.md` (file aktual + status), `WORK_LOG.md` (Gate 1–9.3), `DEFERRED_FINDINGS.md` (DF-01/03 ditutup; #012 dikoreksi), `LICENSE` (Apache-2.0), `.gitignore`, `requirements.txt` (numpy, matplotlib), `unified_debug_gate2.py` + `debug_results.csv` (diagnostik Gate 2).
- `debug_archive/`: 8 skrip debug Gate 2 (arsip).

## 4. Dibuat vs disunting pada sesi ini
**Dibuat baru:** `mechanical_guard.py`, `run_verification.py`, `run_guard_verification.py`, `ari_tutorial.py`, `requirements.txt`, seluruh `results/revision/*`, `results/review_prep/{penyelarasan_disertasi_gate9, revision_guide, inventory_repositori}.md`, dan keluaran `results/verification/{Tabel.tex, baseline.csv, scenarios.csv, checks.csv, manifest.json, models.pdf, ci_by_damage.pdf, guard_verification.json}`.
**Disunting:** `ari_core.py` (inti perbaikan), `test_ari.py`, `run_pipeline.py`, `fine_grid_runner.py`, `bound_enhancement.py`, `test_bound_enhancement.py`, `README.md`, `ARCHITECTURE.md`, `WORK_LOG.md`, `DEFERRED_FINDINGS.md`, audit & checklist.
**Tidak diubah:** `truss_reference.py`, `kinematic_guard.py`, `layered_policy.py`, `run_ablation_bounds.py`, `verification_models.json`, `debug_archive/*`.

## 5. Cara cek manual (±5 menit)
```bash
cd "…/Adjusted Redudancy Index/Coding"
git pull && pip install -r requirements.txt
cd examples
python3 test_truss_reference.py    # harap: SEMUA UJI LOLOS (Tabel 4.1)
python3 test_ari.py                # harap: semua cek keras LULUS (Tabel 4.3 <= 4e-7)
python3 mechanical_guard.py        # harap: ALL PASS (Tabel 4.4, Eq 4.4/4.7)
python3 run_verification.py        # harap: 68/68 LULUS
python3 run_guard_verification.py  # harap: PASS (33/33; bagian D = parametrik)
```
Lalu bandingkan: `results/verification/checks.csv` (68 baris), `guard_verification.json` §D, dan angka-angka di `Tabel.tex`.

## 6. Menunggu keputusan peneliti (revisi akhir)
1. **Tabel 4.5 paruh parametrik** — pilih konvensi kritikalitas final (A: kapasitas state saat itu — konsisten tabel kanonik; B: kapasitas asli — kritis 71/39 cocok draf) dan salin angka sisi-ARI hasil regenerasi (draf 17 vs kode 30; tidak dapat direkonsiliasi dengan mesin tervalidasi).
2. **Istilah naskah** — §2.6 invariansi → invariansi konversi satuan; hapus ε_removed; penomoran edge 1-based; kosakata status Tabel 4.7. (Rinci: `revision_guide.md`.)
