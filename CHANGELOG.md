# Changelog

Format mengikuti Keep a Changelog; versi mengikuti Semantic Versioning.

## 0.1.1 - 2026-11-14

### Diperbaiki

- Postur APBD era 2011-2016 kini dikenali lewat peta varian terpisah. Akar dan induk
  era lama (Pendapatan, Dana Perimbangan, Belanja Tidak Langsung, dan lainnya) tidak
  lagi ikut pool nilai, jadi data era lama tidak dihitung ganda dengan anaknya.
- Perintah analyze dan report untuk dataset apbd menolak permintaan tanpa --periode
  atau di luar rentang 1 sampai 12 dengan pesan singkat, bukan traceback.
- Kegagalan yang wajar (cache kosong, tahun belum diunduh, kelompok tanpa nilai cukup)
  tampil sebagai pesan ramah dengan kode keluar 2.
- Tabel laporan markdown menampilkan p-value kecil dalam format ilmiah dan NaN sebagai
  garis, bukan 0.0000 atau nan.

### Ditambahkan

- Peringatan ke stderr saat --refresh gagal dan cache lama dipakai.
- Permintaan yang diblokir server (HTTP 403) tidak dicoba ulang.
- 9 test baru: postur era lama pada file 2015, ketahanan file era baru, format tabel
  laporan, dan jalur galat CLI.

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
