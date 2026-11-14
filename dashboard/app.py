"""Dashboard Benford APBD. Jalankan: streamlit run dashboard/app.py"""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from benford_apbd.analyze import GROUP_LABEL, GROUP_KEYS, nilai_kelompok, pilih_sumber, run_analysis  # noqa: E402
from benford_apbd.benford import KIND_LABEL, digit_test  # noqa: E402
from benford_apbd.djpk import cached_selections, load_tidy  # noqa: E402
from benford_apbd.report import plot_digit  # noqa: E402

st.set_page_config(page_title="Benford APBD", page_icon=None, layout="wide")

st.title("Benford APBD")
st.caption(
    "Uji distribusi digit atas data APBD dan dana desa dari Portal Data DJPK Kemenkeu. "
    "Angka di sini adalah indikasi statistik untuk menentukan prioritas pemeriksaan, bukan tuduhan penyimpangan."
)

CACHE = ROOT / "data"
pilihan = cached_selections(CACHE)

if not pilihan:
    st.info(
        "Cache masih kosong, jadi belum ada yang bisa dianalisis. Unduh data dulu dari CLI, contoh:\n\n"
        "`benford-apbd fetch apbd --tahun 2025 --periode 12 --scope provinsi`\n\n"
        "atau untuk dana desa (komponen TKDD):\n\n"
        "`benford-apbd fetch tkdd --tahun 2025 --scope provinsi`"
    )
    st.stop()

dataset_pilihan = sorted({p["dataset"] for p in pilihan})
with st.sidebar:
    st.header("Parameter analisis")
    dataset = st.selectbox("Dataset", dataset_pilihan)
    tahun_pilihan = sorted({p["tahun"] for p in pilihan if p["dataset"] == dataset}, reverse=True)
    tahun = st.selectbox("Tahun", tahun_pilihan)
    periode_pilihan = sorted({p["periode"] for p in pilihan if p["dataset"] == dataset and p["tahun"] == tahun})
    periode = st.selectbox("Periode", periode_pilihan) if dataset == "apbd" else None
    group = st.selectbox("Kelompok", list(GROUP_KEYS), format_func=lambda g: GROUP_LABEL[g])
    kolom = st.selectbox("Nilai yang diuji", ["realisasi", "anggaran"])
    kind = st.selectbox("Jenis digit", ["first", "second", "first_two"], format_func=lambda k: KIND_LABEL[k])
    sumber_pilihan = ["auto", "pemda", "provinsi", "nasional"]
    sumber = st.selectbox("Tingkat file", sumber_pilihan, help="auto memilih tingkat paling rinci yang ada di cache")
    hanya_daun = st.checkbox("Hanya baris daun postur (hindari hitung ganda)", value=True)


@st.cache_data(show_spinner=False)
def muat_tidy(cache: str, dataset: str, tahun: int, periode):
    return load_tidy(Path(cache), dataset, tahun, periode)


@st.cache_data(show_spinner=False)
def jalankan_analisis(cache: str, dataset: str, tahun: int, periode, group: str, kolom: str, kind: str, hanya_daun: bool, sumber: str):
    tidy = muat_tidy(cache, dataset, tahun, periode)
    hasil = run_analysis(tidy, group=group, kolom=kolom, kind=kind, hanya_daun=hanya_daun, sumber=sumber)
    return tidy, hasil


try:
    with st.spinner("Menganalisis data cache..."):
        tidy, hasil = jalankan_analisis(str(CACHE), dataset, tahun, periode, group, kolom, kind, hanya_daun, sumber)
except Exception as err:
    st.error(f"Analisis gagal: {err}")
    st.stop()

level_pakai = pilih_sumber(tidy, sumber)["sumber_level"].iloc[0] if "sumber_level" in tidy.columns else None
st.subheader(GROUP_LABEL[group])
if level_pakai:
    st.caption(f"Tingkat file yang dipakai: {level_pakai}; agregat tingkat lain dikecualikan agar tidak dobel hitung.")
st.dataframe(hasil, use_container_width=True, hide_index=True)

keys = GROUP_KEYS[group]
label_baris = []
for _, row in hasil.iterrows():
    label_baris.append(" - ".join(str(row[k]) for k in keys) if keys else "Nasional")

if label_baris:
    terpilih = st.selectbox("Lihat grafik untuk", label_baris, index=0)
    idx = label_baris.index(terpilih)
    row = hasil.iloc[idx]
    key = {k: row[k] for k in keys}
    values = nilai_kelompok(tidy, group, key, kolom=kolom, hanya_daun=hanya_daun, sumber=sumber)
    res = digit_test(values, kind=kind)
    fig = plot_digit(res, GROUP_LABEL[group])
    st.pyplot(fig, use_container_width=True)
    z_terbesar = int(abs(res.z_scores).argmax())
    st.markdown(
        f"Kategori digit paling menyimpang: **{res.categories[z_terbesar]}** "
        f"(z = {res.z_scores[z_terbesar]:.2f}). "
        f"Batang merah keluar dari jalur kesalahan Nigrini 95%, yaitu kandidat nilai untuk diperiksa lebih lanjut. "
        f"Interpretasi lengkap dan batasan metode ada di `docs/METODOLOGI.md`."
    )
else:
    st.warning("Tidak ada kelompok dengan cukup nilai positif pada kombinasi parameter ini.")
