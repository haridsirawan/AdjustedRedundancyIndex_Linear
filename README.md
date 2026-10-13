# Adjusted Redundancy Index — Kode & Verifikasi Model

Repo kode untuk penelitian disertasi **Adjusted Redundancy Index (ARI)**: implementasi komputasi dan verifikasi model terhadap tabel referensi disertasi, dikerjakan berlapis lewat gate verifikasi Gate 1–8.

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
```

## Menjalankan

```bash
cd examples
python3 test_truss_reference.py   # verifikasi solver vs Tabel 4.1
python3 run_pipeline.py           # pipeline lengkap + konsistensi antar-lapisan
```

## Isi repo

| File / folder | Isi |
|---|---|
| `examples/` | Kode implementasi & pengujian (mesin ARI, solver referensi, guard, pipeline) |
| `results/` | Keluaran verifikasi: CSV, JSON, PDF kurva, `review_prep/` |
| `ARCHITECTURE.md` | Arsitektur pipeline + daftar file aktual & statusnya |
| `WORK_LOG.md` | Log progres per gate (Gate 1–8) |
| `DEFERRED_FINDINGS.md` | Temuan yang ditunda beserta statusnya |
| `debug_archive/`, `unified_debug_gate2.py`, `debug_results.csv` | Diagnostik grid-search Gate 2 |

Riwayat lengkap gate, status verifikasi, dan daftar file aktual ada di `ARCHITECTURE.md` dan `WORK_LOG.md`.

Lisensi: Apache 2.0 — lihat `LICENSE`.
