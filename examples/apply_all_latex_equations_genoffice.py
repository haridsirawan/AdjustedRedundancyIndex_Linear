#!/usr/bin/env python3
"""
apply_all_latex_equations_genoffice.py
======================================

Memindai seluruh blok persamaan di Report/Adjusted Redudancy Index.docx,
membangun ops JSON dinamis, dan menerapkannya menggunakan GenOffice docs apply
sehingga seluruh rumus matematika menjadi Native OpenXML Math (m:oMath)
dengan penomoran tepi kanan diapit tanda kurung sesuai Bab V.B.9.b UNY 2023.
"""

import os
import json
import subprocess
import docx
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph

REPORT_PATH = (
    "/Users/harids.irawan/Library/CloudStorage/GoogleDrive-harids.irawan@gmail.com/"
    "My Drive/Documents/2026/Research/Adjusted Redudancy Index/Report/"
    "Adjusted Redudancy Index.docx"
)
OPS_PATH = os.path.join(os.path.dirname(__file__), "genoffice_equation_ops_dynamic.json")

# Definisi rumus LaTeX resmi
EQUATION_DEFINITIONS = [
    ("(2.1)", r"<formula>K_{ff} u_f = p_f \quad (2.1)</formula>"),
    ("(2.2)", r"<formula>\Delta = B u_f, \quad n = D_k \Delta, \quad K_{ff} = B^T D_k B \quad (2.2)</formula>"),
    ("(2.3)", r"<formula>m_i^{(\ell)} = \text{AGG}_{j \in N(i)} M_\ell(h_i, h_j, z_{ij}) \quad (2.3)</formula><formula>h_i^{(\ell+1)} = U_\ell(h_i, m_i) \quad (2.4)</formula>"),
    ("(2.5)", r"<formula>k_e^{\text{aksial}} = \frac{E_e A_e}{L_e}, \quad k_e^{\text{lentur}} = \frac{E_e I_e}{L_e^3} \quad (2.5)</formula>"),
    ("(2.6)", r"<formula>\hat{x}_e = \frac{x_e}{x_e + s_x}, \quad x_e > 0, \ s_x > 0 \quad (2.6)</formula>"),
    ("(2.7)", r"<formula>w_e^M = q_e (\alpha_k \hat{k}_e + \alpha_R \hat{R}_e), \quad \alpha_k + \alpha_R = 1, \ \alpha_k, \alpha_R \ge 0, \ 0 < q_e \le 1 \quad (2.7)</formula>"),
    ("(2.8)", r"<formula>c_e^M = \frac{1}{w_e^M + \epsilon_w}, \quad d^M(p) = \sum_{e \in p} c_e^M, \quad \epsilon_w > 0 \quad (2.8)</formula>"),
    ("(2.14)", r"<formula>w_{e,\lambda}^M = \lambda w_e^M \quad (2.14)</formula>"),
    ("(2.15)", r"<formula>RR_e(\lambda) = \frac{S(G_{e,\lambda}^M)}{S(G^M)} \quad (2.15)</formula><formula>U_e^* = \min\left(\frac{D_e}{R_e}, 1\right) \quad (2.16)</formula>"),
    ("(2.17)", r"<formula>ARI_e(\lambda) = RR_e(\lambda) \cdot U_e^* \quad (2.17)</formula><formula>CI_e(\lambda) = 1 - ARI_e(\lambda) \quad (2.18)</formula>"),
    ("(2.20)", r"<formula>0 \le S(G_{e,\lambda}^M) \le S(G^M), \quad 0 \le RR_e(\lambda) \le 1, \quad 0 \le ARI_e(\lambda) \le 1 \quad (2.20)</formula>"),
    ("(2.21)", r"<formula>\tau_b = \frac{n_c - n_d}{\sqrt{(n_c + n_d + t_x)(n_c + n_d + t_y)}} \quad (2.21)</formula>"),
    ("(3.1)", r"<formula>T_{\text{layak}} = \{\tau \in T : L_{\text{cal}}(\tau) \ge 0{,}95, \ \text{Reduksi}_{\text{cal}}(\tau) \ge 0{,}30\} \quad (3.1)</formula><formula>\tau^* \in \arg\max_{\tau \in T_{\text{layak}}} \text{Reduksi}_{\text{cal}}(\tau) \quad (3.2)</formula>"),
    ("(3.3)", r"<formula>\delta_u^{(s)} = \frac{|u_{\max}^{(s)} - u_{\max}^{(0)}|}{|u_{\max}^{(0)}| + \epsilon_u} \quad (3.3)</formula>"),
    ("(3.4)", r"<formula>\delta_U^{(s)} = \frac{|U_{\max}^{(s)} - U_{\max}^{(0)}|}{|U_{\max}^{(0)}| + \epsilon_U} \quad (3.4)</formula>"),
    ("(3.5)", r"<formula>\delta_F^{(s)} = \max_{g \in G_F} \frac{\max_{a \in g} |F_a^{(s)} - F_a^{(0)}|}{\max_{a \in g} |F_a^{(0)}| + \epsilon_F} \quad (3.5)</formula>"),
    ("(3.6)", r"<formula>\delta_k^{(s)} = \max\left(\frac{k_{\text{sys}}^{(0)} - k_{\text{sys}}^{(s)}}{k_{\text{sys}}^{(0)} + \epsilon_k}, 0\right) \quad (3.6)</formula>"),
    ("(3.7)", r"<formula>\hat{\delta}_h^{(s)} = \frac{\delta_h^{(s)}}{\delta_h^{(s)} + t_h}, \quad y_s = \text{CRC}_{\text{konv},s} = \max_{h \in H} \hat{\delta}_h^{(s)} \quad (3.7)</formula>"),
    ("(3.8)", r"<formula>n_{\text{ref}} = \min\{N, \max\{3, \text{ceil}( 0{,}10 N )\}\} \quad (3.8)</formula><formula>C = C_{\text{peringkat}} \cup C_{\text{konsekuensi}} \cup C_{\text{mekanisme}} \quad (3.9)</formula>"),
    ("(3.10)", r"<formula>\bar{R} = \frac{1}{M}\sum_{m=1}^M R_m, \quad L_{0{,}95} = Q_{0{,}05}\left(\bar{R}^{*(1)}, \ldots, \bar{R}^{*(B)}\right) \quad (3.10)</formula>"),
    ("(3.11)", r"<formula>D_j(s) = \frac{ARI_s(p_j + \Delta p_j) - ARI_s(p_j - \Delta p_j)}{2\Delta p_j} \quad (3.11)</formula>"),
    ("(3.12)", r"<formula>F = \{s \in S : CI_s \ge \tau_{CI}\} \cup A \quad (3.12)</formula>"),
    ("(3.13)", r"<formula>\text{Recall}_{\text{saring}} = \frac{|F \cap C|}{|C|}, \quad \text{Reduksi} = 1 - \frac{|F|}{|S|} \quad (3.13)</formula>"),
    ("(3.14)", r"<formula>\text{Recall}_{\text{akhir}}(F) = \frac{|H_F \cap C|}{|C|} \quad (3.14)</formula>"),
    ("(3.15)", r"<formula>\text{MAE}(Q) = \frac{1}{|Q|}\sum_{s \in Q} |\hat{y}_s - y_s|, \quad \text{RMSE}(Q) = \sqrt{\frac{1}{|Q|}\sum_{s \in Q} (\hat{y}_s - y_s)^2} \quad (3.15)</formula>"),
    ("(3.16)", r"<formula>T_{\text{hemat}} = T_{\text{tanpa}} - T_{\text{ARI-GNN}} \quad (3.16)</formula><formula>r_T = \frac{T_{\text{hemat}}}{T_{\text{tanpa}}} \quad (3.17)</formula>"),
    ("(3.18)", r"<formula>E_v = \frac{1}{3{,}6 \times 10^6} \int_{t_{0,v}}^{t_{1,v}} P_{\text{el},v}(t) \, dt \quad [\text{kWh}] \quad (3.18)</formula>"),
    ("(3.19)", r"<formula>E_{\text{dengan}} = E_{\text{persiapan}} + E_{\text{ARI}} + E_{\text{pengaman}} + E_{\text{GNN}} \quad (3.19)</formula>"),
    ("(3.20)", r"<formula>\Delta E = E_{\text{tanpa}} - E_{\text{dengan}}, \quad r_E = \frac{\Delta E}{E_{\text{tanpa}}} \quad (3.20)</formula>"),
    ("(4.1)", r"<formula>K_0 = \sum_e k_e a_e^T a_e, \quad h_e = k_e a_e K_0^{-1} a_e^T \quad (4.1)</formula>"),
    ("(4.2)", r"<formula>K_{e,\lambda} = K_0 - (1-\lambda) k_e a_e^T a_e, \quad m_e(\lambda) = 1 - (1-\lambda) h_e \quad (4.2)</formula>"),
    ("(4.4)", r"<formula>\frac{\lambda_{\min}(K_{e,\lambda})}{\lambda_{\max}(K_{e,\lambda})} \ge m_e \rho_0 \quad (4.4)</formula>"),
    ("(4.5)", r"<formula>F(s) = 1_{\{\text{CI}(s) \ge \tau \ \vee \ g(s) = 1 \ \vee \ \text{ARI abstain atau tidak stabil}\}} \quad (4.5)</formula>"),
    ("(4.6)", r"<formula>K_0 u_0 = f, \quad N_{j,0} = k_j a_j u_0, \quad D_j = |N_{j,0}| \quad (4.6)</formula>"),
    ("(4.8)", r"<formula>|k_j a_j K_0^{-1} a_e^T| \le \sqrt{\frac{k_j}{k_e} h_j h_e} \quad (4.8)</formula>"),
    ("(4.9)", r"<formula>D_{j,s} = \begin{cases} |N_{j,0}| + \frac{\alpha_s |N_{e,0}|}{m_s}\sqrt{\frac{k_j}{k_e} h_j h_e}, & j \ne e \\ \lambda |N_{e,0}|, & j = e \end{cases} \quad (4.9)</formula>"),
    ("(4.10)", r"<formula>U_s = \max_{j \in E_s} \frac{D_{j,s}}{R_{j,s}} \quad (4.10)</formula>"),
    ("(4.11)", r"<formula>c_i = \lambda_{\max}\left(P_i K_0^{-1} P_i^T\right), \quad d_0 = \max_i |P_i u_0|_2 \quad (4.11)</formula>"),
    ("(4.12)", r"<formula>|P_i \Delta u_s|_2 \le \frac{\alpha_s |N_{e,0}|}{m_s} \sqrt{\frac{c_i h_e}{k_e}}, \quad d_s \le d_0 + \frac{\alpha_s |N_{e,0}|}{m_s}\max_i \sqrt{\frac{c_i h_e}{k_e}} \quad (4.12)</formula>"),
    ("(4.13)", r"<formula>F^+(s) = 1_{\{F(s) = 1 \ \vee \ g_C(s) = 1 \ \vee \ g_D(s) = 1 \ \vee \ \text{batas tidak dapat dihitung}\}} \quad (4.13)</formula>"),
    ("(4.14)", r"<formula>K_e = \frac{E_e A_e}{L_e} b_e^T b_e \quad (4.14)</formula>"),
    ("(4.15)", r"<formula>k_{\text{sys}}^{(0)} = 30 \text{ kN/mm}, \quad u^{(0)} = 1 \text{ mm}, \quad D_1 = 20 \text{ kN}, \quad D_2 = 10 \text{ kN} \quad (4.15)</formula>"),
    ("(4.16)", r"<formula>S(G^M) = \frac{1}{2}\left(\frac{4}{7}\right) + \frac{1}{2}\left(\frac{2}{5}\right) = \frac{17}{35} \approx 0{,}4857 \quad (4.16)</formula>"),
    ("(4.17)", r"<formula>w_{1,\lambda} = \frac{4}{7}\lambda, \quad RR_1(\lambda) = \frac{10\lambda + 7}{17} \quad (4.17)</formula>"),
    ("(4.18)", r"<formula>ARI_1(\lambda) = \frac{10\lambda + 7}{17} \quad (4.18)</formula>"),
    ("(4.19)", r"<formula>u_1(\lambda) = \frac{30}{20\lambda + 10} \quad [\text{mm}] \quad (4.19)</formula>"),
]


def apply_equations():
    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(f"Berkas tidak ditemukan: {REPORT_PATH}")

    doc = docx.Document(REPORT_PATH)
    body_children = list(doc.element.body.iterchildren())

    # Bangun peta dari nomor persamaan ke blok indeks
    eq_ops = []
    applied_count = 0

    # Iterasi dari bawah ke atas agar indeks blok tidak bergeser saat replace_blocks beruntun
    # Namun GenOffice apply menerima seluruh array dan mengeksekusi secara atomik dari atas ke bawah.
    for eq_num, formula_html in EQUATION_DEFINITIONS:
        found_block = None
        for b_idx, child in enumerate(body_children):
            if isinstance(child, CT_P):
                p = Paragraph(child, doc)
                txt = p.text.strip()
                if eq_num in txt and len(txt) < 250:
                    found_block = b_idx
                    break

        if found_block is not None:
            eq_ops.append({
                "op": "replace_blocks",
                "startBlockIndex": found_block,
                "endBlockIndex": found_block + 1,
                "html": formula_html
            })
            applied_count += 1
            print(f"Matched {eq_num:7s} -> block {found_block}")
        else:
            print(f"WARNING: Persamaan {eq_num} tidak ditemukan di naskah!")

    # Urutkan ops secara descending (dari indeks terbesar ke terkecil)
    # sehingga perubahan jumlah blok di bagian bawah tidak mengubah indeks blok di bagian atas
    eq_ops.sort(key=lambda x: x["startBlockIndex"], reverse=True)
    print(f"\nTotal persamaan terpetakan: {len(eq_ops)} (diurutkan descending)")

    # Simpan berkas ops dinamis
    with open(OPS_PATH, "w", encoding="utf-8") as fp:
        json.dump(eq_ops, fp, indent=2)

    print(f"Menerapkan {len(eq_ops)} operasi rumus via GenOffice...")
    cmd = ["/usr/local/bin/genoffice", "docs", "apply", REPORT_PATH, "--ops", OPS_PATH]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("STDERR:", res.stderr)
        raise RuntimeError("Gagal menerapkan operasi rumus GenOffice.")

    print("BERHASIL! Seluruh rumus LaTeX telah dikompilasi menjadi Native OpenXML Math.")


if __name__ == "__main__":
    apply_equations()
