# Adjusted Redundancy Index — Kode & Verifikasi Model

Repo kode untuk penelitian disertasi **Adjusted Redundancy Index (ARI)**: implementasi komputasi dan verifikasi model terhadap tabel referensi disertasi, dikerjakan berlapis lewat gate verifikasi Gate 1–9. Seluruh rantai kanonik (Bagian 2.5–2.18, 4.1–4.5) telah diselaraskan dengan naskah dan direproduksi otomatis — lihat `results/review_prep/penyelarasan_disertasi_gate9.md`.

> Folder lokal repo ini adalah `Coding/` di dalam folder riset — **materi riset pribadi** (artikel, catatan Obsidian, laporan, data bibliometrik VOSviewer) **berada di luar repo dan tidak dilacak git**.

## Pipeline 3-lapisan

```
examples/verification_models.json
        │
        ▼
examples/truss_reference.py    (L1 — solver FE batang: gaya awal, reaksi r^(0), U*, rank)
        │
        ▼
examples/ari_core.py           (L2 — mesin ARI: w_e^M, Φ^K_ij, S(G), RR, ARI, CI; Eq 2.5–2.18)
        │
        ▼
examples/kinematic_guard.py    (L3 — guard kinematik: rank/margin, guard_decision)
        │
        ▼
examples/run_pipeline.py / fine_grid_runner.py → results/ (CSV audit)
examples/curve_extractor.py / plot_curves.py   → results/ (JSON/PDF kurva)
examples/mechanical_guard.py                   (guard Eq 4.1–4.4, h_e SVD — Tabel 4.4)
examples/run_verification.py                   → results/verification/ (kontrak Tabel 4.8)
```

## Menjalankan

```bash
cd examples
python3 ari_tutorial.py           # tutorial rantai ARI (contoh dua batang; Kode 4.2)
python3 test_truss_reference.py   # verifikasi solver vs Tabel 4.1
python3 run_pipeline.py           # pipeline lengkap + konsistensi antar-lapisan
python3 run_verification.py       # verifikasi kanonik penuh 65 pemeriksaan (Tabel 4.1–4.5/4.11)
python3 run_guard_verification.py # paket pengaman -A2 (analitis + regresi + diagnostik)
python3 mechanical_guard.py       # pengaman kinematik Eq 4.1–4.4 (h_e SVD, regresi Tabel 4.4)
```

## Isi repo

| File / folder | Isi |
|---|---|
| `examples/` | Kode implementasi & pengujian (mesin ARI, solver referensi, guard, pipeline) |
| `examples/run_verification.py` | Runner verifikasi kanonik (Tabel 4.1–4.5/4.11) → baseline/scenarios/checks.csv, manifest.json, Tabel.tex, figur |
| `examples/run_guard_verification.py` | Verifikasi paket pengaman §4.2/§4.5.11 (analitis Eq 4.7, regresi Tabel 4.3/4.4/4.11, diagnostik Tabel 4.2/4.5) |
| `examples/ari_tutorial.py` | Tutorial langkah-demi-langkah rantai ARI (contoh dua batang; urutan reproduksi Kode 4.2) |
| `examples/mechanical_guard.py` | Pengaman kinematik Eq 4.1–4.4 (h_e = k_e·a_e·K₀⁻¹·a_eᵀ via SVD; m_e(λ); batas κ ≥ m·ρ₀) |
| `results/` | Keluaran verifikasi: CSV, JSON, PDF kurva, `review_prep/` (+ keluaran kontrak Tabel 4.8 Gate 9) |
| `results/revision/` | Paket parametrik §4.2.4: 16 model (272 skenario) + `decisions.csv` + `remaining_misses.csv` (Gate 9.2) |
| `ARCHITECTURE.md` | Arsitektur pipeline + daftar file aktual & statusnya |
| `WORK_LOG.md` | Log progres per gate (Gate 1–9) |
| `DEFERRED_FINDINGS.md` | Temuan yang ditunda beserta statusnya |
| `debug_archive/`, `unified_debug_gate2.py`, `debug_results.csv` | Diagnostik grid-search Gate 2 |

Riwayat lengkap gate, status verifikasi, dan daftar file aktual ada di `ARCHITECTURE.md` dan `WORK_LOG.md`.

Lisensi: Apache 2.0 — lihat `LICENSE`.
