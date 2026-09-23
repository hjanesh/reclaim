# Reclaim

**A terminal-native data-recovery toolkit for photos & video — with live, colourful dashboards.**

Reclaim packages a battle-tested recovery workflow into one menu-driven CLI: image a failing
card/SSD, carve back your photos, find and rebuild video clips, and sort everything by capture
date — all with live block-map dashboards so you can actually *see* what's happening. It was
built while recovering a reformatted 128 GB SD card full of Sony A7III RAW + 4K footage.

Runs on **macOS (Apple Silicon & Intel)** and **Linux**.

> **Golden rule:** Reclaim **never writes to your source**. Every source device/image is opened
> read-only, and recovered files must go to a *different* drive. When in doubt, image first and
> work from the copy.

---

## Features

| # | Tool | What it does |
|---|------|--------------|
| 1 | **Image a disk/card** | `ddrescue` clone to an image file, with a live neon block-map (rate/ETA, bad-sector map). Work from the image afterwards. |
| 2 | **Recover photos & files** | `photorec` signature carving with a live "haul" dashboard (RAW/JPEG/Video/Audio rollups, per-format table). |
| 3 | **Detect videos** | Scans an image for MP4/MOV clips (Sony XAVC S etc.), showing which are **complete** vs **truncated/fragmented**. |
| 4 | **Recover videos** | Carves complete clips (they play immediately) and repairs broken ones with **untrunc** + `ffmpeg`. |
| 5 | **Organize photos** | Relabels Sony RAW that carving named `.sr2/.tif` → `.arw`, and sorts everything into `YYYY-MM-DD/` folders by EXIF capture date. |
| 6 | **Show disks** | Lists attached drives (internal vs external) so you pick the right one. |

All dashboards share one theme: a steel-framed panel, a green gradient loader, and a
defrag/torrent-style block grid that fills as work progresses.

---

## Install

```bash
git clone https://github.com/hjanesh/reclaim
cd reclaim
./install.sh          # installs ddrescue, photorec, ffmpeg, exiftool, python3 (+ best-effort untrunc)
python3 reclaim.py
```

- **macOS** uses Homebrew (the installer offers to set it up if missing).
- **Linux** uses `apt`.
- `untrunc` (fragmented-video rebuild) is built from source best-effort; if it fails, everything
  else still works and broken-video repair falls back to `ffmpeg`.

---

## The typical recovery flow

1. **Image the media first** (menu **1**). Imaging touches the card/SSD exactly once; all further
   work reads the safe copy. Use a fast, direct **USB-C/Thunderbolt** port — cheap hubs can stall.
2. **Recover photos** (menu **2**) from the image → a folder on another drive.
3. **Detect videos** (menu **3**) to see how many clips survived and their state.
4. **Recover videos** (menu **4**) — complete clips carve cleanly; for broken ones, supply a
   short **reference clip shot on the same camera in the same mode** so `untrunc` can rebuild them.
5. **Organize** (menu **5**) — relabel Sony RAW and sort into dated folders.

You can also point the photo/video steps directly at a raw image you already have.

---

## Safety model

- Sources are opened **read-only** in code (`open(..., 'rb')`, `ddrescue` reads only, `photorec`
  opens read-only). No repair/format/fsck is ever run on your media.
- The tool **refuses** to write output to the same path as the source.
- SD cards don't support TRIM, so a quick/in-camera format usually leaves the data fully intact —
  Reclaim is built around that. (SSDs *do* TRIM; a reformatted SSD is often unrecoverable — image
  it and check, but temper expectations.)

See [docs/SAFETY.md](docs/SAFETY.md) for the full philosophy and the gotchas we hit.

---

## Platform notes

- Developed and syntax-tested on Linux; the macOS-specific device paths (`diskutil`, `/dev/rdiskN`)
  are validated on Apple Silicon. Image-based photo/video recovery is pure Python + `photorec` and
  behaves identically on both.
- Terminal must support 24-bit colour (any modern macOS Terminal/iTerm2 or Linux terminal).

---

## Repo layout

```
reclaim.py            main menu
install.sh            dependency installer (macOS/Linux)
lib/
  theme.py            shared UI (palette, panels, live redraw, prompts)
  platform_utils.py   OS + disk listing (diskutil / lsblk)
  mp4.py              MP4/MOV atom scan/carve logic
  ddwatch.py          ddrescue live dashboard
  phrec_watch.py      photorec live dashboard
  scan_mp4.py         video-clip finder dashboard
  video_recover.py    carve + repair videos
  organize.py         relabel + date-sort
docs/USAGE.md         step-by-step
docs/SAFETY.md        the read-only / imaging philosophy
```

Each `lib/*.py` also runs standalone, e.g. `python3 lib/scan_mp4.py image.img 60`.

---

## License

[MIT](LICENSE) © 2026 Hemanth Janesh. Contributions welcome.

Built on the shoulders of [GNU ddrescue](https://www.gnu.org/software/ddrescue/),
[TestDisk/PhotoRec](https://www.cgsecurity.org/), [FFmpeg](https://ffmpeg.org/),
[ExifTool](https://exiftool.org/), and [untrunc](https://github.com/anthwlock/untrunc).
