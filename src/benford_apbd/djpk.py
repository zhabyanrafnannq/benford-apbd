"""Klien Portal Data DJPK Kemenkeu: unduh dengan cache, parser SpreadsheetML, normalisasi.

Sumber (dicek 2026-11):
- APBD : https://djpk.kemenkeu.go.id/portal/csv_apbd?type=apbd&periode=&tahun=&provinsi=&pemda=
- TKDD (termasuk Dana Desa) : https://djpk.kemenkeu.go.id/portal/csv?type=tkdd&tahun=&provinsi=&pemda=
- Ref wilayah : /portal/provinsi/{tahun} dan /portal/pemda/{prov}/{tahun}

Format berubah-ubah dari tahun ke tahun, jadi parser disusun toleran:
indentasi label menentukan hierarki kalau ada, kalau tidak ada, postur APBD
kanonik di bawah yang menentukan induk-anak.
"""

import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://djpk.kemenkeu.go.id/portal"
NS = "{urn:schemas-microsoft-com:office:spreadsheet}"
USER_AGENT = "benford-apbd/0.1 (riset statistika, akses sopan dengan cache lokal)"

# Postur APBD standar DJPK: (nama akun, daftar anak). Baris induk tidak ikut
# pool nilai supaya tidak dihitung ganda bersama anaknya.
POSTUR_APBD = {
    "Pendapatan Daerah": [
        (
            "PAD",
            [
                "Pajak Daerah",
                "Retribusi Daerah",
                "Hasil Pengelolaan Kekayaan Daerah yang Dipisahkan",
                "Lain-Lain PAD yang Sah",
            ],
        ),
        ("TKDD", ["Pendapatan Transfer Pemerintah Pusat"]),
        (
            "Pendapatan Lainnya",
            [
                "Pendapatan Hibah",
                "Lain-lain Pendapatan Sesuai dengan Ketentuan Peraturan Perundang-Undangan",
            ],
        ),
        ("Pendapatan Transfer Antar Daerah", []),
    ],
    "Belanja Daerah": [
        ("Belanja Pegawai", []),
        ("Belanja Barang dan Jasa", []),
        ("Belanja Modal", []),
        (
            "Belanja Lainnya",
            [
                "Belanja Bagi Hasil",
                "Belanja Bantuan Keuangan",
                "Belanja Bunga",
                "Belanja Hibah",
                "Belanja Bantuan Sosial",
                "Belanja Tidak Terduga",
            ],
        ),
    ],
    "Pembiayaan Daerah": [
        (
            "Penerimaan Pembiayaan Daerah",
            [
                "Sisa Lebih Perhitungan Anggaran Tahun Sebelumnya",
                "Penerimaan Pinjaman Daerah",
            ],
        ),
        (
            "Pengeluaran Pembiayaan Daerah",
            [
                "Penyertaan Modal Daerah",
                "Pembayaran Cicilan Pokok Utang yang Jatuh Tempo",
            ],
        ),
    ],
}

_SKALA_SATUAN = {"m": 1e9, "t": 1e12}  # satuan Miliar / Triliun pada TKDD


def akun_paths_postur() -> dict[str, str]:
    """Peta label akun ke jalur lengkapnya; akar dan induk juga terdaftar."""
    paths = {}
    for root, groups in POSTUR_APBD.items():
        paths.setdefault(root, root)
        for parent, children in groups:
            paths.setdefault(parent, f"{root} > {parent}")
            for child in children:
                paths[child] = f"{root} > {parent} > {child}"
    return paths


class DjpkError(RuntimeError):
    pass


@dataclass
class AccountRow:
    label: str
    indent: int
    anggaran: float | None
    realisasi: float | None
    persen: float | None


def parse_formatted_number(raw: str) -> float | None:
    """Angka DJPK berformat Indonesia: '62.480,25 M' berarti 62.480,25 Miliar.

    '84.65' (persen, desimal titik) tetap 84.65 karena polanya tidak cocok
    dengan pemisah ribuan; eksponensial '2.33E+12' diteruskan ke float langsung.
    """
    s = raw.strip()
    if not s or s in {"-", "--"}:
        return None
    skala = 1.0
    unit = s[-1].lower()
    if len(s) >= 2 and unit in _SKALA_SATUAN and not s[-2].isdigit():
        skala = _SKALA_SATUAN[unit]
        s = s[:-1].strip()
    if "e" in s.lower():
        try:
            return float(s) * skala
        except ValueError:
            return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s) * skala
    except ValueError:
        return None


def parse_spreadsheetml(path: Path) -> list[AccountRow]:
    """Baca SpreadsheetML (hasil endpoint csv_* DJPK) jadi baris akun."""
    root = ET.parse(path).getroot()
    rows = []
    for row in root.iter(f"{NS}Row"):
        cells = list(row.iter(f"{NS}Cell"))
        data = []
        for cell in cells:
            el = cell.find(f"{NS}Data")
            if el is None:
                continue
            data.append((el.get(f"{NS}Type"), el.text or ""))
        if not data:
            continue
        if data[0][1].strip() == "Akun":
            continue
        label = data[0][1]
        vals: list[float | None] = []
        for typ, raw in data[1:4]:
            if typ == "Number":
                try:
                    vals.append(float(raw))
                except ValueError:
                    vals.append(None)
            else:
                vals.append(parse_formatted_number(raw))
        vals += [None] * (3 - len(vals))
        indent = len(label) - len(label.lstrip(" "))
        rows.append(AccountRow(label.strip(), indent, *vals))
    return rows


def _dedup_consecutive(rows: list[AccountRow]) -> list[AccountRow]:
    """Baris ekspor portal kadang terulang persis (mis. 'Belanja Pegawai' dua kali)."""
    out = []
    for r in rows:
        if out and r.label == out[-1].label and r.anggaran == out[-1].anggaran and r.realisasi == out[-1].realisasi:
            continue
        out.append(r)
    return out


def _leaf_by_indent(rows: list[AccountRow]) -> list[bool]:
    """Baris menjadi daun kalau baris berikutnya tidak lebih dalam dari dia."""
    out = []
    for i, r in enumerate(rows):
        nxt = rows[i + 1].indent if i + 1 < len(rows) else -1
        out.append(nxt <= r.indent)
    return out


def _parent_labels() -> set[str]:
    parents = set(POSTUR_APBD)
    for groups in POSTUR_APBD.values():
        for parent, children in groups:
            if children:
                parents.add(parent)
    return parents


def _annotate_flat_apbd(rows: list[AccountRow]) -> list[tuple[AccountRow, str, bool]]:
    """File APBD datar: hierarki diambil dari postur kanonik.

    Label tak dikenal dianggap daun di bawah induk terakhir yang dikenal.
    """
    paths = akun_paths_postur()
    parents = _parent_labels()
    out = []
    last_parent = ""
    for r in rows:
        if r.label in parents:
            last_parent = r.label
        if r.label in paths:
            out.append((r, paths[r.label], r.label not in parents))
        else:
            out.append((r, f"{last_parent} > {r.label}" if last_parent else r.label, True))
    return out


def normalize_rows(rows: list[AccountRow], dataset: str) -> list[dict]:
    rows = _dedup_consecutive(rows)
    recs = []
    indents = {r.indent for r in rows}
    if dataset == "apbd" and len(indents) <= 1:
        annotated = _annotate_flat_apbd(rows)
    else:
        paths = akun_paths_postur()
        stack: list[tuple[int, str]] = []
        annotated = []
        leaves = _leaf_by_indent(rows)
        for r, leaf in zip(rows, leaves):
            while stack and stack[-1][0] >= r.indent:
                stack.pop()
            parent_path = " > ".join(lbl for _, lbl in stack)
            path = f"{parent_path} > {r.label}" if parent_path else r.label
            if dataset == "apbd" and r.label in paths:
                path = paths[r.label]
            annotated.append((r, path, leaf))
            stack.append((r.indent, r.label))
    for r, path, leaf in annotated:
        if r.anggaran is None and r.realisasi is None:
            continue
        recs.append(
            {
                "akun": r.label,
                "akun_path": path,
                "is_leaf": leaf,
                "anggaran": r.anggaran,
                "realisasi": r.realisasi,
                "persen": r.persen,
            }
        )
    return recs


class DjpkClient:
    """Klien HTTP dengan cache file lokal. File yang sudah ada tidak diunduh ulang."""

    def __init__(self, cache_dir: Path, delay: float = 0.4, timeout: float = 60.0):
        self.cache_dir = Path(cache_dir)
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_request = 0.0

    def _get(self, url: str) -> bytes:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                self._last_request = time.monotonic()
                if resp.status_code == 200:
                    return resp.content
                if resp.status_code in (404, 500):
                    raise DjpkError(f"HTTP {resp.status_code} untuk {url}")
                last_err = DjpkError(f"HTTP {resp.status_code} untuk {url}")
            except requests.RequestException as err:
                last_err = err
                self._last_request = time.monotonic()
            time.sleep(2**attempt)
        raise DjpkError(f"gagal mengunduh {url}: {last_err}") from last_err

    def _cache_path(self, relparts: list[str]) -> Path:
        path = self.cache_dir.joinpath(*relparts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _get_cached(self, url: str, relparts: list[str], refresh: bool = False) -> Path:
        path = self._cache_path(relparts)
        if path.exists() and not refresh:
            return path
        try:
            content = self._get(url)
        except DjpkError:
            if path.exists():
                return path
            raise
        path.write_bytes(content)
        return path

    def provinsi(self, tahun: int, refresh: bool = False) -> dict[str, str]:
        path = self._get_cached(f"{BASE_URL}/provinsi/{tahun}", ["ref", f"provinsi_{tahun}.json"], refresh)
        return dict(json.loads(path.read_text(encoding="utf-8")))

    def pemda(self, prov_kode: str, tahun: int, refresh: bool = False) -> dict[str, str]:
        path = self._get_cached(
            f"{BASE_URL}/pemda/{prov_kode}/{tahun}",
            ["ref", f"pemda_{prov_kode}_{tahun}.json"],
            refresh,
        )
        return dict(json.loads(path.read_text(encoding="utf-8")))

    def apbd(self, tahun: int, periode: int, prov_kode: str = "--", pemda_kode: str = "--", refresh: bool = False) -> Path:
        url = f"{BASE_URL}/csv_apbd?type=apbd&periode={periode}&tahun={tahun}&provinsi={prov_kode}&pemda={pemda_kode}"
        name = f"p{periode:02d}_prov{prov_kode}_pemda{pemda_kode}.xml"
        return self._get_cached(url, ["apbd", str(tahun), name], refresh)

    def tkdd(self, tahun: int, prov_kode: str = "--", pemda_kode: str = "--", refresh: bool = False) -> Path:
        url = f"{BASE_URL}/csv?type=tkdd&tahun={tahun}&provinsi={prov_kode}&pemda={pemda_kode}"
        name = f"prov{prov_kode}_pemda{pemda_kode}.xml"
        return self._get_cached(url, ["tkdd", str(tahun), name], refresh)


def scope_targets(client: DjpkClient, dataset: str, tahun: int, periode: int | None, scope: str, refresh: bool = False):
    """Daftar (prov_kode, pemda_kode) sesuai lingkup unduhan yang diminta."""
    targets = []
    if scope == "nasional":
        targets.append(("--", "--"))
    elif scope == "provinsi":
        for kode in client.provinsi(tahun, refresh):
            targets.append((kode, "--"))
    elif scope == "pemda":
        for prov_kode in client.provinsi(tahun, refresh):
            for pemda_kode in client.pemda(prov_kode, tahun, refresh):
                if pemda_kode != "--":
                    targets.append((prov_kode, pemda_kode))
    else:
        raise ValueError(f"lingkup tidak dikenal: {scope}")
    return targets


def fetch_scope(
    cache_dir,
    dataset: str,
    tahun: int,
    periode: int | None,
    scope: str,
    refresh: bool = False,
    delay: float = 0.4,
    provinsi_filter: str | None = None,
):
    """Unduh semua file pada lingkup tertentu; kembalikan (sukses, gagal)."""
    client = DjpkClient(cache_dir, delay=delay)
    client.provinsi(tahun, refresh)
    targets = scope_targets(client, dataset, tahun, periode, scope, refresh)
    if provinsi_filter:
        targets = [t for t in targets if t[0] == provinsi_filter]
    if scope == "pemda":
        for prov_kode, _ in targets:
            client.pemda(prov_kode, tahun, refresh)
    ok, failed = [], []
    for prov_kode, pemda_kode in targets:
        try:
            if dataset == "apbd":
                if periode is None:
                    raise ValueError("dataset apbd wajib punya periode (1 sampai 12)")
                client.apbd(tahun, periode, prov_kode, pemda_kode, refresh)
            elif dataset == "tkdd":
                client.tkdd(tahun, prov_kode, pemda_kode, refresh)
            else:
                raise ValueError(f"dataset tidak dikenal: {dataset}")
            ok.append((prov_kode, pemda_kode))
        except DjpkError as err:
            failed.append(((prov_kode, pemda_kode), str(err)))
    return ok, failed


def load_tidy(cache_dir, dataset: str, tahun: int, periode: int | None = None) -> pd.DataFrame:
    """Normalisasi semua file cache untuk satu dataset/tahun jadi tabel rapi.

    Kolom sumber_level menandai asal file (nasional, provinsi, atau pemda)
    supaya analisis tidak mencampur agregat provinsi dengan detail pemda dan
    menghitung nilai yang sama dua kali.
    """
    base = Path(cache_dir) / dataset / str(tahun)
    pattern = f"p{periode:02d}_prov*.xml" if dataset == "apbd" else "prov*.xml"
    files = sorted(base.glob(pattern)) if base.exists() else []
    recs = []
    provinsi_ref = Path(cache_dir) / "ref"
    nama_prov = {}
    nama_pemda = {}
    if provinsi_ref.exists():
        for p in provinsi_ref.glob(f"provinsi_{tahun}.json"):
            nama_prov.update(json.loads(p.read_text(encoding="utf-8")))
        for p in provinsi_ref.glob(f"pemda_*_{tahun}.json"):
            prov = p.stem.split("_")[1]
            nama_pemda[prov] = json.loads(p.read_text(encoding="utf-8"))
    for f in files:
        m = re.match(r"(?:p(\d+)_)?prov(\S+)_pemda(\S+)\.xml", f.name)
        if not m:
            continue
        periode_f = int(m.group(1)) if m.group(1) else None
        prov_kode, pemda_kode = m.group(2), m.group(3)
        rows = parse_spreadsheetml(f)
        prov_nama = "Nasional" if prov_kode == "--" else nama_prov.get(prov_kode, f"kode {prov_kode}")
        pemda_nama = "Semua pemda" if pemda_kode == "--" else nama_pemda.get(prov_kode, {}).get(pemda_kode, f"kode {pemda_kode}")
        if prov_kode == "--" and pemda_kode == "--":
            sumber_level = "nasional"
        elif pemda_kode == "--":
            sumber_level = "provinsi"
        else:
            sumber_level = "pemda"
        for rec in normalize_rows(rows, dataset):
            rec.update(
                {
                    "dataset": dataset,
                    "tahun": tahun,
                    "periode": periode_f,
                    "kode_provinsi": prov_kode,
                    "nama_provinsi": prov_nama,
                    "kode_pemda": pemda_kode,
                    "nama_pemda": pemda_nama,
                    "sumber_level": sumber_level,
                }
            )
            recs.append(rec)
    if not recs:
        raise DjpkError(
            f"tidak ada file cache untuk {dataset} tahun {tahun}"
            + (f" periode {periode}" if periode else "")
            + ". Jalankan dulu: benford-apbd fetch"
        )
    return pd.DataFrame(recs)


def cached_selections(cache_dir) -> list[dict]:
    """Kombinasi dataset/tahun/periode yang sudah ada di cache, untuk CLI dan dashboard."""
    base = Path(cache_dir)
    out = []
    if not base.exists():
        return out
    for dataset in ("apbd", "tkdd"):
        ddir = base / dataset
        if not ddir.exists():
            continue
        for tdir in sorted(ddir.iterdir()):
            if not tdir.is_dir():
                continue
            if dataset == "apbd":
                period = sorted({int(m.group(1)) for f in tdir.glob("p*_prov*.xml") for m in [re.match(r"p(\d+)_", f.name)] if m})
                for p in period:
                    out.append({"dataset": dataset, "tahun": int(tdir.name), "periode": p})
            else:
                if list(tdir.glob("prov*.xml")):
                    out.append({"dataset": dataset, "tahun": int(tdir.name), "periode": None})
    return out
