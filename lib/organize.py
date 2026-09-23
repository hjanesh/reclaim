#!/usr/bin/env python3
"""
organize.py - tidy a folder of carved files into dated per-shoot folders.

- Relabels Sony RAW that PhotoRec named .sr2/.tif/.tiff → .arw.
- Sorts photos/videos into <out>/YYYY-MM-DD/ by capture date
  (exiftool DateTimeOriginal/CreateDate → falls back to file mtime).
- Dry-run by default; pass --apply to actually move files.

Usage:  python3 organize.py <recovered_dir> <out_dir> [--apply]
"""
import sys, os, csv, subprocess, shutil, datetime
import theme as T

RELABEL = {"sr2": "arw", "srf": "arw", "tif": "arw", "tiff": "arw"}
MEDIA = {"arw", "sr2", "srf", "tif", "tiff", "cr2", "cr3", "nef", "raf", "orf",
         "rw2", "dng", "jpg", "jpeg", "png", "heic", "heif",
         "mov", "mp4", "avi", "mts", "m2ts", "m4v"}


def have(cmd): return shutil.which(cmd) is not None


def exif_dates(root):
    """Map SourceFile -> 'YYYY-MM-DD' using one batched exiftool call."""
    dates = {}
    if not have("exiftool"):
        return dates
    try:
        r = subprocess.run(
            ["exiftool", "-r", "-csv", "-d", "%Y-%m-%d",
             "-DateTimeOriginal", "-CreateDate", "-FileModifyDate", root],
            capture_output=True, text=True, timeout=3600)
        if r.returncode != 0 or not r.stdout:
            return dates
        rdr = csv.DictReader(r.stdout.splitlines())
        for row in rdr:
            src = row.get("SourceFile")
            if not src:
                continue
            for k in ("DateTimeOriginal", "CreateDate", "FileModifyDate"):
                v = (row.get(k) or "").strip()
                if v and v[:4].isdigit():
                    dates[os.path.abspath(src)] = v[:10]
                    break
    except Exception:
        pass
    return dates


def mtime_date(path):
    try:
        return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()
    except OSError:
        return "unknown-date"


def unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while os.path.exists(f"{base}_{i}{ext}"):
        i += 1
    return f"{base}_{i}{ext}"


def main():
    if len(sys.argv) < 3:
        print("usage: python3 organize.py <recovered_dir> <out_dir> [--apply]"); sys.exit(1)
    root = os.path.abspath(os.path.expanduser(sys.argv[1]))
    out = os.path.abspath(os.path.expanduser(sys.argv[2]))
    apply = "--apply" in sys.argv[3:]
    if not os.path.isdir(root):
        T.err(f"not a directory: {root}"); sys.exit(1)

    T.banner("organize", ("APPLY (moving files)" if apply else "DRY-RUN (preview only)"))
    T.info("reading capture dates via exiftool …" if have("exiftool")
           else "exiftool not found - using file modification times")
    dates = exif_dates(root)

    plan = []       # (src, dst)
    counts = {}     # date -> count
    relabels = 0
    for dirpath, _, files in os.walk(root):
        if os.path.abspath(dirpath).startswith(out):
            continue
        for name in files:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext not in MEDIA:
                continue
            src = os.path.join(dirpath, name)
            day = dates.get(os.path.abspath(src)) or mtime_date(src)
            new_ext = RELABEL.get(ext, ext)
            if new_ext != ext:
                relabels += 1
            stem = os.path.splitext(name)[0]
            dst = unique(os.path.join(out, day, f"{stem}.{new_ext}"))
            plan.append((src, dst))
            counts[day] = counts.get(day, 0) + 1

    if not plan:
        T.warn("no media files found to organize."); return

    W = min(T.term()[0] - 2, 78)
    print(T.panel_sep(W))
    for day in sorted(counts):
        print(T.panel_row(f"  {T.fg(T.CYAN)}{day}{T.RESET}   {counts[day]:>5} files", W))
    print(T.panel_bot(W))
    T.info(f"{len(plan)} files → {len(counts)} dated folders under {out}")
    if relabels:
        T.info(f"{relabels} Sony RAW files will be relabelled .sr2/.tif → .arw")

    if not apply:
        T.warn("dry-run only - re-run with --apply to move the files.")
        for src, dst in plan[:6]:
            print(f"    {T.fg(T.MUTED)}{os.path.basename(src)} → "
                  f"{os.path.relpath(dst, out)}{T.RESET}")
        return

    moved = 0
    for src, dst in plan:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.move(src, dst); moved += 1
        except Exception as e:
            T.err(f"failed {src}: {e}")
    T.ok(f"moved {moved} files into {out}")


if __name__ == "__main__":
    main()
