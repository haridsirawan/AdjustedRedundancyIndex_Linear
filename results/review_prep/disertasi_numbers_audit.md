# Audit Angka Naskah vs Output Kode
**Disertasi:** "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening"
**Tanggal audit:** 2026-10-11 (Gate 8 — Review Ringan)
**Sumber data kode (aktual, bukan generate ulang):**
- Tabel 4.1   → `truss_reference.solve_model` (rerun Gate 1; kode identik commit `71b1160`)
- Tabel 4.3   → `results/verification/pipeline_output.csv` (λ=0.00)
- Tabel 4.11  → `results/verification/pipeline_output.csv` (λ=0.00 & kontrol λ=1.00)
**Toleransi:** absolut 5e-4 (Tabel 4.1); relatif 1e-6 (Tabel 4.11, limit ε→0).

---

## Tabel 4.1 — Intact Model Response

| Model | umax (naskah) | umax (kode) | Selisih | Umax (naskah) | Umax (kode) | Selisih | Status |
|-------|---------------|-------------|---------|---------------|-------------|---------|--------|
| Parallel bars | 1.000000 | 1.000000 | 0 | 0.500000 | 0.500000 | 0 | ✅ |
| Triangle | 1.154460 | 1.154460 | <1e-6 | 0.442218 | 0.442218 | <1e-6 | ✅ |
| One diagonal | 5.935311 | 5.935311 | <1e-6 | 0.530330 | 0.530330 | <1e-6 | ✅ |
| Two diagonals | 3.582277 | 3.582277 | <1e-6 | 0.320083 | 0.320083 | <1e-6 | ✅ |

Konvensi yang harus ditulis di naskah: umax = norm resultan per node √(ux²+uy²); M2 wajib menyertakan tie chord (tanpa chord = mekanisme/rank-deficient).

---

## Tabel 4.3 — Square with One Diagonal (λ=0)

Pemetaan label naskah ↔ edge-id kode (0-based): e1≡id0 (AB), e2≡id1 (BC), e3≡id2 (CD), e4≡id3 (DA), e5≡id4 (AC/diagonal).

| Element | RR (naskah) | RR (kode) | CI (naskah) | CI (kode) | Status |
|---------|-------------|-----------|-------------|-----------|--------|
| e1 (AB) | 0.983152 | 0.859874 | 0.016848 | 0.140126 | ❌ DEFERRED (#001) |
| e2 (BC) | 0.964724 | 0.706600 | 0.216162 | 0.425887 | ❌ DEFERRED (#001) |
| e3 (CD) | 1.000000 | 1.000000 | 0.000000 | 0.000000 | ✅ (kasus kritis) |
| e4 (DA) | 1.000000 | 1.000000 | 0.000000 | 0.000000 | ✅ (kasus kritis) |
| e5 (AC) | 0.717285 | 0.791758 | 0.472914 | 0.418189 | ❌ DEFERRED (#001) |

Catatan internal-naskah (temuan baru Gate 8): baris e1/e2 Tabel 4.3 TIDAK konsisten dengan identitas ARI = RR·(1−η·U*), CI = 1−ARI (η=0.5 ⇒ CI ≤ RR dan RR−CI ≥ 0 dengan selisih bertanda tertentu): untuk e1, RR−CI = 0.966304; untuk e2, RR−CI = 0.748562 — keduanya mengimplikasikan nilai U* yang berbeda dari baris lain dan tidak cocok dengan gaya awal solver. Kemungkinan ada dua konvensi CI yang tercampur di naskah — perlu klarifikasi definisi saat review.

Bukti kurva halus (fine grid Δλ=0.05, `results/verification/plots/curve_M3_square_one_diag.pdf`): deviasi #001 bersifat **sistematis** — seluruh kurva RR(λ) id0/id1/id4 bergeser terhadap target tabel di semua λ (bukan artefak lokal di satu titik). Detail di DEFERRED_FINDINGS.md #001 sub-bab "Evidence from Gate 6 Curves".

---

## Tabel 4.11 — Two Parallel Bars (limit ε→0; kode ε=1e-9, tol rel. 1e-6)

| Condition | RR (naskah) | RR (kode) | ARI (naskah) | ARI (kode) | CI (naskah) | CI (kode) | Status |
|-----------|-------------|-----------|--------------|------------|-------------|-----------|--------|
| Intact control (λ=1) | 1 | 1.0 (eksak) | 3/4 = 0.75 | 0.750000 | 1/4 = 0.25 | 0.250000 | ✅ |
| Bar 0 removed (λ=0) | 7/17 = 0.411765 | 0.411764716 | 21/68 = 0.308824 | 0.308824 | 47/68 = 0.691176 | 0.691176 | ✅ |
| Bar 1 removed (λ=0) | 10/17 = 0.588235 | 0.588235304 | 15/34 = 0.441176 | 0.441176 | 19/34 = 0.558824 | 0.558824 | ✅ |

Seluruh rel.err ≤ 3e-8 ≪ 1e-6. Kontrol λ=1: RR=1 eksak, CI=η·U*=0.25 (bukan 0) sesuai kontrak.

---

## Konsistensi antar-artefak (diperiksa otomatis, Gate 8)

| Cek | Hasil |
|-----|-------|
| fine_grid_output.csv (336 baris) vs pipeline_output.csv pada λ irisan {0, .25, .5, .75, 1} | 0 mismatch > 1e-9 ✅ |
| critical_lambdas.json memakai kunci `lambda_guard_flip` (bukan `lambda_crit_guard_flip`) — spot-check manual: M3-e2 guard-flip @ λ=0.00, margin_m 0→0.125, konsisten definisi operasional #009 ✅ |
| Baseline S(G_M): M1=0.485714, M2=0.379544, M3=M4=0.360252 — sama di ari_screening.csv, ari_screening_full.csv, pipeline/fine CSV ✅ |
| Kolom ARI pada pipeline_output.csv utk M3-e2/e3 = 1.0 (RR·(1−η·0), U*=0) — konsisten Eq 2.17 ✅ |

---

## UPDATE GATE 9 (2026-10-13) — SELURUH TEMUAN DITUTUP

**Akar masalah DF-01:** b_jc (Eq 2.12) memakai **komponen reaksi searah kasus beban** (bukan magnitudo vektor reaksi gabungan). Kode lama b={0.577219, 0.422781}; kode benar b={A: 0.95, B: 0.05}.

| Element | RR (naskah) | RR (kode baru) | CI (naskah) | CI (kode baru) | Status |
|---------|-------------|----------------|-------------|----------------|--------|
| e1 (AB) | 0.983152 | 0.983152316 | 0.016848 | 0.016847684 | ✅ |
| e2 (BC) | 0.964724 | 0.964723707 | 0.216162 | 0.216161986 | ✅ |
| e3 (CD) | 1.000000 | 1.000000000 | 0.000000 | 0.000000000 | ✅ |
| e4 (DA) | 1.000000 | 1.000000000 | 0.000000 | 0.000000000 | ✅ |
| e5 (AC) | 0.717285 | 0.717284621 | 0.472914 | 0.472914184 | ✅ |

**Koreksi catatan audit lama:** tuduhan "baris e1/e2 tidak konsisten dengan identitas ARI = RR(1−ηU*)" adalah KELIRU. Dengan U* benar (e1: |D|≈0 → U*=0; e2: 30/80=0.375), identitas terpenuhi: e1: CI = 1−0.983152 = 0.016848 ✓; e2: CI = 1−0.964724×0.8125 = 0.216162 ✓.

**Diagnostik Tabel 4.5 kanonik (reproduksi):** kritis 17; ARI diteruskan 5 (terlewat 14/17); pengaman diteruskan 8 (terlewat 9/17); gabungan diteruskan 11 (terlewat 8/17) — **cocok persis dengan naskah**.

Bukti lengkap: `results/review_prep/penyelarasan_disertasi_gate9.md` + `results/verification/checks.csv` (65/65 LULUS).

## Ringkasan status angka
- **Cocok dengan naskah:** semua Tabel 4.1; semua Tabel 4.11; kasus kritis e3/e4 Tabel 4.3.
- **Tidak cocok / perlu keputusan peneliti:** e1, e2, e5 Tabel 4.3 (#001 — hipotesis kuat: bobot tumpuan b_jc per komponen beban c pada model asimetris); inkonsistensi internal baris e1/e2 naskah thd identitas Eq 2.17–2.18 (baru ditemukan Gate 8).
- Tidak ada angka yang diubah/diimputasi di file ini — semuanya disalin dari artefak hasil eksekusi aktual.
