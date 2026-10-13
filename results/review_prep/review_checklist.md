# Checklist Review Manual Disertasi — Diperbarui Gate 9
**Disertasi:** "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening"
**Status per:** 2026-10-13 (Gate 9 — seluruh tingkat kanonik terselaras & terverifikasi otomatis).
Cara pakai: [x] = sudah terverifikasi otomatis oleh kode (bukti: `results/verification/checks.csv`, `results/review_prep/penyelarasan_disertasi_gate9.md`); [ ] = keputusan penulisan peneliti.

## A. Konsistensi Numerik
- [x] Tabel 4.1 cocok dengan solver (`run_verification.py`; Δ < 5e-4; termasuk kolom W = 15.000000/16.956287/86.139610/51.989854)
- [x] Tabel 4.3 cocok SEMUA baris (e1 0.983152316; e2 0.964723707; e5 0.717284621; e3/e4 eksak) — **DF-01 DITUTUP**
- [x] Tabel 4.11 cocok (7/17, 10/17, 21/68, 15/34, kontrol 3/4 & 1/4)
- [x] Tabel 4.2/4.4/4.5 (kanonik) cocok persis — ARI 5 / pengaman 8 / gabungan 11; kritis 17; terlewat 14/9/8
- [x] Identitas Eq 2.17–2.18 terpenuhi untuk SELURUH baris Tabel 4.3 (koreksi: laporan lama "e1/e2 inkonsisten" keliru — U* e1 = 0; e2 = 0.375)
- [ ] Penulisan: salin Tabel.tex regenerasi ke naskah / pastikan tabel manual identik dengan `results/verification/Tabel.tex`

## B. Konsistensi Formula
- [x] Eq 2.5–2.7 (`compute_edge_weights` / `base_weights_of`) — juga didemonstrasikan di `ari_tutorial.py`
- [x] Eq 2.8–2.10 enumerasi ekshaustif (`enumerate_edge_disjoint_paths`; non-greedy §4.8.6)
- [x] Eq 2.11–2.13 — **hipotesis #001 terbukti**: b_jc = komponen reaksi searah kasus beban (Eq 2.12); π_c ternormalisasi (Eq 2.11); a_ic dari F_c
- [x] Eq 2.14–2.18 — λ=0 = penghapusan sisi (eksak); 0<λ≤1 tanpa renormalisasi; terverifikasi Tabel 4.3/4.11
- [x] Guard kinematik — `mechanical_guard.py` sesuai Eq 4.1–4.4 (h_e SVD, m_e(λ), batas κ ≥ m·ρ0, identitas Eq 4.7); Tabel 4.4 tereproduksi — [ ] sinkronkan deskripsi metode naskah (istilah h_e/m_e, bukan proxy rank)

## C. Konsistensi Konfigurasi
- [x] α_k=α_R=0.5; q_e=1; K=2; γ=1; η=0.5; β=0.1 — cocok §4.1.2 (naskah hal. 112–113)
- [x] ε_w=ε_d=1e-9; ε_R=1e-6 kN; baseline_tol=1e-12; batas pencarian **200.000** keadaan (4.1.2)
- [x] Skala per model: M1 15/30; M2 20/40; M3 & M4 20/80 (4.1.2)
- [x] ε_removed = DEPRECATED (tidak dipakai skor) — [ ] tuliskan di naskah: λ=0 dihapus eksak, tanpa regularisasi hapus-total
- [x] Pelemahan fisik = luas DAN kapasitas ×λ (4.1.5) — [ ] cek kalimat metode

## D. Deferred Findings
- [x] #001 (DF-01): SELESAI — b_jc per komponen; tabel tereproduksi ≤ 4e-7 — [ ] tulis paragraf metode + evidence di bab hasil
- [x] #002 (DF-03): SELESAI — invariansi = konversi satuan kN-mm→N-m (4.1.3), ΔARI = 0 — [ ] perbarui klaim §2.6 agar menyebut konversi satuan
- [ ] #003: narasi batas representasi e3/e4 (sudah didukung guard + Tabel 4.4) — pastikan masuk bab diskusi
- [ ] #004a–d: pilih yang masuk naskah (plateau RR; konvensi kontrol; reklasifikasi #007)
- [ ] #005/#006: tetapkan konvensi penomoran (disarankan: naskah 1-based e1..e5/e6; kode id 0-based didokumentasikan di ARCHITECTURE)
- [x] #007: revisi terkonfirmasi — grid halus: semua mekanisme/guard-flip HANYA di λ=0 — [ ] tulis
- [ ] #009–#011: keputusan masuk Bab Hasil (kontrak 336 baris; kunci `lambda_guard_flip`)
- [x] #012: sinkronisasi angka ✅ (`checks.csv` 65/65; koreksi klaim identitas dilakukan)

## E. Bahan Penulisan yang Sudah Siap
- [x] Struktur folder lengkap (`examples/`, `results/verification/`, `results/review_prep/`)
- [x] Dokumentasi per file (docstring: tujuan, section, dependensi)
- [x] Audit angka naskah vs kode (`disertasi_numbers_audit.md` + koreksi Gate 9)
- [x] Deferred findings dengan status (semua kanonik ditutup)
- [x] Artefak visual: 4 PDF kurva Δλ=0.05 + `models.pdf` + `ci_by_damage.pdf`
- [x] Keluaran kontrak Tabel 4.8: `baseline.csv`, `scenarios.csv`, `checks.csv`, `manifest.json`, `Tabel.tex`
- [x] Laporan penyelarasan: `results/review_prep/penyelarasan_disertasi_gate9.md`
- [ ] Paket parametrik §4.2.4 (272 skenario) — MENUNGGU `results/revision/models.json`
- [x] Regresi hijau penuh: test_truss_reference, test_ari, mechanical_guard, kinematic_guard, run_pipeline, fine_grid_runner, curve_extractor, plot_curves, run_verification (65/65), run_guard_verification (33/33), ari_tutorial (exit 0)

## F. Urutan Reproduksi (Kode 4.2 / 4.5.9)
```bash
cd examples
python3 ari_tutorial.py           # tutorial dua batang (analitis Tabel 4.11)
python3 run_verification.py       # verifikasi kanonik penuh (Tabel 4.1–4.5/4.11)
python3 run_guard_verification.py # paket pengaman §4.2 (analitis + regresi + diagnostik)
# lalu: kompilasi naskah (latexmk) di proyek LaTeX Anda memakai Tabel.tex
```
