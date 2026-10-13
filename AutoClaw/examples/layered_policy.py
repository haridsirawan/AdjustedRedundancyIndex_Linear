"""
layered_policy.py
=================

Layered Forwarding Policy F^+ — Section 4.5 disertasi ARI (Eq 4.13):

    F^+(s) = 1{ F(s)=1  OR  g(s)=1  OR  g_C(s)=1  OR  g_D(s)=1
                 OR  bound_unusable }

dengan urutan evaluasi KRITIS (short-circuit, Eq 4.13 step order):

    1. Kinematic guard DULU  — jika m_s dekat nol / state rank-deficient
       (mekanisme), forward segera; JANGAN evaluasi D_{j,s} yang membagi ~0.
    2. Capacity bound (g_C, Eq 4.9)   — hanya jika langkah 1 lolos.
    3. Displacement bound (g_D, Eq 4.12) — hanya jika langkah 1-2 lolos.
    4. Bound unusable/invalid -> abstain dari numerik TAPI tetap FORWARD
       (konservatif: "Never silently under-bound").

JAMINAN PRE-ANALYSIS (§4.5.6 leakage): fungsi ini TIDAK PERNAH membaca output
solver pasca-disrupsi. Satu-satunya input mekanik adalah ``BoundCache`` yang
dibangun dari model INTAK. Status rank terdisrupsi guard Gate 3 dipakai lewat
getter cache (bukan solusi pasca-disrupsi); ia adalah sinyal KINEMATIKA
(rank/solvabilitas), bukan hasil perpindahan/gaya pasca-disrupsi, dan hanya
memicu forward (tidak pernah memfilter keluar). Keputusan dapat direproduksi
hanya dengan data intak bila mode config ``use_disrupted_rank_signal=False``.

Dependencies: bound_enhancement.BoundCache (Gate Pre-Analysis Task 1),
ari_core.compute_ari (F(s) berbasis CI — opsional via policy_config['ari']).

Satuan: kN, mm, E = 200 kN/mm^2.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bound_enhancement import BoundCache, default_bound_config  # noqa: E402


def default_policy_config() -> dict:
    """Config beku kebijakan berlapis (ambang terpusat, bukan magic number)."""
    cfg = default_bound_config()
    cfg.update(dict(
        ci_forward=0.5,                      # ambang F(s)=1{CI >= ci_forward}
        use_disrupted_rank_signal=True,      # sinyal rank guard utk ordering-1
        require_ari=False,                   # True -> abstain jika ARI None
    ))
    return cfg


def decide_forward(am_or_cache, disruption, policy_config: Optional[dict] = None,
                   ari_result=None) -> dict:
    """Keputusan forwarding berlapis F^+ untuk skenario s=(e, lambda). Eq 4.13.

    Parameters
    ----------
    am_or_cache : BoundCache | AriModelData
        BoundCache (hasil pre-analysis). Jika AriModelData diberikan, cache
        dibangun otomatis dari .model (biaya sekali per model parent).
    disruption : tuple(int, float) | None
        (edge_id e, lambda). None => kontrol state utuh (tidak ada disrupsi).
    policy_config : dict, optional
        Override ``default_policy_config()``.
    ari_result : ScenarioResult | None, optional
        Hasil compute_ari untuk skenario yang sama (lapisan F(s)). Boleh None:
        maka komponen ARI dianggap tidak tersedia (bukan pelanggaran kontrak —
        F^+ tetap konservatif lewat bounds).

    Returns
    -------
    dict dengan:
        forward : bool
        reason  : 'kinematic_guard' | 'capacity_bound' | 'displacement_bound'
                  | 'ari_threshold' | 'abstention' | 'not_forwarded'
        details : dict intermediate lengkap (audit trail)

    Raises
    ------
    ValueError : jika disruption malformed.
    NOTE: fungsi ini tidak pernah memanggil solver pasca-disrupsi (kontrak).
    """
    cfg = default_policy_config()
    if policy_config:
        cfg.update(policy_config)

    if isinstance(am_or_cache, BoundCache):
        bc = am_or_cache
    else:                                     # AriModelData duck-type
        bc = BoundCache(am_or_cache.model,
                        config={k: cfg[k] for k in default_bound_config()})

    details = {"cache_model": bc.facts.model_id}

    # --- kontrol tanpa-edge / lambda==1: tidak ada disrupsi fisik -------------
    if disruption is None:
        fb = db = None
        forward = False
        reason = "not_forwarded"
        if ari_result is not None and ari_result.CI is not None \
                and ari_result.CI >= cfg["ci_forward"]:
            forward, reason = True, "ari_threshold"
        details.update(control_intact=True, force_bound=None,
                       disp_bound=None, kinematic=None)
        return dict(forward=forward, reason=reason, details=details)

    e, lam = int(disruption[0]), float(disruption[1])
    if not (0.0 <= lam <= 1.0):
        raise ValueError(f"lambda={lam} di luar [0,1]")

    # ================= STEP 1: KINEMATIC GUARD (paling awal!) ================
    # Ordering kritis Eq 4.13: m_s ~ 0 / mekanisme -> forward, jangan evaluasi
    # D_{j,s}. Sumber: GuardCache (rank) + m_factor internal cache intak.
    kin = None
    if lam < 1.0 and cfg["use_disrupted_rank_signal"]:
        kin = bc.guard.scenario(e, lam)       # getter reuse Gate 3
        details["kinematic"] = kin
        m_s = bc.m_factor(e, lam)
        details["m_s"] = m_s
        if (not kin.get("solvable", True)) or m_s < cfg["m_margin"]:
            return dict(forward=True, reason="kinematic_guard", details=details)
    elif lam < 1.0:
        m_s = bc.m_factor(e, lam)
        details["m_s"] = m_s
        if m_s < cfg["m_margin"]:
            return dict(forward=True, reason="kinematic_guard", details=details)

    # ================= STEP 2: CAPACITY BOUND (Eq 4.9) =======================
    fb = bc.compute_force_bound(e, lam)
    details["force_bound"] = {k: v for k, v in fb.items()}
    st_f = fb.get("status")
    if st_f == "ok" and fb.get("g_C") == 1:
        return dict(forward=True, reason="capacity_bound", details=details)
    if st_f not in ("ok", "no_redistribution", "control_ok"):
        # unusable_m_near_zero sudah tertangkap step 1; sisanya -> abstain
        if cfg["require_ari"] and (ari_result is None
                                   or ari_result.RR is None):
            return dict(forward=True, reason="abstention", details=details)
        if st_f.startswith("unusable"):
            return dict(forward=True, reason="abstention", details=details)

    # ================= STEP 3: DISPLACEMENT BOUND (Eq 4.12) ==================
    db = bc.compute_displacement_bound(e, lam)
    details["disp_bound"] = {k: v for k, v in db.items()}
    st_d = db.get("status")
    if st_d == "ok" and db.get("g_D") == 1:
        return dict(forward=True, reason="displacement_bound", details=details)
    if st_d.startswith("unusable"):
        return dict(forward=True, reason="abstention", details=details)

    # ================= STEP 4: LAPISAN ARI F(s) ==============================
    if ari_result is not None:
        if ari_result.RR is None or ari_result.status in ("abstain",
                                                           "uncertified",
                                                           "rank_deficient"):
            return dict(forward=True, reason="abstention", details=details)
        if ari_result.CI is not None and ari_result.CI >= cfg["ci_forward"]:
            return dict(forward=True, reason="ari_threshold", details=details)

    return dict(forward=False, reason="not_forwarded", details=details)
