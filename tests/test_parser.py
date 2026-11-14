"""Uji parser SpreadsheetML DJPK dan normalisasi tabel rapi."""

import json

import pytest

from benford_apbd.djpk import (
    DjpkError,
    load_tidy,
    normalize_rows,
    parse_formatted_number,
    parse_spreadsheetml,
)

XML_APBD = """<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="Data APBD"><Table>
<Row><Cell><Data ss:Type="String">Akun</Data></Cell><Cell><Data ss:Type="String">Anggaran</Data></Cell><Cell><Data ss:Type="String">Realisasi</Data></Cell><Cell><Data ss:Type="String">Persentase</Data></Cell></Row>
<Row><Cell><Data ss:Type="String"> Pendapatan Daerah</Data></Cell><Cell><Data ss:Type="Number">2.330604028000E+12</Data></Cell><Cell><Data ss:Type="Number">1972902565890</Data></Cell><Cell><Data ss:Type="String">84.65</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">  PAD</Data></Cell><Cell><Data ss:Type="Number">409754026000</Data></Cell><Cell><Data ss:Type="Number">324463893387</Data></Cell><Cell><Data ss:Type="String">79.19</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">  PAD</Data></Cell><Cell><Data ss:Type="Number">409754026000</Data></Cell><Cell><Data ss:Type="Number">324463893387</Data></Cell><Cell><Data ss:Type="String">79.19</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">   Pajak Daerah</Data></Cell><Cell><Data ss:Type="Number">157788470000</Data></Cell><Cell><Data ss:Type="Number">124104479401</Data></Cell><Cell><Data ss:Type="String">78.65</Data></Cell></Row>
<Row><Cell><Data ss:Type="String"> Belanja Bunga</Data></Cell><Cell><Data ss:Type="Number">116000000</Data></Cell><Cell><Data ss:Type="Number">0</Data></Cell><Cell><Data ss:Type="String">0.00</Data></Cell></Row>
</Table></Worksheet></Workbook>
"""

XML_TKDD = """<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
<Worksheet ss:Name="Data TKDD"><Table>
<Row><Cell><Data ss:Type="String">Akun</Data></Cell><Cell><Data ss:Type="String">Anggaran</Data></Cell><Cell><Data ss:Type="String">Realisasi</Data></Cell><Cell><Data ss:Type="String">Persentase</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">TRANSFER KE DAERAH</Data></Cell><Cell><Data ss:Type="String">62.480,25 M</Data></Cell><Cell><Data ss:Type="String">61.803,21 M</Data></Cell><Cell><Data ss:Type="String">98.92</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">     DANA DESA</Data></Cell><Cell><Data ss:Type="String">7.945,28 M</Data></Cell><Cell><Data ss:Type="String">7.345,91 M</Data></Cell><Cell><Data ss:Type="String">92.46</Data></Cell></Row>
<Row><Cell><Data ss:Type="String">         Dana Desa</Data></Cell><Cell><Data ss:Type="String">7.945,28 M</Data></Cell><Cell><Data ss:Type="String">7.345,91 M</Data></Cell><Cell><Data ss:Type="String">92.46</Data></Cell></Row>
</Table></Worksheet></Workbook>
"""


def tulis_xml(tmp_path, nama, isi):
    f = tmp_path / nama
    f.write_text(isi, encoding="utf-8")
    return f


def test_angka_berformat_indonesia():
    assert parse_formatted_number("62.480,25 M") == pytest.approx(62_480.25e9)
    assert parse_formatted_number("1,50 T") == pytest.approx(1.5e12)
    assert parse_formatted_number("2.330604028000E+12") == pytest.approx(2_330_604_028_000)
    assert parse_formatted_number("-") is None
    assert parse_formatted_number("") is None


def test_akar_postur_bukan_daun():
    from benford_apbd.djpk import AccountRow, _annotate_flat_apbd

    rows = [
        AccountRow("Pendapatan Daerah", 1, 1e12, 9e11, None),
        AccountRow("PAD", 1, 4e11, 3e11, None),
        AccountRow("Pajak Daerah", 1, 1e11, 9e10, None),
    ]
    hasil = _annotate_flat_apbd(rows)
    assert [leaf for _, _, leaf in hasil] == [False, False, True]


def test_parse_spreadsheetml_dan_dedup(tmp_path):
    rows = parse_spreadsheetml(tulis_xml(tmp_path, "x.xml", XML_APBD))
    assert len(rows) == 5  # header dibuang, baris duplikat masih ada di tahap parse
    recs = normalize_rows(rows, "apbd")
    labels = [r["akun"] for r in recs]
    assert labels.count("PAD") == 1  # dedup baris ekspor yang terulang
    by_label = {r["akun"]: r for r in recs}
    assert by_label["Pendapatan Daerah"]["is_leaf"] is False
    assert by_label["PAD"]["is_leaf"] is False
    assert by_label["Pajak Daerah"]["is_leaf"] is True
    assert by_label["Pajak Daerah"]["akun_path"].startswith("Pendapatan Daerah > PAD >")
    assert by_label["Belanja Bunga"]["anggaran"] == 116000000
    assert by_label["Belanja Bunga"]["realisasi"] == 0


def test_parser_tkdd_indentasi(tmp_path):
    rows = parse_spreadsheetml(tulis_xml(tmp_path, "t.xml", XML_TKDD))
    recs = normalize_rows(rows, "tkdd")
    daun = [r for r in recs if r["is_leaf"]]
    assert len(daun) == 1
    assert daun[0]["akun"] == "Dana Desa"
    assert daun[0]["realisasi"] == pytest.approx(7_345.91e9)
    assert "TRANSFER KE DAERAH" in daun[0]["akun_path"]


def test_load_tidy_dari_cache_sintetis(tmp_path):
    adir = tmp_path / "apbd" / "2025"
    adir.mkdir(parents=True)
    (adir / "p12_prov11_pemda01.xml").write_text(XML_APBD, encoding="utf-8")
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "provinsi_2025.json").write_text(json.dumps({"11": "Provinsi Jawa Tengah"}), encoding="utf-8")
    (ref / "pemda_11_2025.json").write_text(json.dumps({"01": "Kab. Banjarnegara"}), encoding="utf-8")
    df = load_tidy(tmp_path, "apbd", 2025, 12)
    assert len(df) == 4
    assert set(df.columns) >= {"akun", "is_leaf", "anggaran", "realisasi", "nama_pemda", "periode"}
    assert (df["nama_pemda"] == "Kab. Banjarnegara").all()
    assert (df["periode"] == 12).all()


def test_load_tidy_tanpa_cache_mengangkat_error(tmp_path):
    with pytest.raises(DjpkError):
        load_tidy(tmp_path, "apbd", 1999, 12)
