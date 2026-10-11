# Checklist Review Manual Disertasi
**Disertasi:** "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening"
**Disiapkan:** Gate 8 (2026-10-11) — untuk review mendalam oleh peneliti (Harids Irawan).
Cara pakai: centang [ ] → [x] saat item diverifikasi terhadap naskah.

## A. Konsistensi Numerik
- [ ] Tabel 4.1 cocok dengan output solver Gate 1 (`examples/test_truss_reference.py`, deviasi < 5e-4; lihat `disertasi_numbers_audit.md` §Tabel 4.1 — semua ✅ di kode)
- [ ] Tabel 4.3 cocok dengan `results/verification/pipeline_output.csv` λ=0 (tol 1e-6) — ⚠️ e1/e2/e5 DEVIASI (#001), e3/e4 PASS
- [ ] Tabel 4.11 cocok dengan `results/verification/ari_screening.csv` / pipeline_output.csv (rel. tol 1e-6) — ✅ PASS semua
- [ ] Tidak ada angka yang "dibulatkan" di naskah tanpa catatan
- [ ] Putuskan: baris e1/e2 Tabel 4.3 naskah tidak konsisten identitas Eq 2.17–2.18 (CI = 1 − RR·(1−η·U*)) — lihat audit §Catatan internal-naskah

## B. Konsistensi Formula
- [ ] Eq 2.5–2.7 (normalisasi x̂ = x/(x+s), w_e^M = q_e(α_k·k̂ + α_R·R̂)) terimplementasi di `ari_core.compute_edge_weights`
- [ ] Eq 2.8–2.10 (pair score Φ^(K), ranking ω_r) menggunakan EXHAUSTIVE enumeration (`enumerate_edge_disjoint_combinations`; JANGAN greedy — §4.8.6)
- [ ] Eq 2.11–2.13 (agregasi S(G); a_ic dari F_c, b_jc dari reaksi INTAK, β=0.1) — ⚠️ UJI HIPOTESIS #001: apakah b_jc harus dihitung PER KOMPONEN BEBAN c pada model asimetris?
- [ ] Eq 2.14–2.18 (disrupsi TANPA renormalisasi; RR, ARI, CI) terverifikasi via Tabel 4.11
- [ ] Guard margin m_e(λ): definisi kode = rank_drop/ndof_free (proxy eigenvalue-solver); naskah menyebut SVD — sinkronkan definisi & tulis di metode

## C. Konsistensi Konfigurasi
- [ ] α_k = α_R = 0.5 ; q_e = 1 (semua kasus kanonik)
- [ ] K = 2, γ = 1 (ω_r seragam)
- [ ] η = 0.5, β = 0.1
- [ ] ε_w = ε_d = 1e-9, ε_R = 1e-6 kN, baseline_tol = 1e-12
- [ ] ε_removed (konvensi hapus-total λ=0) = 1e-8 — TULISKAN di naskah sebagai parameter
- [ ] Skala per model sesuai Section 4.1.2: M1 s_k=15/s_R=30; M2 20/40; M3 & M4 20/80

## D. Deferred Findings yang Perlu Diputuskan
- [ ] #001: Deviasi Tabel 4.3 e1/e2/e5 — bug vs perbedaan interpretasi? (bukti kurva halus: sistematis; hipotesis kuat: b_jc per komponen beban)
- [ ] #002: Invariansi hanya asimtotik & butuh penskalaan SERENTAK semua parameter bertaraf — dokumentasikan sebagai batasan/formulasi, atau klaim ulang di §2.6?
- [ ] #003: Kasus e3/e4 CI≈0 saat rank turun — sudah dijelaskan sbg batas representasi; pastikan narasi masuk bab diskusi
- [ ] #004a-d: Plateau RR(λ≤0.5), rank-deficiency M4, konvensi kontrol edge-less vs per-edge, exhaustive confirmed — mana yang masuk naskah?
- [ ] #005/#006: Penomoran edge 1-based (naskah) vs 0-based (kode) — tetapkan satu konvensi dan pakai konsisten; klasifikasi guard observasional
- [ ] #007: REVISI — grid halus menunjukkan SEMUA mekanisme/guard-flip HANYA di λ=0; jangan klaim parsial tanpa cek ulang toleransi eigvals
- [ ] #008: Monotonisitas global 0 pelanggaran — layak dikutip sebagai properti numerik
- [ ] #009–#011: Kurva RR/CI, λ_kritis, agregat Gate 7 — apakah masuk Bab Hasil? (catat juga kontrak baris 336 bukan 420, dan kunci JSON `lambda_guard_flip`)
- [ ] #012: Sinkronisasi SELURUH angka naskah ↔ artefak kode (gunakan `disertasi_numbers_audit.md`; selisih > 1e-6 wajib dicatat)

## E. Bahan Penulisan yang Sudah Siap
- [ ] Struktur folder lengkap (`examples/`, `results/verification/`, `results/review_prep/`)
- [ ] Dokumentasi per file (docstring modul: tujuan, gate, referensi section, dependensi)
- [ ] Audit angka naskah vs kode (`results/review_prep/disertasi_numbers_audit.md`)
- [ ] Daftar deferred findings dengan severity + kolom Last Checked (`DEFERRED_FINDINGS.md`)
- [ ] Artefak visual: 4 PDF kurva halus Δλ=0.05 (`results/verification/plots/`)
- [ ] Regresi hijau: test_truss_reference, test_ari, kinematic_guard self-test, run_pipeline, fine_grid_runner, plot_curves, curve_extractor (exit 0)
