# Panduan Revisi Akhir Naskah — dari Hasil Penyelarasan Kode (Gate 9.x)
**Tanggal:** 2026-10-13 · Untuk revisi akhir peneliti (sesuai arahan: "saya revisi di akhir").

## A. Revisi numerik wajib (regenerasi dari kode)

1. **Tabel 4.5 paruh parametrik** — struktur & pengaman cocok penuh dengan kode;
   hitungan sisi-ARI berbeda dari draf (draf 17 vs kode 30 pada τ=0.5;
   kritis 71 & tambahan 39 cocok persis pada varian B). Rekomendasi: salin angka
   dari `results/verification/guard_verification.json` (§D) ke naskah; pilih dan
   bekukan **satu** konvensi kritikalitas — A (kapasitas state saat itu; konsisten
   tabel kanonik) atau B (kapasitas asli; cocok draf kritis 71/39) — dan tuliskan
   di metode. Angka ARI-forward diregenerasi dari kode tervalidasi.
2. **Tabel 4.1 / 4.2 / 4.3 / 4.4 / 4.5 (kanonik) / 4.11** — TIDAK perlu diubah;
   semuanya tereproduksi oleh kode (Δ ≤ 4e-7 untuk RR/CI; ≤ 5e-4 untuk Tabel 4.1).
   Gunakan `results/verification/Tabel.tex` (regenerasi) sebagai sumber tabel.
3. **Kasus batas** — nyatakan konvensi ketidaksamaan: "melampaui" = `>` tegas
   (U > 1, d > 2·d0) tanpa toleransi/pembulatan; kasus U = 1.0 atau d = 2·d0
   eksak TIDAK dihitung kritis (mis. M1-e0 @ λ=0.25; P15-e0 @ λ=0).

## B. Revisi istilah/rumus (agar kode ↔ naskah konsisten)

4. **§2.6 invariansi** — gantikan klaim "penskalaan" dengan "invarian terhadap
   konversi satuan menyeluruh (kN-mm → N-m; Bagian 4.1.3)"; penskalaan s saja
   memang mengubah hasil (bukan invariansi formula).
5. **Regularisasi hapus-total** — λ=0 diimplementasikan sebagai PENGHAPUSAN SISI
   eksak (Bagian 2.8); tidak ada ε khusus di skor. Hapus penyebutan ε_removed
   bila ada di kolom konfigurasi.
6. **§4.2.2 h_e** — pastikan rumus tertulis h_e = k_e·a_e·K₀⁻¹·a_eᵀ dengan metode
   SVD baris-U persis seperti Eq 4.1; Tabel 4.4 (h_e = 1.000000 untuk batang
   nol-gaya) sudah konsisten dengan implementasi.
7. **b_jc (Eq 2.12)** — tegaskan frasa "komponen reaksi searah kasus beban c"
   (bukan magnitudo vektor); frasa inilah yang mengunci reproduksi Tabel 4.3.
8. **Penomoran edge** — tetapkan 1-based `e1..e5/e6` di naskah; pemetaan ke id
   kode (0-based) dicatat di `ARCHITECTURE.md`.
9. **Kode status (Tabel 4.7)** — pakai kosakata kanonik (scored, invalid_baseline,
   search_timeout, uncertified, not_forwarded, …); CSV keluaran kini memuat kolom
   `status_code` dan status solver terpisah.

## C. Berkas bukti (siap dilampirkan/dikutip)

- `results/verification/checks.csv` — 68/68 pemeriksaan kanonik LULUS
  (Tabel 4.1–4.5/4.11, Eq 2.19, monotonisitas, diagnostik kanonik).
- `results/verification/baseline.csv`, `scenarios.csv`, `manifest.json`
  (hash sumber + konfigurasi + diagnostik).
- `results/verification/guard_verification.json` — §A–C (kanonik) + §D
  (parametrik: dua konvensi, bandingan draf per metrik).
- `results/revision/{models.json, decisions.csv, remaining_misses.csv, forwarded.csv}`.
- `results/verification/Tabel.tex` — reproduksi Tabel 4.1/4.2/4.3/4.4/4.5 siap tempel.
- `results/review_prep/penyelarasan_disertasi_gate9.md` — laporan pemetaan lengkap.

## D. Yang TIDAK perlu diubah

- Seluruh angka kanonik naskah (paruh pertama Bab 4) — terverifikasi dengan kode.
- Definisi Eq 2.5–2.18 dan 4.1–4.5 — kode sudah disesuaikan ke naskah.
- Struktur bab & daftar tabel — tidak ada perubahan struktur.
