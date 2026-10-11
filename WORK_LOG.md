# WORK LOG — ARI for Mechanics-Based Screening

Disertasi: *Adjusted Redundancy Index (ARI) for Mechanics-Based Screening*
Satuan proyek: Gaya = kN, Panjang = mm, E = 200 kN/mm².

---

## Sesi 1 — Fondasi: Model Kanonik & Solver Referensi (Bagian 3.1.3, 4.1.2, 4.1.3, 4.5.7)

**Tanggal:** 2026-10-11

### Tujuan
Membangun fondasi paling dasar disertasi:
1. Definisi mesin-baca untuk 4 model kanonik verifikasi (Bagian 4.1.2).
2. Solver referensi elemen hingga untuk batang aksial 1D / truss planar 2D
   (Bagian 4.1.3 & 4.5.7) yang mereproduksi **Tabel 4.1 (Intact-Model Response)**.

### File yang dibuat
| File | Isi |
|---|---|
| `examples/verification_models.json` | Definisi 4 model kanonik: M1 dua batang paralel 1D; M2 truss segitiga planar; M3 persegi + 1 diagonal; M4 persegi + 2 diagonal (diagonal TIDAK berbagi simpul tengah). Termasuk material (E = 200 kN/mm²), area, kapasitas, perletakan, beban, dan `expected_results` Tabel 4.1. |
| `examples/truss_reference.py` | Solver referensi: perakitan K global, kondisi batas zero-displacement (pinned / roller_vertical / roller_horizontal), rank-check `K_ff` via `numpy.linalg.eigvals` (toleransi relatif 1e-10 terhadap eigenvalue terbesar), penyelesaian `K_ff u_f = p_f` via `numpy.linalg.solve` (**tanpa pseudoinverse**; rank-deficient → status `"rank_deficient"`), gaya batang, utilisasi U = \|N\|/Capacity, umax (norm resultant perpindahan node), dan regangan energi W = Σ N²L/(2EA). |
| `examples/test_truss_reference.py` | Skrip uji coba: menjalankan solver pada ke-4 model, membandingkan dengan Tabel 4.1 (toleransi 5e-4), plus uji penolakan mekanisme rank-deficient. |

### Keputusan teknis penting
- **Definisi `umax`**: norm resultan perpindahan maksimum per node
  (√(ux²+uy²)), BUKAN komponen tunggal. Ini adalah-satu-satunya definisi yang
  mereproduksi seluruh baris Tabel 4.1 secara konsisten (mis. M3: komponen
  ux = 5.742641 mm vs resultan = 5.935311 mm ✓).
- **Model M2** menyertakan batang bawah (tie chord) (0,0)-(1000,0); tanpanya
  struktur menjadi mekanisme di bawah beban vertikal.
- **Roller "vertical only"** = restraint uy=0 (menahan gaya vertikal), sesuai
  hasil verifikasi numerik terhadap Tabel 4.1.

### Hasil verifikasi (Tabel 4.1)
| Model | umax [mm] (solver / target) | Umax [-] (solver / target) | Status |
|---|---|---|---|
| Parallel bars (M1) | 1.000000 / 1.000000 | 0.500000 / 0.500000 | PASS |
| Triangle (M2) | 1.154460 / 1.154460 | 0.442218 / 0.442218 | PASS |
| One diagonal (M3) | 5.935311 / 5.935311 | 0.530330 / 0.530330 | PASS |
| Two diagonals (M4) | 3.582277 / 3.582277 | 0.320083 / 0.320083 | PASS |

Deviasi maksimum < 5×10⁻⁷. Uji rank-deficient (mekanisme) juga PASS: solver
menolak solusi dan mencatat status `"rank_deficient"` tanpa pseudoinverse.

### Status
✅ **SELESAI** — Kriteria penerimaan terpenuhi seluruhnya.

### Langkah berikutnya (rencana)
- Skenario pemutusan elemen (element-removal / damage cases) per Bagian 4.2.
- Formulasi indeks redundansi & penyesuaian (ARI) berdasarkan respons
  pasca-pemutusan (utilisasi, perpindahan, regangan energi).
- Matriks verifikasi lengkap (Tabel 4.2 dst.) dan kalibrasi ambang screening.
