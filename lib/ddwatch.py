#!/usr/bin/env python3
"""
ddwatch.py — live block-map for a GNU ddrescue run (themed).

Progress/rate come from the growing image file (smooth); the map file overlays
rare bad / non-trimmed / non-scraped regions. Reads image/map only — zero load
on ddrescue, never touches the source device.

Usage:  python3 ddwatch.py <mapfile> [imagefile]
"""
import sys, os, time
import theme as T

STATUS = set("+?*/-")


def parse_map(path):
    """total_bytes, overlays[list of (pos,size,status)] for non-good states."""
    total = 0; overlays = []
    try:
        with open(path) as f:
            data = f.read()
    except OSError:
        return 0, []
    for line in data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if len(p) >= 3 and p[0].startswith("0x") and p[1].startswith("0x") and p[2] in STATUS:
            pos = int(p[0], 16); size = int(p[1], 16)
            total = max(total, pos + size)
            if p[2] in "-/*":
                overlays.append((pos, size, p[2]))
    return total, overlays


def main():
    if len(sys.argv) < 2:
        print("usage: python3 ddwatch.py <mapfile> [imagefile]"); sys.exit(1)
    mapfile = sys.argv[1]
    imgfile = sys.argv[2] if len(sys.argv) > 2 else (
        mapfile[:-4] + ".img" if mapfile.endswith(".map") else mapfile + ".img")

    hist = []
    live = T.Live()
    try:
        with live:
            while True:
                cols, rows = T.term()
                W = max(52, min(100, cols - 2))
                tcols = W // 2
                trows = max(8, min(24, rows - 14))
                N = tcols * trows
                total, overlays = parse_map(mapfile)
                try:
                    cur = os.stat(imgfile).st_size
                except OSError:
                    cur = 0
                now = time.time(); hist.append((now, cur))
                hist[:] = [h for h in hist if now - h[0] <= 30]
                rate = eta = None
                if len(hist) >= 2 and hist[-1][0] > hist[0][0]:
                    r = (hist[-1][1] - hist[0][1]) / (hist[-1][0] - hist[0][0])
                    rate = r
                    if r > 1 and total:
                        eta = max(0, (total - cur) / r)

                cell = total / N if total else 1
                front = int(cur / cell) if total else -1
                pct = (cur / total * 100) if total else 0
                has_bad = any(c == "-" for _, _, c in overlays)

                def cellcol(i):
                    s = i * cell; e = (i + 1) * cell
                    for pos, size, ch in overlays:
                        if pos < e and pos + size > s:
                            return T.RED if ch == "-" else T.ORANGE if ch == "/" else T.YELLOW
                    if e <= cur:
                        return T.GREEN
                    if s >= cur:
                        return T.SLATE
                    return T.CYAN

                L = T.panel_top(W, "ddrescue", "live device image")
                L.append(T.panel_row(" " + T.gradient_bar(cur / total if total else 0, W - 11) +
                                     " " + T.bold(T.fg(T.GREEN) + f"{pct:5.1f}%" + T.RESET), W))
                rs = (T.human(rate) + "/s") if rate else "  --  "
                es = (f"{int(eta // 60)}m {int(eta % 60):02d}s" if eta else "--")
                L.append(T.panel_row(
                    f"  {T.chip(T.GREEN)} rescued {T.bold(T.human_t(cur)):>10} of {T.human_t(total)}"
                    f"    {T.chip(T.SLATE)} rate {rs}   {T.fg(T.MUTED)}eta {es}{T.RESET}", W))
                bad = sum(s for _, s, c in overlays if c == "-")
                bad_x = T.fg(T.RED) + "read errors!" + T.RESET if has_bad else T.fg(T.MUTED) + "errors: 0" + T.RESET
                L.append(T.panel_row(
                    f"  {T.chip(T.RED)} bad {T.human_t(bad):>10}   {bad_x}"
                    f"     {T.chip(T.CYAN)} pos {T.human_t(cur)}", W))
                L.append(T.panel_sep(W))
                for r in range(trows):
                    cells = ""
                    for c in range(tcols):
                        i = r * tcols + c
                        col = T.CYAN if i == front else cellcol(i)
                        cells += T.fg(col) + "■ "
                    L.append(T.panel_row(cells, W))
                L.append(T.panel_sep(W))
                L.append(T.panel_row(
                    f" {T.chip(T.GREEN)} rescued  {T.chip(T.SLATE)} pending  {T.chip(T.YELLOW)} non-trimmed"
                    f"  {T.chip(T.ORANGE)} non-scraped  {T.chip(T.RED)} bad  {T.chip(T.CYAN)} head", W))
                L.append(T.panel_bot(W))
                L.append(T.fg(T.MUTED) + "  reads image/map only · no load on ddrescue · Ctrl-C to quit" + T.RESET)
                live.frame(L)

                if total and cur >= total and not overlays:
                    sys.stdout.write("\n  " + T.fg(T.GREEN) +
                                     T.bold("✔ Imaging complete — device fully copied.") + T.RESET + "\n")
                    break
                time.sleep(2)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
