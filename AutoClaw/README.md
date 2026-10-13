# Suite Verifikasi Model ARI (AutoClaw)

Implementasi dan verifikasi komputasi **Adjusted Redundancy Index (ARI)** terhadap tabel referensi disertasi. Dikerjakan berlapis lewat "gate" Gate 1–8; riwayat lengkap ada di `WORK_LOG.md`, temuan tertunda di `DEFERRED_FINDINGS.md`.

> Seluruh path di dokumen suite ini (`ARCHITECTURE.md`, `WORK_LOG.md`, dll.) relatif terhadap folder `AutoClaw/`.

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
cd AutoClaw/examples
python3 test_truss_reference.py   # verifikasi solver vs Tabel 4.1
python3 run_pipeline.py           # pipeline lengkap + konsistensi antar-lapisan
```

## Isi folder

| File / folder | Isi |
|---|---|
| `examples/` | Kode implementasi & pengujian (mesin ARI, solver referensi, guard, pipeline) |
| `results/` | Keluaran verifikasi: CSV, JSON, PDF kurva, `review_prep/` |
| `ARCHITECTURE.md` | Arsitektur pipeline + daftar file aktual & statusnya |
| `WORK_LOG.md` | Log progres per gate (Gate 1–8) |
| `DEFERRED_FINDINGS.md` | Temuan yang ditunda beserta statusnya |
| `debug_archive/`, `unified_debug_gate2.py`, `debug_results.csv` | Diagnostik grid-search Gate 2 |
