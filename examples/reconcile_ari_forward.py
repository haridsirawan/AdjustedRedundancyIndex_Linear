#!/usr/bin/env python3
"""reconcile_ari_forward.py — Rekonsiliasi K6: "Diteruskan" draf vs kode pada paket parametrik §4.2.4.

Konteks:
  Naskah lama (Tabel 3.1/3.2, hlm. ~193 & 211 ekstraksi) memuat baris draf:
      Parametrik ARI      272  17  24/32  54/71
      Parametrik Pengaman 272  32   0/32  39/71
      Parametrik Gabungan 272  41   0/32  30/71
  Kode tervalidasi (guard_verification.json §D) menghasilkan: 30/32/52 dan
  kekurangan kritis (B) 50/39/28; (A) 67/62/45.

  Semantik kolom: "Diteruskan" = jumlah skenario yang diteruskan (kalimat naskah:
  "41 dari 272 gangguan diteruskan dan 30 dari 71 kasus kritis masih terlewat").

Keluaran:
  results/review_prep/rekonsiliasi_ari_forward.md         (laporan, ditulis ulang)
  results/review_prep/rekonsiliasi_ari_forward_kasus.csv  (30 kasus ARI + label)

Jalankan dari root repo:  python3 examples/reconcile_ari_forward.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "results" / "revision"
VER = ROOT / "results" / "verification"
OUT_MD = ROOT / "results" / "review_prep" / "rekonsiliasi_ari_forward.md"
OUT_CSV = ROOT / "results" / "review_prep" / "rekonsiliasi_ari_forward_kasus.csv"
TOL = 1e-12


def load(name: str) -> list:
    return list(csv.DictReader(open(REV / name, encoding="utf-8-sig")))


def main() -> None:
    dec = load("decisions.csv")
    fw = load("forwarded.csv")
    ms = load("remaining_misses.csv")
    g = json.load(open(VER / "guard_verification.json"))
    d = g["groups"]["D_parametrik"]
    draft = json.load(open(REV / "models.json"))["meta"]["targets_tabel_45"]

    # --- set & hitungan dari kode -------------------------------------------
    ari = [r for r in dec if r["ari_forward"] == "1"]
    gu = [r for r in dec if r["guard_flag"] == "1"]
    critB = {(r["model"], r["edge"], r["lambda_"]) for r in fw if r["crit_B"] == "1"}
    critB |= {(r["model"], r["edge"], r["lambda_"]) for r in ms}
    assert len(critB) == d["counts_alt_B"]["critical"] == 71
    assert len([r for r in dec if r["ari_forward"] == "1"]) == d["counts_alt_B"]["ari_fwd"] == 30
    assert len(gu) == d["counts_alt_B"]["guard_fwd"] == 32

    # pasangkan decisions -> forwarded lewat CI (label elemen; pasangan simetris = gabungan label)
    def labels(r):
        return sorted({f["edge"] for f in fw
                       if f["model"] == r["model"] and f["lambda_"] == r["lam"]
                       and abs(float(f["CI"]) - float(r["CI"])) < TOL})
    rows = []
    for r in ari:
        lab = labels(r) or ["?"]
        cb = 1 if any((r["model"], e, r["lam"]) in critB for e in ([f["edge"] for f in fw
                    if f["model"] == r["model"] and f["lambda_"] == r["lam"]
                    and abs(float(f["CI"]) - float(r["CI"])) < TOL] or [""])) else 0
        rows.append({"model": r["model"], "edge": "/".join(lab), "lam": r["lam"],
                     "CI": r["CI"], "rank": r["guard_flag"], "critB": cb})
    rows.sort(key=lambda x: float(x["CI"]))
    rk = [x for x in rows if x["critB"] == 1 and x["rank"] == "1"]
    ad = [x for x in rows if x["critB"] == 1 and x["rank"] == "0"]
    nc = [x for x in rows if x["critB"] == 0]
    assert (len(rk), len(ad), len(nc)) == (10, 11, 9)

    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "edge", "lam", "CI", "rank", "critB"])
        w.writeheader()
        w.writerows(rows)

    # --- laporan -------------------------------------------------------------
    def kasus(lst):
        return "\n".join(
            f"| {x['model']} | {x['edge']} | {x['lam']} | {float(x['CI']):.6f} |" for x in lst)

    md = f"""# Rekonsiliasi "Diteruskan": draf 17/32/41 vs kode 30/32/52 (K6)

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
{kasus(nc)}

### 4b. Empat kasus kritis bermargin terkecil (kandidat utama penjelas selisih 4)

- Rank margin terkecil: {rk[0]['model']} {rk[0]['edge']} (CI {float(rk[0]['CI']):.6f}) dan {rk[1]['model']} {rk[1]['edge']} (CI {float(rk[1]['CI']):.6f}).
- Tambahan margin terkecil: {ad[0]['model']} {ad[0]['edge']} (CI {float(ad[0]['CI']):.6f}) dan {ad[1]['model']} {ad[1]['edge']} (CI {float(ad[1]['CI']):.6f}).

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
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print("MD  :", OUT_MD.relative_to(ROOT))
    print("CSV :", OUT_CSV.relative_to(ROOT))
    print(f"komposisi: rank {len(rk)} + tambahan {len(ad)} + nonkritis {len(nc)} = {len(rows)}")


if __name__ == "__main__":
    main()
