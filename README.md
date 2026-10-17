# Adjusted Redundancy Index (ARI) — Implementasi Komputasi & Verifikasi Disertasi

Repositori resmi implementasi algoritma, solver referensi elemen hingga, pengaman kinematik berbasis dekomposisi nilai singular (*Singular Value Decomposition* / SVD)

> **Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network**

---

## 1. Arsitektur Pipeline Komputasi

```text
examples/verification_models.json
        │
        ▼
examples/truss_reference.py       (Lapis 1 — Solver FE Batang Aksial 1D/2D: gaya awal, reaksi r^(0), U*, rank)
        │
        ▼
examples/ari_core.py              (Lapis 2 — Mesin Inti ARI: w_e^M, Φ^K_ij, S(G), RR, ARI, CI; Pers. 2.5–2.18)
        │
        ├──► examples/mechanical_guard.py   (Lapis 3a — Pengaman Kinematik SVD h_e, m_e(λ), batas κ; Pers. 4.1–4.7)
        ├──► examples/bound_enhancement.py  (Lapis 3b — Batas Praanalisis Redistribusi Gaya & Perpindahan; §4.4)
        └──► examples/layered_policy.py     (Lapis 3c — Kebijakan Penapisan Berlapis F⁺; Pers. 4.13)
                │
                ▼
        ├──► examples/run_verification.py         ──► results/verification/ (68/68 cek kanonik, Tabel.tex, PDF)
        ├──► examples/run_guard_verification.py   ──► results/revision/     (33/33 cek pengaman & 272 skenario)
        └──► examples/run_pipeline.py             ──► results/verification/ (CSV audit 13 kolom & kurva Δλ=0,05)
```

---

## 2. Instalasi & Cara Menjalankan Verifikasi

### Prasyarat Lingkungan
* Python $\ge 3.9$
* Pustaka ilmiah dasar (`numpy`, `matplotlib`)

```bash
pip install -r requirements.txt
```

### A. Verifikasi Terpadu Satu Pintu (*Recommended*)
Jalankan skrip utama di akar repositori untuk mengeksekusi seluruh 11 tahapan verifikasi secara otomatis:

```bash
python3 run_all_verifications.py
```

### B. Eksekusi Per Modul di Direktori `examples/`

```bash
cd examples

# 1. Verifikasi Kanonik & Pengaman Kinematik (Bukti Utama Bab IV)
python3 ari_tutorial.py              # Tutorial analitis dua batang paralel (Tabel 25 / Tabel 4.11)
python3 test_truss_reference.py      # Uji penerimaan solver FE terhadap 4 model kanonik (Tabel 13 / Tabel 4.1)
python3 test_ari.py                  # Uji mesin ARI, monotonisitas, & invariansi satuan (Tabel 15 / Tabel 4.3)
python3 mechanical_guard.py          # Verifikasi pengaman SVD h_e & identitas aljabar (Tabel 16 / Tabel 4.4)
python3 test_bound_enhancement.py    # Uji konservatisme batas redistribusi & pembesaran perpindahan
python3 test_leakage_audit.py        # Audit anti-kebocoran informasi pascagangguan (4 pemeriksaan)
python3 run_verification.py          # Suite verifikasi kanonik penuh (68/68 pemeriksaan otomatis)
python3 run_guard_verification.py    # Verifikasi pengaman & diagnostik 16 model parametrik (272 skenario)

# 2. Ekstraksi Kurva & Diagnostik Rekonsiliasi
python3 run_pipeline.py              # Orkestrasi 3 lapisan pada grid kasar λ ∈ {1, 0.75, 0.5, 0.25, 0}
python3 fine_grid_runner.py          # Evaluasi grid halus Δλ = 0.05 (336 baris)
python3 curve_extractor.py           # Ekstraksi titik kritis λ_crit & λ_guard_flip
python3 plot_curves.py               # Pembangkitan 4 grafik PDF kurva RR(λ) dan CI(λ)
python3 reconcile_ari_forward.py     # Rekonsiliasi variasi konvensi penerusan 272 skenario parametrik
python3 analyze_remaining_misses.py  # Karakterisasi 28 kasus kritis terlewat & evaluasi kandidat aturan

# 3. Validasi Skala Penuh Multi-Keluarga (S1–S5) & Integrasi Berpasangan GNN (S6)
python3 test_structural_solvers.py   # Uji analitis solver 5 keluarga struktur S1–S5
python3 generate_dataset_s1_s5.py    # Pembangkitan model induk S1–S5 beserta manifest SHA-256
python3 freeze_protocol_config.py    # Pembekuan konfigurasi protokol (ARI-FROZEN-PROTOCOL-v1.0)
python3 run_screening_s1_s5.py       # Simulasi penyaringan ARI v1 baseline lintas keluarga S1–S5
python3 run_screening_v2.py          # Validasi penuh formulasi terpadu ARI v2 (Lulus Gerbang C & D, Zero-Miss)
python3 run_gnn_integration_s6.py    # Evaluasi integrasi ARI v2–GNN (StructGNN-CRC v1.0, T7 & T8) & audit biaya Tabel 4.19
```

---

## 3. Struktur Direktori Repositori

```text
.
├── CITATION.cff                     # Metadata sitasi akademik resmi repositori (GitHub Citation)
├── LICENSE                          # Lisensi perangkat lunak Apache 2.0
├── README.md                        # Dokumentasi utama repositori
├── ARCHITECTURE.md                  # Spesifikasi arsitektur berlapis, kontrak numerik, & peta modul
├── WORK_LOG.md                      # Catatan riwayat verifikasi berjenjang (Gate 1–17)
├── DEFERRED_FINDINGS.md             # Dokumentasi penutupan temuan numerik & rekonsiliasi formula
├── requirements.txt                 # Daftar dependensi pustaka Python
├── manifest_config_frozen.json      # Segel konfigurasi protokol beku (ARI-FROZEN-PROTOCOL-v1.0)
├── run_all_verifications.py         # Skrip eksekusi verifikasi otomatis satu pintu (11 tahap)
├── examples/                        # 29 berkas ilmiah (27 modul Python & 2 spesifikasi model JSON)
└── results/                         # Artefak keluaran verifikasi, diagnostik, dan protokol
    ├── verification/                # Keluaran verifikasi kanonik (68/68 lulus, CSV, JSON, LaTeX, PDF)
    ├── revision/                    # Paket diagnostik 16 model parametrik (272 skenario)
    ├── bounds/                      # Log audit anti-kebocoran & laporan ablasi batas praanalisis
    ├── dataset/                     # Spesifikasi & manifest model multi-keluarga S1–S5
    ├── screening/                   # Artefak keputusan penapisan & kurva kalibrasi ambang
    ├── validation/                  # Laporan evaluasi metrik gerbang validasi & ablasi
    ├── integration/                 # Artefak studi protokol integrasi GNN & tabel rincian biaya
    └── review_prep/                 # Dokumentasi penyelarasan angka naskah, audit, & daftar periksa
```

---

## 4. Lisensi & Sitasi

Kode sumber dalam repositori ini dilisensikan di bawah **Apache License 2.0** (lihat berkas [`LICENSE`](LICENSE)).  
Untuk menyitasi karya ini dalam publikasi ilmiah, gunakan tombol **"Cite this repository"** pada halaman GitHub atau merujuk pada metadata di [`CITATION.cff`](CITATION.cff).
