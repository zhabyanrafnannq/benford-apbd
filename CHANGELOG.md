# Changelog

Format mengikuti Keep a Changelog; versi mengikuti Semantic Versioning.

## 0.1.0 - 2026-11-14

### Ditambahkan

- Klien Portal Data DJPK dengan cache lokal: APBD (per pemda, anggaran dan realisasi)
  dan TKDD (termasuk komponen Dana Desa), plus referensi provinsi dan pemda.
- Parser SpreadsheetML toleran: hierarki dari indentasi label atau postur kanonik APBD,
  angka berformat Indonesia (62.480,25 M), dedup baris ekspor yang terulang.
- Uji digit pertama, kedua, dan dua digit pertama dengan chi-square, MAD berbatas
  Nigrini, jalur grafik 95%, dan interval bootstrap MAD.
- Pemeriksaan angka bulat (akhiran nol) untuk dataset APBD.
- Analisis per kelompok: nasional, per provinsi, per pemda, per jenis akun, dengan
  pemilahan tingkat sumber agar agregat dan detail tidak dobel hitung.
- Generator laporan markdown dengan grafik PNG dan kerangka interpretasi hati-hati.
- CLI `benford-apbd` (fetch, analyze, report, cache) dan dashboard Streamlit.
- 22 test pytest dan CI GitHub Actions (ruff + pytest).
