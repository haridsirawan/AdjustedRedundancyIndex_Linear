# results/revision — Paket Parametrik §4.2.4 (16 model)

**Status:** ✅ terimplementasi (Gate 9.2, 2026-10-13). Spesifikasi model dari peneliti
(2026-10-13). 16 model × (3–6 elemen) × 4 λ ∈ {0, .25, .5, .75} = **272 gangguan**;
8+12 = **32 kasus rank-kurang** (semua di λ=0: 12 segitiga + 20 persegi-1-diagonal).

## Berkas

| File | Isi |
|---|---|
| `models.json` | 16 model parametrik (4 grup × 4 konfigurasi) + `meta.targets_tabel_45` (angka draf peneliti) + konvensi tumpuan & asumsi skala |
| `decisions.csv` | Keputusan penerusan per skenario (CI, status, `ari_forward`, `m_s`, `guard_flag`) — disimpan **sebelum** respons acuan dihitung (kontrak §4.2.3); sha256 tercatat di `guard_verification.json` |
| `remaining_misses.csv` | Kasus kritis yang TIDAK diteruskan kebijakan gabungan (28 baris; varian B — kritis 71) |

## Hasil (juga di `results/verification/guard_verification.json` §D)

| Metrik | Draf Tabel 4.5 | Kode: varian A (kapasitas state saat itu, §4.1.5) | Kode: varian B (kapasitas asli) |
|---|---|---|---|
| N | 272 | **272 ✅** | 272 ✅ |
| Rank-kurang | 32 | **32 ✅** | 32 ✅ |
| Kritis (tambahan) | 71 (39) | 94 (62) | **71 ✅ (39 ✅)** |
| ARI diteruskan | 17 | 30 | 30 |
| Pengaman diteruskan | 32 | **32 ✅** | 32 ✅ |
| Gabungan diteruskan | 41 | 52 | 52 |
| Rank terlewat ARI/pengaman/gabungan | 24/0/0 | 22/**0 ✅**/**0 ✅** | 22/0/0 |
| Kritis terlewat ARI/pengaman/gabungan | 54/39/30 | 67/62/45 | 50/**39 ✅**/28 |

## Catatan rekonsiliasi (untuk revisi akhir)

1. **Struktur & pengaman cocok penuh** dengan draf: N, jumlah rank-kurang, jumlah
   diteruskan pengaman, rank-terlewat pengaman/gabungan = 0.
2. **Kriteria kritis cocok penuh pada varian B** (kapasitas asli): 71/39 — persis draf.
3. **Hitungan ARI-forward berbeda dari draf** (30 vs 17). Seluruh angka di sini
   diregenerasi dari kode tervalidasi penuh terhadap naskah (Tabel 4.1–4.5/4.11
   kanonik; lihat `results/review_prep/penyelarasan_disertasi_gate9.md`). Draf
   kemungkinan memakai akuntansi lama — **angka final direvisi peneliti di akhir**.
4. Konvensi A dipertahankan sebagai primer karena konsisten dengan tabel kanonik
   naskah yang tervalidasi (Tabel 4.5 kanonik = A).

## Regenerasi
```bash
python3 examples/run_guard_verification.py   # bagian [D]
```
