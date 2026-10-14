# Diagnosa 28 Kasus Kritis Terlewat + Evaluasi Kandidat Kebijakan (W1)

**Status:** analisis selesai — keputusan kebijakan menunggu peneliti. Skrip ini tidak mengubah paket.

## 1. Pencirian 28 kasus (`remaining_misses.csv`, varian B — kritis 71)

- Sebab: +perpindahan 23; utilisasi 4; utilisasi+perpindahan 1
- λ: 0.0→19, 0.25→9 — **tidak ada** di λ≥0,5.
- CI: rentang 0.0743 – 0.4978 (median 0.2976) — **semua < 0,5**.
- Semua **tanpa kehilangan rank** (terverifikasi); model tersebar di 13 model
  (terbanyak: P14 4×, P09 3×, P10 3×, P11 3×).
- Pemusatan tematik: 4 kasus "utilisasi" seluruhnya pada P14_tripod (kaki e1/e2), plus
  P16_tripod (utilisasi+perpindahan).

## 2. Evaluasi kandidat aturan praanalisis (aditif; informasi λ & CI saja)

Kolom "Tambahan" = penerusan ekstra terhadap kebijakan sekarang (52). Recall = cakupan
kasus kritis (71); Reduksi = 1 − diteruskan/272.

| Kandidat | Diteruskan | Tambahan | Tertangkap | Sisa | Recall | Reduksi |
|---|---|---|---|---|---|---|
| P0  Kebijakan sekarang (ARI τ=0,5 ∪ pengaman) | 52 | +0 | 0/28 | 28 | 60.6% | 80.9% |
| P1  + λ=0 semua diteruskan | 84 | +32 | 19/28 | 9 | 87.3% | 69.1% |
| P2  + (λ=0 & CI>0,35) | 58 | +6 | 6/28 | 22 | 69.0% | 78.7% |
| P3  + (λ=0 & CI>0,25) | 62 | +10 | 9/28 | 19 | 73.2% | 77.2% |
| P4  + (λ≤0,25 & CI>0,40) | 64 | +12 | 8/28 | 20 | 71.8% | 76.5% |
| P5  + (λ≤0,25 & CI>0,35) | 70 | +18 | 12/28 | 16 | 77.5% | 74.3% |
| P6  + (λ=0 | CI>0,45) | 98 | +46 | 22/28 | 6 | 91.5% | 64.0% |
| P7  ARI τ=0,45 ∪ pengaman | 69 | +17 | 6/28 | 22 | 69.0% | 74.6% |

## 3. Bacaan hasil

1. **Menurunkan ambang τ saja tidak efisien:** kasus terlewat terbesar ber-CI 0,498,
   sehingga penurunan ambang menambah banyak penerusan untuk sedikit tangkapan
   (P7 τ=0,45: +17 penerusan hanya menangkap 6/28).
2. **Aturan λ=0 memberi lompatan cakupan terbesar di antara aturan sederhana**
   (+32 penerusan → 19/28; sisa 9). Rasio tangkapan-terhadap-biaya tertinggi ada di
   P2/P3 (λ=0 & CI>0,35/0,25: +6→6 dan +10→9), tetapi cakupan absolutnya lebih kecil.
3. **Tidak ada aturan berbasis λ/CI yang menangkap seluruh 28** — kasus sisa membutuhkan
   sinyal berorientasi kapasitas/perpindahan (jalur pengayaan §4.4), bukan sekadar ambang.
4. Semua kandidat **tidak mengubah skor ARI** dan tetap memenuhi aturan "tanpa label
   evaluasi" (informasi λ/CI tersedia sebelum inferensi).

## 4. Rekomendasi (keputusan peneliti)

- Jika prioritas = menutup kegagalan mekanisme-level: adopsi P1 (λ=0) sebagai *lapisan
  kehati-hatian* dan dokumentasikan biaya reduksinya; atau P2/P5 bila ingin biaya kecil.
- Jika prioritas = menjaga reduksi: pertahankan kebijakan sekarang dan letakkan 28 kasus
  sebagai batas terukur (sesuai §4.9.5) sampai pengayaan §4.4 tervalidasi.
- Langkah riset lanjut (sinyal baru): uji batas redistribusi gaya / pembesaran perpindahan
  dari model utuh (§4.4.3–4.4.4) pada 28 kasus ini sebagai set uji tetap.

## Lampiran — 28 kasus (urut CI)

| Model | Elemen | λ | CI | Sebab |
|---|---|---|---|---|
| P03_triangle_400x700 | e2 | 0.25 | 0.497806 | +perpindahan |
| P08_sq1d_1000x1000_two_loads | e5 | 0.25 | 0.490197 | +perpindahan |
| P05_sq1d_1000x1000 | e5 | 0.25 | 0.472914 | +perpindahan |
| P10_sq2d_1200x800 | e5 | 0.0 | 0.463485 | +perpindahan |
| P11_sq2d_800x1200 | e5 | 0.0 | 0.456911 | +perpindahan |
| P16_tripod_1000x1000_two_loads | e2 | 0.0 | 0.456709 | utilisasi+perpindahan |
| P02_triangle_600x800 | e3 | 0.25 | 0.440375 | +perpindahan |
| P16_tripod_1000x1000_two_loads | e2 | 0.25 | 0.402504 | +perpindahan |
| P09_sq2d_1000x1000 | e5 | 0.0 | 0.393236 | +perpindahan |
| P07_sq1d_800x1200 | e2 | 0.25 | 0.390828 | +perpindahan |
| P15_tripod_800x1200 | e1 | 0.0 | 0.387328 | +perpindahan |
| P15_tripod_800x1200 | e2 | 0.0 | 0.387328 | +perpindahan |
| P12_sq2d_1000x1000_two_loads | e5 | 0.0 | 0.331900 | +perpindahan |
| P13_tripod_1000x1000 | e1 | 0.0 | 0.297591 | +perpindahan |
| P13_tripod_1000x1000 | e2 | 0.0 | 0.297591 | +perpindahan |
| P08_sq1d_1000x1000_two_loads | e2 | 0.25 | 0.265404 | +perpindahan |
| P14_tripod_1200x800 | e1 | 0.0 | 0.247887 | utilisasi |
| P14_tripod_1200x800 | e2 | 0.0 | 0.247887 | utilisasi |
| P11_sq2d_800x1200 | e2 | 0.0 | 0.218948 | +perpindahan |
| P14_tripod_1200x800 | e1 | 0.25 | 0.218685 | utilisasi |
| P14_tripod_1200x800 | e2 | 0.25 | 0.218685 | utilisasi |
| P11_sq2d_800x1200 | e4 | 0.0 | 0.169179 | +perpindahan |
| P10_sq2d_1200x800 | e2 | 0.0 | 0.165975 | +perpindahan |
| P12_sq2d_1000x1000_two_loads | e2 | 0.0 | 0.146125 | +perpindahan |
| P09_sq2d_1000x1000 | e2 | 0.0 | 0.129509 | +perpindahan |
| P12_sq2d_1000x1000_two_loads | e1 | 0.0 | 0.113905 | +perpindahan |
| P10_sq2d_1200x800 | e4 | 0.0 | 0.074469 | +perpindahan |
| P09_sq2d_1000x1000 | e4 | 0.0 | 0.074334 | +perpindahan |
