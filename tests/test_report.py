"""Uji laporan: tabel markdown tanpa angka menyesatkan."""

import numpy as np
import pandas as pd

from benford_apbd.report import _tabel_markdown


def test_p_value_kecil_pakai_format_ilmiah():
    df = pd.DataFrame([{"nama": "kasus", "p_value": 2.213695e-07}])
    tabel = _tabel_markdown(df)
    assert "2.21e-07" in tabel
    assert "0.0000" not in tabel


def test_nan_tampil_sebagai_garis():
    df = pd.DataFrame([{"nama": "tkdd", "share_2_nol": np.nan, "mad": 0.05}])
    tabel = _tabel_markdown(df)
    assert "nan" not in tabel
    assert "-" in tabel.split("\n")[2]


def test_angka_biasa_tetap_empat_desimal():
    df = pd.DataFrame([{"nama": "kasus", "mad": 0.0158, "n": 594}])
    tabel = _tabel_markdown(df)
    assert "0.0158" in tabel
    assert "594" in tabel
