"""Uji pipeline analisis: pooling, peringkat, dan aturan kolom."""

import numpy as np
import pandas as pd
import pytest

from benford_apbd.analyze import nama_analisis, nilai_kelompok, run_analysis


def buat_tidy(n_benford=1500, n_devian=1500, seed=5):
    rng = np.random.default_rng(seed)
    benford = np.power(10.0, rng.uniform(0.0, 9.0, size=n_benford))
    devian = rng.uniform(3e8, 9e8, size=n_devian)  # digit pertama 3 sampai 9 saja
    recs = []
    for v in benford:
        recs.append(("01", "Provinsi A", "0101", "Kab. Sehat", "Belanja Barang dan Jasa", True, float(v)))
    for v in devian:
        recs.append(("02", "Provinsi B", "0201", "Kab. Devian", "Belanja Barang dan Jasa", True, float(v)))
    return pd.DataFrame(
        recs,
        columns=["kode_provinsi", "nama_provinsi", "kode_pemda", "nama_pemda", "akun", "is_leaf", "realisasi"],
    ).assign(
        dataset="apbd",
        tahun=2025,
        periode=12,
        anggaran=np.nan,
        akun_path="x > Belanja Barang dan Jasa",
        sumber_level="pemda",
    )


def test_peringkat_menempatkan_kelompok_menyimpang_di_atas():
    hasil = run_analysis(buat_tidy(), group="per_pemda", n_boot=200)
    assert list(hasil["nama_pemda"]) == ["Kab. Devian", "Kab. Sehat"]
    atas, bawah = hasil.iloc[0], hasil.iloc[1]
    assert atas["kesesuaian"] == "tidak sesuai"
    assert bawah["kesesuaian"] in ("sesuai dekat", "sesuai")
    assert atas["mad_ci95_bawah"] <= atas["mad"] <= atas["mad_ci95_atas"]
    assert (hasil["n"] == 1500).all()


def test_baris_induk_tidak_masuk_pool():
    tidy = buat_tidy()
    induk = pd.DataFrame(
        [("02", "Provinsi B", "0201", "Kab. Devian", "Belanja Daerah", False, 1e12)],
        columns=["kode_provinsi", "nama_provinsi", "kode_pemda", "nama_pemda", "akun", "is_leaf", "realisasi"],
    ).assign(dataset="apbd", tahun=2025, periode=12, anggaran=np.nan, akun_path="Belanja Daerah", sumber_level="pemda")
    tidy = pd.concat([tidy, induk], ignore_index=True)
    hasil = run_analysis(tidy, group="per_pemda", n_boot=100)
    assert (hasil["n"] == 1500).all()  # baris induk tidak menambah n


def test_sumber_agregat_tidak_dicampur_dengan_detail_pemda():
    tidy = buat_tidy()
    agregat = tidy.head(100).copy()
    agregat["kode_pemda"] = "--"
    agregat["sumber_level"] = "provinsi"
    campur = pd.concat([tidy, agregat], ignore_index=True)
    hasil = run_analysis(campur, group="per_pemda", n_boot=100)
    assert (hasil["n"] == 1500).all()  # file agregat provinsi otomatis dikecualikan
    with pytest.raises(ValueError):
        run_analysis(tidy, group="per_pemda", sumber="provinsi", n_boot=100)  # tidak ada file level provinsi


def test_group_nasional_dan_per_akun():
    tidy = buat_tidy(n_benford=300, n_devian=300)
    nas = run_analysis(tidy, group="nasional", n_boot=100)
    assert len(nas) == 1 and nas.iloc[0]["n"] == 600
    akun = run_analysis(tidy, group="per_akun", n_boot=100)
    assert len(akun) == 1 and akun.iloc[0]["akun"] == "Belanja Barang dan Jasa"


def test_parameter_tidak_valid_ditolak():
    with pytest.raises(ValueError):
        run_analysis(buat_tidy(), group="per_kelurahan")
    with pytest.raises(ValueError):
        run_analysis(buat_tidy(), kolom="persen")


def test_nilai_kelompok_dan_nama_analisis():
    tidy = buat_tidy()
    vals = nilai_kelompok(tidy, "per_pemda", {"kode_pemda": "0201"})
    assert len(vals) == 1500
    nama = nama_analisis("apbd", 2025, 12, "per_provinsi", "realisasi", "first", True)
    assert nama == "apbd_2025_p12_per_provinsi_realisasi_first"
    nama2 = nama_analisis("tkdd", 2025, None, "nasional", "realisasi", "first", False)
    assert nama2 == "tkdd_2025_nasional_realisasi_first_semualevel"
