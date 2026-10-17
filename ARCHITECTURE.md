# ARCHITECTURE — Spesifikasi Teknis & Peta Modul Disertasi ARI

**Status Pembaruan:** 17 Oktober 2026 (Seluruh rantai verifikasi kanonik, pengaman kinematik SVD, diagnostik 272 skenario parametrik, solver multi-keluarga `S1`–`S5`, dan protokol integrasi berpasangan `StructGNN-CRC v1.0` telah tersinkronisasi penuh dengan naskah disertasi).

---

## 1. Arsitektur Komputasi Berlapis

```text
examples/verification_models.json ──► examples/truss_reference.py (Lapis 1: Solver FE Batang Aksial 1D/2D)
                                             │  Gaya awal N_e^(0), reaksi r^(0), utilisasi U*, rank(K_ff)
                                             ▼
                                      examples/ari_core.py (Lapis 2: Mesin Inti ARI, Pers. 2.5–2.18)
                                             │  Bobot w_e^M, pasangan Φ^K_ij, skor S(G), RR, ARI, CI
                                             ▼
            ┌────────────────────────────────┼────────────────────────────────┐
            ▼                                ▼                                ▼
examples/mechanical_guard.py     examples/bound_enhancement.py    examples/kinematic_guard.py
(Pengaman SVD h_e, Pers. 4.1–4.7) (Batas Redistribusi & Perpindahan) (Audit Observasional Rank)
            └────────────────────────────────┼────────────────────────────────┘
                                             ▼
                               examples/layered_policy.py (Kebijakan Berlapis F⁺, Pers. 4.13)
                                             │
        ┌────────────────────────────────────┼────────────────────────────────────┐
        ▼                                    ▼                                    ▼
run_verification.py               run_guard_verification.py             run_pipeline.py / fine_grid_runner.py
(68/68 Cek Kanonik → Tabel.tex)   (33/33 Cek Pengaman & 272 Skenario)   (Grid Kasar & Halus Δλ=0,05 → PDF)
```

---

## 2. Daftar Lengkap Modul Implementasi (`examples/` — 29 Berkas)

### 2.1 Inti Kanonik, Pengaman Kinematik, & Batas Praanalisis
| Berkas | Bab/Subbab Naskah | Fungsi Utama | Status |
| :--- | :--- | :--- | :---: |
| `verification_models.json` | Bab IV Subbab A | Definisi 4 model kanonik (`M1`–`M4`), skala kapasitas, & nilai acuan Tabel 13 | Terverifikasi |
| `truss_reference.py` | Bab III & IV.A | Solver elemen hingga batang aksial 1D/2D (pemeriksaan rank nilai eigen $10^{-10}$, tanpa pseudoinvers) | Terverifikasi |
| `test_truss_reference.py` | Bab IV Subbab A | Uji penerimaan solver terhadap Tabel 13 ($\Delta < 5 \times 10^{-4}$) & penolakan mekanisme | 100% Lulus |
| `ari_core.py` | Bab II (Pers. 2.5–2.18) | Mesin inti ARI: bobot sisi $w_e^M$, enumerasi eksak lintasan *edge-disjoint*, $b_{jc}$ per komponen reaksi, RR, ARI, CI | Terverifikasi |
| `ari_tutorial.py` | Bab IV Subbab H | Tutorial analitis langkah-demi-langkah contoh dua batang paralel (Tabel 25) | 100% Lulus |
| `test_ari.py` | Bab IV Subbab A | Uji diagnostik Tabel 15 & 25, monotonisitas $\text{RR}(\lambda)$, & invariansi konversi satuan | 100% Lulus |
| `mechanical_guard.py` | Bab IV Subbab B (Pers. 4.1–4.7) | Pengaman kinematik berbasis SVD ($h_e = k_e \mathbf{a}_e \mathbf{K}_0^{-1} \mathbf{a}_e^\top$), margin $m_e(\lambda)$, & batas kondisi | 100% Lulus |
| `kinematic_guard.py` | Bab IV Subbab B | Modul audit observasional perubahan rank (`CONSISTENT`, `MECHANISM`, `GRAPH_BLIND`) | Terverifikasi |
| `bound_enhancement.py` | Bab IV Subbab D | Batas praanalisis redistribusi gaya ($\hat{U}_n^{\text{bound}}$) dan pembesaran perpindahan ($\hat{\kappa}_{\text{amp}}$) | Terverifikasi |
| `test_bound_enhancement.py` | Bab IV Subbab D | Uji regresi Tabel 16 & konservatisme batas praanalisis | 100% Lulus |
| `layered_policy.py` | Bab IV Subbab D.5 | Kebijakan penyaringan berlapis $\mathcal{F}^+$ (pengaman kinematik $\to$ batas praanalisis $\to$ ARI) | Terverifikasi |
| `test_leakage_audit.py` | Bab IV Subbab E.6 | Audit otomatis anti-kebocoran informasi pascagangguan (4 pemeriksaan ketat) | 100% Lulus |
| `run_ablation_bounds.py` | Bab IV Subbab D.6 | Evaluasi ablasi kontribusi komponen batas praanalisis | Terverifikasi |

### 2.2 Orkestrasi Verifikasi, Kurva Sensitivitas, & Diagnostik Parametrik
| Berkas | Bab/Subbab Naskah | Fungsi Utama | Status |
| :--- | :--- | :--- | :---: |
| `run_verification.py` | Bab IV Subbab E & G | Runner verifikasi kanonik penuh (68/68 pemeriksaan otomatis) $\to$ CSV, JSON, `Tabel.tex`, PDF | 68/68 Lulus |
| `run_guard_verification.py` | Bab IV Subbab B.4–B.6 | Verifikasi paket pengaman (33/33 lulus) & evaluasi 16 model parametrik (272 skenario) | 33/33 Lulus |
| `run_pipeline.py` | Bab IV Subbab E.2 | Orkestrasi pipeline 3 lapisan pada grid kasar $\lambda \in \{1, 0{,}75, 0{,}5, 0{,}25, 0\}$ (80 skenario) | Terverifikasi |
| `fine_grid_runner.py` | Bab IV Subbab A & E | Evaluasi grid halus $\Delta\lambda = 0{,}05$ (21 titik $\times$ 16 elemen = 336 baris) | Terverifikasi |
| `curve_extractor.py` | Bab IV Subbab A | Ekstraksi titik kritis $\lambda_{\text{crit}}$ ($\text{CI} \ge 0{,}5$) dan titik balik pengaman $\lambda_{\text{guard-flip}}$ | Terverifikasi |
| `plot_curves.py` | Bab IV Subbab A | Pembangkitan 4 grafik PDF kurva halus $\text{RR}(\lambda)$ dan $\text{CI}(\lambda)$ (`M1`–`M4`) | Terverifikasi |
| `reconcile_ari_forward.py` | Bab IV Subbab B.6 | Audit rekonsiliasi variasi konvensi penerusan pada 272 skenario parametrik | Terverifikasi |
| `analyze_remaining_misses.py` | Bab IV Subbab B.5–B.6 | Karakterisasi 28 kasus kritis terlewat & evaluasi sensitivitas aturan aditif | Terverifikasi |

### 2.3 Suite Protokol Lanjutan Multi-Keluarga (`S1`–`S5`) & Integrasi GNN (`S6`)
| Berkas | Bab/Subbab Naskah | Fungsi Utama | Status |
| :--- | :--- | :--- | :---: |
| `structural_solvers.py` | Bab III Subbab I.2 | Suite solver FE 5 keluarga struktur: `S1` Balok, `S2` Rangka Batang, `S3` Portal, `S4` Berpengaku, `S5` Rangka Ruang 3D | Terverifikasi |
| `verification_solvers_s1_s5.json` | Bab III Subbab I.2 | Spesifikasi model acuan analitis untuk pengujian solver `S1`, `S3`, `S4`, dan `S5` | Terverifikasi |
| `test_structural_solvers.py` | Bab III Subbab I.2 | Suite uji penerimaan analitis solver elemen hingga lintas keluarga `S1`–`S5` | 100% Lulus |
| `generate_dataset_s1_s5.py` | Bab III Subbab F & I | Generator deterministik (`seed=2026`) 300 model induk `S1`–`S5` beserta manifest SHA-256 | Terverifikasi |
| `freeze_protocol_config.py` | Bab III Subbab C & I.5 | Pembekuan konfigurasi protokol pra-validasi (`ARI-FROZEN-PROTOCOL-v1.0`) | Terverifikasi |
| `run_screening_s1_s5.py` | Bab IV Subbab I–J | Runner simulasi penyaringan 2-pass anti-leakage, bootstrap $B=10.000$, & studi ablasi | Terverifikasi |
| `gnn_surrogate_s6.py` | Bab III Subbab R | Arsitektur acuan `StructGNN-CRC v1.0` (Message-Passing GNN 3-lapisan pada rangka batang bidang) | Terverifikasi |
| `run_gnn_integration_s6.py` | Bab III.R & IV.J | Protokol evaluasi berpasangan ARI–GNN & audit rincian biaya waktu komputasi (Tabel 31) | Terverifikasi |

---

## 3. Peta Artefak Keluaran (`results/`)

| Subdirektori | Berkas Utama | Keterangan |
| :--- | :--- | :--- |
| `results/verification/` | `baseline.csv`, `scenarios.csv`, `checks.csv` (68/68), `manifest.json`, `guard_verification.json`, `Tabel.tex`, `models.pdf`, `ci_by_damage.pdf`, `pipeline_output.csv`, `fine_grid_output.csv`, `plots/*.pdf` | Bukti numerik kanonik lengkap & kurva sensitivitas |
| `results/revision/` | `models.json`, `decisions.csv`, `forwarded.csv`, `remaining_misses.csv`, `README.md` | Paket evaluasi diagnostik 16 model parametrik (272 skenario) |
| `results/bounds/` | `ablation_report.csv`, `leakage_audit.log` | Bukti audit anti-kebocoran informasi & ablasi batas praanalisis |
| `results/dataset/` | `models_s1.json`..`models_s5.json`, `manifest.json`, `manifest.csv`, `dataset_stats.json` | Spesifikasi dataset 300 model induk lintas keluarga `S1`–`S5` |
| `results/screening/` | `decisions_300.csv`, `forwarded_300.csv`, `remaining_misses_300.csv`, `calibration_grid_tau.csv`, `screening_summary_300.json` | Keluaran simulasi penyaringan operasional & grid kalibrasi ambang |
| `results/validation/` | `full_evaluation_300.csv`, `screening_metrics_by_family_split.csv`, `ablation_300.csv`, `gate_validation_report_300.json` | Rekapitulasi metrik gerbang validasi (A–D) & interval bootstrap |
| `results/integration/` | `gnn_model_card_s6.json`, `gnn_weights_s6.npz`, `treatment_comparison_s6.csv`, `cost_breakdown_table_4_19.csv`, `integration_report_s6.json` | Artefak protokol integrasi berpasangan `StructGNN-CRC v1.0` & rincian biaya |
| `results/review_prep/` | `penyelarasan_disertasi_gate9.md`, `audit_naskah_revisi.md`, `rekonsiliasi_ari_forward.md`, `diagnosa_28_kasus_terlewat.md`, `inventory_repositori.md`, `review_checklist.md` | Dokumentasi audit silang angka naskah, rekonsiliasi, & panduan verifikasi |

---

## 4. Kontrak Numerik Terkunci

* **Parameter Bobot & Formulasi:** $\alpha_k = 0{,}5$, $\alpha_R = 0{,}5$, $q_e = 1{,}0$, $K = 2$, $\gamma = 1{,}0$, $\eta = 0{,}5$, $\beta = 0{,}1$.
* **Toleransi & Regularisasi:** $\varepsilon_w = \varepsilon_d = 10^{-9}$, $\varepsilon_R = 10^{-6}\text{ kN}$, `baseline_tol` $= 10^{-12}$, toleransi rank relatif $= 10^{-10}$ terhadap nilai eigen maksimum (tanpa pseudoinvers), batas anggaran pencarian DFS $= 200.000$ simpul.
* **Perlakuan Kehilangan Penuh ($\lambda = 0$):** Sisi dengan $\lambda = 0$ dihapus secara eksak dari graf topologi sebelum enumerasi lintasan.
* **Skala Referensi Kanonik (`M1`–`M4`):** `M1` ($s_k = 15$, $s_R = 30$), `M2` ($s_k = 20$, $s_R = 40$), `M3` & `M4` ($s_k = 20$, $s_R = 80$); satuan konsisten $\text{kN}$ dan $\text{mm}$ ($E = 200\text{ kN/mm}^2$).
