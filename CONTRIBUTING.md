# Panduan kontribusi

Terima kasih mau ikut merawat benford-apbd. Halaman ini merangkum cara kerja yang
dipakai repo ini supaya perubahan bisa ditinjau cepat.

## Persiapan lingkungan

```bash
git clone <url-repo>
cd benford-apbd
pip install -e ".[dev]"
```

Opsional untuk dashboard:

```bash
pip install -e ".[dev,dashboard]"
```

Sebelum mengusulkan perubahan, pastikan dua ini lulus:

```bash
pytest -q
ruff check src tests
```

## Struktur yang perlu diketahui

| Jalur | Isi |
| --- | --- |
| `src/benford_apbd/benford.py` | matematika digit: chi-square, MAD, batas Nigrini, bootstrap |
| `src/benford_apbd/djpk.py` | klien Portal Data DJPK, cache, parser SpreadsheetML, postur kanonik |
| `src/benford_apbd/analyze.py` | pooling per kelompok, peringkat, pemilahan tingkat sumber |
| `src/benford_apbd/report.py` | grafik dan laporan markdown |
| `src/benford_apbd/cli.py` | antarmuka baris perintah |
| `dashboard/app.py` | Streamlit |
| `docs/METODOLOGI.md` | batasan metode dan etika penyampaian |

## Aturan main

1. **Metode statistik berubah, dokumentasi ikut.** Perubahan apa pun di `benford.py`
   (rumus, batas, definisi digit) wajib disertai pembaruan `docs/METODOLOGI.md` dan
   test yang membuktikan perilaku barunya.
2. **Data tidak masuk repo.** Folder `data/` dan `reports/` sudah di-gitignore. Jangan
   pernah meng-commit hasil unduhan DJPK, laporan, atau grafik keluaran.
3. **Akses server sopan.** Klien sudah punya cache dan jeda antar permintaan. Jangan
   menambah jalur unduhan tanpa cache, dan jangan menaikkan laju permintaan. Kalau perlu
   data besar untuk pengujian, buat fixture kecil sintetis, bukan file asli.
4. **Framing hati-hati.** Teks antarmuka dan laporan memakai kerangka "indikasi
   statistik yang layak diperiksa", bukan tuduhan. Usulan kalimat baru harus
   mempertahankan kerangka ini.
5. **Bahasa.** Identifier dan komentar kode dalam bahasa Inggris; teks yang tampil ke
   pengguna (CLI, laporan, dashboard, README) dalam bahasa Indonesia. Tanpa em dash.
6. **Satu PR satu topik.** PR kecil yang jelas lebih cepat ditinjau daripada PR besar
   yang mencampur banyak hal.

## Melaporkan bug atau mengusulkan fitur

Gunakan template issue yang tersedia. Untuk bug, sertakan perintah persis yang dijalankan,
dataset dan periode, serta output lengkap; tanpa itu reproduksi sulit.

## Pesan commit

Baris pertama bahasa Indonesia, kata kerja di awal, maksimal sekitar 72 karakter,
contoh: "Perbaiki dedup baris ekspor APBD yang terulang".
