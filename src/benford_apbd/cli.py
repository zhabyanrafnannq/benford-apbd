"""Antarmuka baris perintah: benford-apbd fetch / analyze / report / cache."""

import argparse
import sys
from pathlib import Path

from .analyze import GROUP_KEYS, nama_analisis, pilih_sumber, run_analysis
from .djpk import cached_selections, fetch_scope, load_tidy
from .report import generate_report


def cmd_fetch(args) -> int:
    if args.dataset == "apbd" and args.periode is None:
        print("dataset apbd wajib menyebut --periode (1 sampai 12)", file=sys.stderr)
        return 2
    ok, failed = fetch_scope(
        args.cache,
        args.dataset,
        args.tahun,
        args.periode,
        args.scope,
        refresh=args.refresh,
        delay=args.delay,
        provinsi_filter=args.provinsi,
    )
    print(f"selesai: {len(ok)} file tersimpan, {len(failed)} gagal")
    for (prov, pemda), err in failed[:10]:
        print(f"  gagal prov {prov} pemda {pemda}: {err}", file=sys.stderr)
    if failed[10:]:
        print(f"  ...dan {len(failed) - 10} kegagalan lain", file=sys.stderr)
    return 0 if ok else 1


def cmd_analyze(args) -> int:
    tidy = load_tidy(args.cache, args.dataset, args.tahun, args.periode)
    hasil = run_analysis(
        tidy,
        group=args.group,
        kolom=args.kolom,
        kind=args.kind,
        n_boot=args.n_boot,
        seed=args.seed,
        hanya_daun=not args.semualevel,
        sumber=args.sumber,
    )
    level = pilih_sumber(tidy, args.sumber)["sumber_level"].iloc[0] if "sumber_level" in tidy.columns else "tidak bertanda"
    print(f"tingkat file yang dipakai: {level}")
    nama = nama_analisis(args.dataset, args.tahun, args.periode, args.group, args.kolom, args.kind, not args.semualevel)
    tujuan = Path(args.o) if args.o else Path(args.cache) / "processed" / f"analisis_{nama}.csv"
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    hasil.to_csv(tujuan, index=False)
    print(hasil.head(15).to_string(index=False))
    print(f"\nhasil lengkap: {tujuan}")
    return 0


def cmd_report(args) -> int:
    tidy = load_tidy(args.cache, args.dataset, args.tahun, args.periode)
    hasil = run_analysis(
        tidy,
        group=args.group,
        kolom=args.kolom,
        kind=args.kind,
        n_boot=args.n_boot,
        seed=args.seed,
        hanya_daun=not args.semualevel,
        sumber=args.sumber,
    )
    nama = nama_analisis(args.dataset, args.tahun, args.periode, args.group, args.kolom, args.kind, not args.semualevel)
    out_dir = Path(args.out_dir) / args.dataset / str(args.tahun) / nama
    jalur = generate_report(
        tidy,
        hasil,
        args.dataset,
        args.tahun,
        args.periode,
        args.group,
        args.kolom,
        args.kind,
        out_dir,
        top=args.top,
        hanya_daun=not args.semualevel,
        sumber_level=args.sumber,
    )
    print(f"laporan: {jalur}")
    return 0


def cmd_cache(args) -> int:
    pilihan = cached_selections(args.cache)
    if not pilihan:
        print("cache kosong. contoh mulai:\n  benford-apbd fetch apbd --tahun 2025 --periode 12 --scope provinsi")
        return 0
    for p in pilihan:
        periode = f" periode {p['periode']}" if p["periode"] else ""
        print(f"{p['dataset']} {p['tahun']}{periode}")
    return 0


def _tambah_argumen_umum(p):
    p.add_argument("--cache", type=Path, default=Path("data"), help="folder cache data (default: ./data)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="benford-apbd",
        description="Uji Benford atas data APBD dan dana desa dari Portal Data DJPK Kemenkeu.",
    )
    sub = parser.add_subparsers(dest="perintah", required=True)

    f = sub.add_parser("fetch", help="unduh data DJPK ke cache lokal")
    f.add_argument("dataset", choices=["apbd", "tkdd"])
    f.add_argument("--tahun", type=int, required=True)
    f.add_argument("--periode", type=int, default=None, help="untuk apbd: 1 sampai 12 (12 = tahun penuh)")
    f.add_argument("--scope", choices=["nasional", "provinsi", "pemda"], default="provinsi")
    f.add_argument("--provinsi", default=None, help="batasi ke satu kode provinsi, mis. 11")
    f.add_argument("--refresh", action="store_true", help="unduh ulang walau sudah ada di cache")
    f.add_argument("--delay", type=float, default=0.4, help="jarak antar permintaan dalam detik")
    _tambah_argumen_umum(f)
    f.set_defaults(func=cmd_fetch)

    a = sub.add_parser("analyze", help="uji digit per kelompok, simpan CSV")
    a.add_argument("--dataset", choices=["apbd", "tkdd"], required=True)
    a.add_argument("--tahun", type=int, required=True)
    a.add_argument("--periode", type=int, default=None)
    a.add_argument("--group", choices=list(GROUP_KEYS), default="per_provinsi")
    a.add_argument("--kolom", choices=["realisasi", "anggaran"], default="realisasi")
    a.add_argument("--kind", choices=["first", "second", "first_two"], default="first")
    a.add_argument("--n-boot", type=int, default=500)
    a.add_argument("--seed", type=int, default=42)
    a.add_argument("--semualevel", action="store_true", help="sertakan baris induk postur (tidak disarankan)")
    a.add_argument("--sumber", choices=["auto", "nasional", "provinsi", "pemda"], default="auto", help="tingkat file yang dipakai")
    a.add_argument("-o", default=None, help="jalur CSV keluaran")
    _tambah_argumen_umum(a)
    a.set_defaults(func=cmd_analyze)

    r = sub.add_parser("report", help="laporan markdown plus grafik")
    r.add_argument("--dataset", choices=["apbd", "tkdd"], required=True)
    r.add_argument("--tahun", type=int, required=True)
    r.add_argument("--periode", type=int, default=None)
    r.add_argument("--group", choices=list(GROUP_KEYS), default="per_provinsi")
    r.add_argument("--kolom", choices=["realisasi", "anggaran"], default="realisasi")
    r.add_argument("--kind", choices=["first", "second", "first_two"], default="first")
    r.add_argument("--n-boot", type=int, default=500)
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--semualevel", action="store_true")
    r.add_argument("--sumber", choices=["auto", "nasional", "provinsi", "pemda"], default="auto", help="tingkat file yang dipakai")
    r.add_argument("--top", type=int, default=3, help="jumlah grafik kelompok teratas")
    r.add_argument("--out-dir", type=Path, default=Path("reports"))
    _tambah_argumen_umum(r)
    r.set_defaults(func=cmd_report)

    c = sub.add_parser("cache", help="tampilkan isi cache")
    _tambah_argumen_umum(c)
    c.set_defaults(func=cmd_cache)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
