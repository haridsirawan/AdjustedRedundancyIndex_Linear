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
| `AutoClaw/` | Suite verifikasi model ARI (lihat `AutoClaw/README.md`) |
| `LICENSE` | Apache 2.0 |

Folder ini sekaligus merupakan **Obsidian vault** — buka dengan Obsidian untuk menjelajahi catatan (`Notes/`).

## Suite verifikasi model

Implementasi dan verifikasi komputasi model ARI (pipeline 3-lapisan, verifikasi Gate 1–8) berada di folder [`AutoClaw/`](AutoClaw/) — arsitektur, log progres, dan cara menjalankannya dijelaskan di `AutoClaw/README.md`, `AutoClaw/ARCHITECTURE.md`, dan `AutoClaw/WORK_LOG.md`.

## Catatan

- `VOSviewer/VOSviewer.app/` sengaja tidak dilacak (biner aplikasi ±65 MB).
- File yang masih berupa placeholder iCloud (`*.icloud`) tidak ikut tercommit; unduh dulu isinya dari iCloud agar masuk git.
