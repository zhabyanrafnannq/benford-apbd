"""Grafik distribusi digit dan laporan markdown dengan framing hati-hati."""

import datetime as _dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .analyze import GROUP_KEYS, GROUP_LABEL, nilai_kelompok, pilih_sumber
from .benford import KIND_LABEL, digit_test

# Palet tunggu: abu netral untuk batang, tinta gelap untuk garis Benford,
# satu warna merah bata hanya untuk batang yang keluar batas Nigrini.
WARNA_BATANG = "#9aa0ab"
WARNA_TINTA = "#22252a"
WARNA_JALUR = "#d6d9de"
WARNA_SIMPANGAN = "#b3402e"

CATATAN_ETF = (
    "Perlu ditekankan: hasil uji Benford di laporan ini adalah indikasi statistik yang "
    "layak diperiksa lebih lanjut, bukan bukti penyimpangan. Simpangan digit dapat "
    "berasal dari pembulatan, ambang pelaporan, ukuran sampel kecil, atau struktur data "
    "agregat. Baca docs/METODOLOGI.md sebelum menarik kesimpulan apa pun."
)


def plot_digit(result, judul: str, path_png: Path | None = None):
    x = range(len(result.categories))
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    warna = [WARNA_SIMPANGAN if o > h or o < lo else WARNA_BATANG for o, lo, h in zip(result.observed, result.bounds_low, result.bounds_high)]
    ax.bar(x, result.observed, color=warna, width=0.62, label="proporsi teramati")
    ax.fill_between(x, result.bounds_low, result.bounds_high, color=WARNA_JALUR, label="jalur Nigrini 95%")
    ax.plot(x, result.expected, color=WARNA_TINTA, marker="o", markersize=3.5, linewidth=1.4, label="Benford")
    ax.set_xticks(list(x))
    if len(result.categories) > 12:
        # 90 kategori dua digit pertama tidak muat; label tiap kelipatan 5 saja
        ax.set_xticklabels([str(c) if c % 5 == 0 else "" for c in result.categories])
    else:
        ax.set_xticklabels([str(c) for c in result.categories])
    ax.set_xlabel(result.category_label.replace("digit pertama-kedua", "dua digit pertama"))
    ax.set_ylabel("proporsi")
    ax.set_title(f"{judul} (n={result.n}, MAD={result.mad:.4f}, {result.conformity})")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    if path_png is not None:
        fig.savefig(path_png, bbox_inches="tight")
    return fig


def _judul_kelompok(group: str, row: pd.Series) -> str:
    if group == "nasional":
        return "Nasional"
    if group == "per_akun":
        return f"{row['akun']}"
    if group == "per_pemda":
        return f"{row['nama_pemda']} ({row['nama_provinsi']})"
    return f"{row['nama_provinsi']}"


def _tabel_markdown(df: pd.DataFrame) -> str:
    """Tabel markdown tanpa bergantung pada tabulate.

    P-value kecil pakai format ilmiah supaya tidak tampil 0.0000, dan NaN
    (misal kolom angka bulat pada TKDD) tampil sebagai garis, bukan nan.
    """
    cols = list(df.columns)
    def fmt(v):
        if isinstance(v, float):
            if np.isnan(v):
                return "-"
            if v != 0 and abs(v) < 1e-4:
                return f"{v:.2e}"
            return f"{v:.4f}"
        return str(v)
    rows = [[fmt(v) for v in df[c]] for c in cols]
    head = "| " + " | ".join(cols) + " |"
    pemisah = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in zip(*rows)) if rows else ""
    return f"{head}\n{pemisah}\n{body}"


def generate_report(
    tidy: pd.DataFrame,
    hasil: pd.DataFrame,
    dataset: str,
    tahun: int,
    periode: int | None,
    group: str,
    kolom: str,
    kind: str,
    out_dir: Path,
    top: int = 3,
    hanya_daun: bool = True,
    sumber_level: str | None = "auto",
) -> Path:
    """Susun laporan markdown plus grafik PNG untuk kelompok paling menyimpang."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sekarang = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    sumber = "Portal Data DJPK Kemenkeu (djpk.kemenkeu.go.id, data kirim SIKD)"
    periode_txt = f"periode {periode}" if periode else "tanpa periode bulanan"
    judul_level = GROUP_LABEL.get(group, group)
    if "sumber_level" in tidy.columns:
        level_pakai = pilih_sumber(tidy, sumber_level)["sumber_level"].iloc[0]
    else:
        level_pakai = "tidak bertanda"
    tidy = pilih_sumber(tidy, sumber_level)

    lines = [
        f"# Laporan uji Benford: {dataset.upper()} {tahun} ({periode_txt})",
        "",
        f"Dibuat: {sekarang} | Sumber data: {sumber}",
        f"Kelompok: {judul_level} | Nilai yang diuji: {kolom} | Uji: {KIND_LABEL[kind]}",
        f"Tingkat file yang dipakai: {level_pakai} (agregat tingkat lain dikecualikan agar tidak dobel hitung)",
        "",
        "## Ringkasan metode",
        "",
        (
            "Distribusi digit pertama (dan kedua) nilai uang yang beredar secara alami cenderung "
            "mengikuti Hukum Benford. Setiap kelompok diuji dengan chi-square dan Mean Absolute "
            "Deviation (MAD) terhadap proporsi Benford, dengan jalur kesalahan grafik Nigrini 95% "
            "dan interval kepercayaan MAD dari 500 kali resampling bootstrap. Baris induk postur "
            "dikeluarkan dari pool agar tidak dihitung ganda dengan baris anak."
        ),
        "",
        "## Peringkat simpangan",
        "",
        _tabel_markdown(hasil),
        "",
        "## Grafik kelompok paling menyimpang",
        "",
    ]

    top_rows = hasil.head(top)
    for i, (_, row) in enumerate(top_rows.iterrows(), start=1):
        keys = GROUP_KEYS[group]
        key = {k: row[k] for k in keys}
        judul = _judul_kelompok(group, row)
        values = nilai_kelompok(tidy, group, key, kolom=kolom, hanya_daun=hanya_daun, sumber=None)
        try:
            res = digit_test(values, kind=kind)
        except ValueError:
            continue
        nama_png = f"digit_top{i}.png"
        plot_digit(res, judul, out_dir / nama_png)
        z = res.z_scores
        idx_terbesar = int(np.abs(z).argmax())
        kategori = res.categories[idx_terbesar]
        lines += [
            f"### {i}. {judul}",
            "",
            f"![{judul}]({nama_png})",
            "",
            (
                f"MAD {res.mad:.4f} ({res.conformity}), chi-square {res.chi2:.2f} (df {res.df}, "
                f"p={res.p_value:.2g}), n={res.n}. Kategori digit paling menyimpang: "
                f"{kategori} (z={z[idx_terbesar]:.2f})."
            ),
            "",
        ]

    lines += ["## Interpretasi", "", CATATAN_ETF, ""]
    jalur = out_dir / "laporan.md"
    jalur.write_text("\n".join(lines), encoding="utf-8")
    return jalur
