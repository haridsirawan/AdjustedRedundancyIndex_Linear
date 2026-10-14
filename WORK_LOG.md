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


---

# WORK LOG — Gate 2: ARI Core Implementation (SPRINT MODE)
**Researcher:** Harids Irawan
**Date:** Sunday, October 11, 2026
**Gate:** Gate 2 — ARI Core Implementation
**Status:** 🟢 COMPLETED (Sprint Mode — lanjut ke Gate 3 tanpa menunggu review)

## Actions Taken
- [x] `examples/ari_core.py` difinalisasi — 9 fungsi kontrak disertasi lengkap & terdokumentasi (Eq 2.5–2.18): compute_edge_weights, enumerate_simple_paths (DFS, node tak berulang, edge-ID dipertahankan utk multigraph), enumerate_edge_disjoint_combinations (EKSHAUSTIF — bukan greedy, §4.8.6), compute_pair_score, compute_node_weights (b_jc dari reaksi INTAK, tanpa renormalisasi), compute_graph_score, apply_disruption (λ, TANPA renormalisasi, §4.8.4), compute_ari, run_full_screening + audit trail.
- [x] `examples/test_ari.py` difinalisasi — diagnostik blok [1]–[6] + CSV; grid penuh λ∈{1,0.75,0.5,0.25,0} × 16 edge = 80 run dieksekusi (DF-05 ditutup).
- [x] `DEFERRED_FINDINGS.md` dibuat/diperbarui — Finding #001–#004 (penomoran sesuai instruksi peneliti, dipetakan ke DF-nn).
- [x] Konfigurasi default terkunci & diverifikasi di kode: α_k=α_R=0.5, q_e=1, K=2, γ=1, η=0.5, β=0.1; ε_w=ε_d=1e-9, ε_R=1e-6 kN, baseline_tol=1e-12; skala tetap per model sesuai §4.1.2 (M1: s_k=15, s_R=30; M2: 20/40; M3,M4: 20/80). Konvensi λ=0 = hapus edge fisik; uncertified ⇒ abstain (RR/ARI/CI=None).

## Verification Results (ringkasan — detail & bukti di DEFERRED_FINDINGS.md)
| Kasus | Expected | Actual | Match? |
|---|---|---|---|
| Tabel 4.11 — kontrol utuh (per-edge λ=1) | RR=1, CI=η·U*=0.25 | RR=1 eksak, CI=0.25 | ✅ (rel.tol 1e-6) |
| Tabel 4.11 — remove bar 0 | RR=7/17, ARI=21/68, CI=47/68 | 0.411765 / 0.308824 / 0.691176 | ✅ |
| Tabel 4.11 — remove bar 1 | RR=10/17, ARI=15/34, CI=19/34 | 0.588235 / 0.441176 / 0.558824 | ✅ |
| Tabel 4.3 — e3(CD), e4(DA) [KRITIS] | RR=1.0, CI=0.0 | 1.000000 / 0.000000 | ✅ batas representasi |
| Tabel 4.3 — e1(AB) | RR≈0.983152 | 0.859874 | ❌ → Finding #001 |
| Tabel 4.3 — e2(BC) | RR≈0.964724 | 0.706600 | ❌ → Finding #001 |
| Tabel 4.3 — e5(AC) | RR≈0.717285 | 0.791758 | ❌ → Finding #001 |
| Monotonisitas S(λ) M3-e5, M4-e5 (+semua 16 edge) | S tidak naik saat λ turun | PASS; 0 pelanggaran RR-monotonic | ✅ |
| Invariansi skala-serentak ×10 semua parameter bertaraf | ARI tak berubah | ΔARI maks 4.9e-2 → bentuk asimtotik | ⚠️ → Finding #002 |
| Grid penuh skrining | 64 skenario + 16 kontrol | 80 run selesai, tanpa anomali (RR(1)=1 eksak, CI≥0) | ✅ |

## Deferred Findings (referensi untuk review nanti)
- **Finding #001** (DF-01): deviasi >10% RR e1/e2/e5 Square-One-Diagonal vs Tabel 4.3 — sudah dibuktikan BUKAN artefak ε/skala (sweep identik eksak); hipotesis H1–H3 butuh teks disertasi. Sprint mode: dicatat, TIDAK didebug, formula/parameter TIDAK diubah.
- **Finding #002** (DF-03): invariansi hanya berlaku jika SEMUA parameter bertaraf (s_k, s_R, ε_w, ε_d, ε_R, ε_removed) diskalakan serentak, dan itu pun dalam limit ε→0 (asimtotik, bukan eksak). Keputusan formulasi untuk didokumentasikan.
- **Finding #003**: e3/e4 zero-initial-force → CI≈0 saat rank turun 5→4. Batas representasi ARI (skor jalur murni-graf, bukan kendala kinematik) — BUKAN bug. Motivasi Gate 3 (Kinematic Guard).
- **Finding #004** (DF-02/04/05/06): temuan tambahan — plateau RR(λ) pada λ≤0.5 (sifat max-over-paths), rank-deficiency meluas ke seluruh edge M4 saat hapus-total, konvensi kontrol edge-less vs per-edge, exhaustive search tersertifikasi budget.

## Notes for Review
- Regresi Gate 1 dicek ulang setelah perubahan ari_core: solver tetap cocok Tabel 4.1 (Δ < 5e-4, exit 0).
- Audit trail: `results/verification/ari_screening.csv` (68 baris: status mekanik, S_baseline, S_scenario, RR, U*, ARI, CI per skenario).
- Cara menjalankan: `python examples/test_ari.py` (exit 0 = sprint-mode OK; flag DEVIASI-DEFERRED diharapkan).

## Status Gate
🟢 **GATE 2 COMPLETED (Sprint Mode)** — kerangka utuh, semua temuan tercatat.
➡️ Langkah berikutnya: **Gate 3 — Kinematic Guard** (tanpa menunggu review), menutup Finding #003/#004 dengan deteksi mekanisme/rank-diagnostik di sisi ARI.

---

# Gate 3 — Kinematic Guard
**Date:** Sunday, October 11, 2026
**Status:** 🟢 PASSED (self-test exit 0; regresi Gate 1 & Gate 2 tetap hijau)

## Actions Taken
- [x] `examples/kinematic_guard.py` dibuat: `kinetic_snapshot`, `guard_scenario`, `classify`, `annotate_screening` + self-test CLI. Guard bersifat OBSERVASIONAL — RR/ARI/CI tidak diubah (sanity PASS eksak 1e-12).
- [x] `examples/ari_core.py`: ditambahkan `kinetic_snapshot` & `guard_diagnostic` (rank-check via solver Gate 1, eigvals tol relatif 1e-10, tanpa pseudoinverse); kontrol λ=1 per-edge kini membawa snapshot kinematik INTAK di audit trail.
- [x] `DEFERRED_FINDINGS.md`: Finding #005 (penomoran edge Tabel 4.3 = 1-based vs id JSON 0-based → "e3,e4" ≡ id2(CD),id3(DA)) dan #006 (hasil klasifikasi guard).
- [x] Regresi: `test_truss_reference.py` exit 0 (Tabel 4.1), `test_ari.py` exit 0 (Tabel 4.11 LULUS; #001/#002 tetap terdokumentasi).

## Hasil Self-Test (λ=0 hapus-total, 16 skenario)
| Model | Edge | RR | CI_ARI | rank intact→disrupted | Label guard |
|---|---|---|---|---|---|
| M1 | e0,e1 | 0.411765 / 0.588235 | 0.691176 / 0.558824 | 1→1 | CONSISTENT |
| M2 | e0,e1,e2 | 0.500000/0.500000/0.668277 | >0.4 | 3→2 | MECHANISM |
| M3 | id0(AB) | 0.859874 | 0.140126 | 5→4 | MECHANISM |
| M3 | id1(BC) | 0.706600 | 0.425887 | 5→4 | MECHANISM |
| M3 | **id2(CD)** | **1.000000** | **0.000000** | 5→4 | **GRAPH_BLIND** ← Finding #003 |
| M3 | **id3(DA)** | **1.000000** | **0.000000** | 5→4 | **GRAPH_BLIND** ← Finding #003 |
| M3 | id4(AC) | 0.791758 | 0.418189 | 5→4 | MECHANISM |
| M4 | semua e0–e5 | 0.834–1.000 | 0.074–0.300 | 5→5 | CONSISTENT |

Ringkasan: 8 CONSISTENT, 6 MECHANISM, 2 GRAPH_BLIND. Kasus kritis Finding #003 kini TERDETEKSI oleh guard (label GRAPH_BLIND saat CI<0.01 & rank_drop>0), menutup gap representasi ARI murni-graf.

## Temuan Penting
- **Finding #005**: label "e3/e4" pada narasi disertasi ternyata 1-based; dua zero-force member (CD, DA) = id JSON 2,3. Bukti independen dari sisi kinematik — memperkuat hipotesis H2 utk deviasi Tabel 4.3 (#001), namun konfirmasi naskah tetap diperlukan.
- M2 kehilangan elemen tunggal apa pun → mekanisme (rank-deficient): redundansi M2 adalah redundansi beban-jalur, bukan redundansi stabilitas.

## Langkah Selanjutnya
➡️ Gate 4: integrasi pipeline penuh (screening grid λ × guard × CSV berkolom kinematik) & review session utk #001/#002/#005.

---

# Gate 4 — Integrasi Pipeline Penuh (Screening Orchestration)
**Date:** Sunday, October 11, 2026
**Status:** 🟢 PASSED (pipeline exit 0; regresi Gate 1/2/3 tetap hijau)

## Actions Taken
- [x] `examples/run_pipeline.py` dibuat — orkestrasi SATU perintah tiga lapisan:
      Lapisan 1 solver FE Gate 1 → Lapisan 2 mesin ARI Gate 2 (`ari_core`) →
      Lapisan 3 Kinematic Guard Gate 3 (`kinematic_guard`). TIDAK ada perubahan
      formula/parameter (regresi dijaga); guard tetap observasional.
- [x] Grid penuh dieksekusi: λ∈{1, 0.75, 0.5, 0.25, 0} × 16 edge = **64 skenario
      disrupsi + 20 kontrol** (4 kontrol utuh per model + 16 kontrol per-edge
      λ=1) = 84 baris audit.
- [x] Output artefak: `results/verification/ari_screening_full.csv` (kolom
      berjenjang `layer`, rank intak→terdisrupsi, rank_drop, solvable,
      guard_label, U*, S_baseline/S_scenario, RR/ARI/CI, note) dan
      `results/verification/screening_report.json` (agregat per model +
      consistency-checks + daftar inkonsistensi).
- [x] Konsistensi-check antar-lapisan tertanam (built-in) di pipeline (exit code ≠ 0 jika gagal):
      (i) deteksi mekanisme Lapisan-2 vs Lapisan-3 harus sepakat — 64/64 OK;
      (ii) GRAPH_BLIND hanya boleh pada skenario mekanisme — OK;
      (iii) monotonisitas RR(λ) per-edge (RR tak naik saat λ turun) — 0 pelanggaran;
      (iv) kontrol λ=1: RR=1 eksak & CI=η·U*_e — PASS semua edge;
      (v) regresi angka kunci Gate 2 (Tabel 4.11 & kasus kritis Tabel 4.3) — PASS.
- [x] `DEFERRED_FINDINGS.md`: Finding #007 (mekanisme M2 muncul juga pada λ
      parsial — ambang bergantung toleransi eigvals solver) dan #008 (plateau
      RR(λ≤0.5) meluas ke banyak edge M3/M4; seluruh cek lintas-lapisan lulus).
- [x] Regresi gate sebelumnya dijalankan ulang: `test_truss_reference.py` exit 0,
      `test_ari.py` exit 0 (Tabel 4.11 LULUS; #001/#002 tetap terdokumentasi),
      `kinematic_guard.py` exit 0 (GRAPH_BLIND=2).

## Verification Results (aktual dari rerun 2026-10-11)
| Cek | Expected | Actual | Match? |
|---|---|---|---|
| Pipeline selesai | 84 baris (64+20), tanpa error | 84 baris, inkonsistensi=[] | ✅ |
| Tabel 4.11 remove bar0 RR | 7/17 = 0.411765 | 0.411764716 | ✅ (tol 1e-6) |
| Tabel 4.11 remove bar1 RR | 10/17 = 0.588235 | 0.588235304 | ✅ |
| Tabel 4.3 e3(CD)/e4(DA) KRITIS | RR=1, CI=0 | 1.0 / ≤1.1e-16 | ✅ |
| Guard GRAPH_BLIND M3@λ0 | edge id {2,3} | {2,3} | ✅ |
| Sepakatan Lapisan-2 vs -3 (mekanisme) | 64/64 | 64/64 | ✅ |
| Monotonisitas RR per-edge grid penuh | 0 pelanggaran | 0 pelanggaran | ✅ |
| Kontrol λ=1 (RR=1 eksak, CI=η·U*) | 16/16 | 16/16 | ✅ |
| Agregat label guard (64 skenario) | — | 56 CONSISTENT, 6 MECHANISM, 2 GRAPH_BLIND | ℹ️ |
| Baseline S(G_M) M1/M2/M3/M4 | — | 0.485714 / 0.379544 / 0.360252 / 0.360252 | ℹ️ |

## Notes for Review
- Cara menjalankan: `python examples/run_pipeline.py` (exit 0 = PASS).
- Deviasi Tabel 4.3 e1/e2/e5 (#001) TIDAK berubah — pipeline tidak menyentuh
  formula; temuan Gate 4 baru (#007, #008) didokumentasikan untuk review.
- CSV lama Gate 2 (`ari_screening.csv`) dipertahankan sebagai artefak historis;
  CSV pipeline (`ari_screening_full.csv`) adalah sumber tunggal untuk tabel
  disertasi berikutnya.

## Status Gate
🟢 **GATE 4 PASSED** — pipeline penuh audit-ready satu perintah.
➡️ Langkah berikutnya (usulan): Gate 5 — kurva RR(λ) & ambang λ_kritis per edge
(menutup Finding #007), lalu sesi review #001/#002 dengan naskah disertasi.

---

# GATE 5 — Verification Runner & Curve Extraction
**Date:** Sunday, October 11, 2026
**Status:** 🟢 COMPLETED (Sprint Mode — lanjut ke Gate 6)

## Actions Taken
- [x] `examples/run_pipeline.py` diperluas: menulis **schema kanonik Gate 5**
      `results/verification/pipeline_output.csv` dengan kolom wajib
      [model_id, edge_id, lambda, S_intact, S_disrupted, RR, ARI, CI,
      rank_status, margin_m, guard_decision, U_star] (80 baris per-edge;
      kontrol utuh tanpa edge-id tidak masuk skema ini). CSV audit Gate 4
      (`ari_screening_full.csv`) tetap ditulis + kolom margin_m/guard_decision.
- [x] Definisi margin kinematik m_e(λ) := rank_drop / ndof_free (proxy
      observasional; keputusan formulasi dicatat di Finding #009) dan
      guard_decision Clear/Forward ditambahkan ke pipeline.
- [x] Modul baru `examples/curve_extractor.py`: baca pipeline_output.csv,
      interpolasi linear kurva RR(λ)/CI(λ), ekstraksi λ_crit (ambang CI≥0.5,
      konvensi konservatif "batas atas zona kritis" + nilai kontinu di note)
      dan λ_guard-flip (Clear→Forward); abstain → tanpa angka. Output:
      `results/verification/critical_lambdas.json`.
- [x] `DEFERRED_FINDINGS.md`: **Finding #009** (kebutuhan & hasil ekstraksi
      kurva/λ_kritis) + **update hipotesis Finding #001**: dugaan kuat
      kesalahan bobot tumpuan b_jc per komponen beban (c) pada model
      asimetris, BUKAN error regularisasi ε. Tidak ada perubahan formula.
- [x] Regresi penuh dijalankan ulang: Gate 1 PASS, Gate 2 PASS, Gate 3 PASS,
      Gate 4 pipeline PASS (exit 0, inkonsistensi=[]), Gate 5 extractor exit 0.

## Verification Results (aktual, rerun 2026-10-11)
| Cek | Expected | Actual | Match? |
|---|---|---|---|
| run_pipeline exit code | 0 | 0 (84 baris; 64+20) | ✅ |
| pipeline_output.csv schema | 12 kolom kanonik | sesuai, 80 baris data | ✅ |
| curve_extractor exit code | 0 | 0 (critical_lambdas.json terbentuk) | ✅ |
| Tabel 4.11 remove bar0/bar1 RR | 7/17 / 10/17 | 0.411764716 / 0.588235304 | ✅ (tol 1e-6) |
| Tabel 4.3 e3/e4 KRITIS | RR=1, CI=0 | 1.0 / ≤1.1e-16 | ✅ |
| Konsistensi-check antar-lapisan | [] | [] | ✅ |
| λ_crit(CI≥0.5) tercapai | — | M1-e0 @0.25 (kontinu 0.433), M1-e1 @0.0 (0.190), M2-e0/e1/e2 @0.0 (≈0.236); M3/M4 not_reached_on_grid | ℹ️ (#009) |
| Guard-flip Clear→Forward | — | 8 edge (M2×3, M3×5), semua di λ=0 grid coarse | ℹ️ |
| GRAPH-BLIND-LIKE otomatis | memuat M3-e2/e3 CI=0 | 6 edge, incl. M3-e2/e3 worst-CI=0.000000 | ✅ (#003 via pipeline) |
| Abstain edges | 0 | 0 dari 16 | ✅ |

## Notes for Review
- Cara menjalankan: `python examples/run_pipeline.py && python examples/curve_extractor.py`.
- Temuan #001 TIDAK didebug (sprint mode) — hanya hipotesis b_jc-per-komponen
  yang dicatat; penutupan menunggu naskah Section 2.11–2.13.
- Grid λ coarse {1,.75,.5,.25,0} membuat λ_crit berbasis-CI dan berbasis-guard
  sering tidak berimpit → rekomendasi grid halus (Δλ=0.05) utk bab sensitivitas.
- Artefak: results/verification/{pipeline_output.csv, critical_lambdas.json,
  ari_screening_full.csv, screening_report.json}.

## Status Gate
🟢 **GATE 5 COMPLETED (Sprint Mode)** — kerangka ekstraksi kurva & λ_kritis
audit-ready; Finding #007 kini punya instrumen penutup otomatis.
➡️ Langkah berikutnya (usulan): Gate 6 — grid λ halus + plotting, atau sesi
review #001/#002 dengan teks disertasi.

---

# WORK LOG — Gate 6: Fine Grid & Curve Plotting
**Researcher:** Harids Irawan
**Date:** Sunday, October 11, 2026
**Gate:** Gate 6 — Fine Grid (Δλ=0.05) & Curve Plotting
**Status:** 🟢 COMPLETED (Sprint Mode — lanjut ke review/Gate berikutnya)

## Actions Taken
- [x] `examples/fine_grid_runner.py` dibuat — pipeline 3-lapisan (Gate 1–3, parameter identik Gate 5, TIDAK ada formula yang diubah) pada grid λ ∈ {1.00, 0.95, …, 0.05, 0.00} = 21 titik/edge; abstain → "NaN" (tanpa imputasi).
- [x] `examples/plot_curves.py` dibuat — matplotlib backend Agg; per model: subplot RR(λ) atas + CI(λ) bawah; referensi RR=1, CI=0 (horizontal putus-putus), λ=0.5 (vertikal putus-putus); marker 'x' merah = rank_deficient, '*' oranye = guard-flip Clear→Forward; folder plots/ auto-create.
- [x] Eksekusi: exit 0 keduanya. Regresi Gate 1/2/3/4-5 diulang → exit 0 semua.

## Artefak
| File | Lokasi | Isi |
|---|---|---|
| CSV fine grid | `results/verification/fine_grid_output.csv` | 336 baris data + header; kolom IDENTIK pipeline_output.csv Gate 5 |
| Plot M1 | `results/verification/plots/curve_M1_parallel_bars.pdf` | 27 kB |
| Plot M2 | `results/verification/plots/curve_M2_triangle.pdf` | 28 kB |
| Plot M3 | `results/verification/plots/curve_M3_square_one_diag.pdf` | 31 kB |
| Plot M4 | `results/verification/plots/curve_M4_square_two_diag.pdf` | 29 kB |

## Verification Results (aktual)
| Cek | Expected | Actual | Match? |
|---|---|---|---|
| `fine_grid_runner.py` exit code | 0 | 0 | ✅ |
| `plot_curves.py` exit code + 4 PDF | 0 / 4 file | 0 / 4 file (>1 kB) | ✅ |
| Baris CSV | 16 edge × 21 λ = 336 | 336 (M1 42, M2 63, M3 105, M4 126) | ✅* |
| Skenario abstain (NaN) | dicatat, tanpa imputasi | 0 abstain | ✅ |
| Konsistensi fine vs coarse (λ irisan) | RR/CI identik Gate 5 | identik | ✅ |
| Regresi Gate 1–5 | exit 0 semua | gate1=0 gate2=0 gate3=0 gate45=0 | ✅ |

\* Catatan spektra: angka "4×5×21=420" pada perintah mengasumsikan 5 edge/model;
jumlah edge kanonik sebenarnya 2+3+5+6=16 → 336 baris definitif. Didokumentasikan
di DEFERRED_FINDINGS.md #010.

## Notes for Review
- Temuan baru dari kurva halus (#010): SEMUA guard-flip & rank-deficiency terjadi tepat di λ=0.0 pada Δλ=0.05 — memperkuat dugaan bahwa laporan #007 ("mekanisme M2 pada λ parsial 0.5/0.25") adalah artefak grid coarse; cek ulang sebelum klaim naskah.
- Plateau kasus kritis #003 terkonfirmasi visual (M3-e2/e3: RR=1, CI=0 ∀λ>0).
- Aksi review: bandingkan kurva M3 dengan perhitungan manual Section 4.8; tutup #001 via hipotesis b_jc-per-komponen.

## Status Gate
🟢 **GATE 6 COMPLETED (Sprint Mode)** — kerangka visualisasi audit-ready.
➡️ Langkah berikutnya (usulan): sesi review Finding #001/#007 dengan teks disertasi, atau Gate 7 (laporan agregat/ Bab Hasil).

---

# WORK LOG — Gate 8: Review Ringan & Perapian
**Researcher:** Harids Irawan (asisten: eksekusi otomatis)
**Date:** Sunday, October 11, 2026
**Status:** 🟢 COMPLETED (Review Ringan) — review manual mendalam dilakukan oleh peneliti

## Actions Taken
- [x] Audit docstring semua file `examples/`: 9/9 .py punya docstring modul (tujuan/gate/referensi section/dependensi); grep TODO/FIXME = 0; `python -m py_compile examples/*.py` OK. Tidak ada perubahan kode (sesuai kontrak "jangan ubah formula/logika").
- [x] Verifikasi konsistensi header CSV/JSON antar-artefak + cek silang fine-vs-coarse (0 mismatch >1e-9).
- [x] Baru: `results/verification/README.md` (isi tiap artefak + timestamp + perintah regenerasi).
- [x] Baru: `ARCHITECTURE.md` (daftar file AKTUAL + commit hash terakhir per file + status ✅/🟡).
- [x] Baru: `results/review_prep/disertasi_numbers_audit.md` (Tabel 4.1/4.3/4.11 naskah vs angka aktual dari CSV/solver).
- [x] Baru: `results/review_prep/review_checklist.md` (checklist A–E siap dicentang saat review manual).
- [x] Update `DEFERRED_FINDINGS.md`: kolom **Last Checked: 2026-10-11** di semua entri (#001–#011); sub-bab "Evidence from Gate 6 Curves" di #001 (deviasi sistematis, bukan lokal); catatan #002 (uji invariansi TIDAK dijalankan di Gate 6 — terakhir di test_ari.py [4]); verifikasi #009/#010 terhadap definisi operasional critical_lambdas.json; **Finding #012 baru** (sinkronisasi angka naskah↔kode, 🔴 Kritis).

## Verification Results
| Item | Expected | Actual | Match? |
|---|---|---|---|
| Docstring modul semua examples/*.py | 9/9 | 9/9 (termasuk referensi section & dependensi) | ✅ |
| Dead code / TODO relevan | 0 | 0 | ✅ |
| py_compile examples/*.py | exit 0 | exit 0 | ✅ |
| Tabel 4.1 audit (solver rerun) | dev < 5e-4 | ≤1e-6 semua | ✅ |
| Tabel 4.11 audit (pipeline_output.csv) | rel.err < 1e-6 | ≤3e-8 | ✅ |
| Tabel 4.3 e3/e4 | RR=1, CI=0 | 1.0, 0.0 | ✅ |
| Tabel 4.3 e1/e2/e5 | target naskah | 0.8599/0.7066/0.7918 | ❌ → #001 (deferred, tidak didebug) |
| Fine vs coarse pada λ irisan | identik | 0 mismatch >1e-9 (dari 336 baris) | ✅ |
| critical_lambdas.json vs definisi #009 | konsisten | spot-check M3-e2 flip@λ=0, margin 0→0.125 | ✅ (catatan kunci: `lambda_guard_flip`) |

## Temuan Baru Gate 8 (untuk review manual)
1. **Inkonsistensi internal naskah**: baris e1/e2 Tabel 4.3 tidak memenuhi identitas Eq 2.17–2.18 (CI = 1 − RR·(1−η·U*)); e3/e4/e5 konsisten. Didokumentasikan di audit + checklist §A.
2. **Bukti kurva halus #001**: deviasi sistematis di seluruh domain λ (terbesar di hapus-total), memperkuat hipotesis struktur agregasi b_jc-per-komponen-beban, bukan regularisasi.
3. **Gate 7 tidak tersedia di workspace ini**: commit `93a824d` yang dikutip peneliti tidak ada di log branch sandbox (HEAD = `677104d`); file agregat Gate 7 tidak ditemukan. Dicatat di ARCHITECTURE.md sebagai 🟡 — perlu sinkronisasi repo sebelum review memakai artefak Gate 7.
4. Uji invariansi #002 belum dieksekusi ulang di Gate 6 (hanya grid+plot); hasil lama tetap FAIL-asimtotik.

## Status Gate
🟢 **GATE 8 COMPLETED (Review Ringan)** — artefak siap diperiksa.
➡️ Selanjutnya: review manual mendalam oleh peneliti menggunakan `results/review_prep/review_checklist.md` dan `disertasi_numbers_audit.md`.

---

# Gate 9 — Penyelarasan dengan Naskah Disertasi (b_jc per komponen; guard SVD)
**Researcher:** Harids Irawan (dieksekusi oleh AutoClaw)
**Date:** Tuesday, October 13, 2026
**Status:** 🟢 COMPLETED (seluruh runner exit 0; checks.csv 65/65 LULUS)

## Actions Taken
- [x] Verifikasi langsung ke naskah (PDF 222 hal.): formulasi Bagian 2.5–2.9, 4.1.2/4.1.5, 4.2.2, 4.4.3–4.4.5, 4.5.3–4.5.10; Tabel 4.1–4.5, 4.7, 4.8, 4.11–4.13.
- [x] `examples/ari_core.py`: b_jc per KOMPONEN reaksi searah kasus beban (Eq 2.12); kasus beban per arah + π_c ternormalisasi (Eq 2.11); λ=0 = penghapusan eksak dari graf (Bagian 2.8); lintasan kosong ω₁/ε_d utk i==j (Kode 4.1); luas & kapasitas ×λ (4.1.5); batas pencarian 200.000 (4.1.2); status Tabel 4.7 (`status_code` + `solver_status` terpisah); validasi `invalid_input`.
- [x] Modul BARU `examples/mechanical_guard.py` (Eq 4.1–4.4: h_e SVD, m_e(λ), batas kondisi κ ≥ m·ρ0, identitas Eq 4.7).
- [x] `examples/bound_enhancement.py`: h_e diganti dari fraksi-energi (LAMA) ke SVD (Eq 4.1) — sesuai Tabel 4.4 (batang nol-gaya tetap h_e=1.000000).
- [x] Runner BARU `examples/run_verification.py`: baseline.csv, scenarios.csv, checks.csv, manifest.json, Tabel.tex, models.pdf, ci_by_damage.pdf (kontrak Tabel 4.8).
- [x] `examples/test_ari.py`: uji invariansi digantikan uji KONVERSI SATUAN kN-mm → N-m (4.1.3).
- [x] Seluruh artefak `results/` diregenerasi; dokumentasi (DEFERRED_FINDINGS, audit angka, ARCHITECTURE) diperbarui.

## Verification Results
| Uji | Hasil |
|---|---|
| Tabel 4.3 (e1..e5, RR & CI) | ✅ ≤ 4e-7 — **DF-01 DITUTUP** |
| Tabel 4.1 (+kolom W) / 4.2 / 4.4 / 4.11 | ✅ semua cocok |
| Tabel 4.5 kanonik (ARI 5 / pengaman 8 / gabungan 11; kritis 17; terlewat 14/9/8) | ✅ **cocok persis** |
| run_verification.py checks.csv | ✅ 65/65 |
| mechanical_guard self-test (h_e, Eq 4.4 grid 80/80, Eq 4.7 residual < 3e-14) | ✅ ALL PASS |
| Invariansi konversi satuan (4.1.3) | ✅ ΔARI = 0 (M1) / 2.2e-16 (M3) |

## Status Gate
🟢 **GATE 9 COMPLETED** — kode selaras dengan naskah pada seluruh tingkat kanonik.
➡️ Selanjutnya: regenerasi Tabel.tex ke naskah; paket parametrik §4.2.4 (272 skenario) bila `results/revision/models.json` tersedia.

## Gate 9.1 — Pelengkap paket prototipe (hari yang sama)
- [x] `examples/ari_tutorial.py` (urutan reproduksi Kode 4.2): tutorial rantai penuh contoh dua batang; verifikasi Tabel 4.11 — PASS.
- [x] `examples/run_guard_verification.py` (§4.5.11): uji analitis Eq 4.7 + regresi Tabel 4.3/4.4/4.11 + diagnostik Tabel 4.2/4.5 kanonik → `results/verification/guard_verification.json` (33/33 LULUS).
- [x] Paket parametrik §4.2.4 ditandai `pending_material` (butuh `results/revision/models.json`) — bukan kegagalan.
- [x] `review_checklist.md` & `results/verification/README.md` diperbarui mengikuti status Gate 9.

🟢 **GATE 9.1 COMPLETED** — urutan reproduksi Kode 4.2 kini lengkap (ari_tutorial → run_verification → run_guard_verification).

## Gate 9.2 — Paket parametrik §4.2.4 (16 model) terimplementasi
- [x] `results/revision/models.json` dibuat dari spesifikasi peneliti: 4 grup × 4 konfigurasi = 16 model, 272 gangguan; verifikasi struktur: N=272 ✓, rank-kurang=32 ✓ (12 segitiga + 20 persegi-1-diagonal, semua di λ=0) ✓.
- [x] `run_guard_verification.py` bagian [D]: dua konvensi kritikalitas dilaporkan berdampingan — A (kapasitas state saat itu; konsisten tabel kanonik) dan B (kapasitas asli); `decisions.csv` (+sha256; urutan audit §4.2.3) & `remaining_misses.csv` (§4.2.5).
- [x] Hasil: pengaman diteruskan = 32 ✓; kritis 71/39 **cocok persis draf pada varian B**; hitungan ARI-forward berbeda dari draf (30 vs 17) — angka final diregenerasi dari kode tervalidasi; revisi akhir oleh peneliti.

🟢 **GATE 9.2 COMPLETED** — paket parametrik tersedia lengkap; tidak ada lagi item `pending_material`.

## Gate 9.3 + Gate 10 — status_code, perluasan Tabel.tex, lalu audit naskah revisi
**Date:** 13 Oktober 2026 · **Status:** 🟢 COMPLETED

- [x] Gate 9.3: kolom `status_code` (Tabel 4.7) di `pipeline_output.csv` & `fine_grid_output.csv` (13 kolom kanonik); `Tabel.tex` + reproduksi Tabel 4.2/4.4/4.5-kanonik; `results/revision/forwarded.csv` (52 baris); cek kanonik 68/68; helper `_mag` (dead code) dibuang; `requirements.txt`.
- [x] Gate 10 — **audit naskah revisi 193 hlm** (menggantikan 222 hlm): seluruh klaim naskah tentang paket Gate 9 terverifikasi PERSIS terhadap repo — forwarded 20/22/10; remaining_misses 28 = 23/4/1; 68/68; Tabel 4.6 (30/32/52; 22/0/0; 67/62/45; 50/39/28); RR e1–e5 0.983152316…0.717284621. Cross-check “40 kasus rank” = 8 kanonik + 32 parametrik ✓. Peta penomoran tabel lama→baru dicatat. Catatan atribusi asisten (naskah menyebut OpenAI Codex; jejak repo: qwen.ai[bot] Gate 1–8, AutoClaw Gate 9–9.3) diserahkan sebagai keputusan peneliti.
- [x] Laporan transparansi ditulis ulang (Revisi 2) & dokumen Word diperbarui via GenOffice; rincian audit tersimpan di `results/review_prep/audit_naskah_revisi.md`.

🟢 **GATE 9.3 & GATE 10 COMPLETED** — paket terintegrasi di naskah revisi; seluruh angka terverifikasi silang (nol ketidaksesuaian).


## Gate 12 (W2a–W2d) — Implementasi Solver Multi-Keluarga (S1, S3, S4, S5)
**Date:** 14 Oktober 2026 · **Status:** 🟢 COMPLETED (100% PASS)

- [x] W2a (S1): Elemen balok transversal & lentur (Euler-Bernoulli 2D/1D). Verifikasi lendutan titik pusat simply-supported beam (v = PL^3/48EI, Δ=3.33e-9) & cantilever beam (v = PL^3/3EI, Δ=3.33e-9), reaksi tumpuan, momen, dan deteksi mekanisme rotasi (status 'rank_deficient').
- [x] W2b (S3): Elemen portal bidang (2D plane frame) dengan aksial dan lentur. Verifikasi portal lateral (drift ux1 = 2.023366 mm), transformasi koordinat lokal-global, dan pelepasan sendi momen ujung (moment release Mi = 0 eksis nol), serta mekanisme goyang.
- [x] W2c (S4): Portal bidang berpengaku (braced frame). Verifikasi reduksi drift oleh pengaku diagonal (reduksi 59.56%), transfer gaya geser ke bracing (N = 39.54 kN), dan rasio interaksi aksial-lentur (P-M).
- [x] W2d (S5): Rangka ruang 3D (3D space truss). Verifikasi komponen spasial 3D (ux, uy, uz), simetri perpindahan translasi apex (ux=0, uy=4.78e-11), kesetimbangan vertikal (ΣRz = 10.0 kN, Δ=0), dan deteksi mekanisme kinematik ruang 3D.
- [x] Unified Dispatcher:  mendukung 5 keluarga struktur (S1 Balok, S2 Rangka Batang, S3 Portal Bidang, S4 Portal Berpengaku, S5 Rangka Ruang 3D).
- [x] Berkas baru: , , . Seluruh suite pengujian acceptance LULUS (100% PASS).


## Gate 13 (W2e–W2f) — Pembangkitan Dataset Induk 300 Model & Manifest (5 Keluarga)
**Date:** 14 Oktober 2026 · **Status:** 🟢 COMPLETED (100% OK, 300/300 Lulus Solver)

- [x] W2e: Pembangunan manifest spesifikasi lengkap ( & ). Setiap model memiliki ID unik (S1_001 s.d. S5_060), hash spesifikasi SHA-256 anti-duplikasi, atribut satuan terstandarisasi, kondisi batas, dan rincian pembagian data.
- [x] W2f: Pembangkitan 300 model induk lintas lima keluarga struktur secara deterministik (benih seed = 2026) dengan pembagian partisi naskah Bab 3.9.3:
  * Formula Development (120 model, 24/keluarga)
  * Calibration (60 model, 12/keluarga)
  * Blind Validation (60 model, 12/keluarga)
  * Final Test (60 model, 12/keluarga)
- [x] Verifikasi Kestabilan Solver Utuh: Seluruh 300 model dianalisis secara fisik dengan solver terkait; 300/300 berstatus 'ok' (tanpa mekanisme singular/fiktif).
- [x] Statistik Skenario Gangguan: 1.910 total elemen struktur menghasilkan 7.940 skenario penapisan gangguan tunggal (lambda in {0, 0.25, 0.50, 0.75} + kontrol).
- [x] Artefak baru: ,  s.d. , , , .
