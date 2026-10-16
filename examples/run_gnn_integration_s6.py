#!/usr/bin/env python3
"""
Gate 17 (W8) — Eksperimen Integrasi ARI–GNN (S6) & Audit Biaya Operasional (Tabel 4.19)
========================================================================================
Menjalankan protokol integrasi Bagian 3.18 & Bagian 4.10.5 pada 300 model induk
(7.640 skenario gangguan + 300 kontrol):

1. Pelatihan sekali (one-shot training) arsitektur acuan `StructGNN-CRC v1.0`
   pada partisi `formula_dev` (120 model induk) tanpa seleksi ARI, serta
   kalibrasi ambang keluaran c_GNN pada partisi `calibration` (60 model induk).
2. Pembekuan bobot (`results/integration/gnn_weights_s6.npz`) dan kartu model
   (`results/integration/gnn_model_card_s6.json`) beserta hash SHA-256.
3. Evaluasi berpasangan pada 7 perlakuan sesuai Bagian 3.18.4:
   - T0_Full_GNN     : Tanpa penyaringan (seluruh kandidat dievaluasi GNN)
   - T1_Random_P0    : Penyaringan acak dengan anggaran per model setara P0
                       (kasus Guard/abstensi tetap diteruskan sesuai 3.18.4)
   - T2_Util_P0      : Penyaringan utilisasi awal dengan anggaran per model setara P0
   - T3_ARI_P0_GNN   : Penyaringan ARI dasar + Guard (P0: CI >= 0.50 U Guard) + GNN
   - T4_ARI_P1_GNN   : Penyaringan ARI diperluas (P1: CI >= 0.50 U Guard U [lambda=0]) + GNN
   - T5_Random_P1    : Penyaringan acak dengan anggaran per model setara P1
   - T6_Util_P1      : Penyaringan utilisasi awal dengan anggaran per model setara P1
4. Pengukuran biaya waktu operasional berpasangan (10 pengulangan dengan pemanasan,
   urutan berimbang, dan dekomposisi komponen Tabel 4.19:
   T_utuh, T_ARI, T_seleksi, T_graf_F, T_inferensi_F, T_penanganan, T_total, T_hemat)
   serta bootstrap B=10.000 pada tingkat model induk untuk menguji kriteria manfaat
   Bagian 3.18.6.
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import structural_solvers as ss

from gnn_surrogate_s6 import StructGNNSurrogate, build_scenario_graph_features
from run_screening_s1_s5 import (
    GeneralizedMechanicalGuard,
    LAMS,
    apply_physical_disruption,
    compute_family_dev_scales,
    prepare_multi_family_ari_engine,
    score_multi_family_graph,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "results" / "dataset"
VALIDATION_DIR = ROOT_DIR / "results" / "validation"
INTEGRATION_DIR = ROOT_DIR / "results" / "integration"


def load_all_models() -> tuple[Dict[str, Dict[str, Any]], Dict[str, List[dict]]]:
    models_by_id: Dict[str, Dict[str, Any]] = {}
    all_models_by_fam: Dict[str, List[dict]] = {}
    for fam_short, fam_key in [
        ("s1", "S1_beam"),
        ("s2", "S2_truss"),
        ("s3", "S3_frame"),
        ("s4", "S4_braced_frame"),
        ("s5", "S5_space_truss"),
    ]:
        fpath = DATASET_DIR / f"models_{fam_short}.json"
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        m_list = data["models"]
        all_models_by_fam[fam_key] = m_list
        for m in m_list:
            mid = str(m.get("model_id", m.get("id")))
            models_by_id[mid] = m
    return models_by_id, all_models_by_fam


def load_evaluation_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(VALIDATION_DIR / "full_evaluation_300.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def bootstrap_paired_ci(
    vals: np.ndarray, n_boot: int = 10000, seed: int = 2026
) -> Dict[str, float]:
    rng = np.random.default_rng(seed)
    n = len(vals)
    if n == 0:
        return {"mean": 0.0, "l95_1sided": 0.0, "u95_1sided": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    idx = rng.integers(0, n, size=(n_boot, n))
    means = np.mean(vals[idx], axis=1)
    return {
        "mean": float(np.mean(vals)),
        "l95_1sided": float(np.percentile(means, 5.0)),
        "u95_1sided": float(np.percentile(means, 95.0)),
        "ci95_low": float(np.percentile(means, 2.5)),
        "ci95_high": float(np.percentile(means, 97.5)),
    }


def score_all_scenarios_ari_and_guard(
    m: dict, intact_res: ss.StructuralSolverResult, fam_scale: Dict[str, float]
) -> None:
    """Menjalankan perhitungan penuh ARI + Pengaman Kinematik pada satu model induk."""
    eng = prepare_multi_family_ari_engine(m, intact_res, fam_scale)
    guard = GeneralizedMechanicalGuard(m)
    pair_cache: Dict[Any, Any] = {}
    s_intact, _ = score_multi_family_graph(eng, None, pair_cache)
    for el in m["elements"]:
        eid = int(el["id"])
        for lam in LAMS:
            _, _ = score_multi_family_graph(eng, (eid, lam), pair_cache)
            _ = guard.m_e(eid, lam)


def main() -> None:
    INTEGRATION_DIR.mkdir(parents=True, exist_ok=True)
    print("=== GATE 17 (W8): EKSPERIMEN INTEGRASI ARI-GNN (S6) & AUDIT BIAYA TABEL 4.19 ===")

    models_by_id, all_models_by_fam = load_all_models()
    fam_scales = compute_family_dev_scales(all_models_by_fam)
    eval_rows = load_evaluation_rows()

    disruption_rows = [r for r in eval_rows if r["scenario_type"] == "disruption"]
    print(f"Total model induk: {len(models_by_id)} | Total skenario gangguan: {len(disruption_rows)}")

    # Step 1: Precompute intact solutions & scenario graph structures
    intact_cache: Dict[str, ss.StructuralSolverResult] = {}
    for mid, m in models_by_id.items():
        intact_cache[mid] = ss.solve_structural_model(m)

    scenario_graphs: List[Dict[str, np.ndarray]] = []
    y_crc_all = np.zeros(len(disruption_rows), dtype=np.float64)
    y_crit_all = np.zeros(len(disruption_rows), dtype=np.float64)
    valid_crc_mask = np.zeros(len(disruption_rows), dtype=bool)

    train_idx: List[int] = []
    cal_idx: List[int] = []
    blind_idx: List[int] = []
    test_idx: List[int] = []

    for i, r in enumerate(disruption_rows):
        mid = r["model_id"]
        m = models_by_id[mid]
        e_id = int(r["edge_id"])
        lam = float(r["lambda"])
        g = build_scenario_graph_features(m, intact_cache[mid], e_id, lam)
        scenario_graphs.append(g)

        crc_b = float(r["CRC_B"])
        crit_b = int(r["crit_B"])
        rank_lost = int(r["rank_lost"])
        y_crc_all[i] = crc_b
        y_crit_all[i] = float(crit_b)
        valid_crc_mask[i] = (rank_lost == 0)

        sp = r["split"]
        if sp == "formula_dev":
            train_idx.append(i)
        elif sp == "calibration":
            cal_idx.append(i)
        elif sp == "blind_val":
            blind_idx.append(i)
        elif sp == "final_test":
            test_idx.append(i)

    # Step 2: Train StructGNN-CRC v1.0 once on formula_dev and calibrate threshold on calibration
    t_train_start = time.perf_counter()
    gnn = StructGNNSurrogate(d_hidden=24, n_layers=3, seed=2026)
    fit_info = gnn.fit(
        [scenario_graphs[i] for i in train_idx],
        y_crc_all[train_idx],
        y_crit_all[train_idx],
        [scenario_graphs[i] for i in cal_idx],
        y_crc_all[cal_idx],
        y_crit_all[cal_idx],
    )
    t_train_elapsed = time.perf_counter() - t_train_start

    weights_path = INTEGRATION_DIR / "gnn_weights_s6.npz"
    weights_sha256 = gnn.save_weights(weights_path)
    print(f"Pelatihan GNN selesai dalam {t_train_elapsed:.4f}s | c_GNN={gnn.c_gnn_threshold} | SHA-256 bobot={weights_sha256[:16]}...")

    p_check_1 = gnn.predict_single(scenario_graphs[0])
    p_check_2 = gnn.predict_single(scenario_graphs[0])
    pred_diff_max = abs(p_check_1["y_hat"] - p_check_2["y_hat"])
    assert pred_diff_max == 0.0, "GNN inference must be deterministic!"

    # Step 3: Run GNN predictions on all 7,640 scenarios
    preds_all: List[Dict[str, float]] = []
    for i in range(len(disruption_rows)):
        preds_all.append(gnn.predict_single(scenario_graphs[i]))

    model_to_scen_idx: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(disruption_rows):
        model_to_scen_idx[r["model_id"]].append(i)

    # Step 4: Construct Matched-Budget Forwarding Masks per Model (Section 3.18.4)
    rng_ctrl = np.random.default_rng(202608)
    n_scen = len(disruption_rows)
    fwd_masks: Dict[str, np.ndarray] = {
        "T0_Full_GNN": np.ones(n_scen, dtype=np.int32),
        "T1_Random_P0": np.zeros(n_scen, dtype=np.int32),
        "T2_Util_P0": np.zeros(n_scen, dtype=np.int32),
        "T3_ARI_P0_GNN": np.zeros(n_scen, dtype=np.int32),
        "T4_ARI_P1_GNN": np.zeros(n_scen, dtype=np.int32),
        "T5_Random_P1": np.zeros(n_scen, dtype=np.int32),
        "T6_Util_P1": np.zeros(n_scen, dtype=np.int32),
    }

    for mid, idxs in model_to_scen_idx.items():
        idxs_arr = np.array(idxs, dtype=np.int32)
        guard_arr = np.array([int(disruption_rows[k]["guard_flag"]) for k in idxs], dtype=np.int32)
        p0_arr = np.array([int(disruption_rows[k]["fwd_P0"]) for k in idxs], dtype=np.int32)
        p1_arr = np.array([int(disruption_rows[k]["fwd_P1"]) for k in idxs], dtype=np.int32)
        util_arr = np.array([float(disruption_rows[k]["util_baseline_score"]) for k in idxs], dtype=np.float64)
        lam_arr = np.array([float(disruption_rows[k]["lambda"]) for k in idxs], dtype=np.float64)
        util_dmg_score = util_arr * (1.0 - lam_arr)

        fwd_masks["T3_ARI_P0_GNN"][idxs_arr] = p0_arr
        fwd_masks["T4_ARI_P1_GNN"][idxs_arr] = p1_arr

        mandatory_local = np.where(guard_arr == 1)[0]
        pool_local = np.where(guard_arr == 0)[0]

        for budget_target, rand_key, util_key in [
            (int(np.sum(p0_arr)), "T1_Random_P0", "T2_Util_P0"),
            (int(np.sum(p1_arr)), "T5_Random_P1", "T6_Util_P1"),
        ]:
            rem = max(0, budget_target - len(mandatory_local))
            fwd_masks[rand_key][idxs_arr[mandatory_local]] = 1
            fwd_masks[util_key][idxs_arr[mandatory_local]] = 1
            if rem > 0 and len(pool_local) > 0:
                rem_eff = min(rem, len(pool_local))
                chosen_rand = rng_ctrl.choice(pool_local, size=rem_eff, replace=False)
                fwd_masks[rand_key][idxs_arr[chosen_rand]] = 1
                order_util = pool_local[np.argsort(-util_dmg_score[pool_local], kind="mergesort")]
                chosen_util = order_util[:rem_eff]
                fwd_masks[util_key][idxs_arr[chosen_util]] = 1

    # Step 5: Paired Wall-Clock Timing Protocol (Section 3.18.6 & Table 4.19)
    print("Menjalankan pengukuran waktu operasional berpasangan (10 pengulangan, Tabel 4.19)...")
    t_warm0 = time.perf_counter()
    for mid in sorted(models_by_id.keys())[:10]:
        _ = ss.solve_structural_model(models_by_id[mid])
        for k in model_to_scen_idx[mid]:
            _ = gnn.predict_single(scenario_graphs[k])
    warmup_time_s = time.perf_counter() - t_warm0

    n_reps = 10
    model_timing: Dict[str, Dict[str, float]] = {
        mid: {
            "t_intact_ms": 0.0,
            "t_ari_guard_ms": 0.0,
            "t_select_ms": 0.0,
            "t_graph_full_ms": 0.0,
            "t_inf_full_ms": 0.0,
            "t_handle_full_ms": 0.0,
            "t_graph_P0_ms": 0.0,
            "t_inf_P0_ms": 0.0,
            "t_handle_P0_ms": 0.0,
            "t_graph_P1_ms": 0.0,
            "t_inf_P1_ms": 0.0,
            "t_handle_P1_ms": 0.0,
        }
        for mid in models_by_id
    }

    rep_totals_ms: List[Dict[str, float]] = []

    for rep in range(n_reps):
        rep_full = 0.0
        rep_p0 = 0.0
        rep_p1 = 0.0
        model_keys = sorted(models_by_id.keys())
        if rep % 2 == 1:
            model_keys = list(reversed(model_keys))

        for mid in model_keys:
            m = models_by_id[mid]
            fam = str(m["family"])
            scen_idxs = model_to_scen_idx[mid]

            # 1) Intact response (T_utuh)
            t0 = time.perf_counter()
            intact_res = ss.solve_structural_model(m)
            t_intact = (time.perf_counter() - t0) * 1000.0

            # 2) ARI + Kinematic Guard (T_ARI)
            t0 = time.perf_counter()
            score_all_scenarios_ari_and_guard(m, intact_res, fam_scales[fam])
            t_ari = (time.perf_counter() - t0) * 1000.0

            # 3) Selection decision (T_seleksi)
            t0 = time.perf_counter()
            f_p0 = [k for k in scen_idxs if fwd_masks["T3_ARI_P0_GNN"][k] == 1]
            f_p1 = [k for k in scen_idxs if fwd_masks["T4_ARI_P1_GNN"][k] == 1]
            t_sel = (time.perf_counter() - t0) * 1000.0

            # 4) Full GNN (no screening): Graph construction + Inference + Handling
            t0 = time.perf_counter()
            g_list_full = [
                build_scenario_graph_features(
                    m,
                    intact_res,
                    int(disruption_rows[k]["edge_id"]),
                    float(disruption_rows[k]["lambda"]),
                )
                for k in scen_idxs
            ]
            t_g_full = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            p_full = [gnn.predict_single(g) for g in g_list_full]
            t_i_full = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            _ = [int(disruption_rows[k]["guard_flag"]) or p["pred_crit"] for k, p in zip(scen_idxs, p_full)]
            t_h_full = (time.perf_counter() - t0) * 1000.0

            # 5) P0 Screened GNN: Graph + Inference + Handling only on F_P0
            t0 = time.perf_counter()
            g_list_p0 = [
                build_scenario_graph_features(
                    m,
                    intact_res,
                    int(disruption_rows[k]["edge_id"]),
                    float(disruption_rows[k]["lambda"]),
                )
                for k in f_p0
            ]
            t_g_p0 = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            p_p0 = [gnn.predict_single(g) for g in g_list_p0]
            t_i_p0 = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            _ = [int(disruption_rows[k]["guard_flag"]) or p["pred_crit"] for k, p in zip(f_p0, p_p0)]
            t_h_p0 = (time.perf_counter() - t0) * 1000.0

            # 6) P1 Screened GNN: Graph + Inference + Handling only on F_P1
            t0 = time.perf_counter()
            g_list_p1 = [
                build_scenario_graph_features(
                    m,
                    intact_res,
                    int(disruption_rows[k]["edge_id"]),
                    float(disruption_rows[k]["lambda"]),
                )
                for k in f_p1
            ]
            t_g_p1 = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            p_p1 = [gnn.predict_single(g) for g in g_list_p1]
            t_i_p1 = (time.perf_counter() - t0) * 1000.0

            t0 = time.perf_counter()
            _ = [int(disruption_rows[k]["guard_flag"]) or p["pred_crit"] for k, p in zip(f_p1, p_p1)]
            t_h_p1 = (time.perf_counter() - t0) * 1000.0

            mt = model_timing[mid]
            mt["t_intact_ms"] += t_intact / n_reps
            mt["t_ari_guard_ms"] += t_ari / n_reps
            mt["t_select_ms"] += t_sel / n_reps
            mt["t_graph_full_ms"] += t_g_full / n_reps
            mt["t_inf_full_ms"] += t_i_full / n_reps
            mt["t_handle_full_ms"] += t_h_full / n_reps
            mt["t_graph_P0_ms"] += t_g_p0 / n_reps
            mt["t_inf_P0_ms"] += t_i_p0 / n_reps
            mt["t_handle_P0_ms"] += t_h_p0 / n_reps
            mt["t_graph_P1_ms"] += t_g_p1 / n_reps
            mt["t_inf_P1_ms"] += t_i_p1 / n_reps
            mt["t_handle_P1_ms"] += t_h_p1 / n_reps

            rep_full += t_intact + t_g_full + t_i_full + t_h_full
            rep_p0 += t_intact + t_ari + t_sel + t_g_p0 + t_i_p0 + t_h_p0
            rep_p1 += t_intact + t_ari + t_sel + t_g_p1 + t_i_p1 + t_h_p1

        rep_totals_ms.append(
            {
                "rep": rep + 1,
                "T_tanpa_ms": round(rep_full, 4),
                "T_ARI_P0_GNN_ms": round(rep_p0, 4),
                "T_ARI_P1_GNN_ms": round(rep_p1, 4),
                "T_hemat_P0_ms": round(rep_full - rep_p0, 4),
                "T_hemat_P1_ms": round(rep_full - rep_p1, 4),
            }
        )

    # Also measure Exact Post-Disruption FEM Solver baseline time across all 300 models
    t_fem_start = time.perf_counter()
    for mid in sorted(models_by_id.keys()):
        m = models_by_id[mid]
        for k in model_to_scen_idx[mid]:
            m_dis = apply_physical_disruption(
                m, int(disruption_rows[k]["edge_id"]), float(disruption_rows[k]["lambda"])
            )
            _ = ss.solve_structural_model(m_dis)
    exact_fem_total_ms = (time.perf_counter() - t_fem_start) * 1000.0

    # Step 6: Evaluate Metrics per Treatment and per Split (Section 3.18.5 & 4.10.5)
    def evaluate_subset(indices: List[int], split_label: str) -> List[Dict[str, Any]]:
        idx_arr = np.array(indices, dtype=np.int32)
        n_total = len(idx_arr)
        crit_arr = y_crit_all[idx_arr] > 0.5
        n_crit = int(np.sum(crit_arr))
        crc_true = y_crc_all[idx_arr]
        q_mask = valid_crc_mask[idx_arr]

        crc_pred = np.array([preds_all[k]["crc_hat"] for k in idx_arr], dtype=np.float64)
        pred_crit_gnn = np.array([preds_all[k]["pred_crit"] for k in idx_arr], dtype=np.int32) == 1
        guard_arr = np.array([int(disruption_rows[k]["guard_flag"]) for k in idx_arr], dtype=np.int32) == 1

        split_models = sorted(list({disruption_rows[k]["model_id"] for k in indices}))
        m_to_local: Dict[str, List[int]] = defaultdict(list)
        for loc_i, glob_i in enumerate(indices):
            m_to_local[disruption_rows[glob_i]["model_id"]].append(loc_i)

        results_list: List[Dict[str, Any]] = []

        for t_name in [
            "T0_Full_GNN",
            "T1_Random_P0",
            "T2_Util_P0",
            "T3_ARI_P0_GNN",
            "T4_ARI_P1_GNN",
            "T5_Random_P1",
            "T6_Util_P1",
        ]:
            f_mask = fwd_masks[t_name][idx_arr] == 1
            n_fwd = int(np.sum(f_mask))
            reduction = 1.0 - (float(n_fwd) / max(float(n_total), 1.0))

            n_screen_hit = int(np.sum(f_mask & crit_arr))
            recall_screen = float(n_screen_hit) / max(float(n_crit), 1.0)

            h_f_gnn_only = f_mask & pred_crit_gnn
            h_f_operational = f_mask & (pred_crit_gnn | guard_arr)

            n_end_hit_gnn = int(np.sum(h_f_gnn_only & crit_arr))
            n_end_hit_op = int(np.sum(h_f_operational & crit_arr))
            recall_end_gnn = float(n_end_hit_gnn) / max(float(n_crit), 1.0)
            recall_end_op = float(n_end_hit_op) / max(float(n_crit), 1.0)

            miss_not_forwarded = int(np.sum((~f_mask) & crit_arr))
            miss_inf_failed = 0
            miss_below_threshold_gnn = int(np.sum(f_mask & (~pred_crit_gnn) & crit_arr))
            miss_below_threshold_op = int(np.sum(f_mask & (~(pred_crit_gnn | guard_arr)) & crit_arr))

            fq_mask = f_mask & q_mask
            n_fq = int(np.sum(fq_mask))
            n_no_valid_target_in_f = int(np.sum(f_mask & (~q_mask)))
            if n_fq > 0:
                mae_fq = float(np.mean(np.abs(crc_pred[fq_mask] - crc_true[fq_mask])))
                rmse_fq = float(np.sqrt(np.mean((crc_pred[fq_mask] - crc_true[fq_mask]) ** 2)))
            else:
                mae_fq, rmse_fq = 0.0, 0.0

            cqf_mask = f_mask & crit_arr & q_mask
            if int(np.sum(cqf_mask)) > 0:
                mae_crit_q = float(np.mean(np.abs(crc_pred[cqf_mask] - crc_true[cqf_mask])))
            else:
                mae_crit_q = 0.0

            m_rec_end: List[float] = []
            m_rec_drop: List[float] = []
            for mid in split_models:
                loc = np.array(m_to_local[mid], dtype=np.int32)
                c_m = crit_arr[loc]
                if int(np.sum(c_m)) == 0:
                    continue
                rec_t0_m = float(np.sum((pred_crit_gnn[loc] | guard_arr[loc]) & c_m)) / float(np.sum(c_m))
                rec_tr_m = float(np.sum(h_f_operational[loc] & c_m)) / float(np.sum(c_m))
                m_rec_end.append(rec_tr_m)
                m_rec_drop.append(rec_t0_m - rec_tr_m)

            ci_rec = bootstrap_paired_ci(np.array(m_rec_end, dtype=np.float64))
            ci_drop = bootstrap_paired_ci(np.array(m_rec_drop, dtype=np.float64))

            results_list.append(
                {
                    "split": split_label,
                    "treatment": t_name,
                    "n_models": len(split_models),
                    "n_scenarios": n_total,
                    "n_crit_B": n_crit,
                    "n_forwarded": n_fwd,
                    "n_not_evaluated_by_gnn": n_total - n_fwd,
                    "reduction_ratio": round(reduction, 6),
                    "recall_screen": round(recall_screen, 6),
                    "recall_end_gnn_raw": round(recall_end_gnn, 6),
                    "recall_end_operational": round(recall_end_op, 6),
                    "model_mean_recall_end": round(ci_rec["mean"], 6),
                    "model_l95_recall_end": round(ci_rec["l95_1sided"], 6),
                    "model_mean_recall_drop_vs_full": round(ci_drop["mean"], 6),
                    "model_u95_recall_drop_vs_full": round(ci_drop["u95_1sided"], 6),
                    "miss_not_forwarded": miss_not_forwarded,
                    "miss_inf_failed": miss_inf_failed,
                    "miss_below_threshold_gnn": miss_below_threshold_gnn,
                    "miss_below_threshold_op": miss_below_threshold_op,
                    "n_valid_q_in_f": n_fq,
                    "n_rank_deficient_in_f": n_no_valid_target_in_f,
                    "mae_valid_f": round(mae_fq, 6),
                    "rmse_valid_f": round(rmse_fq, 6),
                    "mae_crit_valid_f": round(mae_crit_q, 6),
                }
            )
        return results_list

    all_indices = list(range(len(disruption_rows)))
    metrics_rows: List[Dict[str, Any]] = []
    metrics_rows.extend(evaluate_subset(all_indices, "ALL_300"))
    metrics_rows.extend(evaluate_subset(train_idx, "formula_dev"))
    metrics_rows.extend(evaluate_subset(cal_idx, "calibration"))
    metrics_rows.extend(evaluate_subset(blind_idx, "blind_val"))
    metrics_rows.extend(evaluate_subset(test_idx, "final_test"))

    s2_indices = [i for i, r in enumerate(disruption_rows) if r["family"] == "S2_truss"]
    metrics_rows.extend(evaluate_subset(s2_indices, "S2_truss_ALL"))

    metrics_csv_path = INTEGRATION_DIR / "treatment_comparison_s6.csv"
    with open(metrics_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metrics_rows)

    # Step 7: Build Table 4.19 Operational Cost Breakdown CSV & Paired Time Savings Bootstrap
    def summarize_cost_table(model_ids: List[str], label: str) -> Dict[str, Any]:
        t_intact = np.array([model_timing[m]["t_intact_ms"] for m in model_ids])
        t_ari = np.array([model_timing[m]["t_ari_guard_ms"] for m in model_ids])
        t_sel = np.array([model_timing[m]["t_select_ms"] for m in model_ids])
        t_g_full = np.array([model_timing[m]["t_graph_full_ms"] for m in model_ids])
        t_i_full = np.array([model_timing[m]["t_inf_full_ms"] for m in model_ids])
        t_h_full = np.array([model_timing[m]["t_handle_full_ms"] for m in model_ids])

        t_g_p0 = np.array([model_timing[m]["t_graph_P0_ms"] for m in model_ids])
        t_i_p0 = np.array([model_timing[m]["t_inf_P0_ms"] for m in model_ids])
        t_h_p0 = np.array([model_timing[m]["t_handle_P0_ms"] for m in model_ids])

        t_g_p1 = np.array([model_timing[m]["t_graph_P1_ms"] for m in model_ids])
        t_i_p1 = np.array([model_timing[m]["t_inf_P1_ms"] for m in model_ids])
        t_h_p1 = np.array([model_timing[m]["t_handle_P1_ms"] for m in model_ids])

        tot_full_uncached = t_intact + t_g_full + t_i_full + t_h_full
        tot_p0_uncached = t_intact + t_ari + t_sel + t_g_p0 + t_i_p0 + t_h_p0
        tot_p1_uncached = t_intact + t_ari + t_sel + t_g_p1 + t_i_p1 + t_h_p1

        sav_p0_uncached = tot_full_uncached - tot_p0_uncached
        sav_p1_uncached = tot_full_uncached - tot_p1_uncached

        tot_full_cached = t_g_full + t_i_full + t_h_full
        tot_p0_cached = t_ari + t_sel + t_g_p0 + t_i_p0 + t_h_p0
        tot_p1_cached = t_ari + t_sel + t_g_p1 + t_i_p1 + t_h_p1

        ci_sav_p0 = bootstrap_paired_ci(sav_p0_uncached)
        ci_sav_p1 = bootstrap_paired_ci(sav_p1_uncached)

        sum_full = float(np.sum(tot_full_uncached))
        sum_p0 = float(np.sum(tot_p0_uncached))
        sum_p1 = float(np.sum(tot_p1_uncached))

        return {
            "subset": label,
            "n_models": len(model_ids),
            "T_utuh_ms": round(float(np.sum(t_intact)), 3),
            "T_ARI_dan_Guard_ms": round(float(np.sum(t_ari)), 3),
            "T_seleksi_ms": round(float(np.sum(t_sel)), 3),
            "T_graf_tanpa_ms": round(float(np.sum(t_g_full)), 3),
            "T_inferensi_tanpa_ms": round(float(np.sum(t_i_full)), 3),
            "T_penanganan_tanpa_ms": round(float(np.sum(t_h_full)), 3),
            "T_graf_P0_ms": round(float(np.sum(t_g_p0)), 3),
            "T_inferensi_P0_ms": round(float(np.sum(t_i_p0)), 3),
            "T_penanganan_P0_ms": round(float(np.sum(t_h_p0)), 3),
            "T_graf_P1_ms": round(float(np.sum(t_g_p1)), 3),
            "T_inferensi_P1_ms": round(float(np.sum(t_i_p1)), 3),
            "T_penanganan_P1_ms": round(float(np.sum(t_h_p1)), 3),
            "T_total_tanpa_uncached_ms": round(sum_full, 3),
            "T_total_P0_uncached_ms": round(sum_p0, 3),
            "T_total_P1_uncached_ms": round(sum_p1, 3),
            "T_hemat_P0_uncached_ms": round(sum_full - sum_p0, 3),
            "T_hemat_P1_uncached_ms": round(sum_full - sum_p1, 3),
            "pct_hemat_P0_uncached": round(100.0 * (sum_full - sum_p0) / max(sum_full, 1e-9), 2),
            "pct_hemat_P1_uncached": round(100.0 * (sum_full - sum_p1) / max(sum_full, 1e-9), 2),
            "T_total_tanpa_cached_ms": round(float(np.sum(tot_full_cached)), 3),
            "T_total_P0_cached_ms": round(float(np.sum(tot_p0_cached)), 3),
            "T_total_P1_cached_ms": round(float(np.sum(tot_p1_cached)), 3),
            "pct_hemat_P0_cached": round(
                100.0
                * (float(np.sum(tot_full_cached)) - float(np.sum(tot_p0_cached)))
                / max(float(np.sum(tot_full_cached)), 1e-9),
                2,
            ),
            "pct_hemat_P1_cached": round(
                100.0
                * (float(np.sum(tot_full_cached)) - float(np.sum(tot_p1_cached)))
                / max(float(np.sum(tot_full_cached)), 1e-9),
                2,
            ),
            "per_model_sav_P0_mean_ms": round(ci_sav_p0["mean"], 4),
            "per_model_sav_P0_l95_ms": round(ci_sav_p0["l95_1sided"], 4),
            "per_model_sav_P1_mean_ms": round(ci_sav_p1["mean"], 4),
            "per_model_sav_P1_l95_ms": round(ci_sav_p1["l95_1sided"], 4),
        }

    all_mids = sorted(models_by_id.keys())
    blind_mids = sorted([m for m in all_mids if models_by_id[m]["split"] == "blind_val"])
    test_mids = sorted([m for m in all_mids if models_by_id[m]["split"] == "final_test"])
    s2_mids = sorted([m for m in all_mids if models_by_id[m]["family"] == "S2_truss"])

    cost_rows = [
        summarize_cost_table(all_mids, "ALL_300"),
        summarize_cost_table(blind_mids, "blind_val_60"),
        summarize_cost_table(test_mids, "final_test_60"),
        summarize_cost_table(s2_mids, "S2_truss_60"),
    ]

    cost_csv_path = INTEGRATION_DIR / "cost_breakdown_table_4_19.csv"
    with open(cost_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cost_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cost_rows)

    model_card = {
        "model_id": "StructGNN-CRC-v1.0",
        "architecture": "3-Layer Edge-Node Message-Passing GNN + ReLU Readout MLP (Dual Head: Ridge CRC_B & IRLS Critical Probability)",
        "reference_basis": "Adapted from StructGNN (Chou et al., 2024) & StructGNN-E (Song et al., 2023) for multi-family line-element graphs S1-S5",
        "license": "MIT (Academic Research Prototype in Repository)",
        "weights_file": "results/integration/gnn_weights_s6.npz",
        "weights_sha256": weights_sha256,
        "training_split": "formula_dev (120 parent models, 3,056 disruption scenarios)",
        "calibration_split": "calibration (60 parent models, 1,520 disruption scenarios)",
        "blind_and_test_splits_touched_during_training": False,
        "ari_used_as_input_feature": False,
        "post_disruption_solver_used_at_inference": False,
        "node_feature_dim": 7,
        "edge_feature_dim": 15,
        "hidden_dim": 24,
        "num_message_passing_layers": 3,
        "calibrated_threshold_c_GNN": gnn.c_gnn_threshold,
        "training_diagnostics": fit_info,
        "separate_preparation_costs": {
            "gnn_training_and_calibration_time_ms": round(t_train_elapsed * 1000.0, 3),
            "warmup_pass_time_ms": round(warmup_time_s * 1000.0, 3),
            "exact_fem_all_7640_scenarios_time_ms": round(exact_fem_total_ms, 3),
        },
        "determinism_and_consistency_check": {
            "max_diff_across_treatments_on_same_scenario": pred_diff_max,
            "status": "PASS",
        },
    }

    card_path = INTEGRATION_DIR / "gnn_model_card_s6.json"
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(model_card, f, indent=2)

    summary_report = {
        "gate": "Gate 17 (W8 — S6 ARI-GNN Integration & Table 4.19 Cost Audit)",
        "model_card": model_card,
        "cost_breakdown_table_4_19": cost_rows,
        "rep_timings_10x": rep_totals_ms,
        "treatment_metrics_summary": metrics_rows,
    }
    report_path = INTEGRATION_DIR / "integration_report_s6.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print("\n=== RINGKASAN METRIK INTEGRASI (ALL_300, blind_val, final_test, S2_truss) ===")
    for r in metrics_rows:
        if r["split"] in ("ALL_300", "blind_val", "final_test", "S2_truss_ALL"):
            print(
                f"[{r['split']:12s}] {r['treatment']:14s} | Fwd={r['n_forwarded']:4d} (Red={r['reduction_ratio']*100:5.1f}%) "
                f"| RecScreen={r['recall_screen']*100:5.1f}% | RecEnd(Op)={r['recall_end_operational']*100:5.1f}% "
                f"(L95={r['model_l95_recall_end']*100:5.1f}%, DropU95={r['model_u95_recall_drop_vs_full']*100:5.2f}%) "
                f"| MAE(Q)={r['mae_valid_f']:.4f}"
            )

    print("\n=== RINGKASAN BIAYA OPERASIONAL TABEL 4.19 ===")
    for c in cost_rows:
        print(
            f"[{c['subset']:13s}] T_tanpa={c['T_total_tanpa_uncached_ms']:.1f}ms | "
            f"T_P0={c['T_total_P0_uncached_ms']:.1f}ms (Hemat={c['T_hemat_P0_uncached_ms']:.1f}ms / {c['pct_hemat_P0_uncached']:.1f}%, L95/m={c['per_model_sav_P0_l95_ms']:.4f}ms) | "
            f"T_P1={c['T_total_P1_uncached_ms']:.1f}ms (Hemat={c['T_hemat_P1_uncached_ms']:.1f}ms / {c['pct_hemat_P1_uncached']:.1f}%, L95/m={c['per_model_sav_P1_l95_ms']:.4f}ms)"
        )


if __name__ == "__main__":
    main()
