# benford-apbd

Uji Hukum Benford atas data APBD dan dana desa yang dipublikasikan Portal Data DJPK Kemenkeu.
Alat ini menghitung kesesuaian digit pertama, digit kedua, dan dua digit pertama terhadap
distribusi Benford, lalu memeringkat wilayah dan jenis belanja berdasarkan simpangan,
dengan interval kepercayaan bootstrap.

Hasil uji ini adalah indikasi statistik yang layak diperiksa lebih lanjut, bukan bukti
penyimpangan. Baca [docs/METODOLOGI.md](docs/METODOLOGI.md) untuk batasan metode sebelum
menarik kesimpulan apa pun.

## Kenapa dibuat

Data anggaran daerah Indonesia tersebar sebagai agregat akun di portal DJPK, dan alat uji
digit atas data itu belum ada yang berbahasa Indonesia dan open-source. Paket R
`benfordanalysis` ada, tetapi pengguna harus memecahkan masalah pengambilan dan penataan
data DJPK sendiri. Proyek ini menutup alur itu: unduh, rapikan, uji, peringkat, laporkan.

## Sumber data

| Dataset | Sumber | Cakupan |
| --- | --- | --- |
| APBD | [djpk.kemenkeu.go.id/portal/data/apbd](https://djpk.kemenkeu.go.id/portal/data/apbd) | Postur APBD per pemda, anggaran dan realisasi, 2011 sampai sekarang |
| TKDD (termasuk Dana Desa) | [djpk.kemenkeu.go.id/portal/data/tkdd](https://djpk.kemenkeu.go.id/portal/data/tkdd) | Transfer ke daerah per pemda, termasuk komponen Dana Desa |

Kedua endpoint mengembalikan SpreadsheetML (bukan CSV murni) dan formatnya berubah dari
tahun ke tahun, jadi parser disusun toleran: hierarki akun dibaca dari indentasi label
kalau ada, atau dari peta postur yang dipilih sesuai era file (era 2017 ke atas dan era
2011-2016 memakai nama akun berbeda, keduanya dipetakan agar nilai induk tidak dihitung
ganda).

Catatan: data.go.id sebelumnya dipakai sebagai sumber cadangan, tetapi CKAN API-nya sudah
tidak tersedia (HTTP 404 saat pengecekan 2026-11), jadi fallback belum diaktifkan di kode.
Village-level Dana Desa (per desa) tidak diekspos portal DJPK; yang tersedia adalah total
Dana Desa per pemda.

## Mulai cepat

Butuh Python 3.10+. Semua komputasi CPU-only dan datasetnya kecil (puluhan MB), aman untuk
laptop 8 GB tanpa GPU.

```bash
pip install -e .

# 1. unduh data (tersimpan di ./data, file yang sudah ada tidak diunduh ulang)
benford-apbd fetch apbd --tahun 2025 --periode 12 --scope provinsi

# 2. uji digit per provinsi
benford-apbd analyze --dataset apbd --tahun 2025 --periode 12 --group per_provinsi

# 3. laporan markdown + grafik
benford-apbd report --dataset apbd --tahun 2025 --periode 12 --group per_provinsi
```

Lingkup unduhan: `nasional` (1 file), `provinsi` (34 file agregat provinsi), `pemda`
(sekitar 580 file, satu per pemda, bisa dilanjutkan karena cache). Default jarak antar
permintaan 0,4 detik supaya server DJPK tidak diterpa; naikkan dengan `--delay` atau
batasi dengan `--provinsi 11` untuk satu provinsi saja.

Untuk dana desa:

```bash
benford-apbd fetch tkdd --tahun 2025 --scope provinsi
benford-apbd analyze --dataset tkdd --tahun 2025 --group per_provinsi
```

## Dashboard

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Memilih dataset, tahun, kelompok, dan jenis digit; menampilkan peringkat simpangan dan
grafik digit dengan jalur kesalahan Nigrini 95%. Data yang belum diunduh ditampilkan
sebagai panduan perintah, bukan halaman kosong.

## Jalankan di Streamlit Community Cloud

Dashboard tidak butuh localhost; ia bisa berjalan di [share.streamlit.io](https://share.streamlit.io):

1. Push repo ini ke GitHub.
2. Masuk share.streamlit.io dengan akun GitHub, pilih "New app".
3. Isi repo, branch `main`, main file `dashboard/app.py`, lalu Deploy.

Folder `sample/` membawa potongan unduhan DJPK (sekitar 1,3 MB) sehingga aplikasi cloud
langsung punya data demo tanpa mengunduh apa pun; dashboard selalu memberi tahu bila
sedang memakai data contoh. Server cloud berada di luar Indonesia dan portal DJPK kadang
membatasi akses dari luar negeri, jadi pengunduhan massal sengaja tidak dijalankan dari
cloud. Dependensi untuk cloud ada di `requirements.txt`.

## Perintah

| Perintah | Fungsi |
| --- | --- |
| `benford-apbd fetch` | unduh data DJPK ke cache lokal |
| `benford-apbd analyze` | uji digit per kelompok, keluaran CSV berperingkat |
| `benford-apbd report` | laporan markdown plus grafik PNG |
| `benford-apbd cache` | daftar isi cache |

Kelompok analisis: `nasional`, `per_provinsi`, `per_pemda`, `per_akun` (misal semua nilai
"Belanja Modal" lintas pemda). Jenis uji: `first`, `second`, `first_two`. Nilai yang diuji:
`realisasi` (default) atau `anggaran`.

## Apa yang dihitung

- Distribusi digit dengan proporsi Benford, chi-square, dan peringatan bahwa chi-square
  nyaris selalu signifikan pada n besar.
- Mean Absolute Deviation (MAD) dengan batas kesesuaian Nigrini (dekat, sesuai, marginal,
  tidak sesuai) untuk tiga jenis digit.
- Jalur kesalahan grafik 95% per digit (batang yang keluar jalur digambar merah bata).
- Interval kepercayaan MAD 95% dari bootstrap 500 resampling.
- Porsi nilai berakhiran nol (indikator artefak angka bulat, hanya untuk APBD karena TKDD
  dibulatkan dalam satuan Miliar).
- Baris induk postur dikeluarkan dari pool agar nilai induk dan anak tidak dihitung ganda.

## Batasan

Lengkap di [docs/METODOLOGI.md](docs/METODOLOGI.md). Intinya: n per pemda hanya sekitar
20 nilai, terlalu kecil untuk MAD yang stabil; analisis yang bermakna ada di level
provinsi, nasional, atau per jenis akun; data DJPK adalah agregat akun, bukan transaksi
individual, dan itu mengubah makna simpangan.

## Etika penggunaan

Gunakan untuk pembelajaran forensik statistik, riset, dan jurnalisme data dengan keluaran
yang berhati-hati. Angka pada laporan adalah kandidat untuk diprioritaskan pemeriksaan,
bukan tuduhan kepada wilayah atau pejabat mana pun. Hormati server sumber: pakai cache,
jangan unduh massal tanpa jeda.

## Pengembangan

```bash
pip install -e ".[dev]"
ruff check src tests
pytest -q
```

Struktur: `src/benford_apbd/` (benford.py matematika digit, djpk.py klien dan parser,
analyze.py pipeline, report.py laporan, cli.py) dan `dashboard/app.py`. CI di
`.github/workflows/ci.yml` menjalankan lint dan test pada setiap push.

Mau ikut berkontribusi? Panduan lengkap ada di [CONTRIBUTING.md](CONTRIBUTING.md);
riwayat versi di [CHANGELOG.md](CHANGELOG.md). Laporan bug dan usulan fitur memakai
template issue yang tersedia.

## Lisensi

MIT.
