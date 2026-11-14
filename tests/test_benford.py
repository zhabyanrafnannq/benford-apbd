"""Uji modul benford: distribusi digit, chi-square, MAD, angka bulat."""

import numpy as np
import pytest

from benford_apbd.benford import (
    BENFORD_FIRST,
    conformity_label,
    digit_strings,
    digit_test,
    first_digits,
    mad_bootstrap_ci,
    round_number_stats,
)


def nilai_benford(n: int, seed: int = 7) -> np.ndarray:
    """Nilai dengan mantissa log-seragam: mengikuti Benford secara eksak di limit."""
    rng = np.random.default_rng(seed)
    return np.power(10.0, rng.uniform(0.0, 6.0, size=n))


def test_digit_pertama_mengikuti_benford():
    res = digit_test(nilai_benford(40_000), kind="first")
    assert res.n == 40_000
    assert res.mad < 0.006
    assert res.p_value > 0.05
    assert res.conformity in ("sesuai dekat", "sesuai")


def test_digit_pertama_seragam_tidak_sesuai():
    rng = np.random.default_rng(11)
    res = digit_test(rng.integers(100, 1000, size=40_000), kind="first")
    assert res.mad > 0.015
    assert res.conformity == "tidak sesuai"
    assert res.p_value < 1e-10


def test_digit_kedua_mengikuti_benford():
    res = digit_test(nilai_benford(50_000), kind="second")
    assert res.mad < 0.004
    assert res.categories == list(range(10))
    # digit kedua 0 paling sering, sesuai Benford
    assert res.observed.argmax() == 0


def test_digit_pertama_kedua_mengikuti_benford():
    res = digit_test(nilai_benford(50_000), kind="first_two")
    assert res.mad < 0.0022
    assert res.categories == list(range(10, 100))


def test_nilai_nol_negatif_dan_satudigit():
    assert digit_strings([0, -5.0, 100.0]) == ["5", "100"]
    assert list(first_digits([-7, 0])) == [7]
    with pytest.raises(ValueError):
        digit_test([5.0], kind="second")  # satu digit tidak punya digit kedua


def test_z_score_ekstrem_pada_nilai_seragam_satu_digit():
    res = digit_test([500_000.0] * 1000, kind="first")
    idx = res.categories.index(5)
    assert res.z_scores[idx] > 10  # jauh di luar jalur Nigrini 95%


def test_bootstrap_ci_mencakup_mad():
    digits = first_digits(nilai_benford(5_000))
    res = digit_test(nilai_benford(5_000), kind="first")
    lo, hi = mad_bootstrap_ci(digits, "first", n_boot=300, seed=3)
    assert lo <= res.mad <= hi


def test_label_kesesuaian_mengikuti_batas_nigrini():
    assert conformity_label("first", 0.005) == "sesuai dekat"
    assert conformity_label("first", 0.010) == "sesuai"
    assert conformity_label("first", 0.013) == "marginal"
    assert conformity_label("first", 0.020) == "tidak sesuai"


def test_proporsi_benford_jumlah_satu():
    from benford_apbd.benford import BENFORD_FIRST_TWO, BENFORD_SECOND

    assert abs(sum(BENFORD_FIRST.values()) - 1.0) < 1e-12
    assert abs(sum(BENFORD_SECOND.values()) - 1.0) < 1e-12
    assert abs(sum(BENFORD_FIRST_TWO.values()) - 1.0) < 1e-12


def test_statistik_angka_bulat():
    st = round_number_stats([200.0, 350.0, 471.0, 0])
    assert st["n"] == 3
    assert st["share_2_nol"] == pytest.approx(1 / 3)
    assert st["share_4_nol"] == 0.0
