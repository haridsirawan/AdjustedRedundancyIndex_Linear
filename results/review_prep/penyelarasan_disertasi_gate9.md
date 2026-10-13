# Penyelarasan Kode dengan Naskah Disertasi — Gate 9
**Tanggal:** 2026-10-13 · **Pelaksana:** AutoClaw (arahan peneliti Harids Irawan)
**Cakupan:** seluruh rantai kanonik Bagian 2.5–2.18 + 4.1 + 4.2 + 4.4/4.5 yang diimplementasikan di `examples/`

> Dokumen ini memetakan: (1) setiap butir naskah → perubahan kode → bukti numerik.
> Sumber naskah: PDF disertasi 222 halaman (main.pdf). Semua angka naskah yang
> dikutip telah diverifikasi langsung dari teks naskah.

---

## 1. Temuan akar masalah DF-01 dan penyelesaiannya (🔴 → ✅)

**Naskah (Eq 2.12):** `B_c = Σ_j |r^(0)_jc|` dan `b_jc = β/|V_T| + (1−β)·|r^(0)_jc|/B_c`
dengan "Untuk setiap komponen beban aktif c ∈ D, bobot simpul dan komponen
dibentuk dari model utuh".

**Interpretasi yang BENAR (terverifikasi dari Tabel 4.3):**
`r^(0)_jc` = **komponen reaksi searah komponen beban c** (bukan magnitudo
vektor reaksi gabungan). Untuk M3 (beban ux=30 kN di C; tumpuan A pin, B roler):
r_{A,ux} = −30, r_{B,ux} = 0 → B_c = 30 → **b = {A: 0.95, B: 0.05}**.

**Interpretasi LAMA kode (salah):** magnitudo vektor reaksi gabungan →
b = {0.577219, 0.422781} → deviasi sistematis Tabel 4.3 (DF-01).

**Bukti reproduksi Tabel 4.3 setelah perbaikan** (toleransi naskah 6 desimal):

| Batang | RR kode | RR naskah | Δ | CI kode | CI naskah | Δ |
|---|---|---|---|---|---|---|
| e1 (AB) | 0.983152316 | 0.983152 | +3.2e-7 | 0.016847684 | 0.016848 | −3.2e-7 |
| e2 (BC) | 0.964723707 | 0.964724 | −2.9e-7 | 0.216161986 | 0.216162 | −1.4e-8 |
| e3 (CD) | 1.000000000 | 1.000000 | 0 | 0.000000000 | 0.000000 | ~1e-16 |
| e4 (DA) | 1.000000000 | 1.000000 | 0 | 0.000000000 | 0.000000 | 0 |
| e5 (AC) | 0.717284621 | 0.717285 | −3.8e-7 | 0.472914184 | 0.472914 | +1.8e-7 |

**Koreksi audit lama:** klaim Gate 8 "baris e1/e2 tidak memenuhi identitas
CI = 1 − RR·(1−ηU*)" adalah KELIRU. Dengan U* yang benar — e1: D_e ≈ 0
(zero-force) → U* = 0; e2: 30/80 = 0.375; e5: 42.4264/80 = 0.530330 — identitas
terpenuhi persis untuk kelima baris (mis. e1: 1 − 0.983152·1 = 0.016848 ✓).

## 2. Daftar perubahan kode (per butir naskah)

| # | Butir naskah | Ref | Perubahan kode | Bukti |
|---|---|---|---|---|
| 1 | `r^(0)_jc` = komponen reaksi searah kasus c; b_jc per kasus | Eq 2.12 | `ari_core._case_reaction_component` + `_prepare_cases`: reaksi diambil per komponen arah, kasus 1-solve dipakai ulang (superposisi) | Tabel 4.3 + b={0.95,0.05} |
| 2 | Kasus beban c = **komponen arah** (bukan per simpul); F_c = Σ_i |f_ic| | Bag. 2.7 | `_load_cases` dikelompokkan per arah (ux/uy/uz) atas seluruh simpul beban | model 1-komponen kanonik tidak berubah; umum benar |
| 3 | π_c = (F_c/f_c,ref)/Σ_h(...) **dinormalisasi** | Eq 2.11 | `_prepare_cases` menghitung π_c; bobot agregat Σ=1 (sesuai 4.5.8 "jumlah bobotnya satu") | regresi tidak berubah (1 kasus) |
| 4 | B_c = 0 → b_jc = 1/\|V_T\| | Eq 2.12 | cabang khusus ditambahkan | kode |
| 5 | λ=0: "kehilangan lengkap dilakukan dengan **menghapus sisi**" | Bag. 2.8 | `compute_graph_score`: edge λ=0 **dikeluarkan dari enumerasi lintasan** (bukan cost 1/ε lama); `eps_removed` DEPRECATED | nilai Tabel 4.3/4.11 tidak berubah (setara limit) |
| 6 | Simpul dibebani-dan-ditumpu: satu lintasan kosong, kontribusi ω₁/ε_d | Bag. 2.7 + Kode 4.1 | `compute_pair_score`: cabang `source == target` → ω₁/ε_d (dulu 0) + audit `empty_path_used` | pseudocode 4.5.3 |
| 7 | Pelemahan fisik: luas **dan kapasitas** × λ | Bag. 4.1.5 | `_apply_stiffness_multiplier` menskalakan `capacities` juga | respons acuan diagnostik |
| 8 | Batas pencarian 200.000 keadaan (+ batas waktu opsional) | Bag. 4.1.2 | `MAX_SEARCH_NODES=200_000`; `max_search_time_s` (default None); status `search_timeout` | kode |
| 9 | Kode status operasional | Tabel 4.7 | properti `status_code` (scored/invalid_baseline/search_timeout/uncertified) + field **terpisah** `solver_status` | checks.csv |
| 10 | Validasi masukan | 4.5.6/4.5.7 | `invalid_input` menolak elemen/simpul/kapasitas/beban tidak sah | kode |
| 11 | **h_e = k_e a_e K₀⁻¹ a_eᵀ** (SVD baris-U) — bukan fraksi energi | Eq 4.1–4.2, 4.2.2 | modul baru `mechanical_guard.py` (sumber tunggal); `bound_enhancement.py` diubah memakainya | Tabel 4.4: e3/e4 h=1.000000, m≈0 |
| 12 | m_e(λ)=1−(1−λ)h_e; batas κ ≥ m·ρ0; margin 1e-8; rank 1e-10 | Eq 4.2–4.4 | `MechanicalGuard.margin/guard_flag`; identitas Eq 4.7 diverifikasi (residual < 3e-14) | self-test 15/15 PASS |
| 13 | Invariansi = **konversi satuan** (kN-mm → N-m), bukan skala-s saja | Bag. 2.6/4.1.3 | uji [4] diganti uji konversi menyeluruh (E, A, L, beban, kapasitas, s_k, s_R, ε_R) | ΔARI = 0 (M1) / 2.2e-16 (M3) |

## 3. Validasi menyeluruh vs tabel naskah

| Tabel naskah | Isi | Hasil |
|---|---|---|
| Tabel 4.1 | 4 model utuh (u_max, U_max, W) | ✅ 4/4 model, Δ < 5e-4 (termasuk kolom W: 15.000000 / 16.956287 / 86.139610 / 51.989854) |
| Tabel 4.2 | Status gangguan 64 skenario (rank kurang 3+5) | ✅ rank-turun = 8 (3 M2 + 5 M3) |
| Tabel 4.3 | RR/CI persegi satu diagonal | ✅ 5/5 baris ≤ 4e-7 |
| Tabel 4.4 | Regresi e3/e4 (h_e=1.000000, m_e≈1e-16, rank 4/5) | ✅ 8/8 |
| Tabel 4.5 (kanonik) | Diagnostik τ=0.5: ARI diteruskan **5**, pengaman **8**, gabungan **11**; kritis 17; terlewat 14/9/8 | ✅ **cocok persis** |
| Tabel 4.11 | Dua batang paralel (limit ε→0) | ✅ 7/17, 10/17, kontrol 3/4 & 1/4 |
| Eq 2.19 | Kontrol λ=1: RR=1 eksak, CI=η·U* | ✅ 16/16 edge |
| Monotonisitas RR(λ) | 16 edge × grid {1,.75,.5,.25,0} | ✅ 0 pelanggaran |

**Runner bukti:** `examples/run_verification.py` → **65/65 pemeriksaan LULUS**
(keluaran: `baseline.csv`, `scenarios.csv`, `checks.csv`, `manifest.json`,
`Tabel.tex`, `models.pdf`, `ci_by_damage.pdf` — kontrak Tabel 4.8).
Regresi lain: `test_ari.py` (semua blok PASS), `run_pipeline.py` (PASS),
`mechanical_guard.py` self-test (ALL PASS), `kinematic_guard.py` (PASS),
`test_bound_enhancement.py` (ALL PASS), `test_leakage_audit.py` (PASS),
`test_truss_reference.py` (PASS).

## 4. Catatan & tindak lanjut

1. **Provenance naskah:** naskah menyebut tabel 4.1–4.5 "dihasilkan langsung oleh
   skrip verifikasi" (4.1.7). Kini seluruh angka kanonik tereproduksi oleh repo —
   naskah dan kode konsisten penuh pada tingkat kanonik (6 desimal).
2. **Paket parametrik Tabel 4.5 (272 skenario)** belum direproduksi (butuh 16 model
   parametrik §4.2.4 + `results/revision/models.json` — belum ada di repo).
3. `results/review_prep/review_checklist.md` perlu diperbarui mengikuti status baru
   (DF-01 ditutup); audit angka naskah telah dikoreksi di `disertasi_numbers_audit.md`.
4. `eps_removed` (konfigurasi lama) tidak lagi dipakai untuk skor — dipertahankan
   hanya agar berkas konfigurasi lama tetap dapat dimuat.
5. `bound_enhancement.py` (§4.4, bound praanalisis) kini memakai h_e SVD yang benar;
   angka diagnostik kanonik (Tabel 4.5) sudah konsisten dengan definisi baru ini.
