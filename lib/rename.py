#!/usr/bin/env python3
"""
rename.py - restore original filenames from embedded metadata (best-effort).

Carving (photorec) loses the original names because the card's directory was
overwritten. Some cameras embed the original filename in metadata; where they
do, we restore it exactly. Where they don't (many Sony bodies), we build a
clean, meaningful name from the capture timestamp + camera model instead.

Also relabels Sony RAW that carving named .sr2/.tif → .arw.

Dry-run by default; pass --apply to actually rename/move.

Usage:  python3 rename.py <recovered_dir> <out_dir> [--apply]
"""
import sys, os, csv, subprocess, shutil
import theme as T
import runlog

RELABEL = {"sr2": "arw", "srf": "arw", "tif": "arw", "tiff": "arw"}
MEDIA = {"arw", "sr2", "srf", "tif", "tiff", "cr2", "cr3", "nef", "raf", "orf",
         "rw2", "dng", "gpr", "pef", "srw", "x3f", "3fr", "mef", "iiq", "nrw",
         "jpg", "jpeg", "png", "heic", "heif", "webp", "gif", "bmp",
         "mov", "mp4", "avi", "mts", "m2ts", "m4v", "mkv", "mpg", "mpeg",
         "wmv", "3gp", "insv", "braw", "crm", "ts", "m2t"}
# metadata tags that (for some cameras) hold the original on-card filename
NAME_TAGS = ["OriginalFileName", "PreservedFileName", "OriginalRawFileName",
             "RawFileName", "DocumentName"]


def have(cmd): return shutil.which(cmd) is not None


def gather(root):
    """One batched exiftool call → {abspath: {tag: value}}."""
    cols = (["-FileName", "-Model", "-DateTimeOriginal", "-CreateDate",
             "-SubSecTimeOriginal"] + ["-" + t for t in NAME_TAGS])
    try:
        r = subprocess.run(["exiftool", "-r", "-csv", "-d", "%Y%m%d_%H%M%S"] + cols + [root],
                           capture_output=True, text=True, timeout=3600)
    except Exception as e:
        runlog.warn("exiftool metadata read failed", e)
        return {}
    if not r.stdout:
        return {}
    out = {}
    for row in csv.DictReader(r.stdout.splitlines()):
        src = row.get("SourceFile")
        if src:
            out[os.path.abspath(src)] = row
    return out


def embedded_name(row):
    """Return a clean original stem from metadata, or '' if none/implausible."""
    for t in NAME_TAGS:
        v = (row.get(t) or "").strip()
        if not v:
            continue
        stem = os.path.splitext(os.path.basename(v.replace("\\", "/")))[0]
        if stem and len(stem) <= 64 and all(c.isalnum() or c in "-_." for c in stem):
            return stem
    return ""


def reconstructed_name(row, fallback_stem):
    """Build a meaningful name from capture time + model when no original exists."""
    dt = (row.get("DateTimeOriginal") or row.get("CreateDate") or "").strip()
    model = (row.get("Model") or "").strip().upper()
    if dt and dt[:8].isdigit():
        prefix = "DSC" if ("ILCE" in model or "SONY" in model or "DSC" in model) else "IMG"
        stem = f"{prefix}_{dt}"
        ss = (row.get("SubSecTimeOriginal") or "").strip()
        if ss:
            stem += f"_{ss}"
        return stem
    return fallback_stem


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
        print("usage: python3 rename.py <recovered_dir> <out_dir> [--apply]"); sys.exit(1)
    root = os.path.abspath(os.path.expanduser(sys.argv[1]))
    out = os.path.abspath(os.path.expanduser(sys.argv[2]))
    apply = "--apply" in sys.argv[3:]
    if not os.path.isdir(root):
        T.err(f"not a directory: {root}"); sys.exit(1)
    if not have("exiftool"):
        T.err("exiftool is required - run ./install.sh"); sys.exit(1)
    if apply:
        runlog.set_dir(out)   # only create the log (and out dir) on a real run

    T.banner("rename", ("APPLY (moving files)" if apply else "DRY-RUN (preview only)"))
    T.info("reading metadata via exiftool …")
    meta = gather(root)

    plan = []; embedded = 0; rebuilt = 0; relabels = 0
    for dirpath, _, files in os.walk(root):
        if os.path.abspath(dirpath).startswith(out):
            continue
        for name in files:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext not in MEDIA:
                continue
            src = os.path.join(dirpath, name)
            row = meta.get(os.path.abspath(src), {})
            stem = embedded_name(row)
            if stem:
                embedded += 1
            else:
                stem = reconstructed_name(row, os.path.splitext(name)[0]); rebuilt += 1
            new_ext = RELABEL.get(ext, ext)
            if new_ext != ext:
                relabels += 1
            dst = unique(os.path.join(out, f"{stem}.{new_ext}"))
            plan.append((src, dst))

    if not plan:
        T.warn("no media files found to rename."); return

    T.info(f"{len(plan)} files: {T.fg(T.GREEN)}{embedded} restored from embedded metadata{T.RESET}, "
           f"{T.fg(T.YELLOW)}{rebuilt} rebuilt from capture time/model{T.RESET}")
    if relabels:
        T.info(f"{relabels} Sony RAW relabelled .sr2/.tif -> .arw")
    if embedded == 0:
        T.warn("this camera doesn't embed the on-card filename in metadata, so exact "
               "original names aren't recoverable - files get clean timestamp-based names.")

    for src, dst in plan[:8]:
        print(f"    {T.fg(T.MUTED)}{os.path.basename(src)} -> {os.path.basename(dst)}{T.RESET}")

    if not apply:
        T.warn("dry-run only - re-run with --apply to perform the renames.")
        return

    os.makedirs(out, exist_ok=True)
    moved = 0
    for src, dst in plan:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.move(src, dst); moved += 1
        except Exception as e:
            T.err(f"failed {src}: {e}"); runlog.error(f"rename failed: {src}", e)
    T.ok(f"renamed {moved} files -> {out}")


if __name__ == "__main__":
    main()
