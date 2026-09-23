#!/usr/bin/env python3
"""
phrec_watch.py — live themed dashboard for a PhotoRec recovery run.

Reads ONLY the recovered output folder (counts files/sizes). Zero load on
PhotoRec, never touches the source. Shows an approximate progress bar,
totals + rate, category rollup (RAW/JPEG/Video/Audio/Other) and a per-format
table.

Usage:  python3 phrec_watch.py <recovered_dir> [expected_GB]
"""
import sys, os, time
import theme as T

CATS = [
    ("RAW",   T.GREEN,  {"cr2","cr3","nef","arw","raf","orf","rw2","dng","tif","tiff",
                         "pef","srw","x3f","3fr","mef","iiq","mos","nrw","sr2","srf"}),
    ("JPEG",  T.BLUE,   {"jpg","jpeg","png","heic","heif","gif","bmp","webp"}),
    ("Video", T.PURPLE, {"mov","mp4","avi","mts","m2ts","mxf","3gp","mpg","mpeg",
                         "mkv","wmv","m4v"}),
    ("Audio", T.YELLOW, {"wav","mp3","aac","m4a","flac","ogg","wma"}),
]


def cat_of(ext):
    for name, col, exts in CATS:
        if ext in exts:
            return name, col
    return "Other", T.MUTED


def scan_dir(root):
    exts = {}; nf = nb = folders = 0
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if os.path.basename(e.path).startswith("recup"):
                                folders += 1
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            sz = e.stat().st_size
                            ext = os.path.splitext(e.name)[1].lower().lstrip(".") or "?"
                            r = exts.setdefault(ext, [0, 0]); r[0] += 1; r[1] += sz
                            nf += 1; nb += sz
                    except OSError:
                        pass
        except OSError:
            pass
    return exts, nf, nb, folders


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    target = (float(sys.argv[2]) if len(sys.argv) > 2 else 50) * 1024**3
    hist = []; t0 = time.time()
    live = T.Live()
    try:
        with live:
            while True:
                cols, rows = T.term()
                W = max(52, min(100, cols - 2))
                exts, nf, nb, folders = scan_dir(root)
                now = time.time(); hist.append((now, nb))
                hist[:] = [h for h in hist if now - h[0] <= 30]
                rate = None
                if len(hist) >= 2 and hist[-1][0] > hist[0][0]:
                    rate = (hist[-1][1] - hist[0][1]) / (hist[-1][0] - hist[0][0])

                cat = {n: [0, 0] for n, _, _ in CATS}; cat["Other"] = [0, 0]
                col_of = {n: c for n, c, _ in CATS}; col_of["Other"] = T.MUTED
                for ext, (c, b) in exts.items():
                    nm, _ = cat_of(ext); cat[nm][0] += c; cat[nm][1] += b
                maxcat = max((v[1] for v in cat.values()), default=1) or 1
                pct = min(100.0, nb / target * 100) if target else 0
                el = int(now - t0)
                elapsed = (f"{el//3600}h {el%3600//60:02d}m" if el >= 3600
                           else f"{el//60}m {el%60:02d}s")

                L = T.panel_top(W, "photorec", "recovery haul")
                L.append(T.panel_row(" " + T.hbar(nb / target if target else 0, W - 11, T.GREEN) +
                                     " " + T.bold(T.fg(T.GREEN) + f"{pct:5.1f}%" + T.RESET), W))
                L.append(T.panel_row(T.fg(T.MUTED) +
                         f"   recovered ≈ {T.human_t(nb)} of ~{T.human_t(target)} expected" + T.RESET, W))
                L.append(T.panel_sep(W))
                rs = (T.human(rate) + "/s") if rate else "  --  "
                L.append(T.panel_row(
                    f"  {T.chip(T.CYAN)} files {T.bold(str(nf)):>7}"
                    f"    {T.chip(T.GREEN)} size {T.bold(T.human_t(nb)):>10}", W))
                L.append(T.panel_row(
                    f"  {T.chip(T.PURPLE)} rate {rs:>9}"
                    f"    {T.chip(T.MUTED)} folders {folders:>4}     {T.fg(T.MUTED)}elapsed {elapsed}{T.RESET}", W))
                L.append(T.panel_sep(W))
                L.append(T.panel_row(T.fg(T.MUTED) + "  by category" + T.RESET, W))
                barw = W - 34
                for nm, _, _ in CATS + [("Other", T.MUTED, set())]:
                    c, b = cat[nm]
                    L.append(T.panel_row(
                        f"  {T.chip(col_of[nm])} {nm:<6} {c:>6}  {T.human(b)}  "
                        + T.hbar(b / maxcat, max(6, barw), col_of[nm]), W))
                L.append(T.panel_sep(W))
                L.append(T.panel_row(T.fg(T.MUTED) + "  by format (top by size)" + T.RESET, W))
                rowsx = sorted(exts.items(), key=lambda kv: kv[1][1], reverse=True)[:10]
                maxext = rowsx[0][1][1] if rowsx else 1
                for ext, (c, b) in rowsx:
                    _, col = cat_of(ext)
                    L.append(T.panel_row(
                        f"   {T.fg(col)}{ext:<5}{T.RESET} {c:>6}  {T.human(b)}  "
                        + T.hbar(b / (maxext or 1), max(6, W - 34), col), W))
                if not rowsx:
                    L.append(T.panel_row(T.fg(T.MUTED) + "   (waiting for first files…)" + T.RESET, W))
                L.append(T.panel_bot(W))
                L.append(T.fg(T.MUTED) + "  reads output folder only · no load on photorec · Ctrl-C to quit" + T.RESET)
                live.frame(L)
                time.sleep(2)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
