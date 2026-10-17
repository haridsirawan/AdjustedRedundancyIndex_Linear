# Adjusted Redundancy Index (ARI) — Implementasi Komputasi & Verifikasi Disertasi

Repositori resmi implementasi algoritma, solver referensi elemen hingga, pengaman kinematik berbasis dekomposisi nilai singular (*Singular Value Decomposition* / SVD), serta protokol evaluasi untuk penelitian disertasi doktor:

> **Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network**  
> **Peneliti:** Harids Irawan, S.T., M.T. (NIM 23051690001)  
> **Program Studi:** Doktor Ilmu Teknik (Konsentrasi Teknik Sipil), Sekolah Pascasarjana Universitas Negeri Yogyakarta (2026)

---

## 1. Ruang Lingkup Ilmiah & Kedudukan Bukti

Sejalan dengan batas keabsahan metodologis dan epistemik pada naskah disertasi (Bab I Subbab E, Bab III, Bab IV Subbab I–J, dan Bab V), artefak di dalam repositori ini dikelompokkan secara tegas ke dalam dua kedudukan bukti:

1. **Bukti Terverifikasi Deterministik (*Verified Core Findings*):**
   * **Empat Model Kanonik Batang Aksial 1D/2D (`M1`–`M4`):** Verifikasi numerik eksak lintas 64 skenario gangguan dan 20 kontrol terhadap seluruh persamaan inti ARI (Persamaan 2.5–2.18), menghasilkan kelulusan **68/68 pemeriksaan otomatis** (`results/verification/checks.csv`).
   * **Enam Belas Model Parametrik Pengembangan (272 Skenario):** Evaluasi diagnostik pengembangan pengaman kinematik $h_e = k_e \mathbf{a}_e \mathbf{K}_0^{-1} \mathbf{a}_e^\top$ berbasis SVD (Persamaan 4.1–4.7) yang membuktikan penangkapan **100% kasus kehilangan rank (mekanisme kinematik)** pada graf yang tetap terhubung secara topologis (`results/revision/` & `results/verification/guard_verification.json`). Varian parametrik ini merupakan variasi batas terarah untuk pengujian diagnostik, bukan sampel acak populasi struktur independen.
2. **Protokol Pengembangan & Evaluasi Lanjutan (*Extended Protocols & Feasibility Studies*):**
   * **Suite Solver Multi-Keluarga (`S1`–`S5`) & Protokol Pembekuan (`ARI-FROZEN-PROTOCOL-v1.0`):** Implementasi solver elemen hingga untuk lima keluarga struktur (`S1` Balok Euler-Bernoulli, `S2` Rangka Batang Bidang, `S3` Portal Bidang, `S4` Portal Berpengaku, `S5` Rangka Ruang 3D), pembangkitan dataset terstruktur (`results/dataset/`), serta pembekuan konfigurasi pra-validasi (`manifest_config_frozen.json`).
   * **Protokol Integrasi Berpasangan ARI–GNN (`S6`):** Studi kelayakan arsitektur tunggal `StructGNN-CRC v1.0` pada rangka batang bidang beserta kerangka audit biaya operasional waktu komputasi berpasangan (`results/integration/`).

---

## 2. Arsitektur Pipeline Komputasi

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

## 3. Instalasi & Cara Menjalankan Verifikasi

### Prasyarat Lingkungan
* Python $\ge 3.9$
* Pustaka ilmiah dasar (`numpy`, `matplotlib`)

```bash
pip install -r requirements.txt
```

### A. Verifikasi Terpadu Satu Pintu (*Recommended*)
Jalankan skrip utama di akar repositori untuk mengeksekusi seluruh 9 tahapan verifikasi secara otomatis:

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

# 3. Protokol Multi-Keluarga (S1–S5) & Studi Integrasi Berpasangan GNN (S6)
python3 test_structural_solvers.py   # Uji analitis solver 5 keluarga struktur S1–S5
python3 generate_dataset_s1_s5.py    # Pembangkitan model induk S1–S5 beserta manifest SHA-256
python3 freeze_protocol_config.py    # Pembekuan konfigurasi protokol (ARI-FROZEN-PROTOCOL-v1.0)
python3 run_screening_s1_s5.py       # Simulasi penyaringan 2-pass anti-leakage lintas keluarga S1–S5
python3 run_gnn_integration_s6.py    # Evaluasi protokol integrasi berpasangan & rincian biaya waktu
```

---

## 4. Struktur Direktori Repositori

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
├── run_all_verifications.py         # Skrip eksekusi verifikasi otomatis satu pintu (9 tahap)
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

## 5. Lisensi & Sitasi

Kode sumber dalam repositori ini dilisensikan di bawah **Apache License 2.0** (lihat berkas [`LICENSE`](LICENSE)).  
Untuk menyitasi karya ini dalam publikasi ilmiah, gunakan tombol **"Cite this repository"** pada halaman GitHub atau merujuk pada metadata di [`CITATION.cff`](CITATION.cff).
