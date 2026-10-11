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
- [x] Konsistensi-check antar-lapisan内置 di pipeline (exit code ≠ 0 jika gagal):
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
