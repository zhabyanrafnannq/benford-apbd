"""Uji CLI: validasi periode dan pesan galat yang ramah tanpa traceback."""

import pytest

from benford_apbd.cli import main


def test_analyze_apbd_tanpa_periode_ditolak_lewat_pesan(capsys):
    kode = main(["analyze", "--dataset", "apbd", "--tahun", "2025"])
    assert kode == 2
    assert "wajib menyebut --periode" in capsys.readouterr().err


def test_periode_di_luar_rentang_ditolak_tanpa_jaringan(capsys):
    kode = main(["fetch", "apbd", "--tahun", "2025", "--periode", "13"])
    assert kode == 2
    assert "--periode harus 1 sampai 12" in capsys.readouterr().err


def test_cache_kosong_menghasilkan_pesan_bukan_traceback(capsys, tmp_path):
    kode = main(["analyze", "--dataset", "tkdd", "--tahun", "1999", "--cache", str(tmp_path)])
    assert kode == 2
    err = capsys.readouterr().err
    assert "tidak ada file cache" in err
    assert "Traceback" not in err


def test_analyze_kolom_tidak_valid_pesan_ramah(capsys, tmp_path):
    with pytest.raises(SystemExit):
        main(["analyze", "--dataset", "tkdd", "--tahun", "1999", "--kolom", "persen", "--cache", str(tmp_path)])
