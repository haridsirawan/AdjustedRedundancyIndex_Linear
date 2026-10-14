#!/usr/bin/env python3
"""analyze_remaining_misses.py — Diagnosa 28 kasus kritis terlewat + evaluasi kandidat kebijakan (W1).

Konteks (naskah §4.9.4, prioritas ilmiah pertama):
  Pengaman telah menangani seluruh kasus rank dalam pengembangan, tetapi kejadian
  kapasitas dan perpindahan kritis masih terlewat. Skrip ini:
  1. Mencirikan 28 kasus terlewat (remaining_misses.csv, varian B) — sebab, λ, CI.
  2. Mengevaluasi kandidat aturan praanalisis yang hanya memakai informasi tersedia
     sebelum inferensi (λ dan CI), dengan semantik UNION terhadap kebijakan sekarang
     (ARI τ=0,5 ∪ pengaman). Semua kandidat bersifat ADITIF (tidak mengubah skor).
  3. Mencatat trade-off (penerusan tambahan vs kasus tertangkap) sebagai bahan
     keputusan peneliti — skrip TIDAK mengubah kebijakan paket.

Pencocokan miss→decisions memakai (model, λ, CI) agar bebas ambiguitas label elemen
(pasangan simetris ber-CI identik setara untuk perhitungan).

Keluaran:
  results/review_prep/diagnosa_28_kasus_terlewat.md
  results/review_prep/diagnosa_28_kasus_terlewat.csv

Jalankan dari root repo:  python3 examples/analyze_remaining_misses.py
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "results" / "revision"
OUT_MD = ROOT / "results" / "review_prep" / "diagnosa_28_kasus_terlewat.md"
OUT_CSV = ROOT / "results" / "review_prep" / "diagnosa_28_kasus_terlewat.csv"
TOL = 1e-9
N, KRITIS = 272, 71
BASE_FWD = 52  # ARI(τ=0,5) ∪ pengaman


def main() -> None:
    dec = list(csv.DictReader(open(REV / "decisions.csv", encoding="utf-8-sig")))
    ms = list(csv.DictReader(open(REV / "remaining_misses.csv", encoding="utf-8-sig")))

    def rows_of(model, lam, ci):
        return [r for r in dec if r["model"] == model and r["lam"] == lam
                and abs(float(r["CI"]) - float(ci)) < TOL]

    # --- 1. karakterisasi ----------------------------------------------------
    for r in ms:  # integritas: miss memang tidak diteruskan
        rr = rows_of(r["model"], r["lambda_"], r["CI"])
        assert rr and all(x["ari_forward"] == "0" and x["guard_flag"] == "0" for x in rr)
    cause = Counter(r["cause"] for r in ms)
    lam = Counter(r["lambda_"] for r in ms)
    ci = sorted(float(r["CI"]) for r in ms)
    model_ct = Counter(r["model"] for r in ms)

    # --- 2. evaluasi kandidat (aditif, union) --------------------------------
    def evaluate(name, extra_cond, aris_rule=None):
        """extra_cond(lam, ci): aturan TAMBAHAN. aris_rule: penggantian aturan ARI (default τ=0,5)."""
        ari_rule = (lambda lam, c: c > 0.5) if aris_rule is None else aris_rule
        total = 0
        for r in dec:
            lam_, c_ = r["lam"], float(r["CI"])
            if r["guard_flag"] == "1" or ari_rule(lam_, c_) or (extra_cond and extra_cond(lam_, c_)):
                total += 1
        caught = sum(1 for r in ms if extra_cond and extra_cond(r["lambda_"], float(r["CI"])))
        baru = total - BASE_FWD
        sisa = len(ms) - caught
        recall = (KRITIS - sisa) / KRITIS
        reduksi = 1 - total / N
        return dict(nama=name, total=total, tambahan=baru, tertangkap=caught, sisa=sisa,
                    recall=recall, reduksi=reduksi)

    kandidat = [
        evaluate("P0  Kebijakan sekarang (ARI τ=0,5 ∪ pengaman)", None),
        evaluate("P1  + λ=0 semua diteruskan", lambda l, c: l == "0.0"),
        evaluate("P2  + (λ=0 & CI>0,35)", lambda l, c: l == "0.0" and c > 0.35),
        evaluate("P3  + (λ=0 & CI>0,25)", lambda l, c: l == "0.0" and c > 0.25),
        evaluate("P4  + (λ≤0,25 & CI>0,40)", lambda l, c: l in ("0.0", "0.25") and c > 0.40),
        evaluate("P5  + (λ≤0,25 & CI>0,35)", lambda l, c: l in ("0.0", "0.25") and c > 0.35),
        evaluate("P6  + (λ=0 | CI>0,45)", lambda l, c: l == "0.0" or c > 0.45),
        evaluate("P7  ARI τ=0,45 ∪ pengaman", lambda l, c: c > 0.45, aris_rule=lambda l, c: c > 0.5),
    ]

    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model", "edge", "lambda_", "cause", "CI"])
        w.writeheader()
        w.writerows(sorted(ms, key=lambda r: -float(r["CI"])))

    baris_kandidat = "\n".join(
        f"| {k['nama']} | {k['total']} | {k['tambahan']:+d} | {k['tertangkap']}/28 | {k['sisa']} | "
        f"{k['recall']*100:.1f}% | {k['reduksi']*100:.1f}% |" for k in kandidat)
    baris_28 = "\n".join(
        f"| {r['model']} | {r['edge']} | {r['lambda_']} | {float(r['CI']):.6f} | {r['cause']} |"
        for r in sorted(ms, key=lambda r: -float(r["CI"])))

    md = f"""# Diagnosa 28 Kasus Kritis Terlewat + Evaluasi Kandidat Kebijakan (W1)

**Status:** analisis selesai — keputusan kebijakan menunggu peneliti. Skrip ini tidak mengubah paket.

## 1. Pencirian 28 kasus (`remaining_misses.csv`, varian B — kritis 71)

- Sebab: {'; '.join(f"{k} {v}" for k, v in sorted(cause.items()))}
- λ: {', '.join(f"{k}→{v}" for k, v in sorted(lam.items()))} — **tidak ada** di λ≥0,5.
- CI: rentang {ci[0]:.4f} – {ci[-1]:.4f} (median {ci[len(ci)//2]:.4f}) — **semua < 0,5**.
- Semua **tanpa kehilangan rank** (terverifikasi); model tersebar di {len(model_ct)} model
  (terbanyak: {', '.join(f'{m.split("_")[0]} {n}×' for m, n in model_ct.most_common(4))}).
- Pemusatan tematik: 4 kasus "utilisasi" seluruhnya pada P14_tripod (kaki e1/e2), plus
  P16_tripod (utilisasi+perpindahan).

## 2. Evaluasi kandidat aturan praanalisis (aditif; informasi λ & CI saja)

Kolom "Tambahan" = penerusan ekstra terhadap kebijakan sekarang (52). Recall = cakupan
kasus kritis (71); Reduksi = 1 − diteruskan/272.

| Kandidat | Diteruskan | Tambahan | Tertangkap | Sisa | Recall | Reduksi |
|---|---|---|---|---|---|---|
{baris_kandidat}

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
{baris_28}
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print("MD :", OUT_MD.relative_to(ROOT))
    print("CSV:", OUT_CSV.relative_to(ROOT))
    for k in kandidat:
        print(f"  {k['nama']:46s} total={k['total']:3d} tambahan={k['tambahan']:+3d} "
              f"tangkap={k['tertangkap']:2d}/28 recall={k['recall']*100:.1f}% reduksi={k['reduksi']*100:.1f}%")


if __name__ == "__main__":
    main()
