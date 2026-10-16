"""
freeze_protocol_config.py
=========================

Modul Pembekuan Protokol & Konfigurasi (Gate 14 — W5: Protocol Freezing)
untuk Penelitian Disertasi: "Adjusted Redundancy Index (ARI)" — Harids Irawan (2026).

Sesuai Spesifikasi Naskah Disertasi (Bagian 3.9.4–3.9.5, 3.12–3.13, 4.9.2, 4.10.1, dan 5.2):
--------------------------------------------------------------------------------------------
Membekukan seluruh parameter formula ARI, ambang penapisan (tau), toleransi numerik
solver & pengaman kinematik, definisi label kritis, partisi data 300 model (dengan
kunci segel pada blind_val dan final_test), benih acak (seed = 2026), prosedur
inferensi bootstrap, serta hash SHA-256 kode dan artefak dataset SEBELUM evaluasi
validasi buta (blind_val) dibuka.

Keluaran:
---------
- results/screening/manifest_config_frozen.json
- results/dataset/manifest_config_frozen.json
- manifest_config_frozen.json (salinan indeks root repositori)

Jalankan:
    python3 examples/freeze_protocol_config.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import ari_core as ac
import bound_enhancement as be
import layered_policy as lp
import mechanical_guard as mg
import structural_solvers as ss


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_frozen_manifest() -> Dict[str, Any]:
    dataset_dir = REPO_ROOT / "results" / "dataset"
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest tidak ditemukan: {manifest_path}")

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    models = manifest_data["models"]

    # 1. Rincian partisi data & kunci segel blind_val / final_test
    splits_detail: Dict[str, Any] = {}
    for sp in ["formula_dev", "calibration", "blind_val", "final_test"]:
        m_sp = [m for m in models if m["split"] == sp]
        fam_breakdown: Dict[str, Any] = {}
        for fam in ["S1_beam", "S2_truss", "S3_frame", "S4_braced_frame", "S5_space_truss"]:
            m_fam = [m for m in m_sp if m["family"] == fam]
            fam_breakdown[fam] = {
                "n_models": len(m_fam),
                "n_elements": sum(m["n_elements"] for m in m_fam),
                "n_scenarios": sum(m["n_scenarios"] for m in m_fam),
                "model_id_range": f"{m_fam[0]['model_id']}..{m_fam[-1]['model_id']}" if m_fam else "",
                "model_ids": [m["model_id"] for m in m_fam],
            }
        # Hash gabungan dari seluruh sha256_spec di partisi ini
        split_hash_input = "|".join(f"{m['model_id']}:{m['sha256_spec']}" for m in m_sp)
        split_sha256 = hashlib.sha256(split_hash_input.encode("utf-8")).hexdigest()

        splits_detail[sp] = {
            "role": {
                "formula_dev": "Pemilihan rumus, eksplorasi fitur, dan validasi silang berkelompok (CV)",
                "calibration": "Kalibrasi ambang penapisan (tau) dan aturan penerusan pra-analisis",
                "blind_val": "Validasi buta bebas penyetelan ulang (TERKUNCI sebelum keputusan penerusan disimpan)",
                "final_test": "Uji akhir independen lintas keluarga (TERKUNCI hingga evaluasi validasi buta selesai)",
            }[sp],
            "n_models": len(m_sp),
            "n_elements": sum(m["n_elements"] for m in m_sp),
            "n_scenarios": sum(m["n_scenarios"] for m in m_sp),
            "labels_locked_blind": sp in ("blind_val", "final_test"),
            "tuning_allowed": sp in ("formula_dev", "calibration"),
            "split_spec_sha256": split_sha256,
            "families": fam_breakdown,
        }

    # 2. Hash kode di examples/
    code_hashes: Dict[str, str] = {}
    for fn in sorted(os.listdir(HERE)):
        p = HERE / fn
        if p.is_file() and fn != "freeze_protocol_config.py" and (fn.endswith(".py") or fn.endswith(".json")):
            code_hashes[fn] = sha256_file(p)

    # 3. Hash artefak dataset di results/dataset/
    dataset_hashes: Dict[str, str] = {}
    for fn in sorted(os.listdir(dataset_dir)):
        p = dataset_dir / fn
        if p.is_file() and not fn.startswith(".") and fn != "manifest_config_frozen.json":
            dataset_hashes[fn] = sha256_file(p)

    # 4. Susun struktur manifest_config_frozen
    frozen_payload: Dict[str, Any] = {
        "protocol_id": "ARI-FROZEN-PROTOCOL-v1.0",
        "version": "1.0.0",
        "gate": "Gate 14 (W5 — Pembekuan Protokol Pra-Validasi Buta)",
        "status": "FROZEN_PRE_BLIND_VALIDATION",
        "frozen_date": "2026-10-16",
        "author": "Harids Irawan, S.T., M.T.",
        "institution": "Program Doktor Ilmu Teknik, Konsentrasi Teknik Sipil, Sekolah Pascasarjana Universitas Negeri Yogyakarta",
        "dissertation_sections": [
            "Bagian 3.9.4 (Aturan Pemilihan Ambang yang Dapat Diaudit)",
            "Bagian 3.9.5 (Ablasi, Pembekuan, dan Pembukaan Data Buta)",
            "Bagian 3.10–3.13 (Acuan Mekanis, Pembanding, Gerbang Validasi A–D, Inferensi Statistik)",
            "Bagian 4.9.2 & 4.10.1 (Protokol Finalisasi Naskah dan Data & Keluaran Validasi Utama)",
            "Bagian 5.2 (Ketertelusuran dan Keputusan yang Masih Terbuka)"
        ],
        "units_system": {
            "force": "kN",
            "length": "mm",
            "area": "mm^2",
            "inertia": "mm^4",
            "elastic_modulus": "kN/mm^2",
            "stress": "kN/mm^2",
            "moment": "kN*mm",
            "strain_energy": "kN*mm",
            "default_steel_E": float(ss.DEFAULT_E)
        },
        "random_seeds": {
            "master_seed": 2026,
            "dataset_generation_seed": 2026,
            "family_seed_offsets": {
                "S1_beam": 20261,
                "S2_truss": 20262,
                "S3_frame": 20263,
                "S4_braced_frame": 20264,
                "S5_space_truss": 20265
            },
            "bootstrap_inference_seed": 2026,
            "random_baseline_screening_seed": 2026
        },
        "ari_formula_config": {
            "alpha_k": float(ac.DEFAULT_CONFIG["alpha_k"]),
            "alpha_R": float(ac.DEFAULT_CONFIG["alpha_R"]),
            "alpha_sum_constraint": 1.0,
            "q_e_canonical": 1.0,
            "K_max_edge_disjoint_paths": int(ac.DEFAULT_CONFIG["K"]),
            "gamma_path_rank_decay": float(ac.DEFAULT_CONFIG["gamma"]),
            "beta_support_reaction_floor": float(ac.DEFAULT_CONFIG["beta"]),
            "eta_utilization_penalty": float(ac.DEFAULT_CONFIG["eta"]),
            "disruption_lambdas": [0.0, 0.25, 0.50, 0.75],
            "intact_control_included": True,
            "disruption_rule_lambda_pos": "w_e -> lambda * w_e (tanpa renormalisasi ulang skala s_k, s_R — Bagian 4.8.4)",
            "disruption_rule_lambda_zero": "Sisi e dihapus eksak dari graf skor G_{M_e,0} (Bagian 2.8)",
            "path_search_method": "Enumerasi jalur sederhana edge-disjoint eksak (tersertifikasi, Bagian 4.8.6)",
            "fixed_scales_canonical": ac.FIXED_SCALES,
            "family_default_scales": {
                "S1_beam": {"s_k": 20.0, "s_R": 80.0},
                "S2_truss": {"s_k": 20.0, "s_R": 80.0},
                "S3_frame": {"s_k": 20.0, "s_R": 80.0},
                "S4_braced_frame": {"s_k": 20.0, "s_R": 80.0},
                "S5_space_truss": {"s_k": 20.0, "s_R": 80.0}
            }
        },
        "numerical_tolerances": {
            "eps_w_edge_weight_reg": float(ac.EPS_W),
            "eps_d_path_distance_reg": float(ac.EPS_D),
            "eps_R_capacity_reg": float(ac.EPS_R),
            "baseline_score_tol": float(ac.BASELINE_TOL),
            "solver_rank_tol_relative": float(ss.RANK_TOL_RELATIVE),
            "solver_singular_policy": "REJECT_NO_PSEUDOINVERSE (status='rank_deficient')",
            "analytical_verification_rel_tol": 0.01,
            "guard_margin_tol_m_s": float(mg.MARGIN_TOL),
            "bound_d0_floor_mm": float(be.default_bound_config()["d0_floor"]),
            "bound_h_floor": float(be.default_bound_config()["h_floor"]),
            "bound_near_zero_force_kN": float(be.default_bound_config()["near_zero_force"]),
            "max_search_time_s": float(ac.MAX_SEARCH_TIME_S) if ac.MAX_SEARCH_TIME_S is not None else None,
            "max_search_nodes": 200000,
            "unit_invariance_tol": 1e-12
        },
        "screening_thresholds_and_policy": {
            "tau_ci_primary": 0.50,
            "forwarding_rule_eq_3_12": "F = {s in S : CI_s >= tau_CI} U G_guard U A_abstain",
            "abstention_rule": "Semua skenario dengan status invalid_baseline, search_timeout, atau uncertified WAJIB diteruskan (forward=True)",
            "kinematic_guard_enabled": True,
            "kinematic_guard_rule_eq_4_5": "g(s) = 1 bila m_e(lambda) <= 1e-8 atau K_{e,lambda} rank_deficient -> langsung diteruskan",
            "calibration_grid_T": {
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "n_points": 101,
                "selection_rule_eq_3_1_3_2": "tau* = min argmax_{tau in T_layak} Reduksi_cal(tau) dengan L_cal,0.95(tau) >= 0.95 dan Reduksi_cal(tau) >= 0.30"
            },
            "pre_analysis_bounds_config": be.default_bound_config(),
            "layered_policy_config": lp.default_policy_config(),
            "k8_policy_status": {
                "decision_id": "K8",
                "current_active_policy": "P0 (CI >= 0.50 U Kinematic Guard g(s)=1 U Abstention)",
                "candidate_policies_documented": {
                    "P0": {"rule": "CI >= 0.50 U g(s)=1", "dev_272_forwarded": 52, "dev_272_recall_B": 0.6056, "dev_272_reduction": 0.8088},
                    "P1_recommended": {"rule": "P0 U (lambda == 0.0)", "dev_272_forwarded": 84, "dev_272_recall_B": 0.8732, "dev_272_reduction": 0.6912},
                    "P5_conservative": {"rule": "P0 U (lambda <= 0.25 and CI > 0.35)", "dev_272_forwarded": 70, "dev_272_recall_B": 0.7746, "dev_272_reduction": 0.7426}
                },
                "note": "Titik operasi dasar dibekukan pada tau_CI = 0.50 (P0); kandidat lapisan kehati-hatian P1 dan P5 terdaftar resmi untuk evaluasi komparatif terpisah pada partisi kalibrasi sesuai protokol Bagian 3.9.4–3.9.5."
            }
        },
        "critical_label_and_reference_protocol": {
            "critical_set_definition_eq_3_9": "C = C_peringkat U C_konsekuensi U C_mekanisme",
            "n_ref_formula_eq_3_8": "n_ref = min(N, max(3, ceil(0.10 * N)))",
            "tie_breaking_rule": "Include all tied scenarios at the n_ref boundary (aturan ikatan inklusif)",
            "diagnostic_criticality_criteria": {
                "mechanism": "rank(K_ff(s)) < n_free (singular / mekanisme kinematik)",
                "utilization_exceeded": "U_max(s) > 1.0 (konvensi A: kapasitas state gangguan; konvensi B: kapasitas awal utuh — keduanya dilaporkan berdampingan)",
                "displacement_amplification": "u_max(s) > 2.0 * u_max(0) (A_lim = 2.0)"
            },
            "response_change_indicators_eq_3_3_3_6": ["delta_u", "delta_U", "delta_F", "delta_k"],
            "anti_leakage_contract": "Penyaring (ARI + pengaman) DILARANG membaca kolom respons pascagangguan. Keputusan penerusan disimpan beserta hash SHA-256 sebelum label evaluasi validasi buta dibuka."
        },
        "validation_gates_targets": {
            "Gate_A_mathematical_algorithmic": {
                "range_ari_ci": "[0.0, 1.0]",
                "unit_invariance_max_diff": 1e-12,
                "intact_control_rr": 1.0,
                "post_disruption_leakage": 0
            },
            "Gate_B_mechanical_conformity": {
                "spearman_rho_median_min": 0.70,
                "spearman_rho_ci95_lower_min": 0.50,
                "delta_rho_vs_best_baseline_median_min": 0.10,
                "top_n_ref_coverage_min": 0.80,
                "top1_ci_in_top3_crc": True,
                "normalized_rank_error_median_max": 0.15
            },
            "Gate_C_stability_and_ablation": {
                "perturbation_grid_relative": [-0.10, -0.05, -0.01, 0.01, 0.05, 0.10],
                "rank_correlation_perturbed_min": 0.80,
                "jaccard_critical_set_min": 0.80,
                "mandatory_ablations": [
                    "no_utilization_adjustment (eta = 0)",
                    "single_shortest_path (K = 1)",
                    "stiffness_only_weight (alpha_k = 1.0, alpha_R = 0.0)",
                    "capacity_only_weight (alpha_k = 0.0, alpha_R = 1.0)",
                    "uniform_support_weight (beta = 1.0)",
                    "guard_only_vs_ari_only_vs_combined"
                ]
            },
            "Gate_D_operational_screening": {
                "mean_model_recall_ci95_lower_min": 0.95,
                "mean_model_reduction_min": 0.30,
                "recall_gain_over_random_equal_budget_min": 0.15,
                "recall_gain_over_baseline_ci95_lower_gt": 0.0,
                "bootstrap_resamples_B": 10000,
                "bootstrap_clustering_unit": "parent_model_id (mengambil ulang model induk beserta seluruh skenario turunannya — Persamaan 3.10)",
                "bootstrap_quantile_alpha_one_sided": 0.05
            }
        },
        "dataset_partitions": {
            "total_parent_models": int(manifest_data["total_models"]),
            "total_elements": int(manifest_data["total_elements"]),
            "total_scenarios": int(manifest_data["total_scenarios"]),
            "families": ["S1_beam", "S2_truss", "S3_frame", "S4_braced_frame", "S5_space_truss"],
            "splits": splits_detail
        },
        "software_environment": {
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "platform": platform.platform()
        },
        "artifact_hashes_sha256": {
            "examples_code": code_hashes,
            "dataset_files": dataset_hashes
        }
    }

    # Hitung self-integrity seal SHA-256 atas canonical JSON dari frozen_payload
    canonical_bytes = json.dumps(frozen_payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    frozen_payload["frozen_config_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()
    return frozen_payload


def main() -> None:
    payload = build_frozen_manifest()
    json_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    out_paths = [
        REPO_ROOT / "results" / "screening" / "manifest_config_frozen.json",
        REPO_ROOT / "results" / "dataset" / "manifest_config_frozen.json",
        REPO_ROOT / "manifest_config_frozen.json",
    ]
    for p in out_paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json_text, encoding="utf-8")
        print(f"[SAVED] {p.relative_to(REPO_ROOT)} (SHA-256 config: {payload['frozen_config_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
