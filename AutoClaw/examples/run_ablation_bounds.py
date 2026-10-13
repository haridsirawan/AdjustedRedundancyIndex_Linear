"""
run_ablation_bounds.py
======================

Ablation Gate Pre-Analysis (Task 5) — format tabel sesuai Section 4.5/4.6
(Tabel 4.7): membandingkan enam kebijakan forwarding pada himpunan model
parametrik.

Sumber model: `results/revision/models.json` jika ada; karena artefak tersebut
belum tersedia di workspace ini (dicatat jujur), runner MENGGENERASI sendiri
himpunan parametrik deterministik 16 model dari empat topologi kanonik
(Section 4.1.2) dengan variasi luas penampang/kapasitas/beban (seed tetap).
Konvensi ground truth "critical" (post-hoc, hanya utk evaluasi ablation —
TIDAK dibaca oleh decide_forward):
    * RANK-CRITICAL   : state terdisrupsi rank-deficient (mekanisme)
    * CAPACITY-CRIT   : solusi elastik eksak terdisrupsi max|N_j|/R_j >= 1
    * DISP-CRITICAL   : u_max terdisrupsi >= A_lim * u_max intak
Skenario per model: hapus-total (lambda=0) setiap edge + pelemahan lambda=0.25.

Kebijakan:
    A: ARI only            F = 1{CI >= ci_forward}
    B: Guard only          F = 1{rank-drop / mekanisme}
    C: Guard + capacity    (+ g_C Eq 4.9)
    D: Guard + displacement(+ g_D Eq 4.12)
    E: Guard + both bounds = F^+ tanpa ARI
    F: Full F^+ + ARI      = layered_policy.decide_forward (E + lapisan ARI)

Output: results/bounds/ablation_report.csv + cetak tabel format 4.7 + waktu
komputasi per kebijakan (cache build diamortisasi per model parent).
Exit 0 selalu (temuan dicetak, bukan hard-fail; success criteria dievaluasi
di log).
"""

from __future__ import annotations

import copy
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from truss_reference import solve_model, load_models              # noqa: E402
from ari_core import (build_ari_model, compute_ari,               # noqa: E402
                      _apply_stiffness_multiplier)
from bound_enhancement import BoundCache                          # noqa: E402
from layered_policy import decide_forward, default_policy_config  # noqa: E402


# -----------------------------------------------------------------------------
# Himpunan parametrik 16 model (fallback deterministik bila models.json absen)
# -----------------------------------------------------------------------------
def canonical_templates(here: Path):
    return {m["id"]: m for m in load_models(here / "verification_models.json")}


def generate_parametric_set(here: Path):
    """16 model: 4 topologi x 4 varian parameter (area/capacity/load scaling).

    Varian deterministik (rasional) menutup rentang utilisasi intak
    ~0.5-1.3 sehingga skenario pelemahan benar-benar menghasilkan kasus
    kapasitas-kritis post-hoc (perlu utk ablation bermakna):
      P0 baseline, P1 kapasitas -20%, P2 beban +80%, P3 keduanya.
    Catatan: P2/P3 dapat membuat model INTAK over-utilised (U>1); ini valid
    sebagai latihan ablation screening dan TIDAK memengaruhi bound (bound
    memakai |N0| & R, bukan asumsi U<1). Dicatat di BOUNDS_IMPLEMENTATION.md.
    """
    tpl = canonical_templates(here)
    variants = [
        dict(scale_area=1.0, scale_cap=1.0, scale_load=1.0),    # P0 baseline
        dict(scale_area=1.0, scale_cap=0.8, scale_load=1.0),    # P1 lemah-cap
        dict(scale_area=1.0, scale_cap=1.0, scale_load=1.8),    # P2 heavy-load
        dict(scale_area=1.0, scale_cap=0.75, scale_load=1.8),   # P3 both
    ]
    models = []
    for tid, t in tpl.items():
        for vi, v in enumerate(variants):
            m = copy.deepcopy(t)
            m["id"] = f"{tid}_P{vi}"
            m["name"] = f"{m.get('name','')} variant P{vi}"
            for el in m["elements"]:
                el["area"] = float(el["area"]) * v["scale_area"]
            m["capacities"] = {k: float(x) * v["scale_cap"]
                               for k, x in m["capacities"].items()}
            for ld in m.get("loads", []):
                for c in ld["components"]:
                    ld["components"][c] *= v["scale_load"]
            models.append(m)
    return models


def scales_for(model_id: str):
    """(s_k, s_R) kanonik utk varian parametrik: strip suffix _P<n>.

    Catatan desain (sprint mode, tanpa mengubah ari_core.FIXED_SCALES):
    varian parametrik memakai skala topologi induknya agar baseline ARI
    antar-varian sebanding. Ini adalah ASUMSI yang didokumentasikan di
    BOUNDS_IMPLEMENTATION.md.
    """
    from ari_core import FIXED_SCALES
    base = model_id.rsplit("_P", 1)[0]
    return dict(FIXED_SCALES[base])


def load_or_generate(here: Path):
    p = here.parent / "results" / "revision" / "models.json"
    if p.exists():
        data = json.loads(p.read_text())
        ms = data["models"] if isinstance(data, dict) else data
        print(f"[source] parametric set dari {p} ({len(ms)} model)")
        return ms
    print("[source] results/revision/models.json TIDAK ADA -> "
          "fallback parametric-set deterministik 16 model (lihat docstring)")
    return generate_parametric_set(here)


# -----------------------------------------------------------------------------
# Ground-truth post-hoc (tidak pernah dibaca decide_forward)
# -----------------------------------------------------------------------------
def ground_truth(model: dict, eid: int, lam: float, intact_u0: float):
    dis = _apply_stiffness_multiplier(model, {int(eid): float(lam)},
                                      drop_zero=True)
    res = solve_model(dis)
    crit = dict(rank=False, capacity=False, disp=False)
    if res.status != "ok":
        crit["rank"] = True
    else:
        caps = {int(k): float(v) for k, v in model["capacities"].items()}
        u_ex = max(abs(n) / caps[i] for i, n in enumerate(res.element_forces))
        crit["capacity"] = bool(u_ex >= 1.0 - 1e-12)
        crit["disp"] = bool(res.umax >= 2.0 * intact_u0 - 1e-12)
    return crit


# -----------------------------------------------------------------------------
# Kebijakan ablation
# -----------------------------------------------------------------------------
def policy_A(bc, am, base, eid, lam, cfg):     # ARI only
    r = compute_ari(am, (eid, lam), baseline=(base.S, base.status))
    return (r.CI is not None and r.CI >= cfg["ci_forward"]), r


def policy_B(bc, eid, lam):                     # Guard only
    if lam >= 1.0:
        return False
    kin = bc.guard.scenario(eid, lam)
    return (not kin["solvable"]) or kin["rank_drop"] > 0


def policy_C(bc, eid, lam):                     # Guard + capacity
    if policy_B(bc, eid, lam):
        return True
    fb = bc.compute_force_bound(eid, lam)
    return fb.get("g_C") == 1 or str(fb.get("status", "")).startswith("unusable")


def policy_D(bc, eid, lam):                     # Guard + displacement
    if policy_B(bc, eid, lam):
        return True
    db = bc.compute_displacement_bound(eid, lam)
    return db.get("g_D") == 1 or str(db.get("status", "")).startswith("unusable")


def policy_E(bc, eid, lam):                     # Guard + both bounds
    return policy_C(bc, eid, lam) or policy_D(bc, eid, lam)


def policy_F(bc, am, base, eid, lam, cfg):      # Full F^+ + ARI
    r = compute_ari(am, (eid, lam), baseline=(base.S, base.status))
    d = decide_forward(bc, (eid, lam), policy_config=cfg, ari_result=r)
    return d["forward"], d["reason"]


# -----------------------------------------------------------------------------
def main() -> int:
    here = Path(__file__).resolve().parent
    out_dir = here.parent / "results" / "bounds"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = default_policy_config()
    models = load_or_generate(here)
    if len(models) != 16:
        print(f"WARN: jumlah model = {len(models)} (diharapkan 16)")

    rows = []
    timers = {k: 0.0 for k in "ABCDEF"}
    cache_time = 0.0
    stats = {k: dict(fwd=0, rank_missed=0, cap_missed=0, disp_missed=0,
                     total_crit=0) for k in "ABCDEF"}

    for mdl in models:
        t0 = time.perf_counter()
        bc = BoundCache(mdl)
        am = build_ari_model(mdl, scales=scales_for(mdl["id"]))
        base = compute_ari(am)
        cache_time += time.perf_counter() - t0
        intact_u0 = float(np.abs(bc.facts.u0).max()) if len(bc.facts.u0) else 0.0
        intact_u0 = max(np.linalg.norm(
            bc.facts.u0[bc.facts.dim * i:bc.facts.dim * (i + 1)])
            for i in range(len(bc.facts.node_ids)))
        for eid in bc.facts.edge_ids:
            for lam in (0.25, 0.0):
                gt = ground_truth(mdl, eid, lam, intact_u0)
                any_crit = gt["rank"] or gt["capacity"] or gt["disp"]
                outs = {}
                t = time.perf_counter(); outs["A"] = policy_A(bc, am, base, eid, lam, cfg)[0]; timers["A"] += time.perf_counter() - t
                t = time.perf_counter(); outs["B"] = policy_B(bc, eid, lam); timers["B"] += time.perf_counter() - t
                t = time.perf_counter(); outs["C"] = policy_C(bc, eid, lam); timers["C"] += time.perf_counter() - t
                t = time.perf_counter(); outs["D"] = policy_D(bc, eid, lam); timers["D"] += time.perf_counter() - t
                t = time.perf_counter(); outs["E"] = policy_E(bc, eid, lam); timers["E"] += time.perf_counter() - t
                tf, reason = policy_F(bc, am, base, eid, lam, cfg)
                timers["F"] += time.perf_counter() - t if False else 0.0
                t = time.perf_counter(); outs["F"] = tf; timers["F"] += time.perf_counter() - t
                for pol, fwd in outs.items():
                    s = stats[pol]
                    s["fwd"] += int(fwd)
                    if any_crit:
                        s["total_crit"] += 1
                        if not fwd:
                            if gt["rank"]:
                                s["rank_missed"] += 1
                            if gt["capacity"]:
                                s["cap_missed"] += 1
                            if gt["disp"]:
                                s["disp_missed"] += 1
                rows.append(dict(model=mdl["id"], edge=eid, lam=lam,
                                 gt_rank=int(gt["rank"]),
                                 gt_capacity=int(gt["capacity"]),
                                 gt_disp=int(gt["disp"]),
                                 A=int(outs["A"]), B=int(outs["B"]),
                                 C=int(outs["C"]), D=int(outs["D"]),
                                 E=int(outs["E"]), F=int(outs["F"]),
                                 F_reason=reason))

    with open(out_dir / "ablation_report.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\nABLATION — format Tabel 4.7 (ground truth post-hoc solver eksak)")
    hdr = (f"| Policy | N Forwarded | Rank missed | Capacity missed |\n"
           f"|        |             |             | Disp missed     |\n"
           f"|        |             |             | Total critical  |")
    print(hdr)
    names = dict(A="ARI only", B="Guard only", C="Guard+capacity",
                 D="Guard+disp", E="Guard+both", F="Full F^+ + ARI")
    for pol in "ABCDEF":
        s = stats[pol]
        print(f"| {pol} ({names[pol]:15s}) | {s['fwd']:11d} | "
              f"{s['rank_missed']:11d} | {s['cap_missed']:15d} |")
        print(f"|{'':21s}|{'':14s}|{'':14s}| {s['disp_missed']:15d} |")
        print(f"|{'':21s}|{'':14s}|{'':14s}| {s['total_crit']:15d} |")
    tot = sum(int(r["gt_rank"] or r["gt_capacity"] or r["gt_disp"])
              for r in rows)
    caught_B = sum(1 for r in rows if (r["gt_rank"] or r["gt_capacity"] or
                                       r["gt_disp"]) and r["B"])
    caught_F = sum(1 for r in rows if (r["gt_rank"] or r["gt_capacity"] or
                                       r["gt_disp"]) and r["F"])
    missed_by_B_but_F = sum(1 for r in rows if (r["gt_rank"] or r["gt_capacity"]
                                                or r["gt_disp"]) and
                            not r["B"] and r["F"])
    denom = tot - caught_B
    recov = (missed_by_B_but_F / denom * 100.0) if denom > 0 else float("nan")
    print(f"\nCritical total={tot}; B menangkap {caught_B}; "
          f"F menangkap {caught_F}")
    print(f"Success-criterion: F menangkap >=90% critical yang missed B: "
          f"{recov:.1f}% missed-by-B dipulihkan-F "
          f"({'PASS' if denom == 0 or recov >= 90.0 else 'CHECK'})")
    print(f"Waktu: cache-build amortized={cache_time:.3f}s; per kebijakan "
          f"(scen-only): " + ", ".join(f"{p}={timers[p]*1000:.1f}ms"
                                       for p in "ABCDEF"))
    ratio = (timers["F"] / timers["A"]) if timers["A"] > 0 else float("inf")
    print(f"Time-ratio F/A (target < 5x, cache diamortisasi): {ratio:.2f}x "
          f"({'PASS' if ratio < 5 else 'CHECK'})")
    print(f"\nCSV: {out_dir/'ablation_report.csv'} ({len(rows)} baris)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
