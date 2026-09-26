#!/usr/bin/env python3
"""
verify.py - confirm recovered media is actually readable, and optionally
de-duplicate a folder of carved files. Read-only unless you pass --apply.

Recovery tools happily emit files that don't open. This walks an output folder,
probes each file with the right tool (ffprobe for video, exiftool for photos),
and prints a pass/fail table so you know what truly survived. With --dedup it
groups by SHA-256 (photorec produces many exact duplicates) and, with --apply,
moves the extras into a `duplicates/` subfolder (never deletes).

Usage:  python3 verify.py <folder> [--dedup] [--apply]
"""
import os
import shutil
import subprocess
import sys

import theme as T
import manifest

VIDEO = {"mp4", "mov", "m4v", "avi", "mts", "m2ts", "mkv", "wmv", "mpg", "mpeg", "3gp"}
PHOTO = {"jpg", "jpeg", "png", "heic", "heif", "arw", "cr2", "cr3", "nef", "raf",
         "orf", "rw2", "dng", "tif", "tiff", "gif", "bmp", "webp"}


def have(cmd):
    return shutil.which(cmd) is not None


def check_video(path):
    """True=plays, False=broken, None=can't tell (ffprobe missing)."""
    if not have("ffprobe"):
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, timeout=120)
    except Exception:
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


def check_photo(path):
    """True=readable (has real dimensions), False=broken, None=exiftool missing."""
    if not have("exiftool"):
        return None
    try:
        r = subprocess.run(
            ["exiftool", "-s3", "-ImageWidth", "-ImageHeight", path],
            capture_output=True, text=True, timeout=60)
    except Exception:
        return False
    nums = [x for x in r.stdout.split() if x.isdigit()]
    return len(nums) >= 2 and all(int(x) > 0 for x in nums[:2])


def classify(ext):
    if ext in VIDEO:
        return "video"
    if ext in PHOTO:
        return "photo"
    return "other"


def _iter_media(root):
    for dp, _, files in os.walk(root):
        for name in files:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            kind = classify(ext)
            if kind != "other":
                yield os.path.join(dp, name), ext, kind


def verify_folder(root):
    """Return (results, tally). results: list of (path, kind, status)."""
    results = []
    tally = {"ok": 0, "broken": 0, "unknown": 0}
    for path, _, kind in _iter_media(root):
        good = check_video(path) if kind == "video" else check_photo(path)
        status = "ok" if good else ("unknown" if good is None else "broken")
        tally[status] += 1
        results.append((path, kind, status))
    return results, tally


def find_duplicates(root):
    """Group files by SHA-256. Return {digest: [paths...]} for groups with >1."""
    by_hash = {}
    for path, _, _ in _iter_media(root):
        digest = manifest.sha256(path)
        if digest:
            by_hash.setdefault(digest, []).append(path)
    return {d: sorted(paths) for d, paths in by_hash.items() if len(paths) > 1}


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: python3 verify.py <folder> [--dedup] [--apply]"); sys.exit(1)
    root = os.path.abspath(os.path.expanduser(args[0]))
    do_dedup = "--dedup" in args
    apply = "--apply" in args
    if not os.path.isdir(root):
        T.err(f"not a directory: {root}"); sys.exit(1)

    T.banner("verify", "check recovered media is readable" + (" · de-dupe" if do_dedup else ""))
    if not have("ffprobe"):
        T.warn("ffprobe not found - videos can't be validated (install ffmpeg).")
    if not have("exiftool"):
        T.warn("exiftool not found - photos can't be validated.")

    results, tally = verify_folder(root)
    if not results:
        T.warn("no media files found under that folder."); return

    W = min(T.term()[0] - 2, 78)
    print(T.panel_sep(W))
    shown = [r for r in results if r[2] != "ok"][:20]   # surface problems first
    for path, kind, status in shown:
        col = T.RED if status == "broken" else T.MUTED
        print(T.panel_row(f"  {T.fg(col)}{status:<8}{T.RESET} {kind:<6} "
                          f"{os.path.relpath(path, root)}", W))
    print(T.panel_bot(W))
    T.ok(f"{tally['ok']} readable")
    if tally["broken"]:
        T.err(f"{tally['broken']} broken (listed above)")
    if tally["unknown"]:
        T.warn(f"{tally['unknown']} not checked (validator tool missing)")

    if do_dedup:
        dups = find_duplicates(root)
        extra = sum(len(v) - 1 for v in dups.values())
        T.info(f"{len(dups)} duplicate group(s), {extra} redundant copy(ies)")
        if not extra:
            return
        dup_dir = os.path.join(root, "duplicates")
        if not apply:
            T.warn(f"dry-run - re-run with --dedup --apply to move extras into {dup_dir}/")
            return
        os.makedirs(dup_dir, exist_ok=True)
        moved = 0
        for paths in dups.values():
            for p in paths[1:]:            # keep the first, move the rest
                dst = os.path.join(dup_dir, os.path.basename(p))
                base, ext = os.path.splitext(dst)
                i = 1
                while os.path.exists(dst):
                    dst = f"{base}_{i}{ext}"; i += 1
                try:
                    shutil.move(p, dst); moved += 1
                except OSError as e:
                    T.err(f"failed to move {p}: {e}")
        T.ok(f"moved {moved} duplicate(s) into {dup_dir}")


if __name__ == "__main__":
    main()
