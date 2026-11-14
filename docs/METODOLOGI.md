# Metodologi uji Benford pada data APBD/TKDD

Dokumen ini menjelaskan apa yang dihitung alat ini, kapan simpangan bermakna, kapan
simpangan hanya artefak data, dan bagaimana menyampaikan hasil tanpa tuduhan berlebihan.

## 1. Hukum Benford dalam satu paragraf

Pada banyak kumpulan angka yang tumbuh secara alami (nilai transaksi, populasi, panjang
sungai), digit signifikan pertama tidak merata. Angka 1 muncul sekitar 30,1%, angka 9
sekitar 4,6%, mengikuti P(d) = log10(1 + 1/d). Distribusi digit kedua dan pasangan dua
digit pertama juga punya bentuk baku. Penyimpangan dari bentuk itu menjadi alat skrining
forensik karena angka yang direkayasa manusia (misal dibuat "sepertinya acak" atau
dipenuhi angka bulat) sering meninggalkan jejak pada distribusi digit.

## 2. Apa yang dihitung

| Uji | Kategori | Catatan |
| --- | --- | --- |
| Digit pertama | 1 sampai 9 | Paling stabil untuk n sedang |
| Digit kedua | 0 sampai 9 | Nilai satu-digit tidak diikutkan |
| Dua digit pertama | 10 sampai 99 | Butuh n besar (ribuan) agar informatif |

Ukuran simpangan:

- **Chi-square** kebaikan fitung terhadap frekuensi Benford. Diabaikan jangan-jangan
  salah baca: pada n besar (puluhan ribu) chi-square nyaris selalu signifikan untuk
  simpangan sekecil apa pun. Angka ini dilaporkan tetapi tidak dijadikan dasar
  peringkat.
- **Mean Absolute Deviation (MAD)**, rata-rata selisih mutlak proporsi teramati dan
  Benford, dengan batas kesesuaian Nigrini (2012, Table 7.1):

| Kesesuaian | Digit pertama | Digit kedua | Dua digit pertama |
| --- | --- | --- | --- |
| Dekat | < 0,006 | < 0,0016 | < 0,0012 |
| Sesuai | < 0,012 | < 0,0030 | < 0,0018 |
| Marginal | < 0,015 | < 0,0040 | < 0,0022 |
| Tidak sesuai | di atas itu | di atas itu | di atas itu |

- **Jalur grafik Nigrini 95%** per digit: p ± 1,96 * sqrt(p(1-p)/n). Batang di luar
  jalur digambar merah bata dan menjadi kandidat pemeriksaan.
- **Interval kepercayaan MAD 95%** dari bootstrap resampling (default 500 kali, seed
  tetap 42 supaya hasil bisa direproduksi).
- **Porsi angka bulat** (nilai berakhiran minimal 2 atau 4 nol). Untuk data alami
  porsi akhiran 2 nol seharusnya sekitar 1%. Hanya dihitung untuk APBD karena nilai
  TKDD dibulatkan ke dua desimal dalam satuan Miliar.

## 3. Batasan data DJPK yang wajib diingat

1. **Agregat akun, bukan transaksi.** Data DJPK adalah postur akun per pemda (sekitar
   20 baris daun), bukan rekaman transaksi individual. Benford bekerja paling baik pada
   ribuan nilai transaksi. Simpangan pada agregat berarti "struktur anggarannya tidak
   mengikuti pola alami", bukan "ada transaksi palsu".
2. **Ukuran sampel per pemda kecil.** Dengan sekitar 20 nilai realisasi daun per pemda,
   MAD per pemda tidak stabil. Analisis yang bermakna: pool per provinsi (ratusan nilai),
   pool nasional (belasan ribu), atau pool per jenis akun lintas pemda (ratusan nilai).
   Alat ini menandai setiap kelompok dengan n < 100.
3. **Hitung ganda induk-anak.** Postur APBD bersarang: Pendapatan Daerah memuat PAD yang
   memuat Pajak Daerah. Pool tanpa penyaringan menghitung nilai yang sama berkali-kali.
   Secara default alat ini hanya memakai baris daun; opsi `--semualevel` ada untuk
   reproduksi dan memang menghasilkan simpangan artifisial.
4. **Duplikat ekspor portal.** File per-pemda kadang memuat baris yang terulang persis
   (contoh nyata: "Belanja Pegawai" dua kali dengan angka identik). Parser membuang
   baris duplikat berurutan.
5. **Pembulatan TKDD.** Nilai TKDD berformat "7.945,28 M": hanya lima sampai tujuh digit
   signifikan, dan nol di belakang tidak bermakna. Uji dua digit pertama dan uji angka
   bulat tidak informatif untuk TKDD.
6. **Pasangan anggaran-realisasi berkaitan.** Realisasi satu akun mendekati anggarannya,
   jadi menggabungkan keduanya dalam satu pool tidak menambah informasi independen.
   Alat ini menguji satu kolom nilai per analisis.
7. **Ambang pelaporan dan sisa.** Angka pendapatan transfer berasal dari alokasi pusat
   dengan rumus (bukan perilaku daerah), SiLPA sering jatuh pada angka bulat, dan banyak
   akun bernilai nol dibuang dari pool. Semuanya bisa menggeser distribusi tanpa
   ada yang "mencurigakan".

## 4. Kapan simpangan bermakna, kapan artefak

Periksa dulu daftar artefak sebelum menafsirkan simpangan:

- n < 100 pada kelompok: simpangan bisa murni kebetulan; lihat interval bootstrap, kalau
  rentangnya lebar, jangan menafsirkan.
- Sumber data dibulatkan (TKDD) atau nilai berunit besar (Miliar/Triliun) di TP DBH.
- Satu kelompok didominasi beberapa akun bernilai besar yang berkaitan (misal dua akun
  yang saling mengisi).
- Terdapat ambang administratif (misal alokasi minimal dana desa per desa yang sama).
- Simpangan pada digit kedua jauh lebih sering artefak pembulatan daripada digit pertama.

Simpangan lebih layak ditelusuri kalau: n besar, keluar pada lebih dari satu jenis digit,
konsisten antar tahun pada wilayah yang sama, dan disertai porsi angka bulat yang jauh di
atas normal. Satu baris merah pada satu grafik belum apa-apa.

## 5. Cara menyampaikan hasil

- Tulis "indikasi statistik yang layak diperiksa lebih lanjut", bukan "penyimpangan
  anggaran", "markas korupsi", atau sebutan pejabat dan wilayah.
- Sebutkan n, MAD, dan batas Nigrini di setiap klaim. Angka tanpa n menyesatkan.
- Tampilkan juga kelompok yang sesuai, bukan hanya yang menyimpang, supaya pembaca tidak
  mendapat kesan semua wilayah bermasalah.
- Simpangan Benford tidak pernah menjadi bukti kesalahan administratif, apalagi pidana.
  Alatnya untuk menentukan prioritas pemeriksaan oleh pihak yang berwenang.
- Rujuk kembali dokumen ini saat laporan dikutip di media atau media sosial.

## 6. Teknis ekstraksi digit

Digit diambil dari representasi float terpendek (`numpy.format_float_scientific`) alih-
alih dari log10, supaya kasus batas (misal x/10^k = 0,9999999) tidak salah digit. Nilai
nol dan non-finite dibuang; negatif diambil mutlaknya. Digit trailing zeros bukan digit
signifikan dan otomatis terpotong oleh representasi terpendek.

## 7. Referensi

- Nigrini, M. J. (2012). *Benford's Law: Applications for Forensic Accounting, Auditing,
  and Fraud Detection*. Wiley.
- Nigrini, M. J., & Miller, S. J. (2009). Data diagnostics using second-order tests of
  Benford's Law. *Auditing: A Journal of Practice & Theory*, 28(2).
- Durtschi, C., Hillison, W., & Pacini, C. (2004). The effective use of Benford's Law to
  assist in detecting fraud in accounting data. *Journal of Forensic Accounting*, 5.
