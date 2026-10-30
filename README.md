# Adjusted Redundancy Index (ARI) — Computational Implementation & Dissertation Verification

Official repository for algorithm implementations, reference finite element solvers, and kinematic safeguards based on Singular Value Decomposition (SVD).

> **Development and Validation of the Adjusted Redundancy Index for Pre-Analysis Screening of Element Damage Scenarios in Graph Neural Network-Based Structural Evaluation**

---

## 1. Computational Pipeline Architecture

```text
examples/verification_models.json
        │
        ▼
examples/truss_reference.py       (Layer 1 — 1D/2D Axial Truss FE Solver: initial forces, reactions r^(0), U*, rank)
        │
        ▼
examples/ari_core.py              (Layer 2 — ARI Core Engine: w_e^M, Φ^K_ij, S(G), RR, ARI, CI; Eqs. 2.5–2.18)
        │
        ├──► examples/mechanical_guard.py   (Layer 3a — SVD Kinematic Safeguard h_e, m_e(λ), κ bounds; Eqs. 4.1–4.7)
        ├──► examples/bound_enhancement.py  (Layer 3b — Pre-analysis Bounds for Force Redistribution & Displacement Magnification; §4.4)
        └──► examples/layered_policy.py     (Layer 3c — Layered Screening Policy F⁺; Eq. 4.13)
                │
                ▼
        ├──► examples/run_verification.py         ──► results/verification/ (68/68 canonical checks, Table.tex, PDF)
        ├──► examples/run_guard_verification.py   ──► results/revision/     (33/33 safeguard checks & 272 scenarios)
        └──► examples/run_pipeline.py             ──► results/verification/ (13-column audit CSV & Δλ=0.05 curves)
```

---

## 2. Installation & Running Verifications

### Environment Prerequisites
* Python $\ge 3.9$
* Fundamental scientific libraries (`numpy`, `matplotlib`)

```bash
pip install -r requirements.txt
```

### A. Unified Single-Entry-Point Verification (*Recommended*)
Run the main script at the repository root to automatically execute all 11 verification stages:

```bash
python3 run_all_verifications.py
```

### B. Per-Module Execution in the `examples/` Directory

```bash
cd examples

# 1. Canonical Verification & Kinematic Safeguard (Primary Evidence Chapter IV)
python3 ari_tutorial.py              # Analytical tutorial for two parallel bars (Table 25 / Table 4.11)
python3 test_truss_reference.py      # Acceptance test of FE solver against 4 canonical models (Table 13 / Table 4.1)
python3 test_ari.py                  # Unit test for ARI engine, monotonicity, & unit invariance (Table 15 / Table 4.3)
python3 mechanical_guard.py          # Verification of SVD safeguard h_e & algebraic identities (Table 16 / Table 4.4)
python3 test_bound_enhancement.py    # Conservatism test of redistribution & displacement magnification bounds
python3 test_leakage_audit.py        # Anti-leakage audit for post-damage information (4 inspections)
python3 run_verification.py          # Full canonical verification suite (68/68 automated checks)
python3 run_guard_verification.py    # Safeguard verification & diagnostics for 16 parametric models (272 scenarios)

# 2. Curve Extraction & Reconciliation Diagnostics
python3 run_pipeline.py              # 3-layer orchestration on coarse grid λ ∈ {1, 0.75, 0.5, 0.25, 0}
python3 fine_grid_runner.py          # Fine-grid evaluation Δλ = 0.05 (336 rows)
python3 curve_extractor.py           # Extraction of critical points λ_crit & λ_guard_flip
python3 plot_curves.py               # Generation of 4 PDF plots for RR(λ) and CI(λ) curves
python3 reconcile_ari_forward.py     # Reconciliation of forwarding convention variations across 272 parametric scenarios
python3 analyze_remaining_misses.py  # Characterization of 28 critical missed cases & rule candidate evaluation

# 3. Multi-Family Full-Scale Validation (S1–S5) & Paired GNN Integration (S6)
python3 test_structural_solvers.py   # Analytical solver test for 5 structural families S1–S5
python3 generate_dataset_s1_s5.py    # Generation of parent models S1–S5 with SHA-256 manifests
python3 freeze_protocol_config.py    # Protocol configuration freeze (ARI-FROZEN-PROTOCOL-v1.0)
python3 run_screening_s1_s5.py       # Baseline ARI v1 screening simulation across families S1–S5
python3 run_screening_v2.py          # Full validation of unified ARI v2 formulation (Passed Gates C & D, Zero-Miss)
python3 run_gnn_integration_s6.py    # ARI v2–GNN integration evaluation (StructGNN-CRC v1.0, T7 & T8) & Table 4.19 cost audit
```

---

## 3. Repository Directory Structure

```text
.
├── CITATION.cff                     # Official academic citation metadata (GitHub Citation)
├── LICENSE                          # Apache License 2.0 software license
├── README.md                        # Main repository documentation
├── ARCHITECTURE.md                  # Layered architecture specification, numerical contracts, & module map
├── WORK_LOG.md                      # Tiered verification history log (Gates 1–17)
├── DEFERRED_FINDINGS.md             # Documentation of numerical finding closures & formula reconciliations
├── requirements.txt                 # Python dependency list
├── manifest_config_frozen.json      # Frozen protocol configuration seal (ARI-FROZEN-PROTOCOL-v1.0)
├── run_all_verifications.py         # Unified single-entry automated verification script (11 stages)
├── examples/                        # 29 scientific files (27 Python modules & 2 JSON model specifications)
└── results/                         # Verification output artifacts, diagnostics, and protocol results
    ├── verification/                # Canonical verification output (68/68 passed, CSV, JSON, LaTeX, PDF)
    ├── revision/                    # Diagnostic suite for 16 parametric models (272 scenarios)
    ├── bounds/                      # Anti-leakage audit logs & pre-analysis bound ablation reports
    ├── dataset/                     # Multi-family S1–S5 model specifications & manifests
    ├── screening/                   # Screening decision artifacts & threshold calibration curves
    ├── validation/                  # Validation gate metric evaluation reports & ablations
    ├── integration/                 # GNN integration protocol study artifacts & cost breakdown tables
    └── review_prep/                 # Manuscript numerical consistency documentation, audits, & checklists
```

---

## 4. License & Citation

Source code in this repository is licensed under the **Apache License 2.0** (see [`LICENSE`](LICENSE)).  
To cite this work in scientific publications, please use the **"Cite this repository"** button on GitHub or refer to the metadata in [`CITATION.cff`](CITATION.cff).
