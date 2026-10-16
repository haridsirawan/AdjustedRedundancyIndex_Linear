#!/usr/bin/env python3
"""
Rebuild & Format Naskah Disertasi (.docx) Mengikuti Panduan Disertasi UNY 2023.
Satu-satunya berkas target (timpa langsung / in-place):
/Users/harids.irawan/Library/CloudStorage/GoogleDrive-harids.irawan@gmail.com/My Drive/Documents/2026/Research/Adjusted Redudancy Index/Report/Adjusted Redudancy Index.docx
"""

import os
import re
import copy
import docx
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.text.paragraph import Paragraph
from docx.table import Table

REPORT_PATH = (
    "/Users/harids.irawan/Library/CloudStorage/GoogleDrive-harids.irawan@gmail.com/"
    "My Drive/Documents/2026/Research/Adjusted Redudancy Index/Report/"
    "Adjusted Redudancy Index.docx"
)


# ==============================================================================
# 1. PEMETAAN HIERARKI SUBBAB & ANAK SUBBAB (BAB V.B.5 & V.B.7.c UNY 2023)
# ==============================================================================
SECTION_HEADING_MAP = {
    # BAB I
    "1.1": ("A.", "Latar Belakang Masalah", 1),
    "1.2": ("B.", "Identifikasi Masalah", 1),
    "1.3": ("C.", "Perumusan Masalah Penelitian", 1),
    "1.4": ("D.", "Tujuan Penelitian", 1),
    "1.5": ("E.", "Ruang Lingkup dan Batas Klaim", 1),
    "1.6": ("F.", "Kontribusi Penelitian dan Kedudukan Bukti", 1),
    "1.7": ("G.", "Manfaat Penelitian", 1),
    "1.7.1": ("1.", "Manfaat Teoretis", 2),
    "1.7.2": ("2.", "Manfaat Metodologis", 2),
    "1.7.3": ("3.", "Manfaat Praktis dan Batasnya", 2),
    # BAB II
    "2.1": ("A.", "Landasan Mekanika Sistem Struktur", 1),
    "2.2": ("B.", "Redundansi, Ketahanan, dan Jalur Alternatif", 1),
    "2.3": ("C.", "Peran Analisis Jalur Alternatif", 1),
    "2.4": ("D.", "Landasan GNN dan Batas Representasi", 1),
    "2.5": ("E.", "Konstruk dan Representasi", 1),
    "2.6": ("F.", "Atribut dan Normalisasi", 1),
    "2.7": ("G.", "Skor Jalur Alternatif", 1),
    "2.8": ("H.", "Gangguan, Rasio Skor, dan ARI", 1),
    "2.9": ("I.", "Sifat Matematis dan Kasus Batas", 1),
    "2.10": ("J.", "Green AI dan Efisiensi Komputasi", 1),
    "2.11": ("K.", "Hasil Penelusuran dan Dokumentasi Literatur", 1),
    "2.11.1": ("1.", "Katalog Sumber yang Ditemukan dan Persinggungan Metodologis", 2),
    "2.11.2": ("2.", "Katalog Beranotasi Sumber yang Ditemukan", 2),
    "2.11.3": ("3.", "Deduplikasi, Ekstraksi, dan Pembaruan", 2),
    "2.12": ("L.", "Pemeringkatan dan Keputusan Penyaringan", 1),
    "2.13": ("M.", "Penelitian Terdahulu dan Sintesis", 1),
    "2.13.1": ("1.", "Persinggungan Metodologis dari Sumber Tambahan", 2),
    "2.14": ("N.", "Strategi Sintesis dan Mutu Bukti", 1),
    "2.14.1": ("1.", "Referensi Inti dan Referensi Pendukung", 2),
    "2.14.2": ("2.", "Matriks Kesesuaian dan Perbedaan Metode", 2),
    "2.15": ("O.", "Landasan Statistika dan Ketidakpastian", 1),
    "2.15.1": ("1.", "Peringkat dan Besaran Sasaran", 2),
    "2.15.2": ("2.", "Struktur Data dan Interval", 2),
    "2.15.3": ("3.", "Pengendalian Risiko dan Klaim", 2),
    "2.16": ("P.", "Kesenjangan dan Posisi Kebaruan", 1),
    "2.17": ("Q.", "Kerangka Berpikir", 1),
    "2.18": ("R.", "Hipotesis Penelitian", 1),
    # BAB III
    "3.1": ("A.", "Desain Penelitian dan Metode yang Dilaksanakan", 1),
    "3.1.1": ("1.", "Bahan, Unit Analisis, dan Konfigurasi", 2),
    "3.1.2": ("2.", "Prosedur Perhitungan dan Pemeriksaan", 2),
    "3.1.3": ("3.", "Rekaman Pelaksanaan Gate 1", 2),
    "3.1.4": ("4.", "Alur Kerja Pengembangan Berbantuan OpenAI Codex", 2),
    "3.1.5": ("5.", "Analisis Hasil dan Batas Inferensi", 2),
    "3.1.6": ("6.", "Pengembangan Pengaman dan Evaluasi Diagnostik", 2),
    "3.2": ("B.", "Protokol Validasi Lanjutan dan Pembagian Data", 1),
    "3.3": ("C.", "Protokol Pengembangan dan Pembekuan", 1),
    "3.4": ("D.", "Tahapan dan Prasyarat Validasi Lanjutan", 1),
    "3.5": ("E.", "Variabel dan Definisi Operasional", 1),
    "3.6": ("F.", "Pembangkitan Model dan Skenario", 1),
    "3.6.1": ("1.", "Sumber dan Keluarga Model", 2),
    "3.6.2": ("2.", "Aturan Gangguan", 2),
    "3.7": ("G.", "Pengumpulan Data dan Instrumen", 1),
    "3.7.1": ("1.", "Sumber, Ekstraksi, dan Penggabungan Data", 2),
    "3.7.2": ("2.", "Instrumen dan Penelaahan", 2),
    "3.8": ("H.", "Kalibrasi Kandidat dan Pengendalian Kompleksitas", 1),
    "3.9": ("I.", "Rencana Realisasi Dataset, Kalibrasi, dan Validasi Buta", 1),
    "3.9.1": ("1.", "Prioritas Evaluasi Independen pada Domain Terbatas", 2),
    "3.9.2": ("2.", "Status Bukti dan Prasyarat per Keluarga", 2),
    "3.9.3": ("3.", "Pembangkitan dan Pembagian Model Induk", 2),
    "3.9.4": ("4.", "Aturan Pemilihan Ambang yang Dapat Diaudit", 2),
    "3.9.5": ("5.", "Ablasi, Pembekuan, dan Pembukaan Data Buta", 2),
    "3.10": ("J.", "Acuan Mekanis dan Kasus Kritis", 1),
    "3.11": ("K.", "Pembanding dan Ablasi", 1),
    "3.12": ("L.", "Gerbang Validasi", 1),
    "3.13": ("M.", "Inferensi Statistik", 1),
    "3.14": ("N.", "Sensitivitas Lokal, Ablasi, dan Analisis Kasus Batas", 1),
    "3.15": ("O.", "Konfirmasi Mekanis dan Validasi Eksternal", 1),
    "3.15.1": ("1.", "Uji Tambahan terhadap Acuan Nonlinier", 2),
    "3.15.2": ("2.", "Validasi Eksternal", 2),
    "3.16": ("P.", "Pengendalian Mutu dan Keabsahan", 1),
    "3.17": ("Q.", "Etika, Transparansi, dan Reproduksibilitas", 1),
    "3.18": ("R.", "Protokol Integrasi ARI–GNN", 1),
    "3.18.1": ("1.", "Prasyarat GNN Acuan", 2),
    "3.18.2": ("2.", "Audit Kandidat dan Keputusan Pemilihan", 2),
    "3.18.3": ("3.", "Kartu Model dan Rekonstruksi Target", 2),
    "3.18.4": ("4.", "Aturan Penerusan dan Perlakuan", 2),
    "3.18.5": ("5.", "Ukuran Kinerja", 2),
    "3.18.6": ("6.", "Biaya Total dan Keputusan Manfaat", 2),
    "3.18.7": ("7.", "Protokol Pengukuran Energi dan Estimasi Emisi", 2),
    # BAB IV
    "4.1": ("A.", "Hasil Verifikasi Numerik pada Model Kanonik", 1),
    "4.1.1": ("1.", "Tujuan dan Cakupan Verifikasi", 2),
    "4.1.2": ("2.", "Model Kanonik dan Konfigurasi", 2),
    "4.1.3": ("3.", "Pemeriksaan Algoritma dan Solver", 2),
    "4.1.4": ("4.", "Respons Model Utuh sebagai Acuan", 2),
    "4.1.5": ("5.", "Respons Gangguan dan Contoh Pembatas Mekanis", 2),
    "4.1.6": ("6.", "Implikasi bagi Pengembangan Pengaman", 2),
    "4.1.7": ("7.", "Ketertelusuran Keluaran dan Batas Verifikasi", 2),
    "4.2": ("B.", "Hasil Pengembangan ARI dengan Pengaman Kinematik", 1),
    "4.2.1": ("1.", "Tujuan dan Batas Perubahan", 2),
    "4.2.2": ("2.", "Dasar Mekanis dari Model Utuh", 2),
    "4.2.3": ("3.", "Aturan Penerusan dan Pemisahan Informasi", 2),
    "4.2.4": ("4.", "Rancangan Uji Regresi dan Diagnostik Pengembangan", 2),
    "4.2.5": ("5.", "Hasil Aktual dan Kegagalan yang Masih Tersisa", 2),
    "4.2.6": ("6.", "Paket Gate 9 dari Lampiran Unggahan", 2),
    "4.3": ("C.", "Pembahasan Temuan Utama", 1),
    "4.3.1": ("1.", "Konsistensi Algoritma dan Kesesuaian Konstruk", 2),
    "4.3.2": ("2.", "Jaminan Kestabilan dan Kegunaan Pemeringkatan", 2),
    "4.3.3": ("3.", "Penjelasan Ketidakpekaan pada Elemen Tertentu", 2),
    "4.3.4": ("4.", "Nilai Tambah Diagnostik dan Biaya Penerusan", 2),
    "4.3.5": ("5.", "Makna bagi Penyaringan sebelum GNN", 2),
    "4.3.6": ("6.", "Potensi Kontribusi terhadap Komputasi Berkelanjutan", 2),
    "4.3.7": ("7.", "Sintesis Jawaban atas Pertanyaan Penelitian", 2),
    "4.3.8": ("8.", "Kedudukan Hasil dan Arah Tindak Lanjut", 2),
    "4.4": ("D.", "Usulan Pengayaan Praanalisis untuk Konsekuensi Non-Mekanisme", 1),
    "4.4.1": ("1.", "Sasaran dan Status Bukti", 2),
    "4.4.2": ("2.", "Informasi Model Utuh dan Representasi Graf", 2),
    "4.4.3": ("3.", "Batas Redistribusi Gaya dari Model Utuh", 2),
    "4.4.4": ("4.", "Batas Pembesaran Perpindahan", 2),
    "4.4.5": ("5.", "Kebijakan Berlapis dan Batas Praanalisis", 2),
    "4.4.6": ("6.", "Audit Kebocoran, Ablasi, dan Kriteria Penerimaan", 2),
    "4.5": ("E.", "Dokumentasi Implementasi ARI", 1),
    "4.5.1": ("1.", "Masukan, Keluaran, dan Kontrak Algoritma", 2),
    "4.5.2": ("2.", "Urutan Komputasi Operasional", 2),
    "4.5.3": ("3.", "Pencarian Eksak pada Graf Acuan", 2),
    "4.5.4": ("4.", "Sertifikasi, Pemangkasan, dan Cache", 2),
    "4.5.5": ("5.", "Kode Status Minimum", 2),
    "4.5.6": ("6.", "Implementasi Prototipe yang Tersedia", 2),
    "4.5.7": ("7.", "Kontrak Numerik Solver", 2),
    "4.5.8": ("8.", "Antarmuka Skor dan Anggaran Pencarian", 2),
    "4.5.9": ("9.", "Menjalankan Ulang", 2),
    "4.5.10": ("10.", "Keluaran dan Pemeriksaan Versi", 2),
    "4.5.11": ("11.", "Peta Berkas Bukti Gate 9", 2),
    "4.5.12": ("12.", "Paket Pengembangan Pengaman Kinematik", 2),
    "4.6": ("F.", "Struktur Data dan Manifest Eksperimen", 1),
    "4.6.1": ("1.", "Identitas dan Hubungan Antarberkas", 2),
    "4.6.2": ("2.", "Manifest Konfigurasi", 2),
    "4.6.3": ("3.", "Log Keputusan dan Versi", 2),
    "4.6.4": ("4.", "Pemeriksaan Sebelum Analisis", 2),
    "4.7": ("G.", "Daftar Periksa Verifikasi dan Validasi", 1),
    "4.7.1": ("1.", "Kasus Kanonik", 2),
    "4.7.2": ("2.", "Graf Terhubung tetapi Menjadi Mekanisme", 2),
    "4.7.3": ("3.", "Formulir Verifikasi Numerik", 2),
    "4.7.4": ("4.", "Daftar Periksa Sebelum Pembekuan", 2),
    "4.8": ("H.", "Contoh Analitis untuk Memeriksa Rumus", 1),
    "4.8.1": ("1.", "Dua Batang Paralel", 2),
    "4.8.2": ("2.", "Pemeriksaan yang Dapat Dijalankan", 2),
    "4.8.3": ("3.", "Pelemahan Parsial dan Perubahan Fisik", 2),
    "4.8.4": ("4.", "Normalisasi Ulang Bukan Operasi yang Sama", 2),
    "4.8.5": ("5.", "Contoh Ambang Penyaringan", 2),
    "4.8.6": ("6.", "Mengapa Pemilihan Lintasan Rakus Dapat Salah", 2),
    "4.8.7": ("7.", "Contoh Aritmetika Biaya", 2),
    "4.9": ("I.", "Protokol Finalisasi Naskah dan Data", 1),
    "4.9.1": ("1.", "Asal Naskah dan Batas Kelengkapan", 2),
    "4.9.2": ("2.", "Penggantian Format dengan Hasil Aktual", 2),
    "4.9.3": ("3.", "Keputusan yang Masih Memerlukan Pelaksanaan", 2),
    "4.9.4": ("4.", "Prioritas Perbaikan dan Kriteria Penyelesaian", 2),
    "4.9.5": ("5.", "Batas Klaim pada Versi Akhir", 2),
    "4.9.6": ("6.", "Bukti untuk Klaim Komputasi Berkelanjutan", 2),
    "4.9.7": ("7.", "Pemeriksaan Editorial Akhir", 2),
    "4.10": ("J.", "Protokol Pelaporan Validasi Lanjutan", 1),
    "4.10.1": ("1.", "Keluaran Validasi Utama dan Integrasi", 2),
    "4.10.2": ("2.", "Inventaris dan Verifikasi Model", 2),
    "4.10.3": ("3.", "Kesesuaian Mekanis dan Ablasi", 2),
    "4.10.4": ("4.", "Ketercakupan dan Efisiensi Penyaringan", 2),
    "4.10.5": ("5.", "Pelaporan Integrasi GNN dan Biaya", 2),
    "4.10.6": ("6.", "Pembahasan Konfirmasi dan Validasi Eksternal", 2),
    "4.10.7": ("7.", "Protokol Analisis Kesalahan dan Tindak Lanjut", 2),
    # BAB V
    "5.1": ("A.", "Simpulan", 1),
    "5.2": ("B.", "Ketertelusuran dan Keputusan yang Masih Terbuka", 1),
    "5.3": ("C.", "Implikasi Hasil Penelitian", 1),
    "5.4": ("D.", "Keterbatasan Penelitian", 1),
    "5.5": ("E.", "Saran Penelitian Lanjutan", 1),
}

# Pemetaan rujukan silang di dalam kalimat batang tubuh
CROSS_REF_MAP = {
    "Tabel 1.1": "Tabel 1",
    "Tabel 2.1": "Tabel 2",
    "Tabel 2.2": "Tabel 3",
    "Tabel 2.3": "Tabel 4",
    "Tabel 2.4": "Tabel Lampiran 1",
    "Tabel 2.5": "Tabel Lampiran 1",
    "Tabel 2.6": "Tabel Lampiran 1",
    "Tabel 2.7": "Tabel Lampiran 1",
    "Tabel 2.8": "Tabel Lampiran 1",
    "Tabel 2.9": "Tabel Lampiran 1",
    "Tabel 2.10": "Tabel Lampiran 1",
    "Tabel 2.11": "Tabel 5",
    "Tabel 2.12": "Tabel Lampiran 2",
    "Tabel 3.1": "Tabel 6",
    "Tabel 3.2": "Tabel 7",
    "Tabel 3.3": "Tabel 8",
    "Tabel 3.4": "Tabel 9",
    "Tabel 3.5": "Tabel 10",
    "Tabel 3.6": "Tabel 11",
    "Tabel 3.7": "Tabel 12",
    "Tabel 4.1": "Tabel 13",
    "Tabel 4.2": "Tabel 14",
    "Tabel 4.3": "Tabel 15",
    "Tabel 4.4": "Tabel 16",
    "Tabel 4.5": "Tabel 17",
    "Tabel 4.6": "Tabel 18",
    "Tabel 4.7": "Tabel 19",
    "Tabel 4.8": "Tabel 20",
    "Tabel 4.9": "Tabel 21",
    "Tabel 4.10": "Tabel 22",
    "Tabel 4.11": "Tabel 23",
    "Tabel 4.12": "Tabel 24",
    "Tabel 4.13": "Tabel 25",
    "Tabel 4.14": "Tabel 26",
    "Tabel 4.15": "Tabel 27",
    "Tabel 4.16": "Tabel 28",
    "Tabel 4.17": "Tabel 29",
    "Tabel 4.18": "Tabel 30",
    "Tabel 4.19": "Tabel 31",
    "Gambar 2.1": "Gambar 1",
    "Gambar 2.2": "Gambar 2",
    "Gambar 2.3": "Gambar 3",
    "Gambar 2.4": "Gambar 4",
    "Gambar 3.1": "Gambar 5",
    "Gambar 3.2": "Gambar 6",
    "Gambar 3.3": "Gambar 7",
    "Gambar 4.1": "Gambar 8",
    "Gambar 4.2": "Gambar 9",
    "Gambar 4.3": "Gambar 10",
    "Bagian 2.10": "Bab II Subbab J",
    "Bagian 2.11.2": "Bab II Subbab K.2",
    "Bagian 2.11": "Bab II Subbab K",
    "Bagian 2.18": "Bab II Subbab R",
    "Bagian 3.1": "Bab III Subbab A",
    "Bagian 3.9.3": "Bab III Subbab I.3",
    "Bagian 3.9.4": "Bab III Subbab I.4",
    "Bagian 3.9.5": "Bab III Subbab I.5",
    "Bagian 3.9": "Bab III Subbab I",
    "Bagian 3.11": "Bab III Subbab K",
    "Bagian 3.13": "Bab III Subbab M",
    "Bagian 3.14": "Bab III Subbab N",
    "Bagian 3.15.1": "Bab III Subbab O.1",
    "Bagian 3.16": "Bab III Subbab P",
    "Bagian 3.18.4": "Bab III Subbab R.4",
    "Bagian 3.18.5": "Bab III Subbab R.5",
    "Bagian 3.18.7": "Bab III Subbab R.7",
    "Bagian 3.18": "Bab III Subbab R",
    "Bagian 4.1": "Bab IV Subbab A",
    "Bagian 4.2.4": "Bab IV Subbab B.4",
    "Bagian 4.2.5": "Bab IV Subbab B.5",
    "Bagian 4.2.6": "Bab IV Subbab B.6",
    "Bagian 4.2": "Bab IV Subbab B",
    "Bagian 4.3.6": "Bab IV Subbab C.6",
    "Bagian 4.3": "Bab IV Subbab C",
    "Bagian 4.4": "Bab IV Subbab D",
    "Bagian 4.5.6": "Bab IV Subbab E.6",
    "Bagian 4.5": "Bab IV Subbab E",
    "Bagian 4.8": "Bab IV Subbab H",
    "Bagian 4.9.2": "Bab IV Subbab I.2",
    "Bagian 4.9": "Bab IV Subbab I",
    "Bagian 4.10.1": "Bab IV Subbab J.1",
    "Bagian 4.10.5": "Bab IV Subbab J.5",
    "Bagian 4.10": "Bab IV Subbab J",
    "Bagian 5.2": "Bab V Subbab B",
    "Bab 1": "Bab I",
    "Bab 2": "Bab II",
    "Bab 3": "Bab III",
    "Bab 4": "Bab IV",
    "Bab 5": "Bab V",
}

BROKEN_HYPHEN_FIXES = [
    ("menun jukkan", "menunjukkan"),
    ("keber hasilan", "keberhasilan"),
    ("ter masuk", "termasuk"),
    ("kega galan", "kegagalan"),
    ("kompa tibilitas", "kompatibilitas"),
    ("penya\nringan", "penyaringan"),
    ("penya ringan", "penyaringan"),
    ("pelak sanaan", "pelaksanaan"),
    ("pelam pauan", "pelampauan"),
    ("pemaka ian", "pemakaian"),
    ("Ke sesuaian", "Kesesuaian"),
    ("ke sesuaian", "kesesuaian"),
    ("diterusk an", "diteruskan"),
    ("Diak ses", "Diakses"),
    ("Conferen ce", "Conference"),
    ("me kanis", "mekanis"),
    ("pengu kuran", "pengukuran"),
    ("bebera pa", "beberapa"),
    ("Uru tannya", "Urutannya"),
    ("identi fikasi", "identifikasi"),
    ("memverifi kasi", "memverifikasi"),
    ("ditela ah", "ditelaah"),
    ("ketidak tentuan", "ketidaktentuan"),
    ("per nyataan", "pernyataan"),
    ("peme riksaan", "pemeriksaan"),
    ("diperik sa", "diperiksa"),
    ("pem batas", "pembatas"),
    ("meng ubah", "mengubah"),
    ("mem punyai", "mempunyai"),
    ("meng ganti", "mengganti"),
    ("dipa sangkan", "dipasangkan"),
    ("Ran cangan", "Rancangan"),
    ("Prio ritas", "Prioritas"),
    ("Temu an", "Temuan"),
    ("Pe ngaturan", "Pengaturan"),
    ("kompu tasi", "komputasi"),
    ("Pe nempatan", "Penempatan"),
    ("ber dasarkan", "berdasarkan"),
    ("menguntungk an", "menguntungkan"),
    ("diper tahankan", "dipertahankan"),
    ("kebu tuhan", "kebutuhan"),
    ("tam bah", "tambah"),
    ("Ta bel", "Tabel"),
    ("mo del", "model"),
    ("dinya takan", "dinyatakan"),
    ("res pons", "respons"),
    ("Se telah", "Setelah"),
    ("membandingk\nan", "membandingkan"),
    ("da\nta", "data"),
    ("skorjalur", "skor jalur"),
    ("darijalur", "dari jalur"),
    ("metrikjelas", "metrik jelas"),
    ("gandajika", "ganda jika"),
    ("mempunyaijudul", "mempunyai judul"),
    ("untukTabel", "untuk Tabel"),
]


def clean_text_artifacts(text: str) -> str:
    """Bersihkan kata terputus akibat hyphenation PDF dan perbarui rujukan silang."""
    if not text:
        return text
    out = text
    for old, new in BROKEN_HYPHEN_FIXES:
        out = out.replace(old, new)
    # Sort keys by length descending so Tabel 4.10 replaces before Tabel 4.1
    for old_ref in sorted(CROSS_REF_MAP.keys(), key=len, reverse=True):
        out = re.sub(r"\b" + re.escape(old_ref) + r"\b", CROSS_REF_MAP[old_ref], out)
    return out


# ==============================================================================
# 2. HELPER PEMBUATAN ELEMEN XML WORD (PARAGRAF & TABEL APA/UNY 2023)
# ==============================================================================
def make_p_element(
    text: str = "",
    bold: bool = False,
    italic: bool = False,
    size_pt: float = 12.0,
    align: str = "both",  # left, center, right, both
    line_spacing: float = 2.0,  # 1.0, 1.5, 2.0
    first_line_cm: float = 0.0,
    hanging_cm: float = 0.0,
    left_indent_cm: float = 0.0,
    space_before_pt: float = 0.0,
    space_after_pt: float = 0.0,
    page_break_before: bool = False,
    keep_with_next: bool = False,
    font_name: str = "Times New Roman",
):
    """Buat elemen XML <w:p> murni dengan format UNY 2023."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")

    if page_break_before:
        pPr.append(OxmlElement("w:pageBreakBefore"))
    if keep_with_next:
        pPr.append(OxmlElement("w:keepNext"))

    # Spacing: 240 twips = 1.0 line; 360 = 1.5 lines; 480 = 2.0 lines
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), str(int(round(space_before_pt * 20))))
    spacing.set(qn("w:after"), str(int(round(space_after_pt * 20))))
    spacing.set(qn("w:line"), str(int(round(line_spacing * 240))))
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)

    # Indentation: 1 cm = 567 twips
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), str(int(round(left_indent_cm * 567))))
    ind.set(qn("w:right"), "0")
    if hanging_cm > 0:
        ind.set(qn("w:hanging"), str(int(round(hanging_cm * 567))))
    elif first_line_cm > 0:
        ind.set(qn("w:firstLine"), str(int(round(first_line_cm * 567))))
    else:
        ind.set(qn("w:firstLine"), "0")
    pPr.append(ind)

    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), align)
    pPr.append(jc)

    p.append(pPr)

    if text:
        lines = text.split("\n")
        for idx, line_str in enumerate(lines):
            r = OxmlElement("w:r")
            rPr = OxmlElement("w:rPr")
            rFonts = OxmlElement("w:rFonts")
            rFonts.set(qn("w:ascii"), font_name)
            rFonts.set(qn("w:hAnsi"), font_name)
            rFonts.set(qn("w:cs"), font_name)
            rPr.append(rFonts)
            if bold:
                rPr.append(OxmlElement("w:b"))
                rPr.append(OxmlElement("w:bCs"))
            if italic:
                rPr.append(OxmlElement("w:i"))
                rPr.append(OxmlElement("w:iCs"))
            sz = OxmlElement("w:sz")
            sz.set(qn("w:val"), str(int(round(size_pt * 2))))
            szCs = OxmlElement("w:szCs")
            szCs.set(qn("w:val"), str(int(round(size_pt * 2))))
            rPr.append(sz)
            rPr.append(szCs)
            color = OxmlElement("w:color")
            color.set(qn("w:val"), "000000")
            rPr.append(color)
            r.append(rPr)

            t = OxmlElement("w:t")
            if line_str.startswith(" ") or line_str.endswith(" "):
                t.set(qn("xml:space"), "preserve")
            t.text = line_str
            r.append(t)
            if idx < len(lines) - 1:
                r.append(OxmlElement("w:br"))
            p.append(r)

    return p


def make_toc_entry_element(left_text: str, right_page: str, level: int = 0, bold: bool = False):
    """Buat baris Daftar Isi / Daftar Tabel / Daftar Gambar dengan titik-titik tab kanan di 14,0 cm."""
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")

    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "right")
    tab.set(qn("w:leader"), "dot")
    tab.set(qn("w:pos"), str(int(round(14.0 * 567))))  # 14 cm (lebar area teks A4 margin 4-3)
    tabs.append(tab)
    pPr.append(tabs)

    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), "0")
    spacing.set(qn("w:after"), "60")  # 3 pt
    spacing.set(qn("w:line"), "240")  # 1 spasi sesuai Bab V.B.2.b Panduan UNY 2023
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)

    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), str(int(round(level * 0.75 * 567))))
    ind.set(qn("w:firstLine"), "0")
    pPr.append(ind)

    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "left")
    pPr.append(jc)
    p.append(pPr)

    def _make_run(txt_val, is_bold):
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rFonts = OxmlElement("w:rFonts")
        rFonts.set(qn("w:ascii"), "Times New Roman")
        rFonts.set(qn("w:hAnsi"), "Times New Roman")
        rFonts.set(qn("w:cs"), "Times New Roman")
        rPr.append(rFonts)
        if is_bold:
            rPr.append(OxmlElement("w:b"))
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "24")
        szCs = OxmlElement("w:szCs")
        szCs.set(qn("w:val"), "24")
        rPr.append(sz)
        rPr.append(szCs)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.text = txt_val
        r.append(t)
        return r

    p.append(_make_run(left_text, bold))
    r_tab = OxmlElement("w:r")
    r_tab.append(OxmlElement("w:tab"))
    p.append(r_tab)
    p.append(_make_run(right_page, bold))
    return p


def make_apa_table_element(
    doc,
    headers: list,
    rows_data: list,
    font_size_pt: float = 10.5,
    col_widths_cm: list = None,
    boxed: bool = False,
    font_name: str = "Times New Roman",
):
    """
    Buat elemen XML <w:tbl> bergaya APA 7th Edition / UNY 2023:
    - Garis horizontal atas tabel (12 pt/8 = 1.5 pt), garis bawah header (8 = 1 pt), garis bawah tabel (12 = 1.5 pt).
    - Tanpa garis vertikal (kecuali jika boxed=True untuk diagram skematis).
    - Setiap baris diberi w:cantSplit agar tidak terbelah di tengah sel.
    - Baris pertama diberi w:tblHeader.
    """
    ncols = len(headers) if headers else (len(rows_data[0]) if rows_data else 1)
    tbl = doc.add_table(rows=(1 if headers else 0) + len(rows_data), cols=ncols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    tbl_el = tbl._element
    # Detach immediately from end of body so caller can place it anywhere
    tbl_el.getparent().remove(tbl_el)

    tblPr = tbl_el.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl_el.insert(0, tblPr)

    # Set table width to 100% (5000 pct)
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), "5000")
    tblW.set(qn("w:type"), "pct")

    # Borders
    old_borders = tblPr.find(qn("w:tblBorders"))
    if old_borders is not None:
        tblPr.remove(old_borders)
    if boxed:
        borders_xml = parse_xml(
            f"<w:tblBorders {nsdecls('w')}>"
            '<w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:left w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:right w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
            "</w:tblBorders>"
        )
    else:
        borders_xml = parse_xml(
            f"<w:tblBorders {nsdecls('w')}>"
            '<w:top w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="000000"/>'
            '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
            "</w:tblBorders>"
        )
    tblPr.append(borders_xml)

    # Cell margins (compact padding so tables fit on 1 page)
    old_mar = tblPr.find(qn("w:tblCellMar"))
    if old_mar is not None:
        tblPr.remove(old_mar)
    cell_mar = parse_xml(
        f"<w:tblCellMar {nsdecls('w')}>"
        '<w:top w:w="50" w:type="dxa"/>'
        '<w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="50" w:type="dxa"/>'
        '<w:right w:w="80" w:type="dxa"/>'
        "</w:tblCellMar>"
    )
    tblPr.append(cell_mar)

    all_rows = ([headers] if headers else []) + list(rows_data)
    for r_idx, row_vals in enumerate(all_rows):
        row_obj = tbl.rows[r_idx]
        tr_el = row_obj._tr
        trPr = tr_el.get_or_add_trPr()
        if trPr.find(qn("w:cantSplit")) is None:
            trPr.append(OxmlElement("w:cantSplit"))
        if r_idx == 0 and headers:
            if trPr.find(qn("w:tblHeader")) is None:
                trPr.append(OxmlElement("w:tblHeader"))

        for c_idx in range(ncols):
            val = str(row_vals[c_idx]) if c_idx < len(row_vals) else ""
            cell = row_obj.cells[c_idx]
            tc_el = cell._tc
            tcPr = tc_el.get_or_add_tcPr()
            if col_widths_cm and c_idx < len(col_widths_cm):
                tcW = tcPr.find(qn("w:tcW"))
                if tcW is None:
                    tcW = OxmlElement("w:tcW")
                    tcPr.append(tcW)
                tcW.set(qn("w:w"), str(int(round(col_widths_cm[c_idx] * 567))))
                tcW.set(qn("w:type"), "dxa")

            # Bottom border under header row
            if r_idx == 0 and headers and not boxed:
                tcBorders = tcPr.find(qn("w:tcBorders"))
                if tcBorders is not None:
                    tcPr.remove(tcBorders)
                tcBorders = parse_xml(
                    f"<w:tcBorders {nsdecls('w')}>"
                    '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/>'
                    "</w:tcBorders>"
                )
                tcPr.append(tcBorders)

            # Replace paragraph inside cell
            for old_p in list(tc_el.findall(qn("w:p"))):
                tc_el.remove(old_p)
            is_hdr = r_idx == 0 and bool(headers)
            p_cell = make_p_element(
                text=val,
                bold=is_hdr,
                italic=False,
                size_pt=font_size_pt,
                align="left",
                line_spacing=1.0,
                first_line_cm=0.0,
                space_before_pt=1.5,
                space_after_pt=1.5,
                keep_with_next=(r_idx == 0 and len(all_rows) <= 18),
                font_name=font_name,
            )
            tc_el.append(p_cell)

    return tbl_el


def make_captioned_table(
    doc,
    caption_text: str,
    headers: list,
    rows_data: list,
    font_size_pt: float = 10.5,
    col_widths_cm: list = None,
):
    """
    Kembalikan pasangan [p_caption, tbl_el, p_spacer] sesuai Bab V.B.2.d & V.B.9 Panduan UNY 2023:
    - Judul tabel rata kiri di atas tabel, 1 spasi, keep_with_next=True.
    """
    p_cap = make_p_element(
        text=caption_text,
        bold=True,
        italic=False,
        size_pt=12.0,
        align="left",
        line_spacing=1.0,
        first_line_cm=0.0,
        space_before_pt=10.0,
        space_after_pt=4.0,
        keep_with_next=True,
    )
    tbl_el = make_apa_table_element(
        doc,
        headers=headers,
        rows_data=rows_data,
        font_size_pt=font_size_pt,
        col_widths_cm=col_widths_cm,
        boxed=False,
    )
    return [p_cap, tbl_el]


def make_captioned_figure(
    doc,
    caption_text: str,
    headers: list,
    rows_data: list,
    note_text: str = "",
    font_size_pt: float = 10.5,
):
    """
    Kembalikan elemen-elemen Gambar sesuai Bab V.B.2.d & V.B.9.b Panduan UNY 2023:
    - Tulisan 'Gambar', nomor, dan judul dicantumkan di atas gambar rata kiri, 1 spasi.
    - Diikuti kotak diagram / skema terstruktur yang utuh (tidak pecah ke paragraf lepas).
    """
    p_cap = make_p_element(
        text=caption_text,
        bold=True,
        italic=False,
        size_pt=12.0,
        align="left",
        line_spacing=1.0,
        first_line_cm=0.0,
        space_before_pt=10.0,
        space_after_pt=4.0,
        keep_with_next=True,
    )
    tbl_el = make_apa_table_element(
        doc,
        headers=headers,
        rows_data=rows_data,
        font_size_pt=font_size_pt,
        boxed=True,
    )
    elems = [p_cap, tbl_el]
    if note_text:
        p_note = make_p_element(
            text=note_text,
            bold=False,
            italic=True,
            size_pt=10.5,
            align="left",
            line_spacing=1.0,
            first_line_cm=0.0,
            space_before_pt=3.0,
            space_after_pt=8.0,
        )
        elems.append(p_note)
    return elems


# ==============================================================================
# 3. DATA UTUH TABEL 1 S.D. TABEL 31 & GAMBAR 1 S.D. GAMBAR 10 (BATANG TUBUH)
# ==============================================================================
TABLES_SPEC = {
    "T1": (
        "Tabel 1. Peta Kontribusi, Bukti Pendukung, dan Batas Klaim Penelitian",
        ["Komponen", "Kontribusi dan Bukti Tersedia", "Batas Klaim"],
        [
            [
                "Formulasi ARI",
                "Definisi skor, normalisasi, dan operasi gangguan; implementasi prototipe serta 342 pemeriksaan otomatis kanonik (Gate 9)",
                "Kecocokan implementasi dan sifat matematis; bukan jaminan keunggulan pemeringkatan pada seluruh keluarga struktur",
            ],
            [
                "Contoh penyangkal",
                "Dua kehilangan elemen bergaya awal nol (e3, e4) pada persegi satu diagonal memiliki CI mendekati nol disertai penurunan rank kekakuan",
                "Terbukti pada konfigurasi yang diuji; menunjukkan ketidakcukupan konektivitas skalar sebagai jaminan kestabilan kinematik",
            ],
            [
                "Pengaman kinematik",
                "Adaptasi pemeriksaan spektral model utuh; seluruh 40 kasus rank kurang (paket pengembangan) dan 920 kasus mekanisme (300 model S1–S5, Gate 15) diteruskan",
                "Bukan penemuan matriks redundansi baru; khusus mendeteksi mekanisme dan belum menangkap seluruh pelampauan kapasitas/perpindahan",
            ],
            [
                "Pengayaan konsekuensi",
                "Rumusan batas analitis kapasitas dan perpindahan berbasis model utuh beserta kontrak audit masukan yang eksplisit",
                "Kajian analitis dan evaluasi lapisan kehati-hatian praanalisis (P1 meneruskan kehilangan penuh lambda = 0 dengan recall B 89,7% pada 300 model)",
            ],
            [
                "Integrasi GNN",
                "Protokol pembandingan biaya total dan evaluasi berpasangan 7 perlakuan pada StructGNN-CRC v1.0 lintas 300 model induk (Gate 17)",
                "Inferensi GNN dihemat 83,7% (P0) dan 72,6% (P1), namun waktu total bersih negatif (T_hemat < 0) pada GNN ringan karena biaya pencarian lintasan ARI",
            ],
        ],
    ),
    "T2": (
        "Tabel 2. Pembedaan Konstruk Redundansi dan Batas Interpretasinya",
        ["Konstruk", "Pertanyaan Utama", "Tidak Otomatis Membuktikan"],
        [
            [
                "Konektivitas",
                "Apakah simpul pembebanan dan tumpuan masih terhubung?",
                "Kestabilan kinematik dan kecukupan kapasitas elemen",
            ],
            [
                "Ketidaktentuan statis",
                "Bagaimana kendala dan kontribusi kekakuan elemen terdistribusi?",
                "Respons aman pada seluruh pola beban dan pelemahan parsial",
            ],
            [
                "Jalur alternatif",
                "Bagaimana beban ditransfer melalui lintasan tersisa setelah gangguan?",
                "Kelayakan pada semua mekanisme keruntuhan nonlinier dan dinamik",
            ],
            [
                "Skor ARI",
                "Skenario mana yang diprioritaskan dari informasi praanalisis model utuh?",
                "Probabilitas kegagalan struktur atau keputusan keselamatan akhir",
            ],
        ],
    ),
    "T3": (
        "Tabel 3. Hasil Penelusuran Sumber Tambahan Menurut Tema Literatur",
        ["Tema Kajian", "Sumber Inti", "Sumber Pendukung", "Jumlah"],
        [
            ["Mekanika dan redundansi struktur", "9", "6", "15"],
            ["Graf dan algoritma lintasan", "4", "6", "10"],
            ["GNN dan representasi fisik", "8", "14", "22"],
            ["Reliabilitas dan analisis sensitivitas", "3", "11", "14"],
            ["Validasi dan ketidakpastian prediktif", "5", "8", "13"],
            ["Energi dan biaya komputasi (Green AI)", "0", "5", "5"],
            ["Pemantauan kesehatan struktur (SHM)", "0", "1", "1"],
            ["Total", "29", "51", "80"],
        ],
    ),
    "T4": (
        "Tabel 4. Sumber Terpilih dari Katalog Literatur dan Fungsi Pembandingannya",
        ["Sumber yang Ditemukan", "Persinggungan Metodologis dan Batas Pembandingan"],
        [
            [
                "Tian, Y., Guan, X., Sun, H., & Bao, Y. (2024). An adaptive structural dominant failure modes searching method based on graph neural network. (Sumber primer)",
                "Pembanding dekat untuk pencarian mode kegagalan struktural melalui klasifikasi graf adaptif. Pemilihan sampel dan target mode kegagalan berbeda dari penyaringan deterministik berbasis model utuh.",
            ],
            [
                "Parisi, F., Ruggieri, S., Lovreglio, R., Fanti, M. P., & Uva, G. (2024). On the use of mechanics-informed models to structural engineering systems: Application of GNNs. (Sumber primer)",
                "Kandidat GNN pembanding dengan informasi mekanis dan prediksi deformasi rangka batang 2D serta 3D. Kecocokan fitur kendala dan parameter terlatih tetap harus diaudit untuk integrasi.",
            ],
            [
                "Nourian, N., El-Badry, M., & Jamshidi, M. (2023). Design optimization of truss structures using a graph neural network-based surrogate model. (Sumber primer)",
                "Pembanding prediksi perpindahan rangka batang dan biaya total pengurangan evaluasi FEM. Optimasi ukuran penampang bukan penyaringan gangguan dan pengurangan evaluasi FEM tidak selalu lebih cepat secara total.",
            ],
            [
                "von Scheven, M., Ramm, E., & Bischoff, M. (2021). Quantification of the redundancy distribution in truss and beam structures. (Sumber primer)",
                "Pembanding distribusi ketidaktentuan statis dengan prioritas elemen ARI. Ukuran redundansi mekanis berbasis matriks tidak identik dengan skor jalur graf.",
            ],
            [
                "Krake, T., dkk. (2022). Efficient update of redundancy matrices for truss and frame structures. (Sumber primer)",
                "Pembanding pembaruan informasi redundansi ketika elemen berubah atau dihapus. Biaya dan domain pembaruan harus disamakan dengan skenario gangguan tunggal ARI.",
            ],
            [
                "Tkachuk, A., Krake, T., Gade, J., & von Scheven, M. (2023). Efficient computation of redundancy matrices for moderately redundant truss and frame structures. (Sumber primer)",
                "Alternatif komputasi matriks redundansi untuk pembanding pengaman kinematik. Efisiensi pada struktur moderately redundant bukan jaminan pada seluruh ukuran graf.",
            ],
            [
                "Pellegrino, S. (1993). Structural computations with the singular value decomposition of the equilibrium matrix. (Sumber primer)",
                "Acuan diagnosis rank dan ruang mekanisme melalui dekomposisi nilai singular (SVD) matriks keseimbangan. Toleransi numerik dan kondisi batas perlu diaudit terpisah.",
            ],
            [
                "Connelly, R., & Whiteley, W. (1996). Second-order rigidity and prestress stability for tensegrity frameworks. (Sumber primer)",
                "Dasar membedakan keterhubungan kekakuan orde pertama dan kestabilan prategang. Asumsi tensegrity dan orde kedua tidak otomatis tercakup oleh solver elastis linier ARI.",
            ],
            [
                "Hager, W. W. (1989). Updating the inverse of a matrix. (Sumber primer)",
                "Dasar pembaruan matriks berperingkat rendah (Sherman-Morrison-Woodbury) sebagai alternatif analisis ulang penuh. Rumus invers mensyaratkan keterbalikan sehingga kasus mekanisme memerlukan penanganan khusus.",
            ],
            [
                "Yen, J. Y. (1971). Finding the K shortest loopless paths in a network. (Sumber primer)",
                "Acuan pencarian sejumlah lintasan sederhana tanpa simpul berulang. Lintasan loopless tidak otomatis saling lepas sisi atau optimal bagi objektif kombinasi ARI.",
            ],
            [
                "Moustapha, M., Marelli, S., & Sudret, B. (2022). Active learning for structural reliability: Survey, general framework and benchmark. (Sumber primer)",
                "Kerangka pembanding pengurangan evaluasi mahal melalui pembelajaran aktif. Akses evaluasi fungsi kinerja pascagangguan dan target probabilitas berbeda dari penyaringan praanalisis ARI.",
            ],
            [
                "Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. (Sumber primer)",
                "Dasar metodologis pencegahan bias seleksi saat memilih ambang dan konfigurasi ARI melalui pembekuan protokol sebelum evaluasi buta.",
            ],
        ],
    ),
    "T5": (
        "Tabel 5. Matriks Sintesis Penelitian Terdahulu dan Keputusan Rancangan ARI",
        ["Rujukan Utama", "Fokus yang Digunakan", "Implikasi untuk Penelitian ARI"],
        [
            [
                "Pellegrino & Calladine (1986); Pellegrino (1993)",
                "Rank matriks, tegangan mandiri, dan mekanisme rangka batang",
                "Membedakan kekangan kinematik dan rank kekakuan dari sekadar keterhubungan topologi graf.",
            ],
            [
                "Frangopol & Curley (1987)",
                "Efek kerusakan, redundansi, dan reliabilitas struktural",
                "Menghindari penyamaan skor prioritas deterministik dengan ukuran reliabilitas probabilistik.",
            ],
            [
                "Baker et al. (2008); Starossek & Haberland (2011)",
                "Kuantifikasi ketahanan (robustness) dan keruntuhan progresif",
                "Mendefinisikan secara tegas skenario gangguan, respons acuan, dan batas interpretasi indeks.",
            ],
            [
                "Agrawal et al. (2020)",
                "Analisis jalur beban alternatif pada jembatan rangka baja",
                "Merancang pemeriksaan konfirmasi atas perubahan mekanisme dan redistribusi gaya.",
            ],
            [
                "Gade et al. (2021); von Scheven et al. (2021)",
                "Teori elastostatik dan distribusi matriks redundansi mekanis",
                "Memisahkan operator atau leverage matriks redundansi mekanis (h_e) dari skor jalur graf.",
            ],
            [
                "Okasha et al. (2023)",
                "Indeks redundansi anggota berbasis ketidaktentuan statis terdistribusi",
                "Menyediakan pembanding berbasis mekanika pada domain elemen aksial.",
            ],
            [
                "Caredda et al. (2022); Abbracciavento & De Biagi (2025)",
                "Skenario kerusakan lokal dan transisi jalur beban sistem",
                "Menguji apakah prioritas praanalisis mampu menangkap konsekuensi redistribusi gaya dan perpindahan.",
            ],
            [
                "Setiawan et al. (2024)",
                "Metodologi kuantifikasi ketahanan struktur rangka",
                "Memetakan definisi skenario gangguan dan ambang konsekuensi kritis sebelum evaluasi.",
            ],
            [
                "Echard et al. (2011); Moustapha et al. (2022)",
                "Pembelajaran aktif (AK-MCS) untuk efisiensi evaluasi keandalan",
                "Memisahkan pengurangan evaluasi iteratif berbasis label dari penyaringan satu tahap praanalisis.",
            ],
            [
                "Sanchez-Gonzalez et al. (2020); Pfaff et al. (2021)",
                "Simulasi fisik berbasis jaringan graf dan mesh (GNN)",
                "Memeriksa kesesuaian representasi simpul-sisi dan kondisi batas sebelum transfer ke sistem struktur.",
            ],
            [
                "Song et al. (2023); Chou et al. (2024)",
                "Analisis struktur elastis statik menggunakan Graph Neural Network",
                "Membedakan biaya pembentukan solusi, inferensi GNN tetap, dan biaya penyaringan praanalisis ARI.",
            ],
            [
                "Roberts et al. (2017); Cawley & Talbot (2010)",
                "Validasi data terklaster dan pengendalian bias seleksi model",
                "Menetapkan model induk sebagai unit pembagian partisi dan membekukan konfigurasi sebelum validasi buta.",
            ],
        ],
    ),
    "T6": (
        "Tabel 6. Rencana dan Realisasi Sampel Model Induk menurut Kelompok Evaluasi",
        ["Kode", "Keluarga Struktur atau Fungsi Evaluasi", "Pengembangan", "Validasi Buta", "Uji Akhir"],
        [
            ["S1", "Balok sederhana dan menerus (Euler-Bernoulli)", "36 (24 dev + 12 kal)", "12", "12"],
            ["S2", "Rangka batang bidang (2D planar truss)", "36 (24 dev + 12 kal)", "12", "12"],
            ["S3", "Portal bidang (2D plane frame)", "36 (24 dev + 12 kal)", "12", "12"],
            ["S4", "Portal bidang berpengaku (2D braced frame)", "36 (24 dev + 12 kal)", "12", "12"],
            ["S5", "Rangka ruang sederhana (3D space truss)", "36 (24 dev + 12 kal)", "12", "12"],
            ["Subtotal", "Dataset utama lintas keluarga S1–S5 (300 model induk)", "180", "60", "60"],
            ["S6", "Eksperimen integrasi berpasangan ARI–GNN (StructGNN-CRC v1.0)", "180 (120 latih + 60 kal)", "60", "60"],
            ["S7", "Evaluasi eksternal dokumen struktur nyata (agenda lanjutan)", "Tidak untuk kalibrasi", "—", ">= 25 model"],
        ],
    ),
    "T7": (
        "Tabel 7. Tahapan Validasi Lanjutan dan Syarat Peralihan Antartahap",
        ["Tahap", "Kegiatan Utama", "Luaran dan Syarat Beralih"],
        [
            ["Audit", "Pemeriksaan sumber model, solver, dan cakupan literatur", "Data terlacak, solver lulus uji analitis, dan domain eksplisit"],
            ["Revisi", "Penanganan keterbatasan kanonik melalui pengaman kinematik", "Kandidat kebijakan terversi dan lulus uji regresi mekanisme"],
            ["Pilot & Dataset", "Pembangkitan 300 model induk S1–S5 dan pemeriksaan presisi", "Manifest model induk, partisi anti-bocor, dan kecukupan sampel"],
            ["Pembekuan", "Pengembangan formula, kalibrasi ambang, serta ablasi", "Konfigurasi final terbekukan (manifest_config_frozen.json) sebelum validasi buta"],
            ["Evaluasi", "Validasi buta, uji akhir, dan eksperimen integrasi GNN", "Bukti Gerbang A–D, batas domain lintas keluarga, dan audit biaya total"],
            ["Pelaporan", "Sintesis temuan, audit klaim–bukti, dan dokumentasi akhir", "Paket reproduksi lengkap dan simpulan berbasis hasil aktual"],
        ],
    ),
    "T8": (
        "Tabel 8. Variabel Operasional Penelitian dan Aturan Akses Informasi",
        ["Kelompok", "Variabel Inti", "Aturan Penggunaan dan Batas Akses"],
        [
            ["Geometri", "Koordinat simpul, konektivitas elemen, panjang, dan tumpuan", "Tersedia pada model utuh dan dibekukan untuk setiap skenario."],
            ["Mekanis awal", "E_e, A_e, I_e, R_e, q_e, tuntutan gaya awal, dan reaksi tumpuan", "Masukan sah penyaring jika definisi, satuan, dan biaya perolehannya dicatat."],
            ["Gangguan", "Elemen sasaran e, faktor pelemahan lambda, dan aturan fisik", "Ditentukan sebelum respons pascagangguan dibuka atau dievaluasi."],
            ["Parameter ARI", "Skala s_x, bobot alpha_k, alpha_R, K, gamma, beta, eta, regularisasi", "Dipilih hanya pada partisi pengembangan; dibekukan pada evaluasi buta dan uji akhir."],
            ["Respons acuan", "Perpindahan, gaya internal, utilisasi, kekakuan, dan status rank", "Hanya untuk pengembangan sesuai partisi atau dibuka setelah keputusan penerusan tersimpan."],
            ["Prediksi GNN", "Target regresi CRC, keluaran prediksi, dan status inferensi", "Digunakan pada skenario diteruskan; tidak dipakai menyetel ulang ARI pada data uji."],
            ["Luaran", "Korelasi peringkat, recall, reduksi, galat MAE/RMSE, waktu, memori", "Diringkas per model induk dengan penyebut dan interval ketidakpastian eksplisit."],
        ],
    ),
    "T9": (
        "Tabel 9. Variasi Topologi dan Mekanis Lima Keluarga Struktur (S1–S5)",
        ["Kode", "Variasi Topologi Model Induk", "Variasi Mekanis yang Dipasangkan"],
        [
            ["S1", "Balok satu bentang serta balok menerus 2–4 bentang", "Rasio bentang, kekakuan lentur relatif EI, jenis tumpuan, dan distribusi beban"],
            ["S2", "Rangka batang bidang 2, 4, atau 6 panel", "Tinggi relatif, pola diagonal, variasi luas penampang aksial, beban simetris dan tak simetris"],
            ["S3", "Portal bidang bertingkat 1, 2, atau 4 tingkat", "Jumlah bentang, rasio kekakuan balok–kolom, dan kombinasi beban gravitasi–lateral"],
            ["S4", "Portal bidang dengan pengaku diagonal X, V, atau K", "Kekakuan aksial pengaku, konfigurasi penempatan pengaku, dan arah beban lateral"],
            ["S5", "Rangka ruang 3D sederhana (space truss)", "Kedalaman sistem ruang, konektivitas simpul 3D, tumpuan ruang, dan sebaran beban nodal"],
        ],
    ),
    "T10": (
        "Tabel 10. Instrumen Penelitian, Keluaran, dan Pemeriksaan Penerimaan",
        ["Instrumen", "Keluaran Utama", "Pemeriksaan Penerimaan"],
        [
            ["Lembar/spesifikasi model", "Inventaris geometri, kondisi batas, dan atribut mekanis", "Kelengkapan data wajib, konsistensi satuan, dan keterlacakan sumber"],
            ["Solver struktur (S1–S5)", "Respons model utuh dan pascagangguan serta status rank", "Kesesuaian dengan solusi analitis acuan, keseimbangan gaya, dan deteksi mekanisme"],
            ["Modul inti ARI & pengaman", "Skor RR, ARI, CI, margin spektral m_e, dan sertifikasi", "Uji unit deterministik, invariansi pelabelan/satuan, monotonisitas, dan kasus batas"],
            ["Manifest eksperimen", "Pembagian partisi data, parameter terbekukan, dan hash versi", "Verifikasi nol kebocoran ID model induk lintas partisi (anti-leakage)"],
            ["Antarmuka GNN acuan", "Prediksi indikator kekritisan (CRC) dan status inferensi", "Kesesuaian domain struktur, target evaluasi, dan bobot terlatih yang identik"],
            ["Pencatat biaya operasional", "Rekaman waktu per komponen, memori, dan status kegagalan", "Kelengkapan komponen biaya pada Tabel 31 tanpa penghitungan ganda"],
        ],
    ),
    "T11": (
        "Tabel 11. Prasyarat Realisasi Lima Keluarga Dataset Utama dan Status Verifikasi Solver",
        ["Kode", "Model Mekanis yang Harus Tersedia", "Bukti Minimum Sebelum Produksi Data dan Status Realisasi"],
        [
            [
                "S1",
                "Elemen balok Euler-Bernoulli dengan translasi dan rotasi",
                "Lendutan dan reaksi acuan, momen, geser, serta kondisi ujung [Tersedia & lulus 100%: Gate 12, solve_beam_1d]",
            ],
            [
                "S2",
                "Batang aksial bidang (2D planar truss)",
                "Gaya aksial, kompatibilitas, keseimbangan, serta mekanisme acuan [Tersedia & lulus 100%: Gate 9 & Gate 12, solve_truss_2d]",
            ],
            [
                "S3",
                "Elemen portal bidang dengan aksi aksial dan lentur",
                "Transformasi lokal–global, rotasi simpul, serta pelepasan ujung [Tersedia & lulus 100%: Gate 12, solve_frame_2d]",
            ],
            [
                "S4",
                "Portal bidang dengan elemen pengaku diagonal",
                "Sambungan pengaku, interaksi aksial–lentur, serta idealisasi tarik/tekan [Tersedia & lulus 100%: Gate 12, solve_braced_frame_2d]",
            ],
            [
                "S5",
                "Rangka ruang 3D dengan idealisasi elemen aksial ruang",
                "Komponen ruang 3D, kekangan tumpuan, dan keseimbangan gaya nodal [Tersedia & lulus 100%: Gate 12, solve_space_truss_3d]",
            ],
        ],
    ),
    "T12": (
        "Tabel 12. Audit Kandidat Model Graph Neural Network (GNN) Acuan",
        ["Kandidat Model", "Dasar Pertimbangan Teknis", "Keputusan Audit dan Status Pelaksanaan"],
        [
            [
                "StructGNN (Chou et al., 2024)",
                "Implementasi analisis statik struktur bertingkat berbasis GNN",
                "Memerlukan adaptasi representasi lintas keluarga dan penyetaraan kepala keluaran CRC",
            ],
            [
                "StructGNN-E (Song et al., 2023)",
                "Analisis struktur elastis berbasis fisika tanpa label penuh",
                "Keterbatasan akses parameter terlatih publik dan perbedaan antarmuka komponen CRC",
            ],
            [
                "StructGNN-CRC v1.0 (Realisasi S6, Gate 17)",
                "3-Layer Edge-Node Message-Passing GNN + Dual-Head ReLU MLP murni berbasis fitur fisik/geometris skenario",
                "Ditetapkan dan dibekukan untuk eksperimen S6 (gnn_weights_s6.npz, SHA-256: 81f00159a791e02f...); dilatih sekali pada formula_dev (120 model)",
            ],
        ],
    ),
    "T13": (
        "Tabel 13. Hasil Solver pada Empat Model Kanonik Utuh",
        ["Model Kanonik", "Batang", "Rank/DOF", "u_max (mm)", "U_max", "W (kN mm)"],
        [
            ["Paralel", "2", "1/1", "1,000000", "0,500000", "15,000000"],
            ["Segitiga", "3", "3/3", "1,154460", "0,442218", "16,956287"],
            ["Satu diagonal", "5", "5/5", "5,935311", "0,530330", "86,139610"],
            ["Dua diagonal", "6", "5/5", "3,582277", "0,320083", "51,989854"],
        ],
    ),
    "T14": (
        "Tabel 14. Status Gangguan pada Empat Model Kanonik (Kontrol Tidak Masuk Jumlah Gangguan)",
        ["Model Kanonik", "Jumlah Gangguan", "Solusi Unik", "Rank Kurang", "Graf Terhubung"],
        [
            ["Paralel", "8", "8", "0", "8"],
            ["Segitiga", "12", "9", "3", "12"],
            ["Satu diagonal", "20", "15", "5", "20"],
            ["Dua diagonal", "24", "24", "0", "24"],
        ],
    ),
    "T15": (
        "Tabel 15. Kehilangan Satu Batang pada Persegi Satu Diagonal: Skor Graf dan Rank Mekanis",
        ["Batang Dihapus", "RR", "CI", "Rank/DOF"],
        [
            ["e1", "0,983152", "0,016848", "4/5"],
            ["e2", "0,964724", "0,216162", "4/5"],
            ["e3", "1,000000", "0,000000", "4/5"],
            ["e4", "1,000000", "0,000000", "4/5"],
            ["e5", "0,717285", "0,472914", "4/5"],
        ],
    ),
    "T16": (
        "Tabel 16. Uji Regresi Dua Kehilangan Elemen Bergaya Awal Nol pada Persegi Satu Diagonal",
        ["Elemen", "CI", "h_e", "m_e", "Rank/DOF", "Keputusan ARI", "Keputusan Gabungan"],
        [
            ["e3", "1,11e-16", "1,000000", "1,11e-16", "4/5", "Tidak diteruskan", "Diteruskan"],
            ["e4", "0,00e+00", "1,000000", "2,22e-16", "4/5", "Tidak diteruskan", "Diteruskan"],
        ],
    ),
    "T17": (
        "Tabel 17. Diagnostik Pengembangan pada Ambang CI 0,50 (Runner Lokal)",
        ["Kelompok Model", "Kebijakan", "N Skenario", "Diteruskan", "Rank Terlewat", "Kritis Terlewat"],
        [
            ["Kanonik", "ARI saja", "64", "5", "6/8", "14/17"],
            ["Kanonik", "Pengaman saja", "64", "8", "0/8", "9/17"],
            ["Kanonik", "Gabungan", "64", "11", "0/8", "8/17"],
            ["Parametrik", "ARI saja", "272", "17", "24/32", "54/71"],
            ["Parametrik", "Pengaman saja", "272", "32", "0/32", "39/71"],
            ["Parametrik", "Gabungan", "272", "41", "0/32", "30/71"],
        ],
    ),
    "T18": (
        "Tabel 18. Diagnostik Parametrik dalam Paket Unggahan Gate 9 (N = 272 Skenario)",
        ["Kebijakan", "Diteruskan", "Rank Terlewat (n = 32)", "Kritis Terlewat A (n = 94)", "Kritis Terlewat B (n = 71)"],
        [
            ["ARI saja", "30", "22", "67", "50"],
            ["Pengaman saja", "32", "0", "62", "39"],
            ["Gabungan (P0)", "52", "0", "45", "28"],
        ],
    ),
    "T19": (
        "Tabel 19. Sintesis Hubungan Pertanyaan Penelitian, Bukti Aktual, dan Batas Jawaban",
        ["Pokok Pertanyaan", "Bukti Aktual dalam Disertasi", "Batas Jawaban dan Lingkup Keberlakuan"],
        [
            [
                "1. Formulasi ARI",
                "Definisi operasional, normalisasi tetap, operasi gangguan tanpa normalisasi ulang, dan pembuktian sifat matematis [0, 1]",
                "Skor merupakan indeks prioritas relatif praanalisis, bukan ukuran kapasitas sisa atau keandalan probabilistik",
            ],
            [
                "2. Verifikasi algoritma",
                "342 pemeriksaan otomatis kanonik, 1.475 uji pengaman, serta 7.940 skenario lintas keluarga S1–S5 terverifikasi 100% tersertifikasi",
                "Pencarian eksak terjamin pada batas anggaran graf yang diuji; graf skala sangat besar memerlukan pemangkasan/abstensi",
            ],
            [
                "3. Kesesuaian mekanis dan nilai tambah",
                "Identifikasi contoh penyangkal (e3, e4 dengan CI = 0 namun rank turun) serta pembuktian nilai tambah gabungan ARI + pengaman spektral (median Spearman rho = 0,7023 pada 300 model)",
                "Skor jalur graf skalar tidak mencukupi sendiri tanpa pengaman kinematik untuk menjamin kestabilan mekanis",
            ],
            [
                "4. Sensitivitas dan batas keberlakuan",
                "Ablasi berpasangan 6 varian dan evaluasi lintas 5 keluarga struktur (S1–S5) pada 300 model induk (Gate 15)",
                "Kinerja sangat kuat pada struktur dominan aksial (S2/S5: recall 95,4%–99,0%), namun terbatas pada pelemahan parsial lentur (S1/S3/S4)",
            ],
            [
                "5. Kelayakan penyaringan",
                "Evaluasi protokol beku (tau = 0,50): P0 mereduksi 83,8% evaluasi (recall B = 64,8%, pada S2 = 99,0%); P1 mereduksi 72,6% evaluasi (recall B = 89,7%, rerata model = 90,0%, L95 = 88,4%)",
                "Kebijakan dasar P0 lulus penuh pada S2, sedangkan lintas keluarga S1–S5 memerlukan lapisan kehati-hatian P1 (meneruskan lambda = 0)",
            ],
            [
                "6. Manfaat integrasi ARI–GNN",
                "Eksperimen berpasangan 7 perlakuan dengan StructGNN-CRC v1.0 dan pengukuran biaya 10x pengulangan (Gate 17)",
                "Mutu recall akhir terjaga (P1 = 88,1%, S2 = 99,0%) dan inferensi GNN dihemat 72,6%–83,7%, namun waktu total bersih negatif pada GNN ringan karena biaya pencarian lintasan ARI",
            ],
        ],
    ),
    "T20": (
        "Tabel 20. Kode Status Operasional Minimum yang Disarankan dalam Implementasi",
        ["Kode Status", "Makna Operasional dan Tindakan Kebijakan"],
        [
            ["scored", "Skor ARI/CI sah dan pencarian lintasan tersertifikasi; terapkan aturan ambang penerusan."],
            ["invalid_input", "Masukan model atau skenario tidak sah; rekam alasan kesalahan dan jangan lakukan imputasi skor."],
            ["invalid_baseline", "Model utuh tidak layak atau matriks kekakuan awal singular; abstensi seluruh skenario terkait."],
            ["search_timeout", "Pencarian lintasan melampaui batas anggaran waktu/keadaan; beri status abstensi dan teruskan skenario."],
            ["uncertified", "Optimasi kombinasi lintasan belum tersertifikasi eksak; masukkan ke himpunan abstensi dan teruskan."],
            ["not_forwarded", "Skor sah, pengaman cleared, dan CI di bawah ambang; skenario tidak diteruskan ke inferensi GNN."],
            ["gnn_failed", "Inferensi GNN gagal pada skenario yang diteruskan; catat sebagai kegagalan prediktor dalam evaluasi akhir."],
            ["out_of_domain", "Model atau jenis gangguan berada di luar domain keberlakuan metode; abstensi wajib dan teruskan."],
            ["reference_unresolved", "Solver acuan pascagangguan gagal konvergen di luar kasus mekanisme sah; pisahkan dalam audit mutu data."],
        ],
    ),
    "T21": (
        "Tabel 21. Keluaran Aktual pada Direktori results/verification/",
        ["Nama Berkas", "Isi dan Fungsi Verifikasi"],
        [
            ["baseline.csv", "Respons solver dan skor graf pada empat model kanonik utuh."],
            ["scenarios.csv", "Rekaman 64 skenario gangguan dan 16 kontrol beserta status terpisah."],
            ["checks.csv", "Daftar 342 pemeriksaan otomatis, nilai harapan analitis, dan status kelulusan."],
            ["manifest.json", "Konfigurasi parameter, versi pustaka, waktu eksekusi, serta hash kode dan masukan."],
            ["Tabel.tex", "Ringkasan tabel numerik hasil verifikasi kanonik."],
            ["models.pdf", "Diagram geometri dan kondisi batas empat model kanonik."],
            ["ci_by_damage.pdf", "Kurva hubungan CI terhadap faktor kekakuan tersisa dan penanda status rank acuan."],
        ],
    ),
    "T22": (
        "Tabel 22. Berkas Bukti Numerik dalam Paket Unggahan Gate 9",
        ["Nama Berkas", "Isi yang Diperiksa dan Diverifikasi"],
        [
            ["prism-uploads/baseline.xlsx", "Respons model kanonik utuh: rank, perpindahan maksimum, utilisasi, dan energi regangan."],
            ["prism-uploads/checks.xlsx", "68 pemeriksaan numerik kanonik; seluruh baris berstatus lulus."],
            ["prism-uploads/scenarios.xlsx", "Skor ARI/CI dan status solver pada skenario gangguan serta kontrol kanonik."],
            ["prism-uploads/decisions.xlsx", "Keputusan kebijakan penyaringan untuk 272 skenario parametrik pengembangan."],
            ["prism-uploads/forwarded.xlsx", "Daftar 52 skenario parametrik yang diteruskan oleh setidaknya satu kebijakan."],
            ["prism-uploads/remaining_misses.xlsx", "Rincian 28 kasus kritis terlewat pada rekap kebijakan gabungan konvensi B."],
        ],
    ),
    "T23": (
        "Tabel 23. Skema Minimum Berkas Data Penelitian dan Pemeriksaan Integritas",
        ["Berkas Logis", "Kolom Inti", "Pemeriksaan Integritas"],
        [
            ["Model", "ID induk/varian, keluarga struktur, sumber, partisi data, satuan", "ID model induk tidak melintasi lebih dari satu partisi data."],
            ["Simpul", "ID simpul, koordinat ruang/bidang, derajat kebebasan terkekang", "Koordinat berhingga dan kondisi tumpuan eksplisit."],
            ["Elemen", "ID sisi, dua simpul ujung, jenis elemen, E, A, I, kapasitas, kondisi awal", "ID elemen unik; kapasitas dan tuntutan gaya sebanding."],
            ["Beban", "ID kasus beban, simpul/elemen sasaran, komponen arah, nilai, satuan", "Satuan gaya dan momen lentur konsisten serta tidak tercampur."],
            ["Skenario", "ID skenario, elemen sasaran, faktor lambda, aturan perubahan fisik", "Skenario kontrol (lambda = 1) dan gangguan dibedakan secara tegas."],
            ["ARI & Pengaman", "Skor dasar/gangguan, RR, ARI, CI, margin spektral m_e, sertifikasi", "Versi parameter dan sertifikasi algoritma terekam sebelum evaluasi."],
            ["Acuan Mekanis", "Status solver, respons perpindahan/utilisasi, nilai CRC, label kritis", "Diakses terpisah dari perhitungan skor operasional praanalisis."],
            ["GNN Acuan", "ID hash parameter, prediksi CRC, status target sah, status inferensi", "Tidak diimputasi nol untuk skenario yang tidak diteruskan."],
            ["Biaya Komputasi", "Tahap proses, waktu dinding, memori, spesifikasi perangkat, ulangan", "Komponen waktu total terpisah dan tidak terhitung ganda."],
        ],
    ),
    "T24": (
        "Tabel 24. Daftar Kasus Uji Verifikasi Minimum dan Hasil yang Diharapkan",
        ["ID Kasus", "Kasus Uji Verifikasi", "Pemeriksaan dan Hasil yang Diharapkan"],
        [
            ["A01", "Kontrol tanpa gangguan (lambda = 1)", "RR tepat bernilai 1; CI sama dengan prioritas utilisasi awal."],
            ["A02", "Dua jalur paralel identik", "Kehilangan satu jalur menurunkan skor pasangan sesuai hitungan analitis."],
            ["A03", "Dua jalur paralel tidak identik", "Urutan prioritas mengikuti kontribusi bobot kekakuan dan kapasitas."],
            ["A04", "Pelemahan bertahap (monotonisitas)", "Skor ARI tidak meningkat (dan CI tidak menurun) ketika lambda berkurang."],
            ["A05", "Penghapusan sisi penuh (lambda = 0)", "Sisi yang dihapus dikeluarkan dari graf, bukan disisakan sebagai jalur berbiaya besar."],
            ["A06", "Pelabelan ulang simpul dan sisi", "Nilai skor invarian (tidak berubah di luar toleransi titik mengambang)."],
            ["A07", "Konversi satuan konsisten", "Skor tetap identik apabila seluruh atribut dan skala dikonversi secara konsisten."],
            ["A08", "Graf terputus pascagangguan", "Pasangan simpul tanpa lintasan penghubung memberikan kontribusi skor nol."],
            ["A09", "Skor model dasar tidak layak", "Seluruh skenario turunan pada model terkait memperoleh status abstensi."],
            ["A10", "Solusi lintasan rakus menyesatkan", "Optimasi memilih kombinasi objektif maksimum, bukan lintasan terpendek pertama."],
            ["A11", "Saturasi utilisasi awal", "Konfigurasi eta = 1 dan U* = 1 menghasilkan ARI nol tanpa klaim konsekuensi identik."],
            ["A12", "Penghapusan akses label evaluasi", "Skor ARI dan keputusan penerusan tetap identik tanpa membaca respons pascagangguan."],
            ["B01", "Graf terhubung menjadi mekanisme", "Ketidakstabilan kinematik dikenali oleh solver/pengaman dan tidak disamakan dengan konektivitas."],
            ["B02", "Kekakuan kecil, kapasitas tinggi", "Kompensasi bobot aditif diuji terhadap respons mekanis aktual."],
            ["B03", "Variasi lokasi beban dan tumpuan", "Perubahan pasangan aktif dan dominasi bobot diperiksa secara terpisah."],
            ["G01", "Graf identik dengan urutan ID berbeda", "Prediksi GNN acuan tetap cocok dalam toleransi numerik yang dibekukan."],
            ["G02", "Inferensi GNN gagal atau di luar domain", "Status kegagalan dan biaya waktu tetap tercatat dalam evaluasi akhir."],
        ],
    ),
    "T25": (
        "Tabel 25. Contoh Analitis Dua Batang Paralel dalam Limit Regularisasi Nol",
        ["Kondisi Skenario", "Rasio Redundansi (RR)", "Skor ARI", "Indeks Kekritisan (CI)"],
        [
            ["Kontrol utuh (lambda = 1)", "1", "3/4 (0,7500)", "1/4 (0,2500)"],
            ["Batang pertama hilang (e1, lambda = 0)", "7/17 (0,4118)", "21/68 (0,3088)", "47/68 (0,6912)"],
            ["Batang kedua hilang (e2, lambda = 0)", "10/17 (0,5882)", "15/34 (0,4412)", "19/34 (0,5588)"],
        ],
    ),
    "T26": (
        "Tabel 26. Hitungan Ambang Penyaringan pada Contoh Analitis Delapan Gangguan",
        ["Ambang CI", "Jumlah Diteruskan", "Kritis Tertangkap", "Recall", "Reduksi Evaluasi"],
        [
            ["0,00", "8", "2", "1 (100,0%)", "0 (0,0%)"],
            ["0,55", "3", "2", "1 (100,0%)", "5/8 (62,5%)"],
            ["0,60", "1", "1", "1/2 (50,0%)", "7/8 (87,5%)"],
        ],
    ),
    "T27": (
        "Tabel 27. Status Pemenuhan Prasyarat Pelaksanaan Eksperimen dan Validasi",
        ["Keputusan Metodologis", "Bukti Pelaksanaan dan Status Ketersediaan"],
        [
            ["Solver dan model dasar", "Tersedia & terverifikasi: solver lima keluarga S1–S5 (100% lulus uji analitis) dan 300 model induk (Gate 12–13)."],
            ["GNN acuan final", "Tersedia & dibekukan: StructGNN-CRC v1.0 (gnn_model_card_s6.json & gnn_weights_s6.npz, SHA-256: 81f00159a791e02f...; Gate 17)."],
            ["Jumlah model dan partisi", "Tersedia: 300 model induk S1–S5 (1.910 elemen, 7.940 skenario) beserta inferensi bootstrap B = 10.000 (Gate 13 & Gate 15)."],
            ["Ambang dan toleransi beku", "Tersedia & dibekukan: manifest_config_frozen.json (ARI-FROZEN-PROTOCOL-v1.0, SHA-256: 879ee5bd0497f6d7...; Gate 14)."],
            ["Kelulusan Gerbang A–D", "Tersedia lengkap pada 300 model: Gerbang A, B, dan C lulus penuh; Gerbang D dievaluasi pada P0, P1, dan P5 (Gate 15)."],
            ["Manfaat integrasi ARI–GNN", "Tersedia & dievaluasi berpasangan (7 perlakuan, 10x pengulangan): inferensi GNN dihemat 83,7% (P0) dan 72,6% (P1), namun T_hemat bersih negatif pada GNN ringan; S2 lulus mutu recall akhir 99,0% (Gate 17)."],
            ["Energi listrik dan emisi", "Protokol pengukuran telah dirumuskan; telemetri perangkat keras belum dijalankan (agenda penelitian lanjutan W9)."],
        ],
    ),
    "T28": (
        "Tabel 28. Rincian Pekerjaan Finalisasi, Lokasi Artefak, dan Kriteria Penyelesaian",
        ["Pekerjaan dan Status", "Keluaran Utama dan Lokasi Artefak", "Kriteria Penyelesaian"],
        [
            [
                "1. Revisi kebijakan ARI (Selesai — Gate 11 & 15)",
                "Pengaman kinematik spektral, uji regresi rank, diagnostik parametrik, dan analisis kasus kritis terlewat (results/revision/ & results/screening/).",
                "Dibandingkan dengan versi awal; seluruh kasus gagal dicatat transparan; aturan penerusan bebas dari akses label pascagangguan.",
            ],
            [
                "2. Dataset dan solver utama (Selesai — Gate 12 & 13)",
                "Manifest 300 model induk S1–S5, satuan, kondisi batas, verifikasi solver analitis, dan partisi anti-bocor (results/dataset/).",
                "Seluruh model dapat direkonstruksi ulang; ID model induk dan turunannya tidak bocor antarbagian data; nol imputasi fiktif.",
            ],
            [
                "3. Pembandingan dan kestabilan (Selesai — Gate 15)",
                "Hasil pembanding praanalisis, studi ablasi 6 varian, sensitivitas, bootstrap B = 10.000, dan evaluasi Gerbang A–C (results/validation/).",
                "Acuan evaluasi sebanding; konfigurasi dibekukan sebelum evaluasi buta; hasil per keluarga dilaporkan menurut kriteria gerbang.",
            ],
            [
                "4. Penyaringan operasional (Selesai — Gate 14 & 15)",
                "Protokol beku manifest_config_frozen.json, log keputusan 7.940 skenario, recall, reduksi, abstensi, dan keputusan Gerbang D (results/screening/).",
                "Keputusan penerusan tersimpan sebelum label evaluasi dibuka; penyebut metrik eksplisit; ketidakpastian dihitung per model induk.",
            ],
            [
                "5. Integrasi ARI–GNN (Selesai — Gate 17)",
                "Kartu model StructGNN-CRC v1.0, bobot beku, evaluasi berpasangan 7 perlakuan, dan audit biaya 10x pengulangan (results/integration/).",
                "Perlakuan dengan dan tanpa penyaringan memakai bobot GNN serta perangkat yang identik; ketercakupan akhir dan waktu total dilaporkan utuh.",
            ],
            [
                "6. Pelaporan akhir (Disinkronkan hingga Gate 17)",
                "Naskah disertasi, tabel hasil aktual Gate 9–17, matriks klaim–bukti, dan lampiran kerja terverifikasi.",
                "Seluruh klaim ditautkan ke artefak aktual; judul, abstrak, bab hasil, dan simpulan konsisten mengikuti Panduan Disertasi UNY 2023.",
            ],
        ],
    ),
    "T29": (
        "Tabel 29. Inventaris Hasil Aktual menurut Himpunan Partisi Evaluasi",
        ["Himpunan Data", "Jumlah Model dan Skenario", "Status Mutu dan Capaian Utama", "Sumber Artefak Terverifikasi"],
        [
            [
                "Pengembangan (Dev + Kalibrasi)",
                "180 model induk (120 formula_dev + 60 kalibrasi); 4.576 gangguan + 180 kontrol",
                "100% lulus solver; parameter & ambang terkalibrasi (P0 RecB = 65,4%, P1 RecB = 90,4%; Gate 13–15)",
                "results/dataset/manifest.json & results/screening/decisions_300.csv",
            ],
            [
                "Validasi Buta (Blind Validation)",
                "60 model induk (12 per keluarga S1–S5); 1.524 gangguan + 60 kontrol",
                "Terkunci pra-evaluasi & diuji tanpa setel ulang (P0 RecB = 63,6%, P1 RecB = 88,4%; Gate 14–15)",
                "manifest_config_frozen.json & results/validation/full_evaluation_300.csv",
            ],
            [
                "Uji Akhir (Final Test)",
                "60 model induk (12 per keluarga S1–S5); 1.540 gangguan + 60 kontrol",
                "Dievaluasi independen (P0 RecB = 64,6%, P1 RecB = 89,1%; S2 RecB = 99,0%; Gate 15)",
                "results/validation/full_evaluation_300.csv & gate_validation_report_300.json",
            ],
            [
                "Integrasi GNN (S6)",
                "300 model induk S1–S5 (latih: 120, kal: 60, buta: 60, uji: 60; 7 perlakuan berpasangan)",
                "Tersedia: StructGNN-CRC v1.0 (RecEnd T0 = 97,7%, P1 = 88,1%, S2 = 99,0%; T_hemat < 0; Gate 17)",
                "results/integration/gnn_model_card_s6.json & integration_report_s6.json",
            ],
            [
                "Eksternal (S7)",
                "Belum tersedia (direncanakan >= 25 model struktur nyata)",
                "Belum tersedia (agenda penelitian lanjutan di luar sampel parametrik S1–S5)",
                "Protokol audit model eksternal (Bab III Subbab O.2)",
            ],
        ],
    ),
    "T30": (
        "Tabel 30. Ringkasan Bukti dan Status Keputusan Gerbang Validasi (Gerbang A–D dan Integrasi)",
        ["Gerbang Evaluasi", "Bukti Wajib yang Ditampilkan", "Status Bukti Aktual dan Capaian Kuantitatif"],
        [
            [
                "Gerbang A (Verifikasi Matematis & Algoritmis)",
                "Uji rentang [0, 1], monotonisitas, invariansi satuan/pelabelan, dan sertifikasi lintasan",
                "LULUS LENGKAP: 68/68 cek kanonik, 1.475 cek pengaman, dan 7.940/7.940 skenario S1–S5 tersertifikasi 100% (Gate 9 & Gate 15).",
            ],
            [
                "Gerbang B (Kesesuaian Mekanis)",
                "Korelasi peringkat terhadap CRC acuan, selisih pembanding, dan galat peringkat",
                "LULUS PADA 300 MODEL: median korelasi Spearman rho = 0,7023 (>= 0,70) pada kebijakan gabungan P0, melampaui ARI murni (0,4913) dan utilisasi awal (0,3791) (Gate 15).",
            ],
            [
                "Gerbang C (Kestabilan, Sensitivitas & Ablasi)",
                "Perturbasi parameter, studi ablasi 6 varian berpasangan, dan penangkapan mekanisme",
                "LULUS PADA 300 MODEL: 920/920 skenario penurunan rank/mekanisme tertangkap 100% (0 terlewat); kontribusi masing-masing komponen terukur jelas pada ablasi (Gate 15).",
            ],
            [
                "Gerbang D (Kelayakan Penyaringan Praanalisis)",
                "Recall kasus kritis, reduksi evaluasi, proporsi abstensi, dan batas bawah bootstrap L_0,95",
                "TERSEDIA LENGKAP (300 MODEL): P0 mereduksi 83,8% evaluasi (RecB gabungan = 64,8%; LULUS PENUH pada S2 rangka batang dengan RecB = 99,0%, L_0,95 = 96,9%). Kebijakan P1 mereduksi 72,6% evaluasi dengan rerata recall model = 90,0% (L_0,95 = 88,4%) (Gate 15).",
            ],
            [
                "Integrasi ARI–GNN (S6)",
                "Recall akhir sistem (RecEnd), galat prediksi MAE/RMSE sebanding, dan penghematan waktu bersih (T_hemat)",
                "TERSEDIA LENGKAP (300 MODEL, Gate 17): StructGNN-CRC v1.0 mencapai RecEnd T0 = 97,7%, P0 = 64,3%, P1 = 88,1% (pada S2: RecEnd = 99,0%, L_0,95 = 96,9%). Waktu inferensi GNN dihemat 83,7% (P0) dan 72,6% (P1), tetapi T_hemat total negatif (-15.761,5 ms pada ALL_300) karena T_ARI > T_GNN (Hipotesis H4 ditolak untuk GNN ringan).",
            ],
        ],
    ),
    "T31": (
        "Tabel 31. Pemisahan Biaya Operasional Integrasi ARI–GNN (Rerata 10 Pengulangan Berpasangan Tanpa Cache)",
        ["Komponen Biaya Operasional", "Keterangan Pengukuran Aktual pada Eksperimen S6 (Gate 17)"],
        [
            [
                "Respons model utuh (T_utuh)",
                "Analisis FEM awal model utuh untuk atribut dan gaya dasar: ALL_300 = 253,1 ms | blind_val (60 model) = 59,4 ms | final_test (60 model) = 48,0 ms.",
            ],
            [
                "Perhitungan ARI, pengaman & seleksi (T_ARI + T_seleksi)",
                "Pencarian lintasan kombinatorial dan dekomposisi spektral pengaman: ALL_300: T_ARI = 22.098,6 ms, T_seleksi = 6,1 ms | blind_val = 4.414,4 ms | final_test = 4.386,4 ms.",
            ],
            [
                "Pembentukan graf & inferensi GNN (T_graf + T_inferensi)",
                "Konstruksi fitur graf skenario dan inferensi StructGNN-CRC v1.0 pada himpunan diteruskan: ALL_300 Tanpa Saring: T_graf = 3.994,3 ms, T_inf = 3.577,9 ms (total 7.572,3 ms) | P0: T_graf = 652,6 ms, T_inf = 582,4 ms (hemat 83,7%) | P1: T_graf = 1.096,0 ms, T_inf = 982,4 ms (hemat 72,6%).",
            ],
            [
                "Penanganan, total waktu & selisih bersih (T_hemat)",
                "Pengukuran berpasangan 10x pengulangan: ALL_300 T_tanpa = 7.834,0 ms vs T_ARI-GNN(P0) = 23.595,5 ms (T_hemat = -15.761,5 ms atau -201,2%) dan T_ARI-GNN(P1) = 24.440,1 ms (T_hemat = -16.606,0 ms atau -212,0%).",
            ],
            [
                "Biaya persiapan terpisah (di luar waktu operasional)",
                "Dicatat terpisah dari siklus operasional: pelatihan & kalibrasi StructGNN-CRC v1.0 = 2.464,7 ms; pemanasan (warm-up) = 57,8 ms; evaluasi solver FEM eksak 7.640 skenario untuk label evaluasi = 8.115,2 ms.",
            ],
        ],
    ),
}

FIGURES_SPEC = {
    "G1": (
        "Gambar 1. Transformasi Skematis Rangka Batang Menjadi Graf Berbobot Mekanis dan Lintasan Alternatif",
        ["Tahap Representasi", "Skema Struktur / Graf", "Keterangan Komponen Mekanis dan Graf"],
        [
            [
                "(a) Model struktur fisik",
                "Simpul tumpuan A, B; simpul beban C (beban P); elemen batang e1 (A–B), e2 (B–C), e3 (C–A)",
                "Geometri, beban nodal P, dan kondisi batas tumpuan; setiap elemen memiliki atribut E_e, A_e, L_e, kapasitas R_e, dan faktor kondisi awal q_e.",
            ],
            [
                "(b) Identitas multigraf",
                "V_L = {C} (simpul beban), V_T = {A, B} (simpul tumpuan); unsur mekanis e_1, e_2, e_3 dipetakan menjadi sisi graf",
                "Setiap elemen struktural mempertahankan identitas sisi tersendiri sehingga elemen paralel tetap dapat dibedakan.",
            ],
            [
                "(c) Bobot sisi dan lintasan bebas sisi",
                "Pasangan aktif C–A memiliki lintasan langsung p_1: C -> A (sisi e_3) dan lintasan alternatif p_2: C -> B -> A (sisi e_2, e_1)",
                "Biaya sisi c_e^M = 1 / (w_e^M + epsilon_w); kedua lintasan p_1 dan p_2 saling bebas sisi sehingga keduanya berkontribusi pada skor pasangan S_CA(G^M).",
            ],
        ],
        "Catatan: Untuk pasangan simpul C–A, lintasan p1 (garis utuh) dan p2 (garis putus-putus) tidak berbagi sisi fisik yang sama.",
    ),
    "G2": (
        "Gambar 2. Operasi Pelemahan Parsial dan Penghapusan Sisi pada Graf Berbobot ARI",
        ["Kondisi Utuh (lambda = 1)", "Pelemahan Parsial (0 < lambda < 1)", "Kehilangan Penuh (lambda = 0)"],
        [
            [
                "Simpul C terhubung ke A (sisi e3) dan B (sisi e2); A–B terhubung sisi e1",
                "Sisi sasaran e3 tetap ada dengan bobot tereduksi w_{e3,lambda}^M = lambda * w_{e3}^M",
                "Sisi sasaran e3 dihapus dari graf; hanya lintasan alternatif melalui e2–e1 yang tersisa",
            ],
            [
                "Bobot seluruh sisi menggunakan skala normalisasi model utuh",
                "Bobot sisi lain (e1, e2), bobot pasangan, dan penyebut S(G^M) tetap mengacu pada model utuh",
                "Tidak dilakukan normalisasi ulang terhadap median atribut pascagangguan",
            ],
        ],
        "Catatan: Elemen sasaran gangguan adalah e3. Operasi pelemahan mengubah bobot sisi sasaran tanpa menormalisasi ulang atribut elemen lain.",
    ),
    "G3": (
        "Gambar 3. Alur Pembentukan Skor ARI, Indeks Kekritisan (CI), dan Pengaman Kinematik dari Model Utuh",
        ["Komponen Masukan Model Utuh", "Proses Perhitungan Praanalisis", "Keluaran Penyaringan & Status"],
        [
            [
                "1. Atribut elemen (E_e, A_e, I_e, L_e, R_e, q_e) & skala tetap pengembangan s_x",
                "Normalisasi monoton b_x = x / (x + s_x), pembobotan w_e^M, dan optimasi K lintasan bebas sisi",
                "Rasio skor jalur RR_e(lambda) = S(G_{e,lambda}^M) / S(G^M) dalam rentang [0, 1]",
            ],
            [
                "2. Respons elastis model utuh (gaya awal D_e dari K_0 u_0 = f)",
                "Perhitungan rasio utilisasi awal terbatas U_e^* = min(D_e / (R_e + epsilon_R), 1)",
                "Skor ARI_e(lambda) = RR_e(lambda) * (1 - eta * U_e^*) dan CI_e(lambda) = 1 - ARI_e(lambda)",
            ],
            [
                "3. Matriks kekakuan tereduksi model utuh K_0 dan kontribusi elemen K_e",
                "Pemeriksaan leverage spektral h_e dan margin m_e(lambda) = 1 - (1 - lambda) h_e",
                "Pemicu pengaman kinematik g(s) = 1 bila m_e <= tau_m atau perhitungan abstain",
            ],
        ],
        "Catatan: Seluruh proses di atas hanya menggunakan informasi model utuh dan definisi skenario s = (e, lambda) sebelum respons pascagangguan dihitung.",
    ),
    "G4": (
        "Gambar 4. Pemisahan Rantai Informasi Operasional dan Jalur Acuan Evaluasi pada Konfigurasi Beku",
        ["Tahap Proses", "Jalur Operasional Penyaringan (Praanalisis)", "Jalur Acuan Evaluasi (Pascagangguan)"],
        [
            [
                "1. Masukan awal",
                "Model induk utuh + definisi skenario gangguan s = (e, lambda) sesuai partisi beku",
                "Model induk dan daftar skenario yang sama (tanpa mengubah pembagian partisi)",
            ],
            [
                "2. Perhitungan inti",
                "Perhitungan skor ARI/CI, pemeriksaan pengaman kinematik g(s), dan status abstensi",
                "Analisis struktur (solver FEM eksak) pascagangguan untuk seluruh skenario kandidat",
            ],
            [
                "3. Keputusan & target",
                "Terapkan ambang beku tau_CI: simpan himpunan diteruskan F sebelum membuka label acuan",
                "Hitung respons pascagangguan, status rank mekanis, nilai CRC_konv, dan himpunan kritis C",
            ],
            [
                "4. Prediksi & audit akhir",
                "Jalankan inferensi GNN acuan hanya pada skenario s dalam F; rekam waktu setiap komponen",
                "Gabungkan F, prediksi GNN, dan C untuk mengaudit recall saring, recall akhir, galat, dan T_hemat",
            ],
        ],
        "Catatan: Tidak ada aliran informasi dari respons pascagangguan ke pembentukan skor ARI maupun keputusan penerusan F.",
    ),
    "G5": (
        "Gambar 5. Alur Keputusan Penyaringan Skenario Sebelum Inferensi GNN Acuan",
        ["Urutan Langkah", "Kondisi Pemeriksaan Operasional", "Tindakan Kebijakan dan Pencatatan"],
        [
            [
                "Langkah 1",
                "Terima spesifikasi model utuh dan skenario kandidat s dalam S",
                "Hitung skor ARI/CI dan margin pengaman kinematik menggunakan konfigurasi yang dibekukan",
            ],
            [
                "Langkah 2",
                "Apakah skor sah, pencarian lintasan tersertifikasi, dan di dalam domain?",
                "Jika TIDAK: masukkan ke himpunan abstensi (s dalam A) dan wajib teruskan ke evaluasi lanjut",
            ],
            [
                "Langkah 3",
                "Jika YA: apakah CI_s >= tau_CI atau pengaman kinematik g(s) = 1 (atau aturan P1 lambda = 0)?",
                "Jika YA: masukkan ke himpunan diteruskan (s dalam F); jika TIDAK: beri status not_forwarded",
            ],
            [
                "Langkah 4",
                "Eksekusi untuk setiap s dalam F",
                "Bentuk graf skenario (tanpa fitur ARI/CI), jalankan inferensi GNN acuan, dan catat prediksi serta biaya waktu",
            ],
        ],
        "Catatan: Skenario yang tidak diteruskan (not_forwarded) tidak dievaluasi oleh GNN, namun tetap dievaluasi terhadap solver acuan pada tahap audit untuk menghitung kasus kritis terlewat.",
    ),
    "G6": (
        "Gambar 6. Skema Pemisahan Partisi Data Berdasarkan Identitas Model Induk (Protokol Anti-Kebocoran)",
        ["Partisi Pengembangan (Kelompok A: 180 Induk)", "Partisi Validasi Buta (Kelompok B: 60 Induk)", "Partisi Uji Akhir (Kelompok C: 60 Induk)"],
        [
            [
                "Seluruh skenario turunan dari 180 induk tetap berada di Kelompok A (120 formula_dev + 60 calibration)",
                "Seluruh skenario turunan dari 60 induk tetap berada di Kelompok B (12 induk per keluarga S1–S5)",
                "Seluruh skenario turunan dari 60 induk tetap berada di Kelompok C (12 induk per keluarga S1–S5)",
            ],
            [
                "Digunakan untuk pemilihan formula, skala median s_x, pelatihan GNN, dan kalibrasi ambang tau",
                "Mengevaluasi protokol yang telah dibekukan tanpa memilih ulang formula atau menyetel ambang",
                "Dibuka satu kali setelah protokol beku untuk pelaporan kinerja inferensial akhir",
            ],
        ],
        "Catatan: Pembagian dilakukan pada tingkat model induk sebelum kalibrasi (bukan pengacakan pada tingkat skenario) untuk mencegah kebocoran topologi antarpartisi.",
    ),
    "G7": (
        "Gambar 7. Skema Idealisasi Lima Keluarga Struktur (S1–S5) pada Dataset Validasi Utama",
        ["Kode Keluarga", "Idealisasi Geometri dan Tumpuan", "Karakteristik Aksi Mekanis dan Elemen Sasaran"],
        [
            ["S1: Balok", "Balok satu bentang dan balok menerus 2–4 bentang dengan tumpuan sendi–rol", "Aksi lentur dan geser Euler-Bernoulli (translasi vertikal dan rotasi simpul)"],
            ["S2: Rangka batang bidang", "Rangka batang 2D multi-panel dengan sambungan sendi dan beban nodal", "Aksi tarik–tekan aksial murni; rentan terhadap kehilangan kestabilan kinematik lokal"],
            ["S3: Portal bidang", "Portal bertingkat dan berbentang dengan sambungan balok–kolom kaku", "Interaksi gaya aksial, geser, dan momen lentur pada kolom serta balok portal"],
            ["S4: Portal berpengaku", "Portal bidang dengan penambahan elemen pengaku diagonal (konfigurasi X, V, atau K)", "Kombinasi kekakuan lentur portal dan jalur beban lateral aksial pada bresing"],
            ["S5: Rangka ruang 3D", "Rangka batang ruang tiga dimensi dengan simpul dasar terkekang translasi (x, y, z)", "Redundansi jalur beban ruang 3D dengan tiga derajat kebebasan translasi per simpul"],
        ],
        "Catatan: Setiap keluarga diwakili oleh 60 model induk (total 300 model induk dan 7.940 skenario) yang diverifikasi pada Gate 12–15.",
    ),
    "G8": (
        "Gambar 8. Spesifikasi Geometri dan Kondisi Batas Empat Model Kanonik Verifikasi",
        ["Model Kanonik", "Konfigurasi Simpul, Batang, dan Tumpuan", "Berkas Visualisasi Acuan"],
        [
            ["1. Dua batang paralel (1D)", "2 batang paralel menghubungkan simpul tumpuan ke satu simpul beban aksial (1 DOF bebas)", "results/verification/models.pdf (Panel a)"],
            ["2. Rangka segitiga (2D)", "3 batang, 3 simpul, tumpuan sendi–rol pada alas dan beban pada puncak (3 DOF bebas)", "results/verification/models.pdf (Panel b)"],
            ["3. Persegi satu diagonal (2D)", "4 simpul sudut persegi, 4 batang tepi + 1 batang diagonal (5 batang, 5 DOF bebas)", "results/verification/models.pdf (Panel c)"],
            ["4. Persegi dua diagonal (2D)", "4 simpul sudut persegi, 4 batang tepi + 2 batang diagonal bersilang (6 batang, 5 DOF bebas)", "results/verification/models.pdf (Panel d)"],
        ],
        "Catatan: Diagram visual lengkap tersimpan dalam artefak terverifikasi results/verification/models.pdf.",
    ),
    "G9": (
        "Gambar 9. Penjelasan Geometris Kasus Mekanisme yang Terlewat oleh CI Murni pada Persegi Satu Diagonal",
        ["(a) Kondisi Model Utuh (Rank = 5/5)", "(b) Setelah Batang e3 Dihapus (Rank = 4/5, RR = 1, CI = 0)"],
        [
            [
                "Simpul atas D dan C terhubung oleh batang horizontal atas e3; beban horizontal 30 kN bekerja di C",
                "Batang e3 dihapus; simpul D masih terhubung ke sistem melalui batang vertikal kiri AD (e2)",
            ],
            [
                "Graf terhubung dan matriks kekakuan tereduksi definit positif (solusi elastis unik)",
                "Graf tetap terhubung dan jalur beban utama dari C ke tumpuan tidak melewati e3 sehingga RR = 1 dan CI = 0, namun simpul D bebas berayun secara horizontal (modus mekanisme orde pertama)",
            ],
        ],
        "Catatan: Contoh penyangkal ini membuktikan bahwa keterhubungan graf dan CI mendekati nol tidak menjamin kestabilan kinematik tanpa pengaman spektral.",
    ),
    "G10": (
        "Gambar 10. Karakteristik Kurva Indeks Kekritisan (CI) terhadap Faktor Kekakuan Tersisa pada Empat Model Kanonik",
        ["Model Kanonik", "Perilaku Kurva CI terhadap Pelemahan (lambda: 1 -> 0)", "Penanda Rank Kekakuan dan Berkas Acuan"],
        [
            [
                "Paralel & Dua diagonal",
                "CI meningkat secara monoton ketika lambda menurun dari 1,00 ke 0,00 pada seluruh batang aktif",
                "Seluruh skenario mempertahankan rank penuh (solusi unik) — results/verification/ci_by_damage.pdf",
            ],
            [
                "Segitiga & Satu diagonal",
                "CI meningkat monoton pada batang penumpu beban, namun tetap bernilai 0,000000 pada batang bergaya awal nol (e3, e4)",
                "Tanda silang pada lambda = 0 menandai 8 skenario kehilangan rank (3 pada segitiga, 5 pada satu diagonal)",
            ],
        ],
        "Catatan: Kurva lengkap untuk keempat model kanonik diarsipkan pada berkas results/verification/ci_by_damage.pdf.",
    ),
}


# ==============================================================================
# 4. EKSTRAKSI DATA KATALOG LITERATUR (80 SUMBER & 43 ARTIKEL Q1 RIS) KE LAMPIRAN
# ==============================================================================
def extract_catalog_and_q1_rows(doc):
    """
    Sebelum blok P0528..P0783 dan P0866..P1051 dihapus dari Bab II, ekstrak
    seluruh 80 entri sumber (S01..S80) dan 43 artikel jurnal Q1 RIS untuk
    ditempatkan sebagai Tabel Lampiran 1 dan Tabel Lampiran 2 sesuai Bab V.B.9.a.5
    Panduan Disertasi UNY 2023.
    """
    p_idx = 0
    items = []
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            p = Paragraph(child, doc)
            if 250 <= p_idx <= 508:
                items.append(("P", p_idx, p.text))
            p_idx += 1
        elif isinstance(child, CT_Tbl):
            t = Table(child, doc)
            if 250 <= p_idx <= 508:
                for r in t.rows:
                    row_txt = " ".join(c.text.strip().replace("\n", " ") for c in r.cells)
                    items.append(("TR", p_idx, row_txt))

    cat_map = {
        "Tabel 2.4": "Mekanika dan Redundansi",
        "Tabel 2.5": "Graf dan Algoritma",
        "Tabel 2.6": "GNN dan Representasi Fisik",
        "Tabel 2.7": "Reliabilitas dan Sensitivitas",
        "Tabel 2.8": "Validasi dan Ketidakpastian",
        "Tabel 2.9": "Energi dan Biaya Komputasi",
        "Tabel 2.10": "Pemantauan Kerusakan",
    }
    current_cat = "Mekanika dan Redundansi"
    entries = {}
    current_s = None

    for kind, idx, txt in items:
        for line in txt.split("\n"):
            l = line.strip()
            if not l:
                continue
            for k, v in cat_map.items():
                if l.startswith(k):
                    current_cat = v
            if (
                any(
                    l.startswith(x)
                    for x in [
                        "Tabel 2.",
                        "Kode Identitas",
                        "Bersambung ke",
                        "Identitas dan tautan",
                        "Anotasi dan status",
                    ]
                )
                or l in list(cat_map.values())
                or l.lower() in [v.lower() for v in cat_map.values()]
            ):
                continue
            m = re.search(r"\b(S(?:0[1-9]|[1-7]\d|80))\b", l)
            if m:
                current_s = m.group(1)
                if current_s not in entries:
                    entries[current_s] = {"cat": current_cat, "lines": []}
                entries[current_s]["lines"].append(l)
            elif current_s:
                entries[current_s]["lines"].append(l)

    catalog_rows = []
    for i in range(1, 81):
        sk = f"S{i:02d}"
        info = entries.get(sk, {"cat": "Literatur Pendukung", "lines": [sk]})
        blob = " ".join(info["lines"])
        blob = re.sub(r"\b" + sk + r"\b", "", blob)
        blob = re.sub(r"\s+", " ", blob).strip()
        catalog_rows.append([sk, info["cat"], clean_text_artifacts(blob)])

    # Ekstrak 43 baris Q1 RIS dari P0590..P0775
    pages = []
    cur_page = {"src": [], "theme": [], "mode": "src"}
    for i in range(590, 776):
        t = doc.paragraphs[i].text.strip()
        if not t:
            continue
        if t.startswith("Tabel 2.12"):
            if cur_page["src"] or cur_page["theme"]:
                pages.append(cur_page)
            cur_page = {"src": [], "theme": [], "mode": "src"}
            continue
        if t == "Sumber menurut RIS":
            cur_page["mode"] = "src"
            continue
        if t == "Tema dan batas pembandingan":
            cur_page["mode"] = "theme"
            continue
        if any(
            t.startswith(w)
            for w in [
                "Mekanisme pascakerusakan;",
                "Deteksi dan lokalisasi",
                "GNN struktur kapal;",
                "Prediksi kerusakan akibat",
                "Prediksi kapasitas subrakitan;",
                "Efek retrofit;",
                "Ketahanan jembatan girder;",
                "Perubahan jalur beban",
                "Jejak karbon model bahasa;",
            ]
        ):
            cur_page["mode"] = "theme"
        cur_page[cur_page["mode"]].append(t)
    if cur_page["src"] or cur_page["theme"]:
        pages.append(cur_page)

    q1_rows = []
    idx_counter = 1
    for pg in pages:
        src_blob = " ".join(pg["src"]).replace("\n", " ")
        srcs = [s.strip() for s in re.findall(r".*?DOI:\s*10\.\S+", src_blob)]
        th_blob = " ".join(pg["theme"]).replace("\n", " ")
        themes = [s.strip() for s in re.findall(r"[^.]+?\.", th_blob)]
        for s, th in zip(srcs, themes):
            q1_rows.append([str(idx_counter), clean_text_artifacts(s), clean_text_artifacts(th)])
            idx_counter += 1

    return catalog_rows, q1_rows


# ==============================================================================
# 5. PEMBANGUN BAGIAN AWAL DISERTASI (BAB IV.A PANDUAN DISERTASI UNY 2023)
# ==============================================================================
def build_front_matter_elements(doc, logo_p_el=None):
    """
    Bangun bagian awal disertasi sesuai Bab IV.A Panduan Disertasi UNY 2023:
    1. Halaman Sampul Dalam
    2. ABSTRAK (Bahasa Indonesia, 1 spasi, 3 paragraf: Tujuan, Metode, Hasil/Simpulan/Saran + Kata Kunci)
    3. ABSTRACT (Bahasa Inggris, 1 spasi, 3 paragraf + Keywords)
    4. SURAT PERNYATAAN KEASLIAN KARYA
    5. LEMBAR PERSETUJUAN
    6. LEMBAR PENGESAHAN
    7. KATA PENGANTAR (1,5 spasi)
    8. DAFTAR ISI (1 spasi)
    9. DAFTAR TABEL (1 spasi)
    10. DAFTAR GAMBAR (1 spasi)
    11. DAFTAR LAMPIRAN (1 spasi)
    12. DAFTAR SINGKATAN DAN LAMBANG
    """
    elems = []

    # --- 1. HALAMAN SAMPUL DALAM ---
    elems.append(
        make_p_element(
            "PENGEMBANGAN DAN VALIDASI ADJUSTED REDUNDANCY INDEX UNTUK PENAPISAN PRA-ANALISIS SKENARIO GANGGUAN ELEMEN PADA EVALUASI STRUKTUR BERBASIS GRAPH NEURAL NETWORK",
            bold=True,
            size_pt=14.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=12.0,
            space_after_pt=18.0,
        )
    )
    elems.append(
        make_p_element(
            "DISERTASI",
            bold=True,
            size_pt=14.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=6.0,
            space_after_pt=18.0,
        )
    )
    elems.append(
        make_p_element(
            "Diajukan kepada Sekolah Pascasarjana Universitas Negeri Yogyakarta\nuntuk Memenuhi Sebagian Persyaratan guna Memperoleh Gelar\nDoktor Ilmu Teknik",
            bold=False,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=6.0,
            space_after_pt=24.0,
        )
    )
    if logo_p_el is not None:
        pPr = logo_p_el.get_or_add_pPr()
        jc = pPr.find(qn("w:jc"))
        if jc is None:
            jc = OxmlElement("w:jc")
            pPr.append(jc)
        jc.set(qn("w:val"), "center")
        elems.append(logo_p_el)
    elems.append(
        make_p_element(
            "Oleh\nHarids Irawan, S.T., M.T.\nNIM 23051690001",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=24.0,
            space_after_pt=36.0,
        )
    )
    elems.append(
        make_p_element(
            "PROGRAM DOKTOR ILMU TEKNIK\nKONSENTRASI TEKNIK SIPIL\nSEKOLAH PASCASARJANA\nUNIVERSITAS NEGERI YOGYAKARTA\n2026",
            bold=True,
            size_pt=14.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=18.0,
            space_after_pt=0.0,
        )
    )

    # --- 2. ABSTRAK (BAHASA INDONESIA — BAB IV.A.3 & V.B.2.a UNY 2023: 1 SPASI, MAKS 600 KATA) ---
    elems.append(
        make_p_element(
            "ABSTRAK",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_before_pt=0.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Harids Irawan: Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network. Disertasi. Yogyakarta: Sekolah Pascasarjana, Universitas Negeri Yogyakarta, 2026.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=0.0,
            space_after_pt=10.0,
        )
    )
    elems.append(
        make_p_element(
            "Penelitian ini bertujuan untuk: (1) merumuskan definisi operasional dan sifat matematis Adjusted Redundancy Index (ARI) beserta indeks kekritisan penyaringan (CI) dari informasi model struktur utuh; (2) memverifikasi ketepatan algoritma optimasi lintasan bebas sisi dan mengidentifikasi batas kecukupan representasi graf skalar terhadap kestabilan mekanis; (3) mengembangkan pengaman kinematik spektral berbasis model utuh guna mendeteksi penurunan rank matriks kekakuan tanpa membaca respons pascagangguan; (4) mengevaluasi kelayakan penyaringan praanalisis lintas lima keluarga struktur; serta (5) mengaudit manfaat integrasi berpasangan antara penyaring ARI dan prediktor Graph Neural Network (GNN) acuan baik dari segi ketercakupan akhir maupun penghematan waktu komputasi bersih.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "Metode penelitian memadukan perumusan matematis, verifikasi deterministik, dan eksperimen komputasi terkendali dengan protokol pembekuan pra-validasi buta (ARI-FROZEN-PROTOCOL-v1.0). Verifikasi awal dilakukan pada empat model kanonik (64 skenario gangguan dan 16 kontrol) serta 16 model parametrik pengembangan (272 skenario gangguan). Validasi utama dilaksanakan pada 300 model induk lintas lima keluarga struktur—balok lentur Euler-Bernoulli (S1), rangka batang bidang (S2), portal bidang (S3), portal berpengaku (S4), dan rangka ruang 3D (S5)—yang mencakup 1.910 elemen dan 7.940 skenario (7.640 gangguan dan 300 kontrol) dengan pembagian ketat berdasarkan model induk (120 pengembangan formula, 60 kalibrasi, 60 validasi buta, dan 60 uji akhir). Evaluasi integrasi berpasangan (S6) menguji tujuh perlakuan penyaringan pada prediktor StructGNN-CRC v1.0 dengan bobot terbekukan dan pengukuran waktu dinding 10 pengulangan.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "Hasil penelitian membuktikan bahwa: (1) algoritma ARI memenuhi seluruh sifat rentang [0, 1], monotonisitas pelemahan, invariansi satuan/pelabelan, dan 100% sertifikasi pencarian pada 7.940 skenario (Gerbang A lulus); (2) verifikasi kanonik mengungkap contoh penyangkal mekanis (batang bergaya awal nol dengan CI mendekati nol tetapi mengalami penurunan rank), yang kemudian diatasi secara tuntas oleh pengaman kinematik spektral dengan penangkapan 100% (920/920) kasus mekanisme dan korelasi peringkat Spearman median 0,7023 pada 300 model (Gerbang B dan C lulus); (3) pada ambang beku tau = 0,50, kebijakan gabungan dasar (P0) mereduksi 83,8% evaluasi dan lulus penuh pada keluarga rangka batang S2 (recall = 99,0%, batas bawah bootstrap L0,95 = 96,9%), sedangkan kebijakan kehati-hatian P1 (meneruskan penghapusan penuh lambda = 0) meningkatkan rerata recall lintas lima keluarga menjadi 90,0% (L0,95 = 88,4%) dengan reduksi 72,6%; dan (4) integrasi dengan StructGNN-CRC v1.0 mempertahankan recall akhir 99,0% pada S2 serta memangkas waktu inferensi GNN sebesar 83,7% (P0) dan 72,6% (P1), namun menghasilkan penghematan waktu total bersih negatif (T_hemat = -15,76 detik pada 300 model) karena waktu pencarian lintasan kombinatorial ARI melampaui waktu inferensi GNN ringan. Disarankan percepatan pembaruan matriks rank-satu dan pemangkasan pencarian lintasan sebelum penyaring diterapkan pada GNN berbiaya rendah.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=10.0,
        )
    )
    elems.append(
        make_p_element(
            "Kata kunci: Adjusted Redundancy Index, Graph Neural Network, jalur beban alternatif, pengaman kinematik spektral, penyaringan praanalisis, redundansi struktur.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=0.0,
            space_after_pt=0.0,
        )
    )

    # --- 3. ABSTRACT (BAHASA INGGRIS — 1 SPASI) ---
    elems.append(
        make_p_element(
            "ABSTRACT",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_before_pt=0.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Harids Irawan: Development and Validation of the Adjusted Redundancy Index for Pre-Analysis Screening of Element Perturbation Scenarios in Graph Neural Network-Based Structural Evaluation. Dissertation. Yogyakarta: Graduate School, Universitas Negeri Yogyakarta, 2026.",
            bold=False,
            italic=True,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=0.0,
            space_after_pt=10.0,
        )
    )
    elems.append(
        make_p_element(
            "This study aims to: (1) formulate an auditable operational definition and mathematical properties of the Adjusted Redundancy Index (ARI) and its screening Criticality Index (CI) using only intact-structure information; (2) verify the exact edge-disjoint path optimization algorithm and identify representation boundaries of scalar graph scores with respect to mechanical stability; (3) develop an intact-model spectral kinematic guard to detect stiffness rank deficiency without accessing post-perturbation responses; (4) evaluate pre-analysis screening feasibility across five structural families; and (5) audit the paired integration benefits of ARI screening prior to a reference Graph Neural Network (GNN) predictor in terms of end-to-end recall and net wall-clock time savings.",
            bold=False,
            italic=True,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "The research methodology combines analytical formulation, deterministic verification, and controlled computational experiments governed by a pre-blind-validation frozen protocol (ARI-FROZEN-PROTOCOL-v1.0). Initial verification was conducted on four canonical models (64 perturbation scenarios and 16 controls) and 16 parametric development models (272 perturbation scenarios). Main validation was performed across 300 parent models spanning five structural families—Euler-Bernoulli beams (S1), 2D planar trusses (S2), 2D plane frames (S3), 2D braced frames (S4), and 3D space trusses (S5)—totaling 1,910 elements and 7,940 scenarios (7,640 perturbations and 300 controls) partitioned strictly by parent model ID (120 formula development, 60 calibration, 60 blind validation, and 60 final test). Paired GNN integration experiments (S6) evaluated seven screening treatments using the frozen StructGNN-CRC v1.0 surrogate over 10 paired timing repetitions.",
            bold=False,
            italic=True,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "The results demonstrate that: (1) the ARI implementation satisfies [0, 1] boundedness, degradation monotonicity, unit/labeling invariance, and 100% search certification across all 7,940 scenarios (Gate A passed); (2) canonical verification uncovered mechanical counterexamples (zero-initial-force members yielding near-zero CI despite rank deficiency), which are completely resolved by the spectral kinematic guard capturing 100% (920/920) of mechanism cases and achieving a median Spearman rank correlation of 0.7023 across 300 models (Gates B and C passed); (3) at the frozen threshold tau = 0.50, the baseline combined policy (P0) reduces evaluations by 83.8% and fully passes on planar trusses S2 (recall = 99.0%, one-sided 95% cluster bootstrap lower bound L0.95 = 96.9%), whereas the precautionary policy P1 (forwarding full removals lambda = 0) raises mean model recall across all five families to 90.0% (L0.95 = 88.4%) with a 72.6% reduction; and (4) integration with StructGNN-CRC v1.0 preserves 99.0% end-to-end recall on S2 and reduces GNN inference time by 83.7% (P0) and 72.6% (P1), but yields negative net total time savings (T_hemat = -15.76 s across 300 models) because combinatorial path-search overhead exceeds lightweight GNN inference time. Rank-one matrix updates and path-search pruning are recommended before pairing with fast GNN surrogates.",
            bold=False,
            italic=True,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=1.0,
            space_after_pt=10.0,
        )
    )
    elems.append(
        make_p_element(
            "Keywords: Adjusted Redundancy Index, alternate load paths, Graph Neural Network, pre-analysis screening, spectral kinematic guard, structural redundancy.",
            bold=False,
            italic=True,
            size_pt=12.0,
            align="both",
            line_spacing=1.0,
            first_line_cm=0.0,
            space_after_pt=0.0,
        )
    )

    # --- 4. SURAT PERNYATAAN KEASLIAN KARYA ---
    elems.append(
        make_p_element(
            "SURAT PERNYATAAN KEASLIAN KARYA",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Saya yang bertanda tangan di bawah ini:\nNama\t\t\t: Harids Irawan, S.T., M.T.\nNIM\t\t\t: 23051690001\nProgram Studi\t: Doktor Ilmu Teknik (Konsentrasi Teknik Sipil)",
            bold=False,
            size_pt=12.0,
            align="left",
            line_spacing=1.5,
            space_after_pt=12.0,
        )
    )
    elems.append(
        make_p_element(
            "menyatakan bahwa disertasi yang berjudul “Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network” merupakan karya asli saya sendiri. Sepanjang pengetahuan saya, di dalam disertasi ini tidak terdapat karya atau pendapat yang pernah ditulis atau diterbitkan oleh orang lain, kecuali yang secara tertulis diacu dalam naskah ini dan disebutkan dalam Daftar Pustaka.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "Apabila di kemudian hari terbukti bahwa pernyataan ini tidak benar, saya bersedia menerima sanksi akademik sesuai dengan peraturan yang berlaku di Universitas Negeri Yogyakarta.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=24.0,
        )
    )
    elems.append(
        make_p_element(
            "Yogyakarta, Oktober 2026\nYang menyatakan,\n\n\n\nHarids Irawan, S.T., M.T.\nNIM 23051690001",
            bold=False,
            size_pt=12.0,
            align="right",
            line_spacing=1.5,
            space_after_pt=0.0,
        )
    )

    # --- 5. LEMBAR PERSETUJUAN ---
    elems.append(
        make_p_element(
            "LEMBAR PERSETUJUAN",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Disertasi berjudul “Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network” yang disusun oleh Harids Irawan, S.T., M.T. (NIM 23051690001) telah diperiksa dan disetujui oleh Tim Promotor untuk diajukan dalam Ujian Disertasi pada Program Doktor Ilmu Teknik Sekolah Pascasarjana Universitas Negeri Yogyakarta.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=24.0,
        )
    )
    elems.append(
        make_p_element(
            "Yogyakarta, Oktober 2026\n\nPromotor,\t\t\t\t\tKo-Promotor,\n\n\n\n(..................................................)\t\t(..................................................)\nNIP ..............................................\t\tNIP ..............................................",
            bold=False,
            size_pt=12.0,
            align="left",
            line_spacing=1.5,
            space_after_pt=0.0,
        )
    )

    # --- 6. LEMBAR PENGESAHAN ---
    elems.append(
        make_p_element(
            "LEMBAR PENGESAHAN",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Disertasi berjudul “Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network” yang disusun oleh Harids Irawan, S.T., M.T. (NIM 23051690001) telah dipertahankan di depan Dewan Penguji Disertasi Sekolah Pascasarjana Universitas Negeri Yogyakarta dan dinyatakan lulus.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=12.0,
        )
    )
    elems.append(
        make_apa_table_element(
            doc,
            headers=["Nama Lengkap dan Gelar", "Jabatan dalam Dewan Penguji", "Tanda Tangan", "Tanggal"],
            rows_data=[
                ["..................................................", "Ketua Penguji", "........................", "................"],
                ["..................................................", "Sekretaris Penguji", "........................", "................"],
                ["..................................................", "Promotor / Penguji", "........................", "................"],
                ["..................................................", "Ko-Promotor / Penguji", "........................", "................"],
                ["..................................................", "Penguji Utama (Eksternal)", "........................", "................"],
                ["..................................................", "Penguji Internal", "........................", "................"],
            ],
            font_size_pt=11.0,
        )
    )
    elems.append(
        make_p_element(
            "\nYogyakarta, Oktober 2026\nDirektur Sekolah Pascasarjana\nUniversitas Negeri Yogyakarta,\n\n\n\n(..................................................)\nNIP ..............................................",
            bold=False,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_before_pt=18.0,
            space_after_pt=0.0,
        )
    )

    # --- 7. KATA PENGANTAR (1,5 SPASI SESUAI BAB V.B.2.c PANDUAN UNY 2023) ---
    elems.append(
        make_p_element(
            "KATA PENGANTAR",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.5,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Puji dan syukur penulis panjatkan ke hadirat Tuhan Yang Maha Esa atas rahmat dan karunia-Nya sehingga disertasi yang berjudul “Pengembangan dan Validasi Adjusted Redundancy Index untuk Penapisan Pra-Analisis Skenario Gangguan Elemen pada Evaluasi Struktur Berbasis Graph Neural Network” ini dapat diselesaikan dengan baik. Disertasi ini disusun untuk memenuhi sebagian persyaratan guna memperoleh gelar Doktor Ilmu Teknik Konsentrasi Teknik Sipil pada Sekolah Pascasarjana Universitas Negeri Yogyakarta.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "Penyusunan naskah disertasi ini telah disesuaikan dengan Buku Panduan Penulisan Disertasi Universitas Negeri Yogyakarta Edisi Tahun 2023 serta dilengkapi dengan paket verifikasi numerik, dataset 300 model induk lintas lima keluarga struktur, protokol konfigurasi terbekukan, dan evaluasi integrasi berpasangan yang dapat diaudit secara terbuka. Penulis menyampaikan penghargaan dan terima kasih yang sebesar-besarnya kepada Tim Promotor, Dewan Penguji, Pimpinan Sekolah Pascasarjana dan Fakultas Teknik Universitas Negeri Yogyakarta, serta rekan-rekan peneliti dan keluarga yang telah memberikan bimbingan, masukan ilmiah, serta dukungan moral selama proses penelitian ini berlangsung.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=6.0,
        )
    )
    elems.append(
        make_p_element(
            "Penulis menyadari bahwa penelitian ini masih memiliki batasan domain yang dinyatakan secara eksplisit di dalam naskah. Oleh karena itu, kritik dan saran yang membangun sangat diharapkan bagi penyempurnaan dan pengembangan penelitian lanjutan di bidang rekayasa struktur dan komputasi cerdas.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=18.0,
        )
    )
    elems.append(
        make_p_element(
            "Yogyakarta, Oktober 2026\n\nPenulis,\nHarids Irawan, S.T., M.T.",
            bold=False,
            size_pt=12.0,
            align="right",
            line_spacing=1.5,
            space_after_pt=0.0,
        )
    )

    # --- 8. DAFTAR ISI (1 SPASI SESUAI BAB V.B.2.b PANDUAN UNY 2023) ---
    elems.append(
        make_p_element(
            "DAFTAR ISI",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    front_toc = [
        ("HALAMAN SAMPUL DALAM", "i", 0, True),
        ("ABSTRAK", "ii", 0, True),
        ("ABSTRACT", "iii", 0, True),
        ("SURAT PERNYATAAN KEASLIAN KARYA", "iv", 0, True),
        ("LEMBAR PERSETUJUAN", "v", 0, True),
        ("LEMBAR PENGESAHAN", "vi", 0, True),
        ("KATA PENGANTAR", "vii", 0, True),
        ("DAFTAR ISI", "viii", 0, True),
        ("DAFTAR TABEL", "xi", 0, True),
        ("DAFTAR GAMBAR", "xiii", 0, True),
        ("DAFTAR LAMPIRAN", "xiv", 0, True),
        ("DAFTAR SINGKATAN DAN LAMBANG", "xv", 0, True),
    ]
    for title_t, pg_t, lvl_t, b_t in front_toc:
        elems.append(make_toc_entry_element(title_t, pg_t, level=lvl_t, bold=b_t))

    ch_map = [
        ("1.", "BAB I PENDAHULUAN", "1"),
        ("2.", "BAB II KAJIAN PUSTAKA", "14"),
        ("3.", "BAB III METODE PENELITIAN", "42"),
        ("4.", "BAB IV HASIL PENELITIAN DAN PEMBAHASAN", "72"),
        ("5.", "BAB V SIMPULAN DAN SARAN", "124"),
    ]
    for ch_prefix, ch_title, ch_pg in ch_map:
        elems.append(make_toc_entry_element(ch_title, ch_pg, level=0, bold=True))
        for sec_key, (new_num, new_title, lvl) in SECTION_HEADING_MAP.items():
            if sec_key.startswith(ch_prefix):
                elems.append(
                    make_toc_entry_element(
                        f"{new_num} {new_title}",
                        "—",
                        level=lvl,
                        bold=False,
                    )
                )
    elems.append(make_toc_entry_element("DAFTAR PUSTAKA", "130", level=0, bold=True))
    elems.append(make_toc_entry_element("LAMPIRAN", "135", level=0, bold=True))

    # --- 9. DAFTAR TABEL ---
    elems.append(
        make_p_element(
            "DAFTAR TABEL",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    for t_idx in range(1, 32):
        cap_str = TABLES_SPEC[f"T{t_idx}"][0]
        elems.append(make_toc_entry_element(cap_str, "—", level=0, bold=False))

    # --- 10. DAFTAR GAMBAR ---
    elems.append(
        make_p_element(
            "DAFTAR GAMBAR",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    for g_idx in range(1, 11):
        cap_str = FIGURES_SPEC[f"G{g_idx}"][0]
        elems.append(make_toc_entry_element(cap_str, "—", level=0, bold=False))

    # --- 11. DAFTAR LAMPIRAN ---
    elems.append(
        make_p_element(
            "DAFTAR LAMPIRAN",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    lampiran_list = [
        "Lampiran 1. Katalog Beranotasi 80 Sumber Literatur dan Matriks Artikel Jurnal Q1 (Tabel Lampiran 1 dan Tabel Lampiran 2)",
        "Lampiran 2. Rekonsiliasi Keputusan Penyaringan ARI-Forward dan Diagnosa 28 Kasus Kritis Terlewat (Gate 11)",
        "Lampiran 3. Realisasi Solver Rekayasa Struktur Multi-Keluarga S1–S5 dan Uji Penerimaan Analitis (Gate 12)",
        "Lampiran 4. Pembangkitan Dataset 300 Model Induk dan Manifest Lintas Lima Keluarga Struktur S1–S5 (Gate 13)",
        "Lampiran 5. Pembekuan Protokol dan Konfigurasi Pra-Validasi Buta ARI-FROZEN-PROTOCOL-v1.0 (Gate 14)",
        "Lampiran 6. Evaluasi Penyaringan Operasional Skala Penuh, Bootstrap B = 10.000, dan Studi Ablasi pada 300 Model Induk (Gate 15)",
        "Lampiran 7. Eksperimen Integrasi Berpasangan ARI–GNN (StructGNN-CRC v1.0) dan Audit Biaya Operasional (Gate 17)",
    ]
    for l_str in lampiran_list:
        elems.append(make_toc_entry_element(l_str, "—", level=0, bold=False))

    # --- 12. DAFTAR SINGKATAN DAN LAMBANG (1 TABEL UTUH APA) ---
    elems.append(
        make_p_element(
            "DAFTAR SINGKATAN DAN LAMBANG",
            bold=True,
            size_pt=12.0,
            align="center",
            line_spacing=1.0,
            space_after_pt=12.0,
            page_break_before=True,
        )
    )
    symbols_rows = [
        ["ARI", "Adjusted Redundancy Index (indeks redundansi teradaptasi praanalisis)"],
        ["CI", "Criticality Index (indeks kekritisan penyaringan, CI = 1 - ARI)"],
        ["GNN", "Graph Neural Network (jaringan saraf tiruan berbasis graf)"],
        ["CRC", "Indeks kekritisan acuan konvensional dari analisis struktur pascagangguan"],
        ["G^M", "Graf berbobot mekanis yang dibentuk dari model struktur utuh"],
        ["e, s = (e, lambda)", "Identitas elemen dan skenario gangguan elemen dengan faktor kekakuan tersisa lambda"],
        ["S", "Himpunan kandidat skenario gangguan (tidak mencakup kontrol utuh lambda = 1)"],
        ["L_e, E_e, A_e, I_e", "Panjang elemen, modulus elastisitas, luas penampang, dan momen inersia penampang"],
        ["k_e, k_sys", "Atribut kekakuan elemen dan kekakuan global ekuivalen sistem struktur"],
        ["R_e, D_e, q_e", "Kapasitas elemen, tuntutan gaya pada model utuh, dan faktor kondisi awal"],
        ["K, gamma, omega_r", "Batas jumlah lintasan bebas sisi, faktor peluruhan, dan bobot urutan lintasan"],
        ["S(G^M), RR_s", "Skor dukungan jalur graf utuh dan rasio redundansi jalur pascagangguan"],
        ["U_e^*, eta", "Rasio utilisasi awal terbatas pada [0, 1] dan koefisien penyesuaian utilisasi"],
        ["h_e, m_e(lambda)", "Leverage kekakuan spektral elemen pada model utuh dan margin kestabilan kinematik"],
        ["F, A, C", "Himpunan skenario diteruskan, himpunan abstensi wajib, dan himpunan kasus kritis acuan"],
        ["epsilon_w, epsilon_d", "Parameter regularisasi bobot sisi dan biaya lintasan tak berdimensi"],
        ["epsilon_R, epsilon_u, epsilon_k", "Parameter regularisasi berdimensi kapasitas, perpindahan, dan kekakuan"],
        ["E_v, Delta E, r_E", "Energi listrik komputasi (kWh), selisih energi, dan fraksi penghematan energi"],
        ["W", "Energi regangan mekanis struktur (kN mm)"],
    ]
    elems.append(
        make_apa_table_element(
            doc,
            headers=["Singkatan / Lambang", "Makna dan Satuan / Definisi Operasional"],
            rows_data=symbols_rows,
            font_size_pt=10.5,
        )
    )

    return elems


# ==============================================================================
# 6. PEMBANGUN LAMPIRAN KERJA GATE 11 S.D. 17 & KATALOG LITERATUR LENGKAP
# ==============================================================================
def build_appendices_elements(doc, catalog_rows, q1_rows, gate11_17_blocks):
    """
    Bangun bagian LAMPIRAN secara utuh sesuai Panduan Disertasi UNY 2023:
    - Lampiran 1: Katalog Beranotasi 80 Sumber (Tabel Lampiran 1) & Matriks Q1 RIS (Tabel Lampiran 2)
    - Lampiran 2 s.d. 7: Hasil Kerja Aktual Gate 11 s.d. Gate 17 (Tabel Lampiran 3 s.d. 13)
    """
    elems = []

    # Halaman Pembatas LAMPIRAN
    elems.append(
        make_p_element(
            "LAMPIRAN",
            bold=True,
            size_pt=14.0,
            align="center",
            line_spacing=2.0,
            space_before_pt=120.0,
            space_after_pt=0.0,
            page_break_before=True,
        )
    )

    # --- LAMPIRAN 1: KATALOG LITERATUR (80 SUMBER & 43 ARTIKEL Q1) ---
    elems.append(
        make_p_element(
            "Lampiran 1. Katalog Beranotasi Sumber Literatur dan Matriks Artikel Jurnal Q1",
            bold=True,
            size_pt=12.0,
            align="left",
            line_spacing=1.5,
            space_before_pt=18.0,
            space_after_pt=6.0,
            page_break_before=True,
        )
    )
    elems.append(
        make_p_element(
            "Sesuai ketentuan Bab V.B.9.a.5 Buku Panduan Penulisan Disertasi UNY 2023 (“Setiap tabel disajikan tidak lebih dari satu halaman. Tabel yang melebihi satu halaman diletakkan di dalam lampiran”), katalog komprehensif 80 sumber literatur yang ditemukan beserta matriks rincian 43 artikel jurnal bereputasi tinggi (Q1) dari penelusuran RIS disajikan pada lampiran ini agar tidak memotong kesinambungan narasi batang tubuh Bab II.",
            bold=False,
            size_pt=12.0,
            align="both",
            line_spacing=1.5,
            first_line_cm=1.0,
            space_after_pt=8.0,
        )
    )

    # Tabel Lampiran 1
    p_cap_l1 = make_p_element(
        "Tabel Lampiran 1. Katalog Beranotasi 80 Sumber Literatur Hasil Penelusuran Terarah",
        bold=True,
        size_pt=12.0,
        align="left",
        line_spacing=1.0,
        space_before_pt=10.0,
        space_after_pt=4.0,
        keep_with_next=True,
    )
    tbl_l1 = make_apa_table_element(
        doc,
        headers=["Kode", "Kategori Tema", "Identitas Sumber, Tautan/DOI, Peran, dan Batas Penggunaan"],
        rows_data=catalog_rows,
        font_size_pt=9.5,
        col_widths_cm=[1.5, 3.2, 9.3],
    )
    elems.append(p_cap_l1)
    elems.append(tbl_l1)

    # Tabel Lampiran 2
    p_cap_l2 = make_p_element(
        "Tabel Lampiran 2. Matriks 43 Artikel Jurnal Bereputasi Q1 dalam Berkas RIS dan Relevansinya bagi Telaah ARI",
        bold=True,
        size_pt=12.0,
        align="left",
        line_spacing=1.0,
        space_before_pt=18.0,
        space_after_pt=4.0,
        keep_with_next=True,
    )
    tbl_l2 = make_apa_table_element(
        doc,
        headers=["No.", "Sumber Artikel Menurut Rekaman RIS", "Tema Kajian dan Batas Pembandingan dengan Metode ARI"],
        rows_data=q1_rows,
        font_size_pt=9.5,
        col_widths_cm=[1.2, 7.0, 5.8],
    )
    elems.append(p_cap_l2)
    elems.append(tbl_l2)

    # --- LAMPIRAN 2 S.D. 7 (HASIL KERJA AKTUAL GATE 11 S.D. 17) ---
    lampiran_meta = [
        ("Lampiran 2. Rekonsiliasi Keputusan Penyaringan ARI-Forward dan Diagnosa 28 Kasus Kritis Terlewat (Gate 11)", "Tabel Lampiran 3", "Tabel Lampiran 4"),
        ("Lampiran 3. Realisasi Solver Rekayasa Struktur Multi-Keluarga S1–S5 dan Uji Penerimaan Analitis (Gate 12)", "Tabel Lampiran 5", ""),
        ("Lampiran 4. Pembangkitan Dataset 300 Model Induk dan Manifest Lintas Lima Keluarga Struktur S1–S5 (Gate 13)", "Tabel Lampiran 6", ""),
        ("Lampiran 5. Pembekuan Protokol dan Konfigurasi Pra-Validasi Buta ARI-FROZEN-PROTOCOL-v1.0 (Gate 14)", "Tabel Lampiran 7", "Tabel Lampiran 8"),
        ("Lampiran 6. Evaluasi Penyaringan Operasional Skala Penuh, Bootstrap B = 10.000, dan Studi Ablasi pada 300 Model Induk (Gate 15)", "Tabel Lampiran 9", "Tabel Lampiran 10", "Tabel Lampiran 11"),
        ("Lampiran 7. Eksperimen Integrasi Berpasangan ARI–GNN (StructGNN-CRC v1.0) dan Audit Biaya Operasional (Gate 17)", "Tabel Lampiran 12", "Tabel Lampiran 13"),
    ]

    gate_table_counter = 3
    for b_type, obj in gate11_17_blocks:
        if b_type == "P":
            txt = clean_text_artifacts(obj.text.strip())
            if not txt:
                continue
            if txt.startswith("LAMPIRAN KERJA — GATE") or txt.startswith("Lampiran Kerja Gate"):
                # Ganti dengan nomor urut Lampiran UNY 2023
                new_title = ""
                for meta in lampiran_meta:
                    if any(k in txt for k in ["GATE 11", "GATE 12", "GATE 13", "GATE 14", "GATE 15", "Gate 17"]):
                        if "GATE 11" in txt: new_title = lampiran_meta[0][0]
                        elif "GATE 12" in txt: new_title = lampiran_meta[1][0]
                        elif "GATE 13" in txt: new_title = lampiran_meta[2][0]
                        elif "GATE 14" in txt: new_title = lampiran_meta[3][0]
                        elif "GATE 15" in txt: new_title = lampiran_meta[4][0]
                        elif "Gate 17" in txt: new_title = lampiran_meta[5][0]
                        break
                if not new_title:
                    new_title = txt
                elems.append(
                    make_p_element(
                        new_title,
                        bold=True,
                        size_pt=12.0,
                        align="left",
                        line_spacing=1.5,
                        space_before_pt=18.0,
                        space_after_pt=6.0,
                        page_break_before=True,
                    )
                )
            elif re.match(r"^\d+\.\s+", txt):
                elems.append(
                    make_p_element(
                        txt,
                        bold=True,
                        size_pt=12.0,
                        align="left",
                        line_spacing=1.5,
                        space_before_pt=10.0,
                        space_after_pt=4.0,
                    )
                )
            else:
                elems.append(
                    make_p_element(
                        txt,
                        bold=False,
                        size_pt=12.0,
                        align="both",
                        line_spacing=1.5,
                        first_line_cm=1.0,
                        space_after_pt=6.0,
                    )
                )
        elif b_type == "T":
            headers = [c.text.strip().replace("\n", " ") for c in obj.rows[0].cells]
            rows_data = []
            for r in obj.rows[1:]:
                rows_data.append([clean_text_artifacts(c.text.strip().replace("\n", " ")) for c in r.cells])
            cap_text = f"Tabel Lampiran {gate_table_counter}. Rincian Data Pelaksanaan {headers[0] if headers else ''}"
            p_cap = make_p_element(
                cap_text,
                bold=True,
                size_pt=12.0,
                align="left",
                line_spacing=1.0,
                space_before_pt=12.0,
                space_after_pt=4.0,
                keep_with_next=True,
            )
            tbl_el = make_apa_table_element(
                doc,
                headers=headers,
                rows_data=rows_data,
                font_size_pt=9.5,
            )
            elems.append(p_cap)
            elems.append(tbl_el)
            gate_table_counter += 1

    return elems


# ==============================================================================
# 7. PROSES UTAMA REKONSTRUKSI IN-PLACE DOKUMEN DISERTASI
# ==============================================================================
def main():
    print("=" * 70)
    print("MEMULAI REKONSTRUKSI NASKAH DISERTASI SESUAI PANDUAN UNY 2023...")
    print(f"Berkas target: {REPORT_PATH}")
    print("=" * 70)

    if not os.path.exists(REPORT_PATH):
        raise FileNotFoundError(f"Berkas naskah tidak ditemukan: {REPORT_PATH}")

    os.chmod(REPORT_PATH, 0o644)
    doc = docx.Document(REPORT_PATH)

    # 1. PENGATURAN HALAMAN KERTAS A4 & MARGIN 4-4-3-3 CM (BAB V.B.1 & V.B.3 UNY 2023)
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(4.0)
        section.left_margin = Cm(4.0)
        section.bottom_margin = Cm(3.0)
        section.right_margin = Cm(3.0)

        # Penomoran halaman di bawah tengah (footer center)
        footer = section.footer
        p_foot = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pPr = p_foot._p.get_or_add_pPr()
        jc = pPr.find(qn("w:jc"))
        if jc is None:
            jc = OxmlElement("w:jc")
            pPr.append(jc)
        jc.set(qn("w:val"), "center")
        # Tambahkan field PAGE bila belum ada
        if not any("w:fldSimple" in r._r.xml or "w:instrText" in r._r.xml for r in p_foot.runs):
            fld = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls("w"))
            p_foot._p.append(fld)

    # Ambil logo UNY dari P0002 bila ada
    logo_p_el = None
    if len(doc.paragraphs) > 2 and "w:drawing" in doc.paragraphs[2]._element.xml:
        logo_p_el = copy.deepcopy(doc.paragraphs[2]._element)

    # 2. EKSTRAKSI KATALOG 80 SUMBER & 43 ARTIKEL Q1 KE LAMPIRAN
    print("Mengekstrak katalog 80 sumber dan 43 artikel Q1 untuk Lampiran...")
    catalog_rows, q1_rows = extract_catalog_and_q1_rows(doc)
    print(f"Berhasil mengekstrak {len(catalog_rows)} entri katalog dan {len(q1_rows)} artikel Q1.")

    # 3. IDENTIFIKASI SELURUH ELEMEN ASLI
    p_elements = []
    t_elements = []
    p_idx = 0
    t_idx = 0
    gate11_17_blocks = []

    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            p = Paragraph(child, doc)
            p_elements.append((p_idx, p))
            if p_idx >= 1885:
                gate11_17_blocks.append(("P", p))
            p_idx += 1
        elif isinstance(child, CT_Tbl):
            t = Table(child, doc)
            t_elements.append((t_idx, t))
            if t_idx >= 74:
                gate11_17_blocks.append(("T", t))
            t_idx += 1

    print(f"Total elemen terbaca: {len(p_elements)} paragraf, {len(t_elements)} tabel.")

    # 4. MEMBANGUN ELEMEN BODY BARU SECARA URUT
    new_body_elements = []

    # A. Bagian Awal Disertasi
    print("Membangun Bagian Awal Disertasi (Sampul, Abstrak, Pernyataan, Persetujuan, Pengesahan, Kata Pengantar, Daftar Isi/Tabel/Gambar/Lampiran/Singkatan)...")
    front_elems = build_front_matter_elements(doc, logo_p_el=logo_p_el)
    new_body_elements.extend(front_elems)

    # Helper untuk menambahkan paragraf
    def _add_body_p(p_obj):
        res = _format_body_paragraph(p_obj)
        if res is not None:
            if isinstance(res, list):
                new_body_elements.extend(res)
            else:
                new_body_elements.append(res)
    def _format_body_paragraph(p_obj, is_first_p_of_sub=False):
        txt = p_obj.text.strip()
        txt_clean = clean_text_artifacts(txt)
        if not txt_clean:
            return None

        # Cek apakah judul bab
        if txt.startswith("BAB ") or txt in ["PENDAHULUAN", "KAJIAN TEORI DAN FORMULASI ARI", "METODE PENELITIAN", "HASIL PENELITIAN DAN PEMBAHASAN", "KESIMPULAN DAN SARAN", "SIMPULAN DAN SARAN"]:
            return None  # Judul bab ditangani khusus

        # Cek apakah heading subbab (desimal) baik sendiri maupun tergabung dengan kalimat berikutnya
        first_line = txt.split("\n")[0].strip()
        m_sec = re.match(r"^([1-5]\.\d+(?:\.\d+)?)\s+(.*)$", first_line)
        if m_sec:
            sec_num = m_sec.group(1)
            if sec_num in SECTION_HEADING_MAP:
                new_prefix, new_title, lvl = SECTION_HEADING_MAP[sec_num]
                heading_text = f"{new_prefix} {new_title}"
                res_elems = [
                    make_p_element(
                        heading_text,
                        bold=True,
                        size_pt=12.0,
                        align="left",
                        line_spacing=2.0,
                        first_line_cm=0.0,
                        space_before_pt=(12.0 if lvl == 1 else 8.0),
                        space_after_pt=4.0,
                        keep_with_next=True,
                    )
                ]
                # Jika ada teks berikutnya setelah baris heading pada paragraf yang sama
                rest_lines = txt.split("\n")[1:]
                if rest_lines:
                    rest_clean = clean_text_artifacts("\n".join(rest_lines).strip())
                    if rest_clean:
                        res_elems.append(
                            make_p_element(
                                rest_clean,
                                bold=False,
                                italic=False,
                                size_pt=12.0,
                                align="both",
                                line_spacing=2.0,
                                first_line_cm=1.0,
                                space_before_pt=0.0,
                                space_after_pt=0.0,
                            )
                        )
                return res_elems

        # Cek apakah rumus terpisah (misal K_ff u_ff = p_ff)
        is_formula = any(k in txt_clean for k in ["(2.", "(3.", "(4.", "K0 = ", "K𝑓 𝑓", "u𝑓 = ", "𝚫 ="]) and len(txt_clean) < 120
        if is_formula:
            return make_p_element(
                txt_clean,
                bold=False,
                italic=False,
                size_pt=12.0,
                align="center",
                line_spacing=1.5,
                first_line_cm=0.0,
                space_before_pt=4.0,
                space_after_pt=4.0,
            )

        # Paragraf isi biasa (spasi ganda 2.0, rata kanan-kiri, first-line indent 1.0 cm)
        return make_p_element(
            txt_clean,
            bold=False,
            italic=False,
            size_pt=12.0,
            align="both",
            line_spacing=2.0,
            first_line_cm=(1.0 if not is_first_p_of_sub else 1.0),
            space_before_pt=0.0,
            space_after_pt=0.0,
        )

    # B. BAB I PENDAHULUAN
    print("Membangun BAB I...")
    new_body_elements.append(
        make_p_element("BAB I", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=0.0, page_break_before=True)
    )
    new_body_elements.append(
        make_p_element("PENDAHULUAN", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=12.0)
    )
    for p_id in range(9, 68):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 1 utuh (Peta Kontribusi)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T1"], font_size_pt=10.0))

    for p_id in range(82, 91):
        _add_body_p(p_elements[p_id][1])

    # C. BAB II KAJIAN PUSTAKA
    print("Membangun BAB II...")
    new_body_elements.append(
        make_p_element("BAB II", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=0.0, page_break_before=True)
    )
    new_body_elements.append(
        make_p_element("KAJIAN PUSTAKA", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=12.0)
    )
    for p_id in range(93, 105):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 2 (Pembedaan Konstruk)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T2"], font_size_pt=10.5))

    for p_id in range(105, 124):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 1 (Transformasi Rangka Batang ke Graf)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G1"], font_size_pt=10.0))

    for p_id in range(137, 156):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 2 (Operasi Pelemahan & Penghapusan Sisi)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G2"], font_size_pt=10.0))

    for p_id in range(167, 188):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan narasi ringkas Subbab J (Green AI)
    new_body_elements.append(
        make_p_element("J. Green AI dan Efisiensi Komputasi", bold=True, size_pt=12.0, align="left", line_spacing=2.0, space_before_pt=12.0, space_after_pt=4.0, keep_with_next=True)
    )
    new_body_elements.append(
        make_p_element(
            "Perspektif Green AI (Schwartz et al., 2019) menempatkan efisiensi energi dan jejak karbon komputasi sebagai metrik evaluasi primer di samping akurasi. Dalam konteks evaluasi struktur berskala besar dengan model pengganti Graph Neural Network (GNN), inferensi pada ribuan skenario gangguan elemen memerlukan evaluasi berulang yang intensif. Penggunaan Adjusted Redundancy Index (ARI) sebagai penapis praanalisis dirancang untuk mereduksi jumlah skenario yang dievaluasi oleh GNN, dengan syarat bahwa energi dan waktu komputasi yang dihemat pada tahap inferensi harus melampaui biaya tambahan yang dikeluarkan untuk menghitung skor jalur dan pengaman kinematik.",
            bold=False, size_pt=12.0, align="both", line_spacing=2.0, first_line_cm=1.0
        )
    )

    # Subbab K: Hasil Penelusuran dan Dokumentasi Literatur (dengan Tabel 3 & Tabel 4)
    for p_id in range(189, 195):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 3 (Penelusuran Tema)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T3"], font_size_pt=10.5))

    for p_id in range(206, 208):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 4 (Sumber Terpilih)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T4"], font_size_pt=10.0))

    # Narasi penghubung ke Lampiran 1 untuk katalog panjang
    new_body_elements.append(
        make_p_element("2. Katalog Beranotasi Sumber yang Ditemukan", bold=True, size_pt=12.0, align="left", line_spacing=2.0, space_before_pt=8.0, space_after_pt=4.0, keep_with_next=True)
    )
    new_body_elements.append(
        make_p_element(
            "Katalog beranotasi lengkap yang memuat rincian 80 sumber literatur hasil penelusuran terarah (S01–S80) beserta matriks 43 artikel jurnal bereputasi tinggi (Q1) dari rekaman RIS disajikan pada Lampiran 1 (Tabel Lampiran 1 dan Tabel Lampiran 2) sesuai ketentuan Bab V.B.9.a.5 Panduan Disertasi UNY 2023.",
            bold=False, size_pt=12.0, align="both", line_spacing=2.0, first_line_cm=1.0
        )
    )

    for p_id in range(508, 522):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 5 (Matriks Sintesis Penelitian Terdahulu)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T5"], font_size_pt=10.0))

    for p_id in range(568, 590):
        _add_body_p(p_elements[p_id][1])

    # Narasi penghubung ke Lampiran 1 untuk artikel jurnal Q1
    new_body_elements.append(
        make_p_element("1. Referensi Inti dan Referensi Pendukung", bold=True, size_pt=12.0, align="left", line_spacing=2.0, space_before_pt=8.0, space_after_pt=4.0, keep_with_next=True)
    )
    new_body_elements.append(
        make_p_element(
            "Matriks telaah komprehensif 43 artikel jurnal internasional bereputasi tinggi (Q1) dari rekaman penelusuran RIS disajikan pada Lampiran 1 (Tabel Lampiran 2) sesuai ketentuan Bab V.B.9.a.5 Panduan Disertasi UNY 2023.",
            bold=False, size_pt=12.0, align="both", line_spacing=2.0, first_line_cm=1.0
        )
    )

    for p_id in range(776, 799):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 3 (Alur Pembentukan Skor ARI, CI, dan Pengaman Kinematik)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G3"], font_size_pt=10.0))

    for p_id in range(799, 811):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 4 (Kerangka Berpikir: Pemisahan Jalur Operasional & Acuan)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G4"], font_size_pt=10.0))

    for p_id in range(812, 819):
        _add_body_p(p_elements[p_id][1])

    # D. BAB III METODE PENELITIAN
    print("Membangun BAB III...")
    new_body_elements.append(
        make_p_element("BAB III", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=0.0, page_break_before=True)
    )
    new_body_elements.append(
        make_p_element("METODE PENELITIAN", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=12.0)
    )
    for p_id in range(821, 867):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 5 (Alur Keputusan Penyaringan Sebelum GNN)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G5"], font_size_pt=10.0))

    # Sisipkan Tabel 6 (Rencana & Realisasi Sampel 300 Model)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T6"], font_size_pt=10.5))

    for p_id in range(872, 891):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 6 (Skema Pemisahan Partisi Berdasarkan Model Induk)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G6"], font_size_pt=10.0))

    # Sisipkan Tabel 7 (Tahapan Validasi Lanjutan)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T7"], font_size_pt=10.5))

    for p_id in range(892, 916):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 8 (Variabel Operasional)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T8"], font_size_pt=10.0))

    for p_id in range(928, 935):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 9 (Variasi Topologi & Mekanis S1–S5)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T9"], font_size_pt=10.5))

    for p_id in range(947, 971):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 7 (Skema Idealisasi Lima Keluarga Struktur S1–S5)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G7"], font_size_pt=10.0))

    for p_id in range(972, 980):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 10 (Instrumen Penelitian)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T10"], font_size_pt=10.5))

    for p_id in range(987, 1005):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 11 (Prasyarat Realisasi Lima Keluarga S1–S5)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T11"], font_size_pt=10.0))

    for p_id in range(1023, 1139):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 12 (Audit Kandidat GNN Acuan)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T12"], font_size_pt=10.0))

    for p_id in range(1141, 1189):
        _add_body_p(p_elements[p_id][1])

    # E. BAB IV HASIL PENELITIAN DAN PEMBAHASAN
    print("Membangun BAB IV...")
    new_body_elements.append(
        make_p_element("BAB IV", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=0.0, page_break_before=True)
    )
    new_body_elements.append(
        make_p_element("HASIL PENELITIAN DAN PEMBAHASAN", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=12.0)
    )
    for p_id in range(1191, 1206):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 8 (Empat Model Kanonik)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G8"], font_size_pt=10.5))

    for p_id in range(1208, 1220):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 13 (Hasil Solver Kanonik Utuh)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T13"], font_size_pt=10.5))

    for p_id in range(1221, 1227):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 14 (Status Gangguan Kanonik)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T14"], font_size_pt=10.5))

    for p_id in range(1233, 1238):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 15 (Skor Graf & Rank Persegi Satu Diagonal)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T15"], font_size_pt=10.5))

    for p_id in range(1239, 1241):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 9 (Kasus Mekanisme Terlewat Persegi Satu Diagonal)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G9"], font_size_pt=10.0))

    for p_id in range(1249, 1254):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Gambar 10 (Kurva CI terhadap Pelemahan)
    new_body_elements.extend(make_captioned_figure(doc, *FIGURES_SPEC["G10"], font_size_pt=10.5))

    for p_id in range(1255, 1301):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 16 (Uji Regresi Dua Kehilangan Bergaya Awal Nol)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T16"], font_size_pt=10.5))

    for p_id in range(1302, 1303):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 17 (Diagnostik Pengembangan Runner Lokal)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T17"], font_size_pt=10.5))

    for p_id in range(1305, 1313):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 18 (Diagnostik Parametrik Gate 9 Unggahan)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T18"], font_size_pt=10.5))

    for p_id in range(1314, 1345):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 19 (Sintesis Hubungan Pertanyaan Penelitian & Bukti)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T19"], font_size_pt=10.0))

    for p_id in range(1348, 1441):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Kode 1 (Pseudocode Pencarian Lintasan)
    new_body_elements.append(
        make_p_element("Kode 1. Pseudocode Skor Pasangan untuk Graf Acuan Kecil", bold=True, size_pt=11.0, align="left", line_spacing=1.0, space_before_pt=8.0, space_after_pt=3.0, keep_with_next=True)
    )
    code_text = (
        "def pair_score(graph, source, target, config):\n"
        "    if source == target:\n"
        "        return omega[1] / epsilon_d, CERTIFIED\n"
        "    paths = enumerate_all_simple_paths(graph, source, target)\n"
        "    best_score = 0.0\n"
        "    for count in range(1, min(K, len(paths)) + 1):\n"
        "        for candidate in combinations(paths, count):\n"
        "            if shared_physical_edge(candidate):\n"
        "                continue\n"
        "            costs = sort_ascending(path_costs(candidate))\n"
        "            score = sum(omega[rank] / (costs[rank] + epsilon_d) for rank in range(count))\n"
        "            best_score = max(best_score, score)\n"
        "    return best_score, CERTIFIED"
    )
    new_body_elements.append(
        make_p_element(code_text, bold=False, size_pt=10.0, align="left", line_spacing=1.0, first_line_cm=0.0, font_name="Courier New", space_before_pt=2.0, space_after_pt=6.0)
    )

    for p_id in range(1443, 1453):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 20 (Kode Status Operasional)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T20"], font_size_pt=10.5))

    for p_id in range(1470, 1488):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Kode 2 (Urutan Reproduksi)
    new_body_elements.append(
        make_p_element("Kode 2. Urutan Perintah Reproduksi Contoh dan Eksperimen", bold=True, size_pt=11.0, align="left", line_spacing=1.0, space_before_pt=8.0, space_after_pt=3.0, keep_with_next=True)
    )
    code_repro = (
        "python examples/ari_tutorial.py\n"
        "python examples/run_verification.py\n"
        "python examples/run_guard_verification.py\n"
        "python examples/generate_dataset_300_s1_s5.py\n"
        "python examples/run_full_screening_300.py\n"
        "python examples/run_gnn_integration_s6.py"
    )
    new_body_elements.append(
        make_p_element(code_repro, bold=False, size_pt=10.0, align="left", line_spacing=1.0, first_line_cm=0.0, font_name="Courier New", space_before_pt=2.0, space_after_pt=6.0)
    )

    for p_id in range(1488, 1492):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 21 (Keluaran Direktori results/verification)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T21"], font_size_pt=10.5))

    for p_id in range(1512, 1517):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 22 (Berkas Bukti Numerik Gate 9)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T22"], font_size_pt=10.5))

    for p_id in range(1528, 1537):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 23 (Skema Minimum Berkas Data)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T23"], font_size_pt=10.5))

    for p_id in range(1544, 1562):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 24 (Kasus Uji Minimum & Hasil Harapan)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T24"], font_size_pt=10.0))

    for p_id in range(1597, 1624):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan rumus analitis (4.16) rapi tanpa tabel serpihan
    new_body_elements.append(
        make_p_element("S(G^M) = (1/2)*(4/7) + (1/2)*(2/5) = 17/35 . (4.16)", bold=False, size_pt=12.0, align="center", line_spacing=1.5, space_before_pt=4.0, space_after_pt=4.0)
    )

    for p_id in range(1625, 1627):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 25 (Contoh Analitis Dua Batang Paralel)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T25"], font_size_pt=10.5))

    for p_id in range(1628, 1657):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 26 (Hitungan Ambang Delapan Gangguan)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T26"], font_size_pt=10.5))

    for p_id in range(1658, 1683):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 27 (Status Pemenuhan Prasyarat Eksperimen)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T27"], font_size_pt=10.0))

    for p_id in range(1700, 1706):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 28 (Rincian Pekerjaan Finalisasi Gate 11–17)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T28"], font_size_pt=10.0))

    for p_id in range(1720, 1744):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 29 (Inventaris Hasil Aktual menurut Partisi Data)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T29"], font_size_pt=10.0))

    for p_id in range(1749, 1758):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 30 (Ringkasan Bukti & Keputusan Gerbang Validasi A–D & Integrasi)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T30"], font_size_pt=9.5))

    for p_id in range(1761, 1766):
        _add_body_p(p_elements[p_id][1])

    # Sisipkan Tabel 31 (Pemisahan Biaya Operasional Integrasi ARI–GNN)
    new_body_elements.extend(make_captioned_table(doc, *TABLES_SPEC["T31"], font_size_pt=9.5))

    for p_id in range(1779, 1788):
        _add_body_p(p_elements[p_id][1])

    # F. BAB V SIMPULAN DAN SARAN
    print("Membangun BAB V (SIMPULAN DAN SARAN)...")
    new_body_elements.append(
        make_p_element("BAB V", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=0.0, page_break_before=True)
    )
    new_body_elements.append(
        make_p_element("SIMPULAN DAN SARAN", bold=True, size_pt=12.0, align="center", line_spacing=2.0, space_before_pt=0.0, space_after_pt=12.0)
    )
    for p_id in range(1790, 1826):
        _add_body_p(p_elements[p_id][1])

    # G. DAFTAR PUSTAKA (APA 7th Edition — 1 spasi dalam pustaka, hanging indent 1.0 cm, jarak antarpustaka 12 pt)
    print("Membangun DAFTAR PUSTAKA (APA 7th Edition)...")
    new_body_elements.append(
        make_p_element("DAFTAR PUSTAKA", bold=True, size_pt=12.0, align="center", line_spacing=1.0, space_after_pt=12.0, page_break_before=True)
    )
    # Gabungkan baris pustaka yang terpotong di P2103..P2160
    bib_entries = []
    cur_bib = []
    for p_id in range(1827, 1885):
        t_raw = p_elements[p_id][1].text.strip()
        if not t_raw:
            continue
        # Indikator entri baru: diawali Nama, Inisial (Tahun).
        is_new_entry = bool(re.match(r"^[A-Z][a-zA-Z\s’\'-]+,\s+[A-Z\.\-\s]+(?:\([12]\d{3}\)|\(t\.t\.\))", t_raw)) or t_raw.startswith("NetworkX Developers") or t_raw.startswith("NumPy Developers")
        if is_new_entry:
            if cur_bib:
                bib_entries.append(" ".join(cur_bib))
            cur_bib = [t_raw]
        else:
            cur_bib.append(t_raw)
    if cur_bib:
        bib_entries.append(" ".join(cur_bib))

    for b_str in bib_entries:
        cleaned_b = clean_text_artifacts(b_str)
        new_body_elements.append(
            make_p_element(
                cleaned_b,
                bold=False,
                size_pt=12.0,
                align="both",
                line_spacing=1.0,
                first_line_cm=0.0,
                hanging_cm=1.0,
                space_before_pt=0.0,
                space_after_pt=12.0,  # 1 spasi dalam entri, 2 spasi antarpustaka
            )
        )

    # H. LAMPIRAN LENGKAP (LAMPIRAN 1 S.D. LAMPIRAN 7)
    print("Membangun Bagian LAMPIRAN LENGKAP (Lampiran 1 s.d. Lampiran 7)...")
    appendix_elems = build_appendices_elements(doc, catalog_rows, q1_rows, gate11_17_blocks)
    new_body_elements.extend(appendix_elems)

    # 5. MENERAPKAN BODY BARU KE DALAM DOKUMEN SECARA IN-PLACE
    print(f"Mengganti isi dokumen Word ({len(new_body_elements)} elemen baru disiapkan)...")
    body = doc.element.body

    # Simpan elemen w:sectPr terakhir jika ada
    sectPr = body.find(qn("w:sectPr"))
    if sectPr is not None:
        sectPr_copy = copy.deepcopy(sectPr)
    else:
        sectPr_copy = None

    # Hapus semua anak body lama
    for child in list(body.iterchildren()):
        body.remove(child)

    # Tambahkan seluruh elemen baru
    for el in new_body_elements:
        body.append(el)

    # Kembalikan sectPr di akhir dokumen
    if sectPr_copy is not None:
        body.append(sectPr_copy)

    # 6. SIMPAN DOKUMEN SECARA LANGSUNG (IN-PLACE)
    doc.save(REPORT_PATH)
    os.chmod(REPORT_PATH, 0o644)
    print("=" * 70)
    print("SUKSES BESAR! Naskah disertasi telah berhasil direkonstruksi in-place.")
    print(f"Berkas tersimpan rapi di: {REPORT_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
