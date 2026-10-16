#!/usr/bin/env python3
"""
Gate 17 (W8) — Surrogate Graph Neural Network (StructGNN-CRC v1.0) untuk S6
===========================================================================
Implementasi Message-Passing Graph Neural Network (MP-GNN) berbasis arsitektur
StructGNN (Chou et al., 2024; Song et al., 2023) yang diadaptasi untuk prediksi
respons konsekuensi pascagangguan (CRC_B dan probabilitas kritis p_crit_B)
lintas lima keluarga struktur (S1–S5).

Prinsip Anti-Leakage & Kepatuhan Bagian 3.18 Disertasi:
-------------------------------------------------------
1. ARI, CI, RR, maupun h_e / guard_flag TIDAK menjadi fitur masukan GNN
   (Bagian 3.18.4: "ARI tidak menjadi fitur GNN. Graf suatu skenario memuat
   kondisi fisik gangguan yang sama di semua perlakuan").
2. Fitur graf skenario hanya berasal dari geometri, kekakuan fisik elemen,
   kapasitas elemen, faktor kerusakan fisik (lambda_s), kondisi batas tumpuan,
   beban eksternal, dan respons elastis model utuh pra-gangguan.
3. Pelatihan parameter GNN dilakukan SATU KALI secara eksklusif pada partisi
   pengembangan (`formula_dev`, 120 model induk) tanpa seleksi ARI, dengan
   validasi penghentian/ambang keluaran c_GNN pada partisi `calibration`
   (60 model induk). Partisi `blind_val` (60 model) dan `final_test` (60 model)
   tetap tertutup sepenuhnya selama pelatihan dan kalibrasi.
4. Bobot terlatih dibekukan dan disegel dengan hash SHA-256 di dalam
   `results/integration/gnn_model_card_s6.json` dan `gnn_weights_s6.npz`.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import structural_solvers as ss


FAMILY_ONEHOT = {
    "S1_beam": [1.0, 0.0, 0.0, 0.0, 0.0],
    "S2_truss": [0.0, 1.0, 0.0, 0.0, 0.0],
    "S3_frame": [0.0, 0.0, 1.0, 0.0, 0.0],
    "S4_braced_frame": [0.0, 0.0, 0.0, 1.0, 0.0],
    "S5_space_truss": [0.0, 0.0, 0.0, 0.0, 1.0],
}


def build_scenario_graph_features(
    model: Dict[str, Any],
    intact_res: ss.StructuralSolverResult,
    target_edge_id: int,
    lam: float,
) -> Dict[str, np.ndarray]:
    """
    Membangun representasi graf fisik skenario gangguan (V, E, X_V, X_E, endpoints)
    untuk inferensi GNN tanpa memasukkan skor ARI/CI/Guard.
    """
    fam = str(model["family"])
    nodes = model["nodes"]
    elements = model["elements"]
    n_nodes = len(nodes)
    n_edges = len(elements)

    # Map node id -> index 0..n_nodes-1
    sorted_nids = sorted(int(nd["id"]) for nd in nodes)
    nid_to_idx = {nid: i for i, nid in enumerate(sorted_nids)}

    coords = np.zeros((n_nodes, 3), dtype=np.float64)
    for nd in nodes:
        idx = nid_to_idx[int(nd["id"])]
        if "coords" in nd:
            c = [float(v) for v in nd["coords"]]
            while len(c) < 3:
                c.append(0.0)
        else:
            c = [float(nd.get("x", 0.0)), float(nd.get("y", 0.0)), float(nd.get("z", 0.0))]
        coords[idx, :] = c[:3]

    span_scale = max(float(np.ptp(coords[:, 0])), float(np.ptp(coords[:, 1])), 1.0)
    coords_norm = coords / span_scale

    # Supports per node from boundary_conditions
    supp_map: Dict[int, float] = {}
    for key, spec in model.get("boundary_conditions", {}).items():
        nid = int(key.split("_", 1)[1]) if "_" in str(key) else int(key)
        if nid not in nid_to_idx:
            continue
        idx = nid_to_idx[nid]
        if isinstance(spec, str):
            supp_map[idx] = 1.0 if "fix" in spec.lower() else 0.6
        elif isinstance(spec, list):
            supp_map[idx] = min(1.0, len(spec) / 3.0)
        elif isinstance(spec, dict):
            supp_map[idx] = min(1.0, len(spec) / 3.0)
        else:
            supp_map[idx] = 0.6

    # Loads per node
    load_mag = np.zeros(n_nodes, dtype=np.float64)
    for ld in model.get("loads", []):
        nid = int(ld["node"])
        if nid not in nid_to_idx:
            continue
        idx = nid_to_idx[nid]
        comps = ld.get("components", ld)
        sq = 0.0
        for k_c, v_c in comps.items():
            if k_c == "node":
                continue
            fv = float(v_c)
            if "m" in str(k_c).lower():
                fv /= 1000.0
            sq += fv * fv
        load_mag[idx] += math.sqrt(sq)
    max_load = max(float(np.max(load_mag)), 1.0)
    load_norm = load_mag / max_load

    # Node degree and edge endpoints
    deg = np.zeros(n_nodes, dtype=np.float64)
    edge_endpoints: List[Tuple[int, int]] = []
    target_idx_local = 0
    for e_i, el in enumerate(elements):
        eid = int(el["id"])
        u = nid_to_idx[int(el["nodes"][0])]
        v = nid_to_idx[int(el["nodes"][1])]
        edge_endpoints.append((u, v))
        if eid == target_edge_id:
            target_idx_local = e_i
        w_eff = float(lam) if eid == target_edge_id else 1.0
        deg[u] += w_eff
        deg[v] += w_eff
    max_deg = max(float(np.max(deg)), 1.0)

    # Node features X_V (dim = 7)
    X_V = np.zeros((n_nodes, 7), dtype=np.float64)
    for i in range(n_nodes):
        X_V[i, 0] = coords_norm[i, 0]
        X_V[i, 1] = coords_norm[i, 1]
        X_V[i, 2] = coords_norm[i, 2]
        X_V[i, 3] = supp_map.get(i, 0.0)
        X_V[i, 4] = load_norm[i]
        X_V[i, 5] = deg[i] / max_deg
        X_V[i, 6] = min(deg[i] / 6.0, 1.0)

    # Edge physical features X_E (dim = 15)
    u_intact_arr = np.zeros(n_edges, dtype=np.float64)
    stiff_arr = np.zeros(n_edges, dtype=np.float64)
    cap_arr = np.zeros(n_edges, dtype=np.float64)
    len_arr = np.zeros(n_edges, dtype=np.float64)

    for e_i, el in enumerate(elements):
        u, v = edge_endpoints[e_i]
        L = max(float(np.linalg.norm(coords[v] - coords[u])), 1.0)
        len_arr[e_i] = L
        E_mod = float(el.get("E", ss.DEFAULT_E))
        A_sec = float(el.get("A", el.get("area", 2000.0)))
        I_sec = float(el.get("I", 1.0e6))
        el_type = str(el.get("type", "")).lower()

        if fam in ("S2_truss", "S5_space_truss") or el_type == "brace":
            stiff_arr[e_i] = E_mod * A_sec / L
            cap_arr[e_i] = float(el.get("capacity", el.get("N_capacity", 300.0)))
        elif fam == "S1_beam":
            stiff_arr[e_i] = E_mod * I_sec / (L ** 3)
            cap_arr[e_i] = float(el.get("M_capacity", 50000.0))
        else:
            stiff_arr[e_i] = (E_mod * A_sec / L) + 12.0 * E_mod * I_sec / (L ** 3)
            cap_arr[e_i] = float(el.get("M_capacity", 100000.0))

        if e_i < len(intact_res.utilizations):
            u_intact_arr[e_i] = float(intact_res.utilizations[e_i])

    med_stiff = max(float(np.median(stiff_arr)), 1e-6)
    med_cap = max(float(np.median(cap_arr)), 1e-6)
    max_len = max(float(np.max(len_arr)), 1.0)
    u_max_0 = max(float(np.max(u_intact_arr)), 1e-6)
    u_mean_0 = float(np.mean(u_intact_arr))

    fam_oh = FAMILY_ONEHOT.get(fam, [0.0] * 5)

    X_E = np.zeros((n_edges, 15), dtype=np.float64)
    for e_i in range(n_edges):
        u, v = edge_endpoints[e_i]
        is_target = 1.0 if (e_i == target_idx_local and lam < 1.0) else 0.0
        lam_edge = float(lam) if e_i == target_idx_local else 1.0
        dmg_frac = 1.0 - lam_edge
        k_rel = min(stiff_arr[e_i] / med_stiff, 5.0) / 5.0
        c_rel = min(cap_arr[e_i] / med_cap, 5.0) / 5.0
        u0 = min(u_intact_arr[e_i], 2.0)
        min_d_uv = min(deg[u], deg[v]) / 6.0

        X_E[e_i, 0] = is_target
        X_E[e_i, 1] = lam_edge
        X_E[e_i, 2] = dmg_frac
        X_E[e_i, 3] = 1.0 if (is_target > 0.5 and lam_edge <= 1e-9) else 0.0
        X_E[e_i, 4] = k_rel * lam_edge
        X_E[e_i, 5] = c_rel * lam_edge
        X_E[e_i, 6] = u0
        X_E[e_i, 7] = u0 / u_max_0
        X_E[e_i, 8] = len_arr[e_i] / max_len
        X_E[e_i, 9] = min_d_uv
        X_E[e_i, 10:15] = fam_oh

    return {
        "X_V": X_V,
        "X_E": X_E,
        "endpoints": np.array(edge_endpoints, dtype=np.int32),
        "target_idx": np.int32(target_idx_local),
        "lam": np.float64(lam),
        "u_max_0": np.float64(u_max_0),
        "u_mean_0": np.float64(u_mean_0),
        "n_nodes": np.int32(n_nodes),
        "n_edges": np.int32(n_edges),
    }


class StructGNNSurrogate:
    """
    Message-Passing Graph Neural Network (3-Layer Edge-Node MP-GNN + Readout MLP)
    untuk memprediksi konsekuensi pascagangguan CRC_B dan skor probabilitas kritis.
    """

    def __init__(self, d_hidden: int = 24, n_layers: int = 3, seed: int = 2026):
        self.d_hidden = d_hidden
        self.n_layers = n_layers
        self.seed = seed
        rng = np.random.default_rng(seed)

        self.W_V0 = rng.normal(0.0, 0.45, size=(7, d_hidden))
        self.b_V0 = rng.normal(0.0, 0.1, size=(d_hidden,))
        self.W_E0 = rng.normal(0.0, 0.45, size=(15, d_hidden))
        self.b_E0 = rng.normal(0.0, 0.1, size=(d_hidden,))

        self.W_Vm = [
            rng.normal(0.0, 0.35 / math.sqrt(d_hidden), size=(d_hidden, d_hidden))
            for _ in range(n_layers)
        ]
        self.W_Em = [
            rng.normal(0.0, 0.35 / math.sqrt(d_hidden), size=(d_hidden, d_hidden))
            for _ in range(n_layers)
        ]

        self.z_dim = 4 * d_hidden + 15 + 10
        self.d_mlp = 64
        self.W_R1 = rng.normal(0.0, 0.40 / math.sqrt(self.z_dim), size=(self.z_dim, self.d_mlp))
        self.b_R1 = rng.normal(0.0, 0.10, size=(self.d_mlp,))

        self.head_dim = self.z_dim + self.d_mlp + 1
        self.w_crc = np.zeros(self.head_dim, dtype=np.float64)
        self.w_crit = np.zeros(self.head_dim, dtype=np.float64)
        self.z_mean = np.zeros(self.z_dim, dtype=np.float64)
        self.z_std = np.ones(self.z_dim, dtype=np.float64)
        self.c_gnn_threshold = 0.35

    def compute_graph_embedding(self, g: Dict[str, np.ndarray]) -> np.ndarray:
        X_V = g["X_V"]
        X_E = g["X_E"]
        endpoints = g["endpoints"]
        n_v = int(g["n_nodes"])
        n_e = int(g["n_edges"])
        t_idx = int(g["target_idx"])

        H_V = np.tanh(X_V @ self.W_V0 + self.b_V0)
        H_E = np.tanh(X_E @ self.W_E0 + self.b_E0)

        w_phys = X_E[:, 1:2]
        u_idx = endpoints[:, 0]
        v_idx = endpoints[:, 1]

        for l_i in range(self.n_layers):
            msg_e = H_E * w_phys
            M_V = np.zeros((n_v, self.d_hidden), dtype=np.float64)
            np.add.at(M_V, u_idx, msg_e)
            np.add.at(M_V, v_idx, msg_e)

            H_V = np.tanh(H_V + M_V @ self.W_Vm[l_i])
            node_pair_sum = H_V[u_idx] + H_V[v_idx]
            H_E = np.tanh(H_E + node_pair_sum @ self.W_Em[l_i])

        h_target = H_E[t_idx]
        h_e_mean = np.mean(H_E, axis=0)
        h_e_max = np.max(H_E, axis=0)
        h_v_mean = np.mean(H_V, axis=0)
        x_target = X_E[t_idx]

        lam = float(g["lam"])
        u_max_0 = float(g["u_max_0"])
        u_mean_0 = float(g["u_mean_0"])
        u_target = float(x_target[6])
        k_target = float(x_target[4])
        dmg = 1.0 - lam
        redistr_proxy = u_max_0 + dmg * u_target * (1.0 + k_target)
        min_deg_norm = float(np.min(X_V[:, 6]))
        target_min_deg = float(x_target[9])

        global_stats = np.array(
            [
                lam,
                dmg,
                1.0 if lam <= 1e-9 else 0.0,
                u_max_0,
                u_mean_0,
                u_target * dmg,
                redistr_proxy,
                min_deg_norm,
                target_min_deg,
                float(n_e) / max(float(n_v), 1.0),
            ],
            dtype=np.float64,
        )

        return np.concatenate([h_target, h_e_mean, h_e_max, h_v_mean, x_target, global_stats])

    def _build_design_row(self, z_raw: np.ndarray) -> np.ndarray:
        z_norm = (z_raw - self.z_mean) / self.z_std
        h_mlp = np.maximum(0.0, z_norm @ self.W_R1 + self.b_R1)
        return np.concatenate([z_norm, h_mlp, [1.0]])

    def fit(
        self,
        graphs_train: List[Dict[str, np.ndarray]],
        y_crc_train: np.ndarray,
        y_crit_train: np.ndarray,
        graphs_cal: List[Dict[str, np.ndarray]],
        y_crc_cal: np.ndarray,
        y_crit_cal: np.ndarray,
    ) -> Dict[str, Any]:
        Z_train = np.vstack([self.compute_graph_embedding(g) for g in graphs_train])
        self.z_mean = np.mean(Z_train, axis=0)
        self.z_std = np.std(Z_train, axis=0)
        self.z_std[self.z_std < 1e-6] = 1.0

        Phi_train = np.vstack([self._build_design_row(z) for z in Z_train])

        reg_crc = 2.5 * np.eye(self.head_dim)
        reg_crc[-1, -1] = 0.0
        self.w_crc = np.linalg.solve(
            Phi_train.T @ Phi_train + reg_crc, Phi_train.T @ y_crc_train
        )

        w = np.zeros(self.head_dim, dtype=np.float64)
        reg_log = 1.5 * np.eye(self.head_dim)
        reg_log[-1, -1] = 0.0
        pos_weight = 2.2
        sample_w = np.where(y_crit_train > 0.5, pos_weight, 1.0)

        for _ in range(18):
            logits = np.clip(Phi_train @ w, -20.0, 20.0)
            probs = 1.0 / (1.0 + np.exp(-logits))
            W_diag = sample_w * probs * (1.0 - probs) + 1e-5
            grad = Phi_train.T @ (sample_w * (probs - y_crit_train)) + reg_log @ w
            H = (Phi_train.T * W_diag) @ Phi_train + reg_log
            step = np.linalg.solve(H, grad)
            w -= step
            if float(np.linalg.norm(step)) < 1e-6:
                break
        self.w_crit = w

        Z_cal = np.vstack([self.compute_graph_embedding(g) for g in graphs_cal])
        Phi_cal = np.vstack([self._build_design_row(z) for z in Z_cal])
        crc_pred_cal = np.clip(Phi_cal @ self.w_crc, 0.0, 1.0)
        prob_pred_cal = 1.0 / (1.0 + np.exp(-np.clip(Phi_cal @ self.w_crit, -20.0, 20.0)))
        score_cal = 0.5 * crc_pred_cal + 0.5 * prob_pred_cal

        best_c = 0.30
        for c_cand in np.linspace(0.50, 0.20, 61):
            rec_cal = float(np.mean(score_cal[y_crit_cal > 0.5] >= c_cand))
            if rec_cal >= 0.965:
                best_c = float(round(c_cand, 4))
                break
        self.c_gnn_threshold = best_c

        crc_pred_tr = np.clip(Phi_train @ self.w_crc, 0.0, 1.0)
        mae_tr = float(np.mean(np.abs(crc_pred_tr - y_crc_train)))
        rmse_tr = float(np.sqrt(np.mean((crc_pred_tr - y_crc_train) ** 2)))
        mae_cal = float(np.mean(np.abs(crc_pred_cal - y_crc_cal)))
        rmse_cal = float(np.sqrt(np.mean((crc_pred_cal - y_crc_cal) ** 2)))
        rec_cal_final = float(np.mean(score_cal[y_crit_cal > 0.5] >= self.c_gnn_threshold))

        return {
            "train_samples": int(len(y_crc_train)),
            "cal_samples": int(len(y_crc_cal)),
            "c_gnn_threshold": self.c_gnn_threshold,
            "train_mae_crc": round(mae_tr, 6),
            "train_rmse_crc": round(rmse_tr, 6),
            "cal_mae_crc": round(mae_cal, 6),
            "cal_rmse_crc": round(rmse_cal, 6),
            "cal_crit_recall": round(rec_cal_final, 6),
        }

    def predict_single(self, g: Dict[str, np.ndarray]) -> Dict[str, float]:
        z = self.compute_graph_embedding(g)
        phi = self._build_design_row(z)
        crc_hat = float(np.clip(phi @ self.w_crc, 0.0, 1.0))
        logit = float(np.clip(phi @ self.w_crit, -20.0, 20.0))
        prob_crit = 1.0 / (1.0 + math.exp(-logit))
        y_hat = 0.5 * crc_hat + 0.5 * prob_crit
        is_crit_pred = 1 if y_hat >= self.c_gnn_threshold else 0
        return {
            "crc_hat": crc_hat,
            "prob_crit": prob_crit,
            "y_hat": y_hat,
            "pred_crit": is_crit_pred,
        }

    def save_weights(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            W_V0=self.W_V0,
            b_V0=self.b_V0,
            W_E0=self.W_E0,
            b_E0=self.b_E0,
            W_Vm_0=self.W_Vm[0],
            W_Vm_1=self.W_Vm[1],
            W_Vm_2=self.W_Vm[2],
            W_Em_0=self.W_Em[0],
            W_Em_1=self.W_Em[1],
            W_Em_2=self.W_Em[2],
            W_R1=self.W_R1,
            b_R1=self.b_R1,
            w_crc=self.w_crc,
            w_crit=self.w_crit,
            z_mean=self.z_mean,
            z_std=self.z_std,
            c_gnn_threshold=np.array([self.c_gnn_threshold]),
        )
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
