# Adjusted Redundancy Index (ARI)

Repositori penelitian disertasi **Adjusted Redundancy Index (ARI)** — indeks redundansi yang disesuaikan untuk struktur batang/rangka — mencakup studi literatur, analisis bibliometrik, serta implementasi dan verifikasi model komputasinya.

## Struktur repositori

| Folder / file | Isi |
|---|---|
| `Article/` | Artikel rujukan (PDF) |
| `Books/` | Buku & standar rujukan |
| `Notes/` | Catatan riset (markdown) |
| `Report/`, `Final Report/` | Draf dan laporan akhir |
| `Presentation/` | Materi presentasi |
| `VOSviewer/` | Data & hasil analisis bibliometrik (SLR/PRISMA, jaringan jurnal) |
| `examples/` | Kode implementasi & verifikasi model ARI |
| `results/` | Keluaran pipeline verifikasi (CSV, JSON, PDF) |
| `ARCHITECTURE.md` | Arsitektur pipeline 3-lapisan verifikasi |
| `WORK_LOG.md` | Log progres verifikasi Gate 1–8 |
| `DEFERRED_FINDINGS.md` | Temuan yang ditunda beserta statusnya |

Folder ini sekaligus merupakan **Obsidian vault** — buka dengan Obsidian untuk menjelajahi catatan (`Notes/`).

## Verifikasi model (pipeline ARI)

Pipeline 3-lapisan untuk memverifikasi mesin ARI terhadap tabel referensi disertasi:

```
verification_models.json → truss_reference.py (L1: solver FE)
                        → ari_core.py          (L2: mesin ARI, Eq 2.5–2.18)
                        → kinematic_guard.py   (L3: guard rank/margin)
                        → run_pipeline.py / fine_grid_runner.py → CSV/JSON/PDF
```

Jalankan dari folder `examples/`. Detail gate, status verifikasi, dan daftar file aktual ada di `ARCHITECTURE.md` dan `WORK_LOG.md`.

## Catatan

- `VOSviewer/VOSviewer.app/` sengaja tidak dilacak (biner aplikasi ±65 MB).
- File yang masih berupa placeholder iCloud (`*.icloud`) tidak ikut tercommit; unduh dulu isinya dari iCloud agar masuk git.
- `Presentation/` kosong dipertahankan lewat `.gitkeep` agar struktur folder utuh saat di-clone.
- Lisensi: Apache 2.0 — lihat `LICENSE`.
