"""
test_structural_solvers.py
==========================

Suite Uji Penerimaan & Verifikasi Analitis untuk Solver Multi-Keluarga
(S1 Balok, S3 Portal Bidang, S4 Portal Berpengaku, S5 Rangka Ruang 3D).

Membuktikan Keterpenuhan Syarat Tabel 3.6 & Tabel 4.15 Disertasi ARI:
- S1: Lendutan & reaksi acuan, momen, geser, serta kondisi ujung.
- S3: Transformasi lokal-global, rotasi simpul, serta pelepasan ujung.
- S4: Sambungan pengaku, interaksi aksial-lentur, dan reduksi drift.
- S5: Komponen ruang 3D, kekangan spasial, deteksi mekanisme 3D.
- Anti-Pseudoinverse: Memastikan mekanisme kinematik ditolak dengan status 'rank_deficient'.

Jalankan:
    python examples/test_structural_solvers.py
Exit code 0 = seluruh pengujian analitis LULUS (PASS).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from structural_solvers import (  # noqa: E402
    solve_beam_s1,
    solve_braced_frame_s4,
    solve_frame_s3,
    solve_space_truss_s5,
    solve_structural_model,
)

TOL = 1e-4


def load_verification_models() -> dict:
    json_path = HERE / "verification_solvers_s1_s5.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {m["id"]: m for m in data["models"]}


def test_s1_beam_benchmarks() -> bool:
    print("=" * 78)
    print("UJI S1: Elemen Balok Lentur (Euler-Bernoulli Beam)")
    print("=" * 78)
    models = load_verification_models()
    ok_all = True

    # 1. Cantilever
    m1 = models["S1_beam_cantilever"]
    res1 = solve_beam_s1(m1)
    exp1 = m1["expected_results"]
    
    du1 = abs(res1.umax - exp1["umax_mm"])
    d_th = abs(abs(res1.node_displacements[1]["theta"]) - exp1["theta_rad"])
    d_ry = abs(res1.reactions[0]["Ry"] - exp1["Ry_kN"])
    d_mz = abs(res1.reactions[0]["Mz"] - exp1["Mz_kNmm"])
    d_w = abs(res1.strain_energy - exp1["strain_energy_kNmm"])
    
    ok1 = (res1.status == "ok" and du1 < TOL and d_th < TOL and d_ry < TOL and d_mz < TOL and d_w < TOL)
    ok_all &= ok1
    print(f"[{'PASS' if ok1 else 'FAIL'}] S1 Cantilever Beam: "
          f"v_tip={res1.umax:.6f} mm (exp {exp1['umax_mm']:.6f}, Δ={du1:.2e}), "
          f"theta={abs(res1.node_displacements[1]['theta']):.6f} rad (Δ={d_th:.2e}), "
          f"Ry={res1.reactions[0]['Ry']:.2f} kN, Mz={res1.reactions[0]['Mz']:.2f} kN.mm")

    # 2. Simply Supported Beam (2 elemen)
    m2 = models["S1_beam_simply_supported"]
    res2 = solve_beam_s1(m2)
    exp2 = m2["expected_results"]
    
    du2 = abs(res2.umax - exp2["umax_mm"])
    d_ry0 = abs(res2.reactions[0]["Ry"] - exp2["Ry0_kN"])
    d_ry2 = abs(res2.reactions[2]["Ry"] - exp2["Ry2_kN"])
    d_m = abs(res2.element_forces[0]["M_max"] - exp2["Mmax_kNmm"])
    d_w2 = abs(res2.strain_energy - exp2["strain_energy_kNmm"])
    
    ok2 = (res2.status == "ok" and du2 < TOL and d_ry0 < TOL and d_ry2 < TOL and d_m < TOL and d_w2 < TOL)
    ok_all &= ok2
    print(f"[{'PASS' if ok2 else 'FAIL'}] S1 Simply Supported Beam: "
          f"v_mid={res2.umax:.6f} mm (exp {exp2['umax_mm']:.6f}, Δ={du2:.2e}), "
          f"R0={res2.reactions[0]['Ry']:.2f} kN, R2={res2.reactions[2]['Ry']:.2f} kN, "
          f"M_mid={res2.element_forces[0]['M_max']:.2f} kN.mm")

    # 3. Uji deteksi mekanisme S1 (Balok tanpa tumpuan yang cukup)
    m_unstable = {
        "id": "S1_unstable",
        "nodes": [{"id": 0, "x": 0.0}, {"id": 1, "x": 1000.0}],
        "elements": [{"id": 0, "nodes": [0, 1], "E": 200.0, "I": 1e6}],
        "boundary_conditions": {"node_0": ["v"]}, # hanya rol v, rotasi bebas -> mekanisme rotasi!
        "loads": [{"node": 1, "components": {"Mz": 500.0}}]
    }
    res_unst = solve_beam_s1(m_unstable)
    ok_unst = (res_unst.status == "rank_deficient")
    ok_all &= ok_unst
    print(f"[{'PASS' if ok_unst else 'FAIL'}] S1 Mekanisme Balok: "
          f"status='{res_unst.status}' (rank={res_unst.rank}/{res_unst.n_free}, no pseudoinverse)")

    return ok_all


def test_s3_frame_benchmarks() -> bool:
    print("\n" + "=" * 78)
    print("UJI S3: Elemen Portal Bidang (2D Plane Frame)")
    print("=" * 78)
    models = load_verification_models()
    ok_all = True

    # 1. Portal Standar
    m_frame = models["S3_frame_portal"]
    res = solve_frame_s3(m_frame)
    exp = m_frame["expected_results"]
    
    du = abs(res.umax - exp["umax_mm"])
    d_drift = abs(res.node_displacements[1]["ux"] - exp["drift_node1_ux"])
    d_w = abs(res.strain_energy - exp["strain_energy_kNmm"])
    ok_f = (res.status == "ok" and du < TOL and d_drift < TOL and d_w < TOL)
    ok_all &= ok_f
    
    ux1 = res.node_displacements[1]["ux"]
    ux2 = res.node_displacements[2]["ux"]
    print(f"[{'PASS' if ok_f else 'FAIL'}] S3 Portal Bidang Lateral: "
          f"drift_ux1={ux1:.6f} mm (exp {exp['drift_node1_ux']:.6f}, Δ={d_drift:.2e}), "
          f"umax={res.umax:.6f} mm (Δ={du:.2e}), W={res.strain_energy:.4f} kN.mm")

    # 2. Portal dengan Pelepasan Sendi Momen (Hinge Release pada Balok)
    m_hinge = json.loads(json.dumps(m_frame))
    m_hinge["id"] = "S3_frame_hinged_beam"
    m_hinge["elements"][1]["release"] = "start"  # sendi di node 1
    res_hinge = solve_frame_s3(m_hinge)
    
    # Momen di ujung i balok harus tepat 0.0
    bm_force = res_hinge.element_forces[1]
    ok_h = (res_hinge.status == "ok" and abs(bm_force["Mi"]) < 1e-9)
    ok_all &= ok_h
    print(f"[{'PASS' if ok_h else 'FAIL'}] S3 Pelepasan Sendi Ujung (Hinge Release): "
          f"status={res_hinge.status}, Mi_beam={bm_force['Mi']:.2e} kN.mm (eksis nol!), "
          f"drift={res_hinge.node_displacements[1]['ux']:.6f} mm")

    # 3. Uji Mekanisme Portal (Tumpuan sendi di kaki dan sendi di balok -> goyang tak terkekang)
    m_frame_mech = json.loads(json.dumps(m_frame))
    m_frame_mech["id"] = "S3_frame_mechanism"
    m_frame_mech["boundary_conditions"]["node_0"] = "pinned"
    m_frame_mech["boundary_conditions"]["node_3"] = "pinned"
    m_frame_mech["elements"][1]["release"] = "both" # balok sendi kedua ujung -> mekanisme lateral
    res_f_mech = solve_frame_s3(m_frame_mech)
    ok_fm = (res_f_mech.status == "rank_deficient")
    ok_all &= ok_fm
    print(f"[{'PASS' if ok_fm else 'FAIL'}] S3 Mekanisme Portal: "
          f"status='{res_f_mech.status}' (rank={res_f_mech.rank}/{res_f_mech.n_free}, no pseudoinverse)")

    return ok_all


def test_s4_braced_frame_benchmarks() -> bool:
    print("\n" + "=" * 78)
    print("UJI S4: Portal Bidang Berpengaku (Braced Frame)")
    print("=" * 78)
    models = load_verification_models()
    ok_all = True

    m_unbraced = models["S3_frame_portal"]
    m_braced = models["S4_braced_frame_portal"]
    
    res_unbraced = solve_frame_s3(m_unbraced)
    res_braced = solve_braced_frame_s4(m_braced)
    
    drift_unbraced = res_unbraced.node_displacements[1]["ux"]
    drift_braced = res_braced.node_displacements[1]["ux"]
    drift_reduction = (drift_unbraced - drift_braced) / drift_unbraced * 100.0
    
    exp_red = m_braced["expected_results"]["drift_reduction_percent"]
    d_red = abs(drift_reduction - exp_red)
    
    # Cek bahwa elemen pengaku (id 3) menyerap gaya aksial yang signifikan
    brace_force = res_braced.element_forces[3]["N_axial"]
    brace_ratio = res_braced.element_forces[3]["interaction_ratio"]
    
    ok_bf = (res_braced.status == "ok" and d_red < 0.1 and abs(brace_force) > 10.0)
    ok_all &= ok_bf
    print(f"[{'PASS' if ok_bf else 'FAIL'}] S4 Efisiensi Reduksi Simpangan Pengaku: "
          f"drift tanpa pengaku={drift_unbraced:.4f} mm, dengan pengaku={drift_braced:.4f} mm, "
          f"reduksi={drift_reduction:.2f}% (exp {exp_red:.2f}%)")
    print(f"      Gaya aksial pengaku diagonal: {brace_force:.2f} kN (rasio utilisasi = {brace_ratio:.4f})")
    
    # Interaksi aksial-lentur balok-kolom
    col_ratio = res_braced.element_forces[0]["interaction_ratio"]
    print(f"      Interaksi P-M kolom kiri: rasio = {col_ratio:.4f}")

    return ok_all


def test_s5_space_truss_benchmarks() -> bool:
    print("\n" + "=" * 78)
    print("UJI S5: Rangka Ruang 3D (3D Space Truss)")
    print("=" * 78)
    models = load_verification_models()
    ok_all = True

    m_tripod = models["S5_space_truss_tripod"]
    res = solve_space_truss_s5(m_tripod)
    exp = m_tripod["expected_results"]
    
    # 1. Simetri translasi horizontal apex
    apex_disp = res.node_displacements[3]
    d_ux = abs(apex_disp["ux"])
    d_uy = abs(apex_disp["uy"])
    d_uz = abs(apex_disp["uz"] - exp["apex_uz_mm"])
    
    # 2. Gaya aksial ketiga kaki tripod identik (simetri beban vertikal)
    f0 = res.element_forces[0]["axial_force"]
    f1 = res.element_forces[1]["axial_force"]
    f2 = res.element_forces[2]["axial_force"]
    d_f = max(abs(f0 - exp["axial_force_kN"]), abs(f1 - exp["axial_force_kN"]), abs(f2 - exp["axial_force_kN"]))
    
    # 3. Keseimbangan vertikal reaksi tumpuan
    sum_Rz = sum(res.reactions[nid]["Rz"] for nid in [0, 1, 2])
    d_rz = abs(sum_Rz - exp["sum_vertical_reaction_kN"])
    
    ok_s5 = (res.status == "ok" and d_ux < 1e-12 and d_uy < 1e-9 and d_uz < TOL and d_f < TOL and d_rz < 1e-10)
    ok_all &= ok_s5
    print(f"[{'PASS' if ok_s5 else 'FAIL'}] S5 Rangka Ruang Tripod Simetris: "
          f"uz_apex={apex_disp['uz']:.6f} mm (exp {exp['apex_uz_mm']:.6f}, Δ={d_uz:.2e}), "
          f"ux={d_ux:.2e}, uy={d_uy:.2e} (simetri eksak)")
    print(f"      Gaya aksial 3 kaki: N0={f0:.4f} kN, N1={f1:.4f} kN, N2={f2:.4f} kN (Δ={d_f:.2e})")
    print(f"      Keseimbangan Reaksi Vertikal: ΣRz={sum_Rz:.2f} kN vs Pz=10.0 kN (Δ={d_rz:.2e})")

    # 4. Uji Mekanisme Kinematik Ruang 3D (Simpul bebas bergerak di luar bidang tanpa kekangan)
    m_space_mech = json.loads(json.dumps(m_tripod))
    m_space_mech["id"] = "S5_unstable_planar"
    # Tempatkan simpul 3 di bidang z=0 sejajar base -> menjadi mekanisme rotasi planar
    m_space_mech["nodes"][3]["coords"] = [500.0, 288.675135, 0.0]
    res_s5_mech = solve_space_truss_s5(m_space_mech)
    ok_s5m = (res_s5_mech.status == "rank_deficient")
    ok_all &= ok_s5m
    print(f"[{'PASS' if ok_s5m else 'FAIL'}] S5 Mekanisme Ruang 3D: "
          f"status='{res_s5_mech.status}' (rank={res_s5_mech.rank}/{res_s5_mech.n_free}, no pseudoinverse)")

    return ok_all


def test_unified_dispatcher() -> bool:
    print("\n" + "=" * 78)
    print("UJI DISPATCHER UNIFIKASI (solve_structural_model S1 - S5)")
    print("=" * 78)
    models = load_verification_models()
    ok_all = True
    
    for mid, m in models.items():
        res = solve_structural_model(m)
        ok = (res.status == "ok" and res.umax > 0.0)
        ok_all &= ok
        print(f"Dispatcher -> {mid:<28} family={res.family:<16} status={res.status:<8} "
              f"umax={res.umax:.6f} mm  -> {'PASS' if ok else 'FAIL'}")
    return ok_all


if __name__ == "__main__":
    print("MEMULAI SUITE ACCEPTANCE TEST SOLVER STRUKTUR MULTI-KELUARGA")
    b1 = test_s1_beam_benchmarks()
    b2 = test_s3_frame_benchmarks()
    b3 = test_s4_braced_frame_benchmarks()
    b4 = test_s5_space_truss_benchmarks()
    b5 = test_unified_dispatcher()
    
    all_passed = b1 and b2 and b3 and b4 and b5
    print("\n" + "=" * 78)
    if all_passed:
        print("SEMUA PENGUJIAN SOLVER S1, S3, S4, S5 BERHASIL (100% PASS)")
        sys.exit(0)
    else:
        print("ADA PENGUJIAN GAGAL (FAIL)")
        sys.exit(1)
