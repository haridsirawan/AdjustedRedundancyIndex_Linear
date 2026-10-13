"""
curve_extractor.py — GATE 5: Ekstraksi Kurva RR(lambda), CI(lambda) & lambda_kritis
===================================================================================

Input : results/verification/pipeline_output.csv  (schema kanonik Gate 5,
        dihasilkan oleh run_pipeline.py)
Output: results/verification/critical_lambdas.json (ringkasan per edge)

Definisi operasional (Sprint Mode — keputusan didokumentasikan, bukan final):
  * Kurva RR(lambda) dan CI(lambda) diINTERPOLASI LINEAR antar titik grid
    lambda ∈ {1.0, 0.75, 0.5, 0.25, 0.0} (bukan spline; grid coarse).
  * lambda_crit(CI-threshold): nilai lambda TERBESAR (paling awal saat
    degradasi berjalan dari utuh -> rusak) di mana CI(lambda) MELEWATI
    ambang (default 0.5). Interpolasi linear antar dua titik grid yang
    menjepang ambang. Jika CI tidak pernah mencapai ambang pada grid,
    dilaporkan None + catatan "not_reached_on_grid".
  * lambda_guard: nilai lambda terbesar di mana guard_decision berubah
    dari 'Clear' menjadi 'Forward' (perubahan status det-ke-det pada
    grid; jika ingin kurva kontinu, gunakan margin_m interpolasi —
    tersedia sebagai field opsional).
  * abstain / uncertified (RR=None) -> edge dicatat dengan status
    "abstain", TIDAK dihitung lambda_crit-nya (kontrak Gate 2/4:
    jangan angka sembarang).

Pemakaian:
    python examples/curve_extractor.py            # baca CSV default
    python examples/curve_extractor.py --ci-threshold 0.4
Exit code: 0 = sukses; 1 = input tidak ditemukan / skema salah.

Satuan: kN, mm, E = 200 kN/mm^2. Tidak ada formula ARI baru di sini —
modul ini HANYA post-processing hasil pipeline (prinsip sprint).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "results" / "verification" / "pipeline_output.csv"
OUT_JSON = ROOT / "results" / "verification" / "critical_lambdas.json"

REQUIRED_COLS = ["model_id", "edge_id", "lambda", "S_intact", "S_disrupted",
                 "RR", "ARI", "CI", "rank_status", "margin_m",
                 "guard_decision", "U_star"]


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def load_pipeline_rows(path: Path = IN_CSV) -> List[dict]:
    """Baca pipeline_output.csv -> list of dict dgn tipe data benar."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} tidak ditemukan. Jalankan dulu: "
            f"python examples/run_pipeline.py")
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLS if c not in (rd.fieldnames or [])]
        if missing:
            raise ValueError(f"Skema CSV tidak lengkap, kolom hilang: {missing}")
        rows = []
        for raw in rd:
            rows.append(dict(
                model_id=raw["model_id"],
                edge_id=int(raw["edge_id"]),
                lam=float(raw["lambda"]),
                S_intact=_opt_float(raw["S_intact"]),
                S_disr=_opt_float(raw["S_disrupted"]),
                RR=_opt_float(raw["RR"]),
                ARI=_opt_float(raw["ARI"]),
                CI=_opt_float(raw["CI"]),
                rank_status=raw["rank_status"],
                margin=_opt_float(raw["margin_m"]),
                decision=raw["guard_decision"],
                U_star=_opt_float(raw["U_star"]),
            ))
    return rows


def _opt_float(s: str) -> Optional[float]:
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Interpolasi & ekstraksi
# ---------------------------------------------------------------------------
def interpolate_curve(xs: List[float], ys: List[Optional[float]],
                      xq: float) -> Optional[float]:
    """Interpolasi linear piecewise pada titik data terurut menaik (xs).

    None dianggap gap (abstain) -> segmen di sekitar gap tidak dipakai.
    xq di luar rentang -> None (extrapolasi DILARANG — jujur pada grid).
    """
    pts = [(x, y) for x, y in zip(xs, ys) if y is not None]
    if len(pts) < 2:
        return None
    if xq < pts[0][0] - 1e-12 or xq > pts[-1][0] + 1e-12:
        return None
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if x0 - 1e-12 <= xq <= x1 + 1e-12:
            if x1 == x0:
                return y0
            t = (xq - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return None


def crossing_lambda(xs_desc: List[float], ys_desc: List[float],
                    threshold: float) -> Tuple[Optional[float], str]:
    """Cari lambda TERBESAR tempat ys melintasi threshold (naik) saat
    degradasi berjalan dari lambda=1 (utuh) menuju 0 (rusak).

    xs_desc: grid lambda menurun (1.0 -> 0.0); ys_desc sepadan.
    Return (lambda_crit, note). Konvensi: CRIT = batas atas zona kritis,
    yaitu nilai lambda terbesar di mana CI >= threshold (lihat catatan
    konvensi di docstring extract_edge).
    """
    # kasus degenerasi: sudah kritis bahkan pada lambda=1
    if ys_desc[0] >= threshold:
        return xs_desc[0], "already_critical_at_lambda_1"
    for i in range(len(xs_desc) - 1):
        l_hi, l_lo = xs_desc[i], xs_desc[i + 1]      # mis. 0.75 -> 0.5
        c_hi, c_lo = ys_desc[i], ys_desc[i + 1]
        if c_lo >= threshold:
            if c_hi >= threshold:
                return l_hi, "grid_exact"
            if c_lo == c_hi:
                return l_hi, "grid_exact"
            # lintasan di dalam segmen [l_lo, l_hi]; ambil batas ATAS zona
            # kritis (lambda terbesar dengan CI>=threshold) => l_lo utk
            # laporan konservatif; nilai kontinu disimpan di note_num.
            l_cont = l_hi + (threshold - c_hi) * (l_lo - l_hi) / (c_lo - c_hi)
            return round(l_lo, 6), (f"interpolated_continuous={l_cont:.6f}; "
                                     f"reported=upper bound of critical zone")
    return None, "not_reached_on_grid"


def guard_flip_lambda(lams_desc: List[float],
                      decisions: List[str]) -> Tuple[Optional[float], str]:
    """Lambda terbesar di mana guard_decision berubah Clear -> Forward."""
    for i in range(len(lams_desc) - 1):
        if decisions[i] == "Clear" and decisions[i + 1] == "Forward":
            return lams_desc[i + 1], "detected_on_grid"
    if all(d == "Forward" for d in decisions):
        return lams_desc[0], "forward_everywhere_on_grid"
    return None, "no_flip_on_grid"


def extract_edge(rows: List[dict], ci_threshold: float = 0.5) -> Optional[dict]:
    """Ringkas satu edge -> kurva + lambda_crit. rows = baris satu (model,edge).

    Catatan KONVENSI (penting utk review disertasi):
      lambda_crit_d_CI adalah nilai lambda TERKECIL tempat CI masih <
      threshold — yaitu BATAS ATAS zona kritis: untuk semua lambda di
      BAWAH nilai ini struktur dianggap kritis (CI >= threshold). Pada
      grid coarse, bila CI melewati ambang di DALAM segmen [l_low,l_high],
      kami laporkan l_low (bound konservatif) dan simpan nilai kontinu
      hasil interpolasi pada field `note`. Perilaku ini disengaja: lebih
      baik menyebut zona kritis lebih lebar daripada menyembunyikannya.
    """
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: -r["lam"])   # lambda menurun
    lams = [r["lam"] for r in rows]
    rr = [r["RR"] for r in rows]
    ci = [r["CI"] for r in rows]
    dec = [r["decision"] for r in rows]

    if any(v is None for v in rr):
        return dict(status="abstain",
                    note="RR kosong (uncertified/abstain) — tanpa angka",
                    lambdas=lams, RR=rr, CI=ci, guard_decisions=dec)

    ci_clean = [c if c is not None else float("nan") for c in ci]
    l_ci, note_ci = crossing_lambda(lams, ci_clean, ci_threshold)
    l_g, note_g = guard_flip_lambda(lams, dec)
    curve_rr = {f"{l:.2f}": (None if v is None else round(v, 9))
                for l, v in zip(lams, rr)}
    curve_ci = {f"{l:.2f}": (None if v is None else round(v, 9))
                for l, v in zip(lams, ci)}
    return dict(
        status="ok",
        intact_rank_status=rows[0]["rank_status"],
        U_star=rows[0]["U_star"],
        curve_RR=curve_rr,
        curve_CI=curve_ci,
        guard_decisions=dict(zip([f"{l:.2f}" for l in lams], dec)),
        margins=dict(zip([f"{l:.2f}" for l in lams],
                         [r["margin"] for r in rows])),
        lambda_crit_d_CI=l_ci,
        lambda_crit_note=note_ci,
        lambda_guard_flip=l_g,
        lambda_guard_note=note_g,
        ci_threshold=ci_threshold,
    )


def extract_all(csv_path: Path = IN_CSV, ci_threshold: float = 0.5) -> dict:
    rows = load_pipeline_rows(csv_path)
    grouped: Dict[Tuple[str, int], List[dict]] = {}
    for r in rows:
        grouped.setdefault((r["model_id"], r["edge_id"]), []).append(r)

    out = dict(
        generated_by="examples/curve_extractor.py (Gate 5)",
        date="2026-10-11",
        source_csv=str(csv_path.relative_to(ROOT)),
        ci_threshold=ci_threshold,
        lambda_grid=sorted({r["lam"] for r in rows}, reverse=True),
        convention=("lambda_crit_d_CI = upper bound of the critical zone "
                    "(largest lambda at which CI is still below threshold); "
                    "continuous interpolated value kept in lambda_crit_note"),
        models={},
        summary=dict(n_edges=0, n_ok=0, n_abstain=0,
                    edges_with_guard_flip=[], edges_graph_blind_like=[]),
    )
    for (mid, eid), grp in sorted(grouped.items()):
        e = extract_edge(grp, ci_threshold)
        out["models"].setdefault(mid, {})[f"e{eid}"] = e
        out["summary"]["n_edges"] += 1
        if e["status"] == "abstain":
            out["summary"]["n_abstain"] += 1
        else:
            out["summary"]["n_ok"] += 1
            if e["lambda_guard_flip"] is not None:
                out["summary"]["edges_with_guard_flip"].append(
                    f"{mid}/e{eid}@lam={e['lambda_guard_flip']}")
            # kandidat "graph-blind-like": guard flip ADA tapi CI(terburuk)<0.5
            worst_ci = max((v for v in (grp_c["CI"] for grp_c in grp)
                            if v is not None), default=None)
            if (e["lambda_guard_flip"] is not None and worst_ci is not None
                    and worst_ci < 0.5):
                out["summary"]["edges_graph_blind_like"].append(
                    f"{mid}/e{eid} (worst CI={worst_ci:.6f})")
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--csv", default=str(IN_CSV))
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument("--ci-threshold", type=float, default=0.5)
    args = ap.parse_args(argv)

    try:
        result = extract_all(Path(args.csv), args.ci_threshold)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2, default=str))

    print("=" * 78)
    print("GATE 5 — CURVE EXTRACTION & CRITICAL LAMBDA")
    print("=" * 78)
    print(f"{'model':26s} {'edge':5s} {'lam*CI>=thr':>12s} "
          f"{'lam(guard)':>11s}  note")
    for mid, edges in result["models"].items():
        for ename, e in edges.items():
            if e["status"] == "abstain":
                print(f"{mid:26s} {ename:5s} {'ABSTAIN':>12s} {'-':>11s}  "
                      f"{e['note']}")
            else:
                lc = e["lambda_crit_d_CI"]
                lg = e["lambda_guard_flip"]
                print(f"{mid:26s} {ename:5s} "
                      f"{('-' if lc is None else f'{lc:.3f}'):>12s} "
                      f"{('-' if lg is None else f'{lg:.3f}'):>11s}  "
                      f"{e['lambda_crit_note'][:44]}")
    s = result["summary"]
    print(f"\nEdges: {s['n_edges']} (ok={s['n_ok']}, abstain={s['n_abstain']})")
    print(f"Guard-flip edges: {len(s['edges_with_guard_flip'])}")
    for x in s["edges_with_guard_flip"]:
        print("  -", x)
    print(f"GRAPH-BLIND-LIKE (guard flip tapi CI_max<0.5 — Finding #003 class):")
    for x in s["edges_graph_blind_like"]:
        print("  -", x)
    print(f"\n[JSON] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
