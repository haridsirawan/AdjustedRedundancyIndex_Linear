#!/usr/bin/env python3
"""
run_all_verifications.py
========================
Skrip verifikasi terpadu satu pintu (single-entry-point runner) untuk repositori
penelitian disertasi "Adjusted Redundancy Index (ARI)" — Harids Irawan (2026).

Menjalankan seluruh suite pengujian deterministik dan verifikasi berlapis:
  1. Verifikasi Solver Referensi Rangka Batang (Tabel 13 / Tabel 4.1)
  2. Tutorial Rantai Komputasi ARI Dua Batang (Tabel 25 / Tabel 4.11)
  3. Pengujian Inti Mesin ARI & Invariansi Satuan (Tabel 15 / Tabel 4.3)
  4. Verifikasi Pengaman Kinematik SVD (Persamaan 4.1–4.7 & Tabel 16 / Tabel 4.4)
  5. Pengujian Batas Praanalisis & Audit Anti-Kebocoran Informasi (Leakage Audit)
  6. Suite Verifikasi Kanonik Penuh (68/68 Pemeriksaan Otomatis)
  7. Verifikasi Paket Pengaman & Diagnostik Parametrik 16 Model (272 Skenario)
  8. Suite Uji Analitis Solver Elemen Hingga Multi-Keluarga (S1–S5)

Cara menjalankan dari root repositori:
    python3 run_all_verifications.py
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT_DIR / "examples"

VERIFICATION_SUITE = [
    ("1. Solver Referensi Batang Aksial (M1–M4)", "test_truss_reference.py"),
    ("2. Tutorial Analitis Dua Batang Paralel", "ari_tutorial.py"),
    ("3. Mesin Inti ARI & Invariansi Konversi Satuan", "test_ari.py"),
    ("4. Pengaman Kinematik Berbasis SVD (h_e)", "mechanical_guard.py"),
    ("5. Batas Praanalisis (Bound Enhancement)", "test_bound_enhancement.py"),
    ("6. Audit Anti-Kebocoran Informasi (Leakage Audit)", "test_leakage_audit.py"),
    ("7. Verifikasi Kanonik Penuh (68/68 Pemeriksaan)", "run_verification.py"),
    ("8. Diagnostik Pengaman & 16 Model Parametrik (272 Skenario)", "run_guard_verification.py"),
    ("9. Solver Elemen Hingga Multi-Keluarga (S1–S5)", "test_structural_solvers.py"),
    ("10. Validasi Penuh ARI v2 pada 300 Model Induk (S1–S5)", "run_screening_v2.py"),
    ("11. Integrasi Penapisan ARI v2–GNN (StructGNN-CRC v1.0)", "run_gnn_integration_s6.py"),
]


def main() -> int:
    print("=" * 78)
    print("SUITE VERIFIKASI TERPADU — ADJUSTED REDUNDANCY INDEX (ARI)")
    print("=" * 78)

    results = []
    t0_all = time.perf_counter()

    for label, script_name in VERIFICATION_SUITE:
        script_path = EXAMPLES_DIR / script_name
        print(f"\n>>> Menjalankan {label} ({script_name})...")
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(EXAMPLES_DIR),
            capture_output=True,
            text=True,
        )
        dt = time.perf_counter() - t0
        passed = proc.returncode == 0
        status_str = "LULUS (PASS)" if passed else f"GAGAL (EXIT {proc.returncode})"
        print(f"    Status: {status_str} [{dt:.2f} dtk]")
        if not passed:
            print("    --- STDOUT ---")
            print(proc.stdout[-1200:] if proc.stdout else "(kosong)")
            print("    --- STDERR ---")
            print(proc.stderr[-1200:] if proc.stderr else "(kosong)")
        results.append((label, script_name, passed, dt))

    total_dt = time.perf_counter() - t0_all
    n_pass = sum(1 for _, _, ok, _ in results if ok)
    n_total = len(results)

    print("\n" + "=" * 78)
    print("RINGKASAN HASIL VERIFIKASI REPOSITORI ARI")
    print("=" * 78)
    print(f"{'Tahap Verifikasi':<52} | {'Status':<12} | {'Waktu':>8}")
    print("-" * 78)
    for label, _, ok, dt in results:
        st = "LULUS" if ok else "GAGAL"
        print(f"{label:<52} | {st:<12} | {dt:>6.2f} s")
    print("-" * 78)
    print(f"Total Tahap Lulus: {n_pass}/{n_total} | Total Waktu Eksekusi: {total_dt:.2f} detik")
    print("=" * 78)

    return 0 if n_pass == n_total else 1


if __name__ == "__main__":
    sys.exit(main())
