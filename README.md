# benford-apbd

![CI](https://github.com/zhabyanrafnannq/benford-apbd/actions/workflows/ci.yml/badge.svg)

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

## Alur kerja

| Langkah | Perintah | Keluaran |
| --- | --- | --- |
| 1. Unduh | `benford-apbd fetch` | `data/raw/` dan `data/ref/` (cache XML dan JSON portal DJPK) |
| 2. Uji | `benford-apbd analyze` | CSV berperingkat di `data/processed/` |
| 3. Laporan | `benford-apbd report` | `reports/` berisi laporan markdown plus grafik PNG |
| 4. Jelajahi | `streamlit run dashboard/app.py` | tampilan interaktif atas cache |

Setiap langkah hanya membaca folder cache, jadi bisa diulang berapa kali tanpa
mengunduh ulang apa pun. Tanpa cache, dashboard otomatis memakai `sample/` sebagai
data contoh dan menandainya dengan jelas.

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

## Dokumentasi perintah

### `fetch`: unduh data

```bash
benford-apbd fetch <apbd|tkdd> --tahun 2025 [--periode 12] [--scope provinsi]
                   [--provinsi 11] [--refresh] [--delay 0.4] [--cache data]
```

| Opsi | Fungsi |
| --- | --- |
| `--tahun` | tahun anggaran (portal menyediakan 2011 sampai sekarang) |
| `--periode` | wajib untuk apbd, 1 sampai 12; 12 berarti satu tahun penuh |
| `--scope` | `nasional` (1 file), `provinsi` (38 file agregat), `pemda` (sekitar 580 file per pemda) |
| `--provinsi` | batasi unduhan ke satu kode provinsi, mis. `11` (Jawa Tengah) |
| `--refresh` | unduh ulang file yang sudah ada di cache |
| `--delay` | jeda antar permintaan dalam detik (default 0,4; jangan diturunkan) |

Unduhan bersifat cache: file yang sudah ada tidak diunduh ulang, dan lingkup `pemda`
bisa dilanjutkan bila terputus. Permintaan yang diblokir server (403) atau tak ada
(404) tidak dicoba ulang; kegagalan dilaporkan di akhir tanpa menghentikan unduhan lain.

### `analyze`: uji digit per kelompok

```bash
benford-apbd analyze --dataset apbd --tahun 2025 --periode 12 --group per_provinsi
                     --kolom realisasi --kind first --n-boot 500 --seed 42
                     [--sumber auto] [-o hasil.csv]
```

| Opsi | Fungsi |
| --- | --- |
| `--group` | `nasional`, `per_provinsi`, `per_pemda`, atau `per_akun` (misal semua nilai "Belanja Modal" lintas pemda) |
| `--kolom` | nilai yang masuk pool: `realisasi` (default) atau `anggaran` |
| `--kind` | jenis uji digit: `first`, `second`, `first_two` |
| `--sumber` | tingkat file yang dipakai: `auto` (default, memilih yang paling rinci), `pemda`, `provinsi`, `nasional` |
| `--n-boot`, `--seed` | jumlah resampling bootstrap dan benih acak (default 500 dan 42, hasil reproducible) |
| `--semualevel` | sertakan baris induk postur; menghasilkan simpangan artifisial, tidak disarankan |
| `-o` | jalur CSV keluaran (default: `data/processed/analisis_*.csv`) |

Contoh keluaran (dipotong):

```
tingkat file yang dipakai: pemda
kode_provinsi      nama_provinsi    n    mad  mad_ci95_bawah  ...  kesesuaian   p_value  share_2_nol
11  Provinsi Jawa Tengah  594  0.0158  0.0118  ...  tidak sesuai  0.0257  0.1599
```

Kolom penting: `n` (jumlah nilai diuji), `mad` beserta interval bootstrap 95%,
`kesesuaian` (batas Nigrini), `p_value` (chi-square, ingat: hampir selalu signifikan
pada n besar), `share_2_nol` (porsi nilai berakhiran minimal dua nol, hanya APBD), dan
`catatan` (mis. peringatan n < 100).

### `report`: laporan markdown plus grafik

Opsi sama dengan `analyze`, ditambah `--top N` (jumlah grafik kelompok paling
menyimpang, default 3) dan `--out-dir` (default `reports/`). Keluarannya `laporan.md`
berisi ringkasan metode, tabel peringkat, grafik digit dengan jalur kesalahan Nigrini
95%, dan paragraf interpretasi yang menegaskan batas kesimpulan.

### `cache`: daftar isi cache

Menampilkan kombinasi dataset, tahun, dan periode yang siap dianalisis. Contoh:

```
apbd 2015 periode 12
apbd 2025 periode 12
tkdd 2018
tkdd 2025
```

## Parameter analisis pada dashboard

Sidebar "Parameter analisis" berisi delapan kontrol yang benar-benar mengubah hasil:

| Kontrol | Pilihan | Fungsi |
| --- | --- | --- |
| Dataset | `apbd`, `tkdd` | sumber data yang dianalisis |
| Tahun | mengikuti isi cache | tahun anggaran |
| Periode | 1 sampai 12 | hanya untuk APBD; hilang otomatis untuk TKDD |
| Kelompok | Nasional, Per provinsi, Per pemda, Per jenis akun | cara penggabungan nilai |
| Nilai yang diuji | `realisasi`, `anggaran` | kolom angka yang masuk pool |
| Jenis digit | digit pertama, digit kedua, digit pertama-kedua | uji distribusi yang dijalankan |
| Tingkat file | `auto`, `pemda`, `provinsi`, `nasional` | tingkat cache yang dipakai |
| Checkbox baris daun | dicentang (default) | hanya akun terdalam postur yang masuk pool |

Di atas tabel hasil selalu ada keterangan tingkat file yang dipakai, dan setiap grafik
menandai batang yang keluar jalur Nigrini dengan merah bata.

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

Mau ikut berkontribusi? Panduan lengkap ada di [CONTRIBUTING.md](CONTRIBUTING.md);
riwayat versi di [CHANGELOG.md](CHANGELOG.md). Laporan bug dan usulan fitur memakai
template issue yang tersedia.

## Struktur repo

| Jalur | Isi |
| --- | --- |
| `src/benford_apbd/benford.py` | matematika digit: chi-square, MAD berbatas Nigrini, bootstrap, angka bulat |
| `src/benford_apbd/djpk.py` | klien portal DJPK, cache, parser SpreadsheetML, dua varian postur era |
| `src/benford_apbd/analyze.py` | pooling per kelompok, pemilahan tingkat sumber, peringkat simpangan |
| `src/benford_apbd/report.py` | grafik digit dan generator laporan markdown |
| `src/benford_apbd/cli.py` | antarmuka baris perintah |
| `dashboard/app.py` | Streamlit: parameter analisis, tabel peringkat, grafik |
| `sample/` | potongan unduhan DJPK (1,3 MB) untuk data demo dashboard cloud |
| `tests/` | 33 test pytest atas parser, statistik, analisis, CLI, dan laporan |
| `.github/` | CI (ruff + pytest), template issue dan pull request |
| `docs/METODOLOGI.md` | batasan metode dan etika penyampaian hasil |
| `data/`, `reports/` | cache unduhan dan keluaran lokal; di-gitignore, terbentuk saat dijalankan |

## Lisensi

MIT.
