# Kebijakan keamanan

## Cakupan

benford-apbd adalah alat analisis data publik. Ia tidak memproses data pribadi, tidak
menyimpan kredensial, dan tidak menjalankan kode dari sumber data (file DJPK hanya
diparse sebagai XML, tidak pernah dieksekusi).

Laporkan di sini jika Anda menemukan:

- kode yang mengeksekusi konten dari file data atau respons server,
- kebocoran jalur sistem pada CLI atau dashboard (misal penulisan file di luar folder
  proyek),
- permintaan jaringan yang tidak terduga ke selain djpk.kemenkeu.go.id.

## Cara melaporkan

Buka GitHub Security Advisory pada tab Security repo ini, atau hubungi pengelola lewat
kontak yang tercantum di CODE_OF_CONDUCT.md. Mohon sertakan langkah reproduksi. Laporan
dijawab dalam hitungan hari, dan perbaikan dirilis lewat CHANGELOG.md.

## Yang bukan cakupan

Pertanyaan penggunaan dan hasil analisis sebaiknya masuk issue biasa, bukan laporan
keamanan.
