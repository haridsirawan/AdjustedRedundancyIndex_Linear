# DEFERRED FINDINGS — Gate 2 (Sprint Mode)
**Project:** ARI Disertasi — Adjusted Redundancy Index
**Date:** Sunday, October 11, 2026
**Konvensi:** Setiap temuan dicatat lengkap dengan bukti numerik; perbaikan
ditunda hingga fase detail-after-skeleton. ID = DF-nn, dipetakan ke penomoran Finding #nnn sesuai instruksi peneliti.

---

## DF-01 (Finding #001) — Deviasi Tabel 4.3 pada e1(AB), e2(BC), e5(AC)
**Status:** 🔴 OPEN (di luar kendali parameter saat ini)
**Model:** M3_square_one_diagonal, skenario hapus-total (λ=0).

| Edge (Tabel 4.3) | RR kode | RR disertasi | CI kode | CI disertasi |
|---|---|---|---|---|
| e1 (AB) | 0.859874 | 0.983152 | 0.140126 | 0.016848 |
| e2 (BC) | 0.706600 | 0.964724 | 0.425887 | 0.216162 |
| e3 (CD) | 1.000000 ✅ (→ Finding #003) | 1.000000 | 0.000000 ✅ | 0.000000 |
| e4 (DA) | 1.000000 ✅ (→ Finding #003) | 1.000000 | 0.000000 ✅ | 0.000000 |
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

**Update hipotesis (Gate 5, 2026-10-11):** Dugaan kuat: kesalahan
perhitungan bobot tumpuan (b_jc) **per komponen beban (c)** pada model
asimetris — bukan error regularisasi ε. Bukti pendukung parsial: b_map
kode {0: 0.57721, 1: 0.42279} berasal dari SATU load case gabungan
(f_ux=30, f_uy=0 di node 2); jika disertasi memperlakukan komponen beban
secara terpisah atau memakai reaksi per-case, distribusi b_jc berubah dan
dapat menggeser RR e1/e2/e5 sementara e3/e4 (zero-force) tetap ~1.
Sesuai instruksi sprint: TIDAK ada perubahan formula/parameter; hanya
hipotesis yang dicatat. Investigasi lanjutan dilakukan terpisah.

---

## DF-02 (Finding #004a) — Rank-deficiency state terdisrupsi vs skor murni-graf
**Status:** 🟡 DOCUMENTED (keputusan implementasi)
Pada hapus-total M3, SEMUA skenario e0–e4 membuat K_ff rank-deficient
(mekanisme; node 3 lepas / rotasi bebas). Solver Gate 1 menolak tanpa
pseudoinverse. Tabel 4.3 disertasi ternyata TIDAK meng-abstain kasus ini —
skor jalur dihitung murni-graf pada topologi terdisrupsi. Implementasi kini
berstatus `ok_with_rank_deficiency` (peringatan audit, RR/CI tetap dihitung).
Risiko reviewer: interpretasi "struktur sudah mekanisme tapi CI kecil" harus
dijelaskan di bab diskusi (konsisten dgn narasi batas representasi e3/e4).

---

## DF-03 (Finding #002) — Invariansi penskalaan: bentuk asimtotik, bukan eksak
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

## DF-04 (Finding #004b) — Kontrol utuh (tanpa edge-id) tidak punya U*_e
**Status:** 🟢 RESOLVED (konvensi)
Baris "intact control" Tabel 4.11 (ARI=3/4, CI=1/4) mensyaratkan penalti
U* = 0.5 = Umax model. Untuk skenario edge-less, `compute_ari(disruption=None)`
mengembalikan RR=1, ARI=1, CI=0 (tidak ada edge ⇒ tidak ada utilisasi edge).
Nilai 0.75/0.25 direproduksi lewat kontrol per-edge λ=1 (CI=η·U*_e — PASS)
dan lewat RR×(1−η·Umax_intact) di test. Kontrak "kontrol λ=1: CI=η·U*_e
(bukan 0)" terpenuhi persis.

---

## DF-05 (Finding #004c) — Skrining grid penuh 64+16 & temuan turunannya
**Status:** 🟢 CLOSED (dieksekusi 2026-10-11; temuan baru dicatat sbg #004)
Grid penuh λ∈{1,0.75,0.5,0.25,0} × 16 edge = 80 run selesai (<2 dtk).
Audit check: RR(λ=1)=1 eksak semua edge; tidak ada CI<0; monotonisitas RR
menurun terhadap λ: 0 pelanggaran pada seluruh 16 edge × 4 model.
CSV audit kini memuat 68 baris (kontrol per-model + seluruh kombinasi
edge×λ yang relevan untuk tabel perbandingan).

---

## DF-06 (Finding #004d) — Greedy vs exhaustive (Section 4.8.6)
**Status:** 🟢 NO ISSUE
Enumerasi EKSHAUSTIF semua kombinasi jalur edge-disjoint |P|≤K; status
`certified/uncertified` via budget DFS (500k node). Tidak pernah mengembalikan
angka bila pencarian tidak selesai (status uncertified ⇒ RR/ARI/CI = None).

---

## Finding #003 — Batas representasi e3/e4 (rujukan ringkas)
Terkonfirmasi lewat kode: lihat DF-01 (baris e3/e4 PASS eksak RR=1, CI=0) dan
DF-02. Narasi resmi: "e3 dan e4 membawa gaya awal nol di bawah beban yang
diberikan, dan penghapusannya tidak mengubah skor jalur optimal untuk K=2.
Ini adalah batas representasi ARI, bukan bug." → masuk Gate 3 (Kinematic Guard).

---

## Finding #004 — Temuan tambahan selama eksekusi grid penuh
**(a) Plateau λ (M3-e4/M3-e5 penamaan internal):** RR konstan 0.791758 untuk
λ∈{0.5,0.25,0}. Analisis: setelah w_e^M·λ turun di bawah bobot jalur pesaing,
kombinasi jalur optimal berpindah permanen ke set alternatif → skor tidak lagi
peka λ. Bukan diskontinuitas bug; sifat max-over-paths. Perlu dicek apakah
disertasi mengharapkan kelancaran kurva RR(λ) (Gate 3/4).
**(b) Status rank-deficient meluas ke M4:** pada hapus-total SEMUA edge M4
(two diagonals) menghasilkan K_ff rank-deficient (chord tepi hilang → node
lepas), namun skor murni-graf tetap dihitung (`ok_with_rank_deficiency`,
DF-02). Konsisten dgn perlakuan Tabel 4.3 utk M3 e3/e4.
**(c) Kontrol utuh edge-less vs kontrol per-edge:** dikunci konvensi DF-04 —
laporkan keduanya; angka Tabel 4.11 (ARI=3/4) direproduksi oleh kontrol
per-edge λ=1, BUKAN oleh kontrol edge-less (CI=0). Harus eksplisit di naskah.
**(d) Peringatan reviewer potensial:** karena (a)+(b), CI kecil dapat muncul
pada struktur yang secara mekanis sudah mekanisme — narasi 'screening-only,
bukan safety assessment' wajib ada di bab diskusi disertasi.

---

## Finding #005 (Gate 3) — Penomoran edge: "e1..e5" pada Tabel 4.3 = 1-based vs `id` JSON 0-based

**Status**: BARU (ditemukan saat self-test Gate 3, 2026-10-11). Relevan utk Finding #001.

**Bukti dari `kinematic_guard.py` [2]** (rank-drop state terdisrupsi, hapus-total):
- Edge JSON id=2 (CD) dan id=3 (DA) adalah **zero-force members** intak → rank turun 5→4 dengan RR=1.000000, CI=0.000000 → terlabel `GRAPH_BLIND`.
- Narasi disertasi menyebut kasus kritis "e3 dan e4". Jika label tabel adalah **1-based**, maka e3≡id2(CD), e4≡id3(DA) — cocok persis dengan temuan guard. Ini juga menggeser hipotesis pemetaan nama utk #001 (H2): target tabel e1,e2,e5 mungkin ≡ id0,id1,id4 — yang memang sudah kami pakai di test_ari.py; namun perlu dikonfirmasi dari naskah.
- Catatan tambahan: M2_planar_triangle kehilangan chord/leg manapun → rank-deficient (MECHANISM); M4 tetap rank-penuh utk semua hapus tunggal (konsisten: dua diagonal + perimeter = stabil).

**Keputusan sprint**: tidak mengubah kode; dokumentasi & self-test kini memakai id JSON eksplisit (id2/id3) dgn catatan padanan label tabel.

---

## Finding #006 (Gate 3) — Kinematic Guard terpasang; klasifikasi observasional

Guard menambahkan kolom audit `kinematic` (intact_rank→disrupted_rank, rank_drop, solvable, min/max eig) dan `guard_label` ∈ {CONSISTENT, MECHANISM, GRAPH_BLIND} TANPA mengubah RR/ARI/CI (sanity [4] PASS eksak 1e-12). Kontrol λ=1 per-edge kini membawa snapshot kinematik INTAK di audit trail. Hasil skrining λ=0 (16 skenario): 8 CONSISTENT, 6 MECHANISM, 2 GRAPH_BLIND (M3 id2, id3). Ambang GRAPH_BLIND: CI < 0.01 & rank_drop > 0 (`CI_BLIND_TOL`).

---

## Finding #007 (Gate 4) — Mekanisme terdeteksi pada parsial λ>0 di M2 (bukan hanya hapus-total)

**Status**: BARU (pipeline grid penuh λ∈{1,0.75,0.5,0.25,0}, 2026-10-11).

**Bukti** (`results/verification/screening_report.json`, agregat guard per model):
M2_planar_triangle: MECHANISM = 3 dari 12 skenario disrupsi. Label MECHANISM
muncul juga untuk λ PARSIAL (mis. leg e0/e1 dengan EA→λ·EA cukup kecil
sehingga rasio kekakuan chord terhadap gaya horisontal membuat K_ff rank-deficient
menurut toleransi eigvals relatif 1e-10), bukan hanya λ=0.
Perlu dicatat di naskah bahwa "ambang mekanisme" bergantung toleransi numerik
solver; untuk aplikasi nyata ambang λ_kritis sebaiknya dilaporkan per edge
(dari CSV pipeline, kolom `solvable`). Implikasi Gate 5 (jika ada): kurva
RR(λ) dapat berpotongan dengan batas solvabilitas mekanik sebelum λ=0.

---

## Finding #008 (Gate 4) — Perpanjangan plateau RR(λ): konsistensi lintas-lapisan & monotonisitas global

**Status**: INFO (tidak ada pelanggaran; keputusan verifikasi Gate 4).

Grid penuh pipeline (64 skenario disrupsi + 20 kontrol = 84 baris CSV)
memperluas temuan #004(a): plateau RR(λ≤0.5) terjadi pada banyak edge M3/M4
(bukan hanya e4/e5). Semua cek antar-lapisan LULUS tanpa inkonsistensi:
(i) deteksi mekanisme Lapisan-2 vs Lapisan-3 sepakat pada 64/64 skenario;
(ii) tidak ada GRAPH_BLIND tanpa mekanisme; (iii) RR monoton tak-naik per-edge
pada seluruh 16 edge; (iv) regresi angka kunci Gate 2 (Tabel 4.11 & kasus
kritis Tabel 4.3) cocok dalam toleransi. Tidak ada perubahan formula/parameter
— pipeline murni orkestrasi. Ambang CI_BLIND_TOL=0.01 dipertahankan; nilai
CI=1.11e-16 pada M3-id2 saat λ=0 mengonfirmasi floor numerik max(1−ARI,0).

---

## Finding #009 (Gate 5) — Kebutuhan ekstraksi kurva RR(λ) & λ_kritis utk analisis sensitivitas per edge

**Status**: INFO (kebutuhan terpenuhi oleh `examples/curve_extractor.py`, 2026-10-11).

Pipeline Gate 4 menghasilkan grid λ∈{1,0.75,0.5,0.25,0} per edge, namun
angka kunci sensitivitas (pada λ berapa CI menembus ambang; pada λ berapa
guard berubah Clear→Forward) belum diekstrak secara sistematis — ini yang
dibutuhkan untuk menutup Finding #007 (mekanisme M2 muncul pada λ parsial)
dan untuk bab analisis sensitivitas disertasi. Gate 5 menambahkan:

* `results/verification/pipeline_output.csv` — schema kanonik 12 kolom
  [model_id, edge_id, lambda, S_intact, S_disrupted, RR, ARI, CI,
  rank_status, margin_m, guard_decision, U_star] (80 baris per-edge).
* `examples/curve_extractor.py` → `results/verification/critical_lambdas.json`.

**Definisi operasional yang perlu direview (Sprint Mode):**
1. Interpolasi LINEAR antar titik grid coarse (bukan spline). Nilai kontinu
   lintasan CI=0.5 disimpan di `lambda_crit_note`; angka yang dilaporkan
   adalah batas ATAS zona kritis (konservatif).
2. Margin kinematik m_e(λ) := rank_drop/ndof_free (fraksi DOF bebas intak
   yang hilang). Ini proxy observasional — BUKAN analisis nullspace penuh;
   keputusan formulasi utk didokumentasikan di naskah.
3. guard_decision = "Clear" jika solvable & m=0, selain itu "Forward".
   Deteksi flip hanya sedetail grid λ.

**Hasil aktual (grid coarse, threshold CI≥0.5):**
* λ_crit tercapai HANYA pada M1-e0 (lapor 0.25; kontinu 0.4333), M1-e1
  (0.0; kontinu 0.1905), M2-e0/e1/e2 (0.0; kontinu ≈0.236). Semua edge
  M3/M4: `not_reached_on_grid` — konsisten dengan plateau RR(λ≤0.5)
  (#004a/#008): degradasi parsial nyaris tidak mengubah skor jalur.
* Guard-flip (Clear→Forward) pada 8 edge (M2 semua, M3 semua) — semuanya
  di λ=0.0 pada grid ini.
* Kelas GRAPH-BLIND-LIKE (guard flip tapi CI_max<0.5): 6 edge, termasuk
  M3-e2/e3 dengan worst CI = 0.000000 persis (reproduksi Finding #003 via
  pipeline otomatis — penutup mekanistik #007 utk kasus nol-gaya).

Implikasi utk naskah: pada grid coarse, λ_kritis berbasis-CI dan berbasis-
guard sering TIDAK berimpit; rekomendasi grid λ lebih halus (mis. 0.05)
atau definisi formal m_e(λ) diperlukan sebelum klaim numerik dibuat.
