#!/usr/bin/env python3
"""
video_recover.py — carve + repair video clips from a disk image (themed).

- Reuses the cached clip table from "Detect" if present (no re-scan); else scans
  and caches it.
- COMPLETE clips (moov+mdat) are carved straight out and play immediately.
- Truncated/fragment clips are carved raw, then repaired best-effort:
    1) untrunc <reference> <broken>   — tries EACH reference clip you provide
       (a single file, or a whole folder of references for mixed resolutions/fps)
    2) ffmpeg -c copy remux           — fallback
Reads the image READ-ONLY; writes only into the output directory.

Usage:  python3 video_recover.py <image> <out_dir> [reference_file_or_dir] [scan_GB]
"""
import sys, os, time, shutil, subprocess, glob
import theme as T
import mp4

REF_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mts", ".m2ts"}


def which(x): return shutil.which(x) is not None


def collect_refs(path):
    """Reference can be one file OR a folder of clips. Return a list of files."""
    if not path:
        return []
    p = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(p):
        out = []
        for dp, _, fs in os.walk(p):
            for f in fs:
                if os.path.splitext(f)[1].lower() in REF_EXTS:
                    out.append(os.path.join(dp, f))
        return sorted(out)
    if os.path.isfile(p):
        return [p]
    return []


def _cleanup_fixed(raw_path):
    for c in glob.glob(raw_path + "*fixed*.mp4"):
        try:
            os.remove(c)
        except OSError:
            pass


def repair(raw_path, references, out_mp4):
    """Return the tool that succeeded, or None. Tries each reference with untrunc."""
    if which("untrunc"):
        for ref in references:
            _cleanup_fixed(raw_path)
            try:
                subprocess.run(["untrunc", ref, raw_path],
                               capture_output=True, text=True, timeout=1800)
            except Exception:
                continue
            for c in sorted(glob.glob(raw_path + "*fixed*.mp4")):
                if os.path.getsize(c) > 0:
                    shutil.move(c, out_mp4)
                    return "untrunc"
        _cleanup_fixed(raw_path)
    if which("ffmpeg"):
        try:
            r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw_path,
                                "-c", "copy", out_mp4],
                               capture_output=True, text=True, timeout=1800)
            if r.returncode == 0 and os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 0:
                return "ffmpeg"
            if os.path.exists(out_mp4):
                os.remove(out_mp4)
        except Exception:
            pass
    return None


def get_clips(image, limit):
    """Reuse cached clip table if available, else scan (and cache)."""
    clips, _ = mp4.load_clips(image)
    if clips:
        T.info(f"using cached clip table ({len(clips)} clips) — no re-scan needed")
        return sorted(clips, key=lambda c: c["off"])
    T.banner("video_recover", "phase 1 · scanning for clips (no cache found)")
    found = []

    def prog(pos, count):
        sys.stdout.write(f"\r  scanning {T.human_t(pos)} / {T.human_t(limit)}  ·  "
                         f"{count} clips found   ")
        sys.stdout.flush()
    try:
        for c in mp4.scan(image, limit, progress=prog):
            found.append(c)
    except KeyboardInterrupt:
        pass
    print()
    found.sort(key=lambda c: c["off"])
    mp4.save_clips(image, found, limit)
    return found


def main():
    if len(sys.argv) < 3:
        print("usage: python3 video_recover.py <image> <out_dir> [reference_file_or_dir] [scan_GB]")
        sys.exit(1)
    image = sys.argv[1]
    out_dir = os.path.abspath(os.path.expanduser(sys.argv[2]))
    ref_arg = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else ""
    scan_gb = float(sys.argv[4]) if len(sys.argv) > 4 else 60

    if not os.path.isfile(image):
        T.err(f"image not found: {image}"); sys.exit(1)
    if os.path.abspath(image).startswith(out_dir.rstrip("/") + "/"):
        T.err("output dir must not contain the source image"); sys.exit(1)

    references = collect_refs(ref_arg)
    good_dir = os.path.join(out_dir, "videos")
    raw_dir = os.path.join(out_dir, "videos_broken")
    os.makedirs(good_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    img_size = os.path.getsize(image)
    limit = min(scan_gb * 1024**3, img_size)

    clips = get_clips(image, limit)
    if not clips:
        T.warn("no clips found — try a larger scan_GB, or delete the .clips.json cache and re-scan.")
        return
    if references:
        T.info(f"{len(references)} reference clip(s) available for untrunc repair")
    else:
        T.warn("no reference clips — broken clips limited to ffmpeg remux (often can't fix truncation)")

    # ---- carve + repair with a live table ----
    results = []
    live = T.Live()
    with live:
        for n, c in enumerate(clips, 1):
            base = f"clip_{n:03d}"
            if c["state"] == "complete":
                mp4.carve(image, c["off"], c["size"], os.path.join(good_dir, base + ".mp4"))
                results.append((n, c, "carved", "playable"))
            else:
                raw = os.path.join(raw_dir, base + ".raw")
                mp4.carve(image, c["off"], c["size"], raw)
                out = os.path.join(good_dir, base + "_recovered.mp4")
                tool = repair(raw, references, out)
                if tool:
                    results.append((n, c, "repaired", tool))
                    try:
                        os.remove(raw)
                    except OSError:
                        pass
                else:
                    results.append((n, c, "raw-only", "needs matching reference"))
            _render(live, clips, results, references)
    _summary(results, good_dir, raw_dir)


def _render(live, clips, results, references):
    cols, rows = T.term()
    W = max(52, min(100, cols - 2))
    done = len(results); total = len(clips)
    L = T.panel_top(W, "video_recover", "phase 2 · carving + repair")
    L.append(T.panel_row(" " + T.gradient_bar(done / total if total else 0, W - 11) +
                         " " + T.bold(T.fg(T.GREEN) + f"{done}/{total}" + T.RESET), W))
    refs = f"{len(references)} clip(s)" if references else T.fg(T.MUTED) + "none" + T.RESET
    L.append(T.panel_row(f"  {T.fg(T.MUTED)}references:{T.RESET} {refs}", W))
    L.append(T.panel_sep(W))
    L.append(T.panel_row(f"  {'#':>3}  {'SIZE':>9}  RESULT", W))
    for n, c, state, outcome in results[-(max(6, rows - 12)):]:
        if state == "carved":
            tag = T.fg(T.GREEN) + "playable" + T.RESET
        elif state == "repaired":
            tag = T.fg(T.CYAN) + f"repaired ({outcome})" + T.RESET
        else:
            tag = T.fg(T.YELLOW) + "raw-only" + T.RESET
        L.append(T.panel_row(f"  {n:>3}  {T.human_t(c['size']):>9}  {tag}", W))
    L.append(T.panel_bot(W))
    live.frame(L)


def _summary(results, good_dir, raw_dir):
    playable = sum(1 for _, _, s, _ in results if s in ("carved", "repaired"))
    rawonly = sum(1 for _, _, s, _ in results if s == "raw-only")
    print("\n" + T.bold(T.fg(T.TITLE) + "  video recovery summary" + T.RESET))
    T.ok(f"{playable} playable clip(s) -> {good_dir}")
    if rawonly:
        T.warn(f"{rawonly} clip(s) could not be repaired -> raw carves in {raw_dir}")
        T.info("add a reference clip shot in the SAME mode + install untrunc, then re-run.")


if __name__ == "__main__":
    main()
