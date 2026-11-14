"""Uji distribusi digit (Benford) atas sekumpulan nilai uang, murni numpy + scipy."""

from dataclasses import dataclass

import numpy as np
from scipy import stats

# P(digit pertama = d) = log10(1 + 1/d), Nigrini 2012.
BENFORD_FIRST = {d: float(np.log10(1.0 + 1.0 / d)) for d in range(1, 10)}


def _second_digit_probs() -> dict[int, float]:
    probs = dict.fromkeys(range(10), 0.0)
    for m in range(10, 100):
        probs[m % 10] += np.log10(1.0 + 1.0 / m)
    return probs


def _first_two_probs() -> dict[int, float]:
    return {m: float(np.log10(1.0 + 1.0 / m)) for m in range(10, 100)}


BENFORD_SECOND = _second_digit_probs()
BENFORD_FIRST_TWO = _first_two_probs()

EXPECTED = {
    "first": BENFORD_FIRST,
    "second": BENFORD_SECOND,
    "first_two": BENFORD_FIRST_TWO,
}

# Batas MAD kesesuaian menurut Nigrini (2012, Table 7.1).
MAD_BANDS = {
    "first": (0.006, 0.012, 0.015),
    "second": (0.0016, 0.0030, 0.0040),
    "first_two": (0.0012, 0.0018, 0.0022),
}
CONFORMITY_LABELS = ("sesuai dekat", "sesuai", "marginal", "tidak sesuai")

KIND_LABEL = {
    "first": "digit pertama",
    "second": "digit kedua",
    "first_two": "digit pertama-kedua",
}


def conformity_label(kind: str, mad: float) -> str:
    """Terjemahkan MAD ke label kesesuaian sesuai batas Nigrini."""
    b1, b2, b3 = MAD_BANDS[kind]
    if mad < b1:
        return CONFORMITY_LABELS[0]
    if mad < b2:
        return CONFORMITY_LABELS[1]
    if mad < b3:
        return CONFORMITY_LABELS[2]
    return CONFORMITY_LABELS[3]


def digit_strings(values) -> list[str]:
    """Rangkaian digit per nilai positif, apa adanya seperti tercatat.

    Nilai bulat (dataset APBD berupa Rupiah bulat) dipakai sebagai integer utuh
    supaya angka bulat seperti 100.000.000 tidak terpotong jadi "1" dan justru
    hilang dari uji digit kedua. Nilai pecahan memakai representasi float
    terpendek, yang sekaligus memangkas derau presisi pada nilai TKDD hasil
    skala Miliar. Penentuan digit tidak memakai log10 agar kasus batas
    (mis. x/10^k = 0,9999999) tidak salah digit.
    """
    out = []
    for v in values:
        x = float(v)
        if not np.isfinite(x) or x == 0.0:
            continue
        a = abs(x)
        if a.is_integer():
            out.append(str(int(a)))
        else:
            mant = np.format_float_scientific(a, unique=True, trim="-").split("e")[0].replace(".", "")
            if mant:
                out.append(mant)
    return out


def _digits_of(values, take) -> np.ndarray:
    out = []
    for s in digit_strings(values):
        if len(s) >= take[1] + 1:
            out.append(int(s[take[0] : take[1] + 1]))
    return np.array(out, dtype=int)


def first_digits(values) -> np.ndarray:
    """Digit signifikan pertama, 1 sampai 9."""
    return _digits_of(values, (0, 0))


def second_digits(values) -> np.ndarray:
    """Digit signifikan kedua, 0 sampai 9. Nilai satu digit tidak dihitung."""
    return _digits_of(values, (1, 1))


def first_two_digits(values) -> np.ndarray:
    """Dua digit signifikan pertama, 10 sampai 99."""
    return _digits_of(values, (0, 1))


EXTRACTORS = {
    "first": first_digits,
    "second": second_digits,
    "first_two": first_two_digits,
}


@dataclass
class DigitResult:
    kind: str
    n: int
    categories: list[int]
    observed: np.ndarray  # proporsi teramati per kategori
    expected: np.ndarray  # proporsi Benford per kategori
    chi2: float
    df: int
    p_value: float
    mad: float
    conformity: str
    z_scores: np.ndarray
    bounds_low: np.ndarray  # batas grafik Nigrini: p ± 1.96 * sqrt(p(1-p)/n)
    bounds_high: np.ndarray

    @property
    def category_label(self) -> str:
        return KIND_LABEL[self.kind]


def digit_test(values, kind: str = "first") -> DigitResult:
    """Uji kesesuaian satu jenis digit terhadap distribusi Benford.

    Chi-square dilaporkan apa adanya, tetapi pada n besar chi-square nyaris
    selalu signifikan untuk simpangan sekecil apa pun; MAD yang jadi patokan
    kesesuaian. Lihat docs/METODOLOGI.md.
    """
    if kind not in EXTRACTORS:
        raise ValueError(f"jenis digit tidak dikenal: {kind}")
    digits = EXTRACTORS[kind](values)
    cats = sorted(EXPECTED[kind])
    n = len(digits)
    if n == 0:
        raise ValueError("tidak ada nilai positif yang bisa diuji")
    counts = np.bincount(digits - min(cats), minlength=len(cats))[: len(cats)]
    props = counts / n
    probs = np.array([EXPECTED[kind][c] for c in cats])
    expected_counts = n * probs
    chi2 = float(((counts - expected_counts) ** 2 / expected_counts).sum())
    df = len(cats) - 1
    p_value = float(stats.chi2.sf(chi2, df))
    mad = float(np.abs(props - probs).mean())
    se = np.sqrt(probs * (1.0 - probs) / n)
    z = (props - probs) / se
    return DigitResult(
        kind=kind,
        n=n,
        categories=cats,
        observed=props,
        expected=probs,
        chi2=chi2,
        df=df,
        p_value=p_value,
        mad=mad,
        conformity=conformity_label(kind, mad),
        z_scores=z,
        bounds_low=probs - 1.96 * se,
        bounds_high=probs + 1.96 * se,
    )


def mad_bootstrap_ci(digits: np.ndarray, kind: str, n_boot: int = 500, seed: int = 42):
    """Interval kepercayaan MAD lewat resampling digit yang sudah diekstrak.

    Digit diekstrak sekali di luar fungsi ini supaya bootstrap tidak mengulang
    konversi string yang mahal.
    """
    cats = sorted(EXPECTED[kind])
    probs = np.array([EXPECTED[kind][c] for c in cats])
    offset = min(cats)
    rng = np.random.default_rng(seed)
    n = len(digits)
    mads = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        counts = np.bincount(digits[idx] - offset, minlength=len(cats))[: len(cats)]
        mads[i] = np.abs(counts / n - probs).mean()
    return float(np.quantile(mads, 0.025)), float(np.quantile(mads, 0.975))


def round_number_stats(values) -> dict[str, float]:
    """Cek artefak angka bulat dari jumlah nol di belakang angka bulat.

    Hanya bermakna untuk angka mentah berpresisi penuh (dataset APBD). Data
    TKDD dibulatkan ke dua desimal dalam satuan Miliar, jadi nol di belakang
    tidak mencerminkan nilai aslinya.
    """
    trailing = []
    for v in values:
        x = float(v)
        if not np.isfinite(x) or x <= 0:
            continue
        s = str(int(abs(x)))
        trailing.append(len(s) - len(s.rstrip("0")))
    if not trailing:
        return {"n": 0, "share_2_nol": np.nan, "share_4_nol": np.nan}
    t = np.array(trailing)
    n = len(t)
    return {
        "n": n,
        "share_2_nol": float((t >= 2).mean()),
        "share_4_nol": float((t >= 4).mean()),
    }
