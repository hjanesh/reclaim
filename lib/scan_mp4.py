#!/usr/bin/env python3
"""
scan_mp4.py — READ-ONLY video-clip finder with a live themed dashboard.

Scans a disk image for MP4/MOV clips (Sony XAVC S etc.), showing a live block
map + stats, then prints a results table (complete vs truncated). Writes
NOTHING to the image. Uses the shared theme + mp4 modules.

Usage:  python3 scan_mp4.py <image> [scan_GB]
"""
import sys, os, time
import theme as T
import mp4


def main():
    if len(sys.argv) < 2:
        print("usage: python3 scan_mp4.py <image> [scan_GB]"); sys.exit(1)
    image = sys.argv[1]
    if not os.path.isfile(image):
        T.err(f"image not found: {image}"); sys.exit(1)
    img_size = os.path.getsize(image)
    limit = min((float(sys.argv[2]) if len(sys.argv) > 2 else 60) * 1024**3, img_size)

    clips = []
    st = {"pos": 0}
    hist = []
    last = [0.0]

    def render():
        cols, rows = T.term()
        W = max(52, min(100, cols - 2))
        tcols = W // 2
        trows = max(8, min(22, rows - 16))
        N = tcols * trows
        pos = st["pos"]
        pct = pos / limit * 100 if limit else 0
        comp = sum(1 for c in clips if c["state"] == "complete")
        trn = len(clips) - comp
        now = time.time()
        rate = eta = None
        if len(hist) >= 2 and hist[-1][0] > hist[0][0]:
            r = (hist[-1][1] - hist[0][1]) / (hist[-1][0] - hist[0][0])
            rate = r
            if r > 0:
                eta = max(0, (limit - pos) / r)
        cell = limit / N if limit else 1

        def cellcol(i):
            s = i * cell; e = (i + 1) * cell
            if s >= pos:
                return T.DARK
            best = T.SLATE
            for c in clips:
                if c["off"] < e and c["off"] + c["size"] > s:
                    if c["state"] == "complete":
                        return T.GREEN
                    best = T.RED if c["state"] == "fragment" else T.YELLOW
            if s <= pos < e:
                return T.CYAN
            return best

        L = T.panel_top(W, "scan_mp4", "video clip finder")
        L.append(T.panel_row(" " + T.gradient_bar(pos / limit if limit else 0, W - 11) +
                             " " + T.bold(T.fg(T.GREEN) + f"{pct:5.1f}%" + T.RESET), W))
        rs = (T.human(rate) + "/s") if rate else "  --  "
        es = (f"{int(eta // 60)}m {int(eta % 60):02d}s" if eta else "--")
        L.append(T.panel_row(
            f"  {T.chip(T.CYAN)} scanned {T.bold(T.human_t(pos)):>10} of {T.human_t(limit)}"
            f"    {T.chip(T.SLATE)} rate {rs}   {T.fg(T.MUTED)}eta {es}{T.RESET}", W))
        L.append(T.panel_row(
            f"  {T.chip(T.GREEN)} complete {T.bold(str(comp)):>4}"
            f"     {T.chip(T.YELLOW)} truncated {T.bold(str(trn)):>4}"
            f"     {T.chip(T.CYAN)} clips {T.bold(str(len(clips))):>4}", W))
        L.append(T.panel_sep(W))
        for r in range(trows):
            cells = "".join(T.fg(cellcol(r * tcols + c)) + "■ " for c in range(tcols))
            L.append(T.panel_row(cells, W))
        L.append(T.panel_sep(W))
        L.append(T.panel_row(
            f" {T.chip(T.GREEN)} complete  {T.chip(T.YELLOW)} truncated  {T.chip(T.RED)} fragment"
            f"  {T.chip(T.SLATE)} scanned  {T.chip(T.DARK)} not-yet  {T.chip(T.CYAN)} head", W))
        L.append(T.panel_bot(W))
        L.append(T.fg(T.MUTED) + "  reads image only · writes nothing · Ctrl-C to quit" + T.RESET)
        live.frame(L)

    def maybe():
        now = time.time()
        hist.append((now, st["pos"]))
        hist[:] = [h for h in hist if now - h[0] <= 15]
        if now - last[0] > 0.25:
            render(); last[0] = now

    def progress(pos, count):
        st["pos"] = pos; maybe()

    live = T.Live()
    try:
        with live:
            for clip in mp4.scan(image, limit, progress=progress):
                clips.append(clip); maybe()
            st["pos"] = limit; render()
    except KeyboardInterrupt:
        pass

    # ---- final table ----
    clips_sorted = sorted(clips, key=lambda c: c["off"])
    if mp4.save_clips(image, clips_sorted, st["pos"]):
        T.info(f"clip table cached → {os.path.basename(mp4.cache_path(image))} "
               f"(Recover will reuse it, no re-scan)")
    print("\n" + T.bold(T.fg(T.TITLE) + "  video clips found" + T.RESET))
    if not clips_sorted:
        T.warn("none > 512 KB in range — try a larger scan_GB, or clips are fragmented.")
        return
    print(T.fg(T.MUTED) + f"  {'#':>2}  {'OFFSET (GB)':>12}  {'SIZE':>10}  STATE      BRAND" + T.RESET)
    comp = 0
    for n, c in enumerate(clips_sorted, 1):
        if c["state"] == "complete":
            state = T.fg(T.GREEN) + "COMPLETE" + T.RESET; comp += 1
        elif c["state"] == "trunc":
            state = T.fg(T.YELLOW) + "trunc" + T.RESET
        else:
            state = T.fg(T.RED) + "fragment" + T.RESET
        print(f"  {n:>2}  {c['off']/1024**3:>12.3f}  {T.human_t(c['size']):>10}  "
              f"{state:<18} {c['brand']}")
    print(f"\n  {T.fg(T.GREEN)}{comp} complete{T.RESET} · "
          f"{T.fg(T.YELLOW)}{len(clips_sorted)-comp} need rebuild{T.RESET}")


if __name__ == "__main__":
    main()
