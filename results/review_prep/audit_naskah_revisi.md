# Audit Naskah Revisi (193 halaman) vs Paket Gate 9
**Tanggal:** 13 Oktober 2026 · **Pelaksana:** AutoClaw · **Status:** ✅ seluruh klaim terverifikasi — nol ketidaksesuaian numerik.

## Konteks
Naskah `main.pdf` versi baru (**193 halaman**, menggantikan versi 222 halaman) kini mengintegrasikan
paket Gate 9: §3.1.4 (alur kerja asisten + `run_verification.py`), §4.2.6 + **Tabel 4.6** (snapshot
Gate 9, terpisah dari runner lokal Tabel 4.5), §4.5.11 + **Tabel 4.10** (berkas bukti unggahan),
§4.5.12 (paket pengaman kinematik). Audit ini memeriksa setiap klaim numerik terhadap repositori.

## Hasil audit (klaim naskah → data repo)
| Klaim naskah | Data repositori | Verdict |
|---|---|---|
| forwarded: 20 hanya-ARI, 22 hanya-pengaman, 10 keduanya | `forwarded.csv`: 20/22/10 (total 52) | ✅ persis |
| remaining_misses: 28 = 23 perpindahan + 4 utilisasi + 1 keduanya | `remaining_misses.csv`: 23/4/1 | ✅ persis |
| 68/68 cek kanonik lulus | `checks.csv`: 68/68 | ✅ persis |
| Tabel 4.6: 30/32/52; rank 22/0/0; kritis-A (n=94) 67/62/45; kritis-B (n=71) 50/39/28 | `guard_verification.json` §D | ✅ persis |
| RR e1–e5 = 0.983152316 / 0.964723707 / 1 / 1 / 0.717284621 | `checks.csv`/`test_ari` | ✅ persis |
| Tabel 4.10 daftar xlsx (baseline/checks/scenarios/decisions/forwarded/remaining_misses) | `Transparansi ARI/data/*.xlsx` | ✅ keenam ada |
| "Kebijakan gabungan meneruskan seluruh 40 kasus rank kurang" (§4.2.5, §5) | 8 kanonik (Tabel 4.2) + 32 parametrik = **40** | ✅ konsisten |

## Peta penomoran tabel (lama 222 hlm → baru 193 hlm)
| Isi | Lama | Baru |
|---|---|---|
| Diagnostik kanonik/parametrik | 4.5 | 4.5 (lokal) + **4.6 (unggahan, baru)** |
| Kode status | 4.7 | 4.8 |
| Keluaran results/verification | 4.8 | 4.9 |
| Berkas bukti unggahan | — | **4.10 (baru)** |
| Skema minimum berkas | 4.9 | 4.11 |
| Kasus uji minimum | 4.10 | 4.12 |
| Contoh analitis dua batang | 4.11 | 4.13 |
| Hitungan ambang | 4.12 | 4.14 |

## Catatan untuk keputusan peneliti (bukan kesalahan angka)
1. **Atribusi asisten:** §3.1.4 menyebut *OpenAI Codex*. Jejak repo: cabang verifikasi Gate 1–8 ber-author commit **"qwen.ai[bot]"**; Gate 9–9.3 (runner, guard, parametrik, lampiran) dieksekusi oleh **AutoClaw**. Jika Codex memang dipakai untuk bagian lain (mis. LaTeX), penyebutan saat ini tetap sah; penyelarasan atribusi sepenuhnya keputusan peneliti.
2. **Selisih ARI 17 vs 30:** naskah sudah menanganinya secara tepat (dua tabel terpisah + catatan "belum dapat direkonsiliasi"); tinggal keputusan akhir (rekalulasi lokal vs penyajian ganda).

## Kesimpulan
**Tidak ditemukan satu pun ketidaksesuaian numerik.** Paket Gate 9 yang diunggah dan seluruh
angka yang dikutip naskah revisi konsisten dengan repositori pada commit `97d8829` (+ commit audit).
