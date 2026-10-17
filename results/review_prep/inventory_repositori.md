# Inventaris Repositori — Adjusted Redundancy Index (ARI)

**Pembaruan Terakhir:** 17 Oktober 2026  
**Peneliti:** Harids Irawan, S.T., M.T. (Sekolah Pascasarjana Universitas Negeri Yogyakarta)  
**Repositori GitHub:** `https://github.com/haridsirawan/Adjusted-Redundancy-Index`

---

## 1. Ringkasan Status Repositori

| Parameter | Keterangan |
| :--- | :--- |
| **Cabang Utama** | `main` |
| **Total Berkas di `examples/`** | 29 berkas ilmiah (27 modul Python & 2 berkas spesifikasi JSON) |
| **Subdirektori `results/`** | 8 subdirektori (`verification`, `revision`, `bounds`, `dataset`, `screening`, `validation`, `integration`, `review_prep`) |
| **Runner Verifikasi Satu Pintu** | `python3 run_all_verifications.py` (9/9 tahap lulus 100%) |
| **Status Pemeriksaan Kanonik** | 68/68 pemeriksaan otomatis LULUS (`results/verification/checks.csv`) |
| **Status Pemeriksaan Pengaman SVD** | 33/33 pemeriksaan LULUS (`results/verification/guard_verification.json`) |
| **Kebersihan Repositori** | Bebas dari skrip *debugging* sementara (`debug_archive/`), bebas dari skrip pemformatan dokumen Word lokal, dan bebas dari *cache* sistem operasi |

---

## 2. Daftar Lengkap Berkas Repositori

### 2.1 Berkas Akar (*Root Directory* — 9 Berkas)
| Berkas | Fungsi |
| :--- | :--- |
| `README.md` | Dokumentasi utama repositori, ruang lingkup epistemik, & panduan eksekusi |
| `ARCHITECTURE.md` | Spesifikasi arsitektur berlapis, kontrak numerik terkunci, & peta modul |
| `CITATION.cff` | Metadata sitasi akademik standar GitHub untuk disertasi |
| `LICENSE` | Lisensi perangkat lunak terbuka Apache 2.0 |
| `requirements.txt` | Daftar dependensi pustaka Python (`numpy`, `matplotlib`) |
| `run_all_verifications.py` | Skrip eksekusi otomatis satu pintu untuk seluruh 9 tahapan verifikasi |
| `manifest_config_frozen.json` | Segel konfigurasi protokol beku (`ARI-FROZEN-PROTOCOL-v1.0`) |
| `WORK_LOG.md` | Catatan riwayat verifikasi berjenjang (Gate 1 s.d. Gate 17) |
| `DEFERRED_FINDINGS.md` | Dokumentasi penutupan temuan numerik & rekonsiliasi formula |

### 2.2 Direktori `examples/` — Kode Sumber & Spesifikasi Model (29 Berkas)
| Berkas | Fungsi |
| :--- | :--- |
| `ari_core.py` | Mesin inti ARI (Pers. 2.5–2.18: bobot sisi, enumerasi lintasan eksak, $b_{jc}$ per komponen reaksi, RR, ARI, CI) |
| `ari_tutorial.py` | Tutorial analitis rantai perhitungan ARI pada dua batang paralel (Tabel 25) |
| `truss_reference.py` | Solver elemen hingga batang aksial 1D/2D dengan pemeriksaan rank nilai eigen $10^{-10}$ |
| `test_truss_reference.py` | Uji penerimaan solver terhadap 4 model kanonik (Tabel 13) & penolakan mekanisme |
| `verification_models.json` | Spesifikasi 4 model kanonik (`M1`–`M4`) beserta parameter skala & nilai acuan |
| `test_ari.py` | Pengujian diagnostik inti ARI, monotonisitas $\text{RR}(\lambda)$, & invariansi konversi satuan |
| `mechanical_guard.py` | Pengaman kinematik berbasis SVD ($h_e = k_e \mathbf{a}_e \mathbf{K}_0^{-1} \mathbf{a}_e^\top$, margin $m_e(\lambda)$, batas $\kappa$) |
| `kinematic_guard.py` | Modul audit observasional perubahan rank (`CONSISTENT`, `MECHANISM`, `GRAPH_BLIND`) |
| `bound_enhancement.py` | Batas praanalisis redistribusi gaya dan pembesaran perpindahan (§4.4) |
| `test_bound_enhancement.py` | Uji regresi Tabel 16 dan sifat konservatisme batas praanalisis |
| `layered_policy.py` | Kebijakan penyaringan berlapis $\mathcal{F}^+$ (Pers. 4.13) |
| `test_leakage_audit.py` | Audit otomatis anti-kebocoran informasi pascagangguan (4 pemeriksaan) |
| `run_ablation_bounds.py` | Evaluasi ablasi komponen batas praanalisis |
| `run_verification.py` | Runner verifikasi kanonik penuh (68/68 pemeriksaan otomatis) |
| `run_guard_verification.py` | Runner verifikasi pengaman (33/33 lulus) & diagnostik 16 model parametrik (272 skenario) |
| `run_pipeline.py` | Orkestrasi pipeline 3 lapisan pada grid kasar $\lambda \in \{1, 0{,}75, 0{,}5, 0{,}25, 0\}$ |
| `fine_grid_runner.py` | Evaluasi grid halus $\Delta\lambda = 0{,}05$ (336 baris) |
| `curve_extractor.py` | Ekstraksi titik kritis $\lambda_{\text{crit}}$ dan $\lambda_{\text{guard-flip}}$ |
| `plot_curves.py` | Pembangkitan 4 grafik PDF kurva $\text{RR}(\lambda)$ dan $\text{CI}(\lambda)$ |
| `reconcile_ari_forward.py` | Rekonsiliasi variasi konvensi penerusan pada 272 skenario parametrik |
| `analyze_remaining_misses.py` | Karakterisasi 28 kasus kritis terlewat & evaluasi kandidat aturan aditif |
| `structural_solvers.py` | Suite solver elemen hingga 5 keluarga struktur (`S1`–`S5`) |
| `verification_solvers_s1_s5.json` | Spesifikasi model acuan analitis untuk solver multi-keluarga `S1`–`S5` |
| `test_structural_solvers.py` | Suite uji analitis solver elemen hingga lintas keluarga `S1`–`S5` |
| `generate_dataset_s1_s5.py` | Pembangkitan deterministik 300 model induk `S1`–`S5` & manifest SHA-256 |
| `freeze_protocol_config.py` | Pembekuan konfigurasi protokol pra-validasi (`ARI-FROZEN-PROTOCOL-v1.0`) |
| `run_screening_s1_s5.py` | Runner simulasi penyaringan 2-pass anti-leakage lintas keluarga `S1`–`S5` |
| `gnn_surrogate_s6.py` | Implementasi arsitektur acuan `StructGNN-CRC v1.0` pada rangka batang bidang |
| `run_gnn_integration_s6.py` | Evaluasi protokol integrasi berpasangan ARI–GNN & rincian biaya waktu komputasi |

### 2.3 Direktori `results/` — Artefak Keluaran Terstruktur
* **`results/verification/`**: `baseline.csv`, `scenarios.csv`, `checks.csv` (68/68 lulus), `manifest.json`, `guard_verification.json`, `Tabel.tex`, `models.pdf`, `ci_by_damage.pdf`, `pipeline_output.csv`, `fine_grid_output.csv`, `ari_screening.csv`, `ari_screening_full.csv`, `screening_report.json`, `critical_lambdas.json`, `plots/curve_M1..M4*.pdf`, `README.md`.
* **`results/revision/`**: `models.json` (16 model parametrik), `decisions.csv` (272 skenario), `forwarded.csv` (52 skenario), `remaining_misses.csv` (28 skenario), `README.md`.
* **`results/bounds/`**: `ablation_report.csv`, `leakage_audit.log`.
* **`results/dataset/`**: `models_s1.json` s.d. `models_s5.json`, `manifest.json`, `manifest.csv`, `dataset_stats.json`, `manifest_config_frozen.json`.
* **`results/screening/`**: `decisions_300.csv`, `forwarded_300.csv`, `remaining_misses_300.csv`, `calibration_grid_tau.csv`, `screening_summary_300.json`, `manifest_config_frozen.json`.
* **`results/validation/`**: `full_evaluation_300.csv`, `screening_metrics_by_family_split.csv`, `ablation_300.csv`, `gate_validation_report_300.json`.
* **`results/integration/`**: `gnn_model_card_s6.json`, `gnn_weights_s6.npz`, `treatment_comparison_s6.csv`, `cost_breakdown_table_4_19.csv`, `integration_report_s6.json`.
* **`results/review_prep/`**: `penyelarasan_disertasi_gate9.md`, `audit_naskah_revisi.md`, `rekonsiliasi_ari_forward.md`, `rekonsiliasi_ari_forward_kasus.csv`, `diagnosa_28_kasus_terlewat.md`, `diagnosa_28_kasus_terlewat.csv`, `disertasi_numbers_audit.md`, `review_checklist.md`, `revision_guide.md`, `inventory_repositori.md`.

---

## 3. Prosedur Pemeriksaan Cepat

```bash
python3 run_all_verifications.py
```

Seluruh 9 tahapan verifikasi berjalan otomatis dalam $\approx 12$ detik dengan status akhir **9/9 LULUS**.
