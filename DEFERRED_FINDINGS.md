# DEFERRED FINDINGS — Gate 2 (Sprint Mode)
**Project:** ARI Disertasi — Adjusted Redundancy Index
**Date:** Sunday, October 11, 2026
**Konvensi:** Setiap temuan dicatat lengkap dengan bukti numerik; perbaikan
ditunda hingga fase detail-after-skeleton. ID = DF-nn.

---

## DF-01 — Deviasi Tabel 4.3 pada e1(AB), e2(BC), e5(AC)
**Status:** 🔴 OPEN (di luar kendali parameter saat ini)
**Model:** M3_square_one_diagonal, skenario hapus-total (λ=0).

| Edge (Tabel 4.3) | RR kode | RR disertasi | CI kode | CI disertasi |
|---|---|---|---|---|
| e1 (AB) | 0.859874 | 0.983152 | 0.140126 | 0.016848 |
| e2 (BC) | 0.706600 | 0.964724 | 0.425887 | 0.216162 |
| e3 (CD) | 1.000000 ✅ | 1.000000 | 0.000000 ✅ | 0.000000 |
| e4 (DA) | 1.000000 ✅ | 1.000000 | 0.000000 ✅ | 0.000000 |
| e5 (AC) | 0.791758 | 0.717285 | 0.418189 | 0.472914 |

**Eksplorasi yang sudah dilakukan (semua TIDAK mereproduksi target):**
1. `eps_removed` sweep 1e-3 … 1e-8 → hasil **identik eksak** untuk semua nilai.
   Bukti: deviasi BUKAN efek regularisasi epsilon.
2. Konvensi edge-dipertahankan-w-0 vs edge-dihapus-fisik → skor identik
   (jalur tak-terbatas tereliminasi oleh ranking ω seragam K=2).
3. Skala s_k/s_R alternatif (rasio 1/2, 1/4, dsb.) → tidak menghasilkan
   triple (RR_e1, RR_e2, RR_e5) = (0.983152, 0.964724, 0.717285).
4. Struktur agregat S(G) kode diverifikasi ANALITIK penuh:
   - b_map = {0: 0.57721, 1: 0.42279} (β=0.1, reaksi utuh R0=√(30²+30²)=42.426, R1=30) ✓
   - Φ(2,0)=0.353553 (=1/(2·√2)), Φ(2,1)=0.369398 (=½(1/4+1/2.1877)) ✓
   - S_base = 0.360252 ✓ ; semua intermediate tercetak di test_ari.py [6].
5. Target 0.983152 ≈ 1 − 1/59.2 dan 0.964724 ≈ 1 − 1/28.2 tidak cocok dengan
   rasio rasional sederhana dari graf ber-bobot w^M mana pun pada topologi M3
   dengan aturan Eq 2.8–2.13 yang dikunci kontrak.

**Hipotesis tersisa (butuh teks disertasi utk ditutup):**
- (H1) Tabel 4.3 dihitung dengan **agregasi π_c multi-komponen**: beban node 2
  dipecah menjadi dua load case (ux=+30 dan uy=0→satu kasus; atau ux & uy
  terpisah dengan F_c per komponen) sehingga a_ic/b_jc berbeda. Catatan:
  komponen uy=30@node2 bernilai NOL di M3 — tetapi jika disertasi memakai
  orientasi beban/penamaan simpul berbeda (mis. beban vertikal), struktur
  bobot a,b berubah total.
- (H2) Penamaan edge Tabel 4.3 bukan AB,BC,CD,DA,AC melainkan urutan lain
  (mis. diagonal = e1). Jika peta (kode e4→disertasi e1) dsb.: RR kode
  {0.8599, 0.7066, 1, 1, 0.7918} vs target {0.9832, 0.9647, 1, 1, 0.7173} —
  tetap tidak ada bijeksi yang cocok (dua nilai ~1 harus memetakan ke
  target <1 selain slot e3/e4).
- (H3) Definisi d^M(p) memakai panjang geometri L_e sebagai pembobot tambahan
  (d = Σ c_e·L_e/L_ref) — belum diuji terhadap tabel.

**Tindakan sprint:** deviasi di-flag `DEVIASI-DEFERRED`, tidak memblokir gate.
Kasus KRITIS penerimaan (e3/e4: rank turun tapi CI≈0) sudah PASS.

---

## DF-02 — Rank-deficiency state terdisrupsi vs skor murni-graf
**Status:** 🟡 DOCUMENTED (keputusan implementasi)
Pada hapus-total M3, SEMUA skenario e0–e4 membuat K_ff rank-deficient
(mekanisme; node 3 lepas / rotasi bebas). Solver Gate 1 menolak tanpa
pseudoinverse. Tabel 4.3 disertasi ternyata TIDAK meng-abstain kasus ini —
skor jalur dihitung murni-graf pada topologi terdisrupsi. Implementasi kini
berstatus `ok_with_rank_deficiency` (peringatan audit, RR/CI tetap dihitung).
Risiko reviewer: interpretasi "struktur sudah mekanisme tapi CI kecil" harus
dijelaskan di bab diskusi (konsisten dgn narasi batas representasi e3/e4).

---

## DF-03 — Invariansi penskalaan: bentuk asimtotik, bukan eksak
**Status:** 🟡 PARTIAL PASS (ambang longgar 5e-3; murni-x10 gagal)
Temuan:
- x10 HANYA (s_k,s_R): ΔARI hingga O(1e0) → jelas TIDAK invarian.
- x10 SERENTAK (s_k,s_R,ε_w,ε_d,ε_R,ε_removed): ΔARI terukur 4.86e-02 (M1),
  1.47e-02 (M3) → TIDAK nol-eksak. Analisis: k̂=x/(x+s) invarian hanya sampai
  koreksi order ε_eff/w (cost 1/(w+ε) vs 1/w). Saat eps→0 limit, deviasi → 0
  secara asimtotik; uji x100/x1000 menurunkan ΔARI sebanding (belum diuji).
- Keputusan formulasi yg harus didokumentasikan: klaim invariansi di Section
  2.6 hanya sah dalam limit ε→0 ATAU bila ε diinterpretasikan bertaraf sama
  dengan atribut (unit-aware regularization). Perlu konfirmasi penulis.

---

## DF-04 — Kontrol utuh (tanpa edge-id) tidak punya U*_e
**Status:** 🟢 RESOLVED (konvensi)
Baris "intact control" Tabel 4.11 (ARI=3/4, CI=1/4) mensyaratkan penalti
U* = 0.5 = Umax model. Untuk skenario edge-less, `compute_ari(disruption=None)`
mengembalikan RR=1, ARI=1, CI=0 (tidak ada edge ⇒ tidak ada utilisasi edge).
Nilai 0.75/0.25 direproduksi lewat kontrol per-edge λ=1 (CI=η·U*_e — PASS)
dan lewat RR×(1−η·Umax_intact) di test. Kontrak "kontrol λ=1: CI=η·U*_e
(bukan 0)" terpenuhi persis.

---

## DF-05 — Cakupan skrining: 64 skenario + 16 kontrol belum dijalankan penuh
**Status:** 🟡 DEFERRED (sprint mode)
Test saat ini menjalankan λ∈{0} (20 baris CSV). Grid penuh λ∈{0,0.25,0.5,0.75,1}
× 16 edge = 80 run ≈ trivial secara komputasi (path search exhaustif pada
graf ≤6 node selesai <10 ms/scenario); akan diaktifkan saat finalisasi Gate 2.
Blok monotonisitas sudah membuktikan lintasan λ tengah berfungsi benar.

---

## DF-06 — Greedy vs exhaustive (Section 4.8.6)
**Status:** 🟢 NO ISSUE
Enumerasi EKSHAUSTIF semua kombinasi jalur edge-disjoint |P|≤K; status
`certified/uncertified` via budget DFS (500k node). Tidak pernah mengembalikan
angka bila pencarian tidak selesai (status uncertified ⇒ RR/ARI/CI = None).
