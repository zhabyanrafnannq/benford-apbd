"""Pooling nilai per kelompok, uji digit, peringkat simpangan dengan interval bootstrap."""

import numpy as np
import pandas as pd

from .benford import EXTRACTORS, digit_test, mad_bootstrap_ci, round_number_stats

GROUP_KEYS = {
    "nasional": [],
    "per_provinsi": ["kode_provinsi", "nama_provinsi"],
    "per_pemda": ["kode_provinsi", "nama_provinsi", "kode_pemda", "nama_pemda"],
    "per_akun": ["akun"],
}

GROUP_LABEL = {
    "nasional": "Nasional",
    "per_provinsi": "Per provinsi",
    "per_pemda": "Per pemda",
    "per_akun": "Per jenis akun",
}


def pilih_sumber(tidy: pd.DataFrame, sumber: str | None = None) -> pd.DataFrame:
    """Saring tingkat sumber file (nasional/provinsi/pemda).

    'auto' memilih tingkat paling rinci yang tersedia supaya agregat provinsi
    tidak ikut terhitung bersama detail pemda yang lebih banyak.
    """
    if "sumber_level" not in tidy.columns:
        return tidy
    if sumber is None or sumber == "auto":
        for level in ("pemda", "provinsi", "nasional"):
            if (tidy["sumber_level"] == level).any():
                sumber = level
                break
        else:
            return tidy
    if sumber not in ("nasional", "provinsi", "pemda"):
        raise ValueError(f"tingkat sumber tidak dikenal: {sumber}")
    return tidy[tidy["sumber_level"] == sumber]


def run_analysis(
    tidy: pd.DataFrame,
    group: str = "per_provinsi",
    kolom: str = "realisasi",
    kind: str = "first",
    n_boot: int = 500,
    seed: int = 42,
    hanya_daun: bool = True,
    sumber: str | None = "auto",
) -> pd.DataFrame:
    """Uji digit untuk setiap kelompok, urut dari simpangan (MAD) terbesar.

    Kolom nilai bisa 'realisasi' atau 'anggaran'. Secara default hanya baris
    daun postur yang dipakai supaya nilai induk dan anak tidak dihitung dua
    kali. Ingat: pasangan anggaran-realisasi pada akun yang sama saling
    berkaitan, jadi menggabungkan keduanya tidak menambah independensi.
    """
    if group not in GROUP_KEYS:
        raise ValueError(f"kelompok tidak dikenal: {group}")
    if kolom not in ("anggaran", "realisasi"):
        raise ValueError(f"kolom nilai tidak dikenal: {kolom}")
    tidy = pilih_sumber(tidy, sumber)
    df = tidy[tidy["is_leaf"]] if hanya_daun else tidy
    df = df[df[kolom].notna() & (df[kolom] > 0)]
    keys = GROUP_KEYS[group]
    is_apbd = bool((df["dataset"] == "apbd").all())
    hasil = []
    if keys:
        iterator = df.groupby(keys, sort=True, dropna=False)
    else:
        iterator = [("<semua>", df)]
    for key, sub in iterator:
        if not isinstance(key, tuple):
            key = (key,)
        values = sub[kolom].to_numpy(dtype=float)
        if len(values) < 5:
            continue
        try:
            res = digit_test(values, kind=kind)
        except ValueError:
            continue
        digits = EXTRACTORS[kind](values)
        mad_lo, mad_hi = mad_bootstrap_ci(digits, kind, n_boot=n_boot, seed=seed)
        catatan = []
        if res.n < 100:
            catatan.append("n < 100, MAD tidak stabil")
        bulat = round_number_stats(values) if is_apbd else {"share_2_nol": np.nan, "share_4_nol": np.nan}
        if not is_apbd:
            catatan.append("tkdd dibulatkan dalam Miliar, angka bulat tidak diuji")
        hasil.append(
            {
                **dict(zip(keys, key if isinstance(key, tuple) else (key,))),
                "n": res.n,
                "mad": res.mad,
                "mad_ci95_bawah": mad_lo,
                "mad_ci95_atas": mad_hi,
                "kesesuaian": res.conformity,
                "chi2": round(res.chi2, 3),
                "df": res.df,
                "p_value": res.p_value,
                "share_2_nol": bulat["share_2_nol"],
                "share_4_nol": bulat["share_4_nol"],
                "catatan": "; ".join(catatan),
            }
        )
    if not hasil:
        raise ValueError("tidak ada kelompok dengan cukup nilai positif untuk diuji")
    out = pd.DataFrame(hasil)
    return out.sort_values("mad", ascending=False).reset_index(drop=True)


def nama_analisis(dataset: str, tahun: int, periode: int | None, group: str, kolom: str, kind: str, hanya_daun: bool) -> str:
    parts = [dataset, str(tahun)]
    if periode is not None:
        parts.append(f"p{periode:02d}")
    parts += [group, kolom, kind]
    if not hanya_daun:
        parts.append("semualevel")
    return "_".join(parts)


def nilai_kelompok(
    tidy: pd.DataFrame, group: str, key: dict, kolom: str = "realisasi", hanya_daun: bool = True, sumber: str | None = "auto"
) -> np.ndarray:
    """Nilai satu kelompok tertentu, untuk grafik dan laporan turunan."""
    tidy = pilih_sumber(tidy, sumber)
    df = tidy[tidy["is_leaf"]] if hanya_daun else tidy
    mask = df[kolom].notna() & (df[kolom] > 0)
    for kol, val in key.items():
        mask &= df[kol] == val
    return df.loc[mask, kolom].to_numpy(dtype=float)
