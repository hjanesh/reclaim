#!/usr/bin/env python3
"""
video_recover.py — carve + repair video clips from a disk image (themed).

- Scans the image for MP4/MOV clips (shared mp4 module).
- COMPLETE clips (moov+mdat) are carved straight out and play immediately.
- Truncated/fragment clips are carved raw, then repaired best-effort:
    1) untrunc <reference> <broken>   (needs a reference clip from the same camera)
    2) ffmpeg -c copy remux           (fallback)
Reads the image READ-ONLY; writes only into the output directory.

Usage:  python3 video_recover.py <image> <out_dir> [reference_clip] [scan_GB]
"""
import sys, os, time, shutil, subprocess, glob
import theme as T
import mp4


def which(x): return shutil.which(x) is not None


def repair(raw_path, reference, out_mp4):
    """Try to turn a broken raw carve into a playable file. Returns tool name or None."""
    # 1) untrunc with a reference clip
    if reference and which("untrunc"):
        try:
            subprocess.run(["untrunc", reference, raw_path],
                           capture_output=True, text=True, timeout=1800)
        except Exception:
            pass
        cands = sorted(glob.glob(raw_path + "*fixed*.mp4") + glob.glob(raw_path + "_fixed.mp4"))
        for c in cands:
            if os.path.getsize(c) > 0:
                shutil.move(c, out_mp4); return "untrunc"
    # 2) ffmpeg remux fallback
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


def main():
    if len(sys.argv) < 3:
        print("usage: python3 video_recover.py <image> <out_dir> [reference_clip] [scan_GB]")
        sys.exit(1)
    image = sys.argv[1]
    out_dir = os.path.abspath(os.path.expanduser(sys.argv[2]))
    reference = os.path.abspath(os.path.expanduser(sys.argv[3])) if len(sys.argv) > 3 and sys.argv[3] else None
    scan_gb = float(sys.argv[4]) if len(sys.argv) > 4 else 60

    if not os.path.isfile(image):
        T.err(f"image not found: {image}"); sys.exit(1)
    if os.path.abspath(image).startswith(out_dir.rstrip("/") + "/"):
        T.err("output dir must not contain the source image"); sys.exit(1)
    good_dir = os.path.join(out_dir, "videos")
    raw_dir = os.path.join(out_dir, "videos_broken")
    os.makedirs(good_dir, exist_ok=True)
    os.makedirs(raw_dir, exist_ok=True)
    img_size = os.path.getsize(image)
    limit = min(scan_gb * 1024**3, img_size)

    # ---- phase 1: scan ----
    T.banner("video_recover", "phase 1 · scanning for clips")
    clips = []
    def prog(pos, count):
        sys.stdout.write(f"\r  scanning {T.human_t(pos)} / {T.human_t(limit)}  ·  "
                         f"{count} clips found   ")
        sys.stdout.flush()
    try:
        for c in mp4.scan(image, limit, progress=prog):
            clips.append(c)
    except KeyboardInterrupt:
        pass
    print()
    if not clips:
        T.warn("no clips found in range — try a larger scan_GB."); return
    clips.sort(key=lambda c: c["off"])

    # ---- phase 2: carve + repair, with a live table ----
    results = []   # (n, state, size, outcome)
    live = T.Live()
    with live:
        for n, c in enumerate(clips, 1):
            base = f"clip_{n:03d}"
            if c["state"] == "complete":
                out = os.path.join(good_dir, base + ".mp4")
                mp4.carve(image, c["off"], c["size"], out)
                results.append((n, c, "carved", "playable"))
            else:
                raw = os.path.join(raw_dir, base + ".raw")
                mp4.carve(image, c["off"], c["size"], raw)
                out = os.path.join(good_dir, base + "_recovered.mp4")
                tool = repair(raw, reference, out)
                if tool:
                    results.append((n, c, "repaired", tool))
                    try: os.remove(raw)
                    except OSError: pass
                else:
                    results.append((n, c, "raw-only", "needs reference/untrunc"))
            _render(live, clips, results, reference)
    _summary(results, good_dir, raw_dir)


def _render(live, clips, results, reference):
    cols, rows = T.term()
    W = max(52, min(100, cols - 2))
    done = len(results)
    total = len(clips)
    L = T.panel_top(W, "video_recover", "phase 2 · carving + repair")
    L.append(T.panel_row(" " + T.gradient_bar(done / total if total else 0, W - 11) +
                         " " + T.bold(T.fg(T.GREEN) + f"{done}/{total}" + T.RESET), W))
    refs = reference if reference else T.fg(T.MUTED) + "none (repairs limited)" + T.RESET
    L.append(T.panel_row(f"  {T.fg(T.MUTED)}reference:{T.RESET} {refs}", W))
    L.append(T.panel_sep(W))
    L.append(T.panel_row(f"  {'#':>3}  {'SIZE':>9}  RESULT", W))
    shown = results[-(max(6, rows - 12)):]
    for n, c, state, outcome in shown:
        if state == "carved":
            tag = T.fg(T.GREEN) + "✔ playable" + T.RESET
        elif state == "repaired":
            tag = T.fg(T.CYAN) + f"✔ repaired ({outcome})" + T.RESET
        else:
            tag = T.fg(T.YELLOW) + "… raw-only" + T.RESET
        L.append(T.panel_row(f"  {n:>3}  {T.human_t(c['size']):>9}  {tag}", W))
    L.append(T.panel_bot(W))
    live.frame(L)


def _summary(results, good_dir, raw_dir):
    playable = sum(1 for _, _, s, _ in results if s in ("carved", "repaired"))
    rawonly = sum(1 for _, _, s, _ in results if s == "raw-only")
    print("\n" + T.bold(T.fg(T.TITLE) + "  video recovery summary" + T.RESET))
    T.ok(f"{playable} playable clip(s) → {good_dir}")
    if rawonly:
        T.warn(f"{rawonly} clip(s) could not be repaired → raw carves in {raw_dir}")
        T.info("provide a reference clip from the same camera + install untrunc, then re-run.")


if __name__ == "__main__":
    main()
