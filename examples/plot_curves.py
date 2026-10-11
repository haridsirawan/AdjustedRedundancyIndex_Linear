"""
plot_curves.py — GATE 6: Visualisasi Kurva RR(lambda) & CI(lambda) Grid Halus
=============================================================================
Disertasi "Adjusted Redundancy Index (ARI) for Mechanics-Based Screening".

Membaca results/verification/fine_grid_output.csv (keluaran
fine_grid_runner.py, Delta-lambda = 0.05) dan menghasilkan SATU figure PDF
per model kanonik dengan 2 subplot vertikal:

    Subplot atas : kurva RR(lambda) untuk semua edge (1 warna per edge).
    Subplot bawah: kurva CI(lambda) untuk semua edge.

Elemen referensi visual:
  * garis horizontal putus-putus   : RR = 1 (subplot atas), CI = 0 (bawah);
  * garis vertikal putus-putus     : lambda = 0.5 (ambang diagnostik);
  * marker 'x' merah              : titik dengan rank_status = rank_deficient;
  * marker '*' oranye             : titik GUARD-FLIP, yaitu titik pertama
    pada urutan lambda menurun di mana guard_decision berubah
    "Clear" -> "Forward" per edge.

Nilai abstain disimpan sebagai string "NaN" oleh runner dan otomatis
dilewati matplotlib (tidak ada imputasi angka).

Output (folder dibuat otomatis bila belum ada):
    results/verification/plots/curve_M1_parallel_bars.pdf
    results/verification/plots/curve_M2_triangle.pdf
    results/verification/plots/curve_M3_square_one_diag.pdf
    results/verification/plots/curve_M4_square_two_diag.pdf

Pemakaian:
    python examples/plot_curves.py
Exit code: 0 = keempat PDF terbentuk; 1 = input/keluaran tidak lengkap.

Sprint mode: TIDAK mengubah formula/parameter — murni visualisasi.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                 # backend tanpa display (spektra Gate 6)
import matplotlib.pyplot as plt       # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "results" / "verification" / "fine_grid_output.csv"
PLOT_DIR = ROOT / "results" / "verification" / "plots"

# model_id pada CSV -> nama file & judul figure
MODEL_META = {
    "M1_parallel_bars_1d": ("curve_M1_parallel_bars.pdf",
                            "M1 — Two Parallel 1D Bars"),
    "M2_planar_triangle": ("curve_M2_triangle.pdf",
                           "M2 — Planar Triangular Truss"),
    "M3_square_one_diagonal": ("curve_M3_square_one_diag.pdf",
                               "M3 — Square with One Diagonal"),
    "M4_square_two_diagonals": ("curve_M4_square_two_diag.pdf",
                                "M4 — Square with Two Diagonals"),
}


def _f(x: str):
    """Parse float toleran: ''/'NaN'/invalid -> None (skip, no imputasi)."""
    if x is None:
        return None
    x = str(x).strip()
    if x in ("", "NaN", "nan"):
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    return None if v != v else v


def load_series(path: Path):
    """Kembalikan {model_id: {edge_id: [rows sorted by lambda desc]}}.

    rows: dict(lam, RR, CI, rank_status, guard_decision).
    """
    data: dict = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            mid = r["model_id"]
            eid = int(r["edge_id"])
            data.setdefault(mid, {}).setdefault(eid, []).append(dict(
                lam=_f(r["lambda"]),
                RR=_f(r["RR"]),
                CI=_f(r["CI"]),
                rank_status=r["rank_status"].strip(),
                guard=r["guard_decision"].strip(),
            ))
    for mid in data:
        for eid in data[mid]:
            data[mid][eid].sort(key=lambda d: -(d["lam"] if d["lam"]
                                                is not None else -1))
    return data


def guard_flips(series: list) -> list:
    """Indeks titik pertama per edge saat guard Clear->Forward (lambda turun)."""
    flips, prev = [], None
    for i, d in enumerate(series):
        cur = d["guard"]
        if prev == "Clear" and cur == "Forward":
            flips.append(i)
        if cur:                      # jangan reset pada kolom kosong
            prev = cur
    return flips


def plot_model(mid: str, edges: dict, fname: str, title: str,
               out_dir: Path) -> Path:
    fig, (ax_rr, ax_ci) = plt.subplots(2, 1, figsize=(9.0, 8.5), sharex=True)

    colors = plt.cm.tab10(range(len(edges)))
    for (eid, series), col in zip(sorted(edges.items()), colors):
        lam = [d["lam"] for d in series]
        rr = [d["RR"] for d in series]
        ci = [d["CI"] for d in series]
        lbl = f"e{eid}"
        ax_rr.plot(lam, rr, "-o", ms=3.5, lw=1.3, color=col, label=lbl)
        ax_ci.plot(lam, ci, "-s", ms=3.5, lw=1.3, color=col, label=lbl)

        # marker 'x' merah: rank_deficient
        rx = [d["lam"] for d in series if d["rank_status"] == "rank_deficient"]
        ry = [d["RR"] for d in series if d["rank_status"] == "rank_deficient"]
        if rx:
            ax_rr.scatter(rx, ry, marker="x", s=60, color="red", zorder=5,
                          label=f"{lbl}: rank deficient" if len(rx) else None)
        cx = [d["lam"] for d in series if d["rank_status"] == "rank_deficient"]
        cy = [d["CI"] for d in series if d["rank_status"] == "rank_deficient"]
        if cx:
            ax_ci.scatter(cx, cy, marker="x", s=60, color="red", zorder=5)

        # marker '*' oranye: guard-flip Clear->Forward
        fi = guard_flips(series)
        fx = [series[i]["lam"] for i in fi]
        fy = [series[i]["RR"] for i in fi]
        fc = [series[i]["CI"] for i in fi]
        if fx:
            ax_rr.scatter(fx, fy, marker="*", s=140, color="darkorange",
                          zorder=6, label=f"{lbl}: guard flip")
            ax_ci.scatter(fx, fc, marker="*", s=140, color="darkorange",
                          zorder=6)

    # garis referensi
    ax_rr.axhline(1.0, ls="--", lw=0.9, color="grey")
    ax_ci.axhline(0.0, ls="--", lw=0.9, color="grey")
    for ax in (ax_rr, ax_ci):
        ax.axvline(0.5, ls="--", lw=0.9, color="purple", alpha=0.7)
        ax.grid(True, alpha=0.35)

    ax_rr.set_ylabel("RR$_e(\\lambda)$")
    ax_rr.set_title(f"{title} — Score Ratio & Criticality vs $\\lambda$"
                    f"  (fine grid $\\Delta\\lambda$=0.05)")
    ax_ci.set_ylabel("CI$_e(\\lambda)$")
    ax_ci.set_xlabel("$\\lambda$  (factor kondisi; 1 = utuh, 0 = hapus-total)")
    ax_ci.set_xticks([round(1.0 - 0.1 * i, 1) for i in range(11)])

    h1, l1 = ax_rr.get_legend_handles_labels()
    ax_rr.legend(h1, l1, loc="center left", bbox_to_anchor=(1.01, 0.5),
                 fontsize=8, ncol=1, title="edge")
    fig.tight_layout()

    out_dir.mkdir(parents=True, exist_ok=True)      # folder auto-create
    path = out_dir / fname
    fig.savefig(path, format="pdf", bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv) -> int:
    print("=" * 78)
    print("GATE 6 — PLOT CURVES (fine_grid_output.csv -> 4 PDF)")
    print("=" * 78)
    if not IN_CSV.exists():
        print(f"ERROR: input tidak ada: {IN_CSV}\n"
              f"Jalankan dulu: python examples/fine_grid_runner.py")
        return 1

    data = load_series(IN_CSV)
    ok = True
    for mid, (fname, title) in MODEL_META.items():
        if mid not in data:
            print(f"FAIL  {mid}: tidak ditemukan dalam CSV")
            ok = False
            continue
        p = plot_model(mid, data[mid], fname, title, PLOT_DIR)
        exists = p.exists() and p.stat().st_size > 1000
        print(f"{'PASS' if exists else 'FAIL'}  {p.name:<32s} ({p.stat().st_size if p.exists() else 0} bytes)")
        ok = ok and exists

    print(f"\nFolder plot: {PLOT_DIR}")
    print("PLOT: PASS" if ok else "PLOT: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
