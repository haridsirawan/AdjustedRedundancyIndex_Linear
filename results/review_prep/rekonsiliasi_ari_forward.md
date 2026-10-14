# Rekonsiliasi "Diteruskan": draf 17/32/41 vs kode 30/32/52 (K6)

**Status:** selesai — selisih terlokalisasi dan terjelaskan; **nol tindakan naskah** selain
catatan yang sudah ada (naskah revisi telah memakai angka kode).

## 1. Sumber angka

- **Draf (angka peneliti, pra-kode):** naskah lama Tabel 3.1/3.2 + `models.json → meta.targets_tabel_45`.
- **Kode tervalidasi:** `results/verification/guard_verification.json` §D + `results/revision/`
  (`decisions.csv` 272 baris, `forwarded.csv` 52, `remaining_misses.csv` 28).
- Semantik kolom "Diteruskan" (kalimat naskah lama): *"41 dari 272 gangguan diteruskan dan
  30 dari 71 kasus kritis masih terlewat"* — jadi = jumlah skenario diteruskan, bukan subset kritis.

## 2. Tabel perbandingan (varian B = kapasitas asli; kritis 71/39)

| Metrik | Draf | Kode (A) | Kode (B) | Cocok |
|---|---|---|---|---|
| N | 272 | 272 | 272 | A+B |
| Rank-kurang | 32 | 32 | 32 | A+B |
| Kritis total / tambahan | 71 / 39 | 94 / 62 | 71 / 39 | B |
| ARI diteruskan | 17 | 30 | 30 | - |
| Pengaman diteruskan | 32 | 32 | 32 | A+B |
| Gabungan diteruskan | 41 | 52 | 52 | - |
| Rank terlewat ARI | 24 | 22 | 22 | - |
| Rank terlewat pengaman / gabungan | 0 / 0 | 0 / 0 | 0 / 0 | A+B |
| Kritis terlewat ARI | 54 | 67 | 50 | - |
| Kritis terlewat pengaman | 39 | 62 | 39 | B |
| Kritis terlewat gabungan | 30 | 45 | 28 | - |

Seluruh **agregat** cocok (N, rank 32, kritis 71/39, rank-terlewat 0, kritis-terlewat pengaman 39).
Selisih **hanya** pada baris ARI dan turunannya (gabungan).

## 3. Dekomposisi set ARI (kode): 30 = 10 + 11 + 9

- **10 rank-kritis** (λ=0, rank turun & kritis)
- **11 kritis-tambahan** (kritis tanpa kehilangan rank)
- **9 nonkritis** (CI > 0,5 tetapi tidak kritis; CI 0,50–0,64)

Implikasi draf (17 = 8 rank + 9 tambahan + 0 nonkritis, dari 24/32 dan 54/71):
selisih 13 = **9 nonkritis + 4 kritis** (2 rank + 2 tambahan).

## 4. Kasus

### 4a. Sembilan nonkritis yang diteruskan kode (semua ber-CI dekat ambang)

| Model | Elemen | λ | CI |
|---|---|---|---|
| P03_triangle_400x700 | e3 | 0.5 | 0.505819 |
| P14_tripod_1200x800 | e3 | 0.75 | 0.530926 |
| P07_sq1d_800x1200 | e5 | 0.75 | 0.536402 |
| P13_tripod_1000x1000 | e3 | 0.25 | 0.558034 |
| P06_sq1d_1200x800 | e5 | 0.5 | 0.564510 |
| P16_tripod_1000x1000_two_loads | e3 | 0.0 | 0.568752 |
| P15_tripod_800x1200 | e3 | 0.0 | 0.585626 |
| P07_sq1d_800x1200 | e5 | 0.5 | 0.606537 |
| P14_tripod_1200x800 | e3 | 0.5 | 0.635844 |

### 4b. Empat kasus kritis bermargin terkecil (kandidat utama penjelas selisih 4)

- Rank margin terkecil: P02_triangle_600x800 e3 (CI 0.559414) dan P06_sq1d_1200x800 e5 (CI 0.564510).
- Tambahan margin terkecil: P04_triangle_500x900 e2/e3 (CI 0.504983) dan P04_triangle_500x900 e2/e3 (CI 0.504983).

Semua selisih berada di pita CI ≈ 0,50–0,57.

### 4c. Daftar lengkap 30 kasus: lihat `rekonsiliasi_ari_forward_kasus.csv`.

## 5. Interpretasi yang didukung bukti

1. **Pengaman identik** (32/32, 0/32, 39/71) — tidak ada selisih sedikit pun di sisi pengaman.
2. **Agregat identik** — penomoran skenario, rank-kurang, dan definisi kritis (varian B) sama persis.
3. **Kanonik identik** — baris kanonik (5/8/11; 14/9/8) cocok penuh draf maupun kode.
4. Selisih **terkurung** pada penerusan ARI di pita CI 0,50–0,57 — kasus batas ambang τ = 0,5.
5. Preseden terdokumentasi: draf lama memang mendahului koreksi Gate 9 (DF-01 b_jc, π_c,
   λ=0 eksak, i==j ω₁/ε_d, kapasitas ×λ) dan koreksi itu mengubah CI tingkat kasus —
   pada kanonik terbukti (Tabel 4.3) dan di sini terlihat sebagai pergeseran margin.

**Kesimpulan:** selisih 17-vs-30 bukan galat komputasi pada kode tervalidasi dan bukan
kesalahan aritmetika pada draf; keduanya adalah **snapshot yang konsisten internal** pada
versi formula berbeda. Angka yang berlaku adalah hasil kode tervalidasi (30/32/52;
kritis-terlewat B 50/39/28; A 67/62/45), yang telah dipakai naskah revisi.

## 6. Rekomendasi

- **K6 ditutup** dengan laporan ini sebagai bukti penutupan (bukan keputusan ilmiah baru).
- Opsional: satu catatan kaki pada tabel hasil — *"Hitungan ARI-forward draf lama (17)
  berasal dari versi pra-koreksi formula; angka berlaku = 30 (kode tervalidasi)."*
- Tidak ada perubahan angka naskah lebih lanjut.
