#!/usr/bin/env python3
"""
Otomasi Konversi Rumus Disertasi ke Native Equation (OpenXML Math / m:oMath)
yang Didukung Penuh oleh GenOffice Docs dan Microsoft Word.

Berdasarkan Panduan Penulisan Disertasi Pascasarjana UNY 2023 Bab V.B.9.b:
"Penomoran rumus matematika menggunakan angka arab yang ditempatkan di tepi kanan,
di antara dua tanda kurung."
"""

import os
import json
import subprocess

REPORT_PATH = '/Users/harids.irawan/Library/CloudStorage/GoogleDrive-harids.irawan@gmail.com/My Drive/Documents/2026/Research/Adjusted Redudancy Index/Report/Adjusted Redudancy Index.docx'
OPS_PATH = os.path.join(os.path.dirname(__file__), 'genoffice_equation_ops.json')

def apply_latex_equations():
    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(f'Berkas target tidak ditemukan: {REPORT_PATH}')
    if not os.path.exists(OPS_PATH):
        raise FileNotFoundError(f'Berkas ops tidak ditemukan: {OPS_PATH}')

    print(f'Menerapkan 38 blok operasi rumus LaTeX ke: {REPORT_PATH}...')
    cmd = ['/usr/local/bin/genoffice', 'docs', 'apply', REPORT_PATH, '--ops', OPS_PATH]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print('Error:', res.stderr)
        raise RuntimeError('Gagal menerapkan operasi rumus GenOffice.')
    print('Konversi rumus LaTeX ke Native OpenXML Math berhasil 100%.')

if __name__ == '__main__':
    apply_latex_equations()
