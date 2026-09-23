# Reclaim

A terminal data recovery toolkit for photos and video, with live dashboards.

Reclaim packages a complete recovery workflow into one menu driven CLI: image a failing card or
SSD, carve back your photos, find and rebuild video clips, and sort everything by capture date.
Each long running step shows a live block map so you can see progress, rate, and results. It was
built while recovering a reformatted 128 GB SD card of Sony A7III RAW and 4K footage.

Supports macOS (Apple Silicon and Intel) and Linux.

> Golden rule: Reclaim never writes to your source. Every source device or image is opened read
> only, and recovered files go to a different location. When in doubt, image first and work from
> the copy.

## Features

| # | Tool | What it does |
|---|------|--------------|
| 1 | Image a disk or card | `ddrescue` clone to an image file, with a live block map (rate, ETA, bad sector map). |
| 2 | Recover photos and files | `photorec` signature carving with a live dashboard (RAW/JPEG/Video/Audio rollups, per format table). |
| 3 | Detect videos | Scans an image for MP4/MOV clips and reports which are complete vs truncated. Caches the result. |
| 4 | Recover videos | Carves complete clips (play immediately) and repairs broken ones with untrunc (multiple references supported) and ffmpeg. Reuses the Detect cache. |
| 5 | Organize photos | Relabels Sony RAW carved as `.sr2`/`.tif` to `.arw`, and sorts into `YYYY-MM-DD/` folders by EXIF capture date. |
| 6 | Rename to original names | Restores original filenames from embedded metadata where cameras store them, otherwise builds clean timestamp based names. |
| 7 | Show disks | Lists attached drives so you can pick the right one. |

Steps are independent and resumable. Scan for videos one day and carve them another. `ddrescue`
and `photorec` resume from their map and session files. See
[docs/USAGE.md](docs/USAGE.md#running-steps-on-different-days).

## Install

```bash
git clone https://github.com/hjanesh/reclaim
cd reclaim
./install.sh
python3 reclaim.py
```

- New Mac with nothing installed? Follow [docs/SETUP-MACOS.md](docs/SETUP-MACOS.md), a from zero
  guide (Xcode tools, Homebrew, git, then Reclaim).
- macOS uses Homebrew. Linux uses `apt`.
- `install.sh` installs `ddrescue`, `photorec` (from `testdisk`), `ffmpeg`, `exiftool`, and
  `python3`, and builds `untrunc` best effort. If untrunc does not build, complete clips still
  carve and broken video repair falls back to ffmpeg.

## Choosing paths

Every path prompt accepts three things:

- Type or paste a path.
- Press `f` to open a native file or folder picker (Finder on macOS, zenity or kdialog on Linux).
- Press `b` to go back to the menu.

Output prompts default to a folder inside the repo (`output/photos`, `output/videos`, and so on),
which is git ignored. Press Enter to accept the default, or type/pick anywhere else.

## Typical recovery flow

1. Image the media first (option 1). This touches the card or SSD once; all further work reads the
   safe copy. Use a fast, direct USB-C or Thunderbolt port. Cheap or USB 2.0 cables cap throughput.
2. Recover photos (option 2) from the image.
3. Detect videos (option 3) to see how many clips survived and their state.
4. Recover videos (option 4). Complete clips carve cleanly. For broken ones, supply reference
   clips shot on the same camera in the same mode (a single file or a folder of references).
5. Organize (option 5) or Rename (option 6) to tidy the results.

## Dashboards and background tools

The live dashboard is the source of truth. `photorec` and `ddrescue` are launched detached, with
their own output written to a log file in the output folder (for example
`output/photos/photorec_run.log`), so their text UI cannot interfere with the dashboard.

## Safety model

- Sources are opened read only in code. No repair, format, or fsck is run on your media.
- The tool refuses to write output to the same path as the source.
- SD cards generally do not support TRIM, so a quick or in camera format usually leaves the data
  intact, which is why recovery works. SSDs do support TRIM, so a reformatted SSD is often
  unrecoverable. Image it and check, but set expectations low.

See [docs/SAFETY.md](docs/SAFETY.md) for the full philosophy and known gotchas.

## Repo layout

```
reclaim.py            main menu
install.sh            dependency installer (macOS and Linux)
lib/
  theme.py            shared UI (palette, panels, live redraw, prompts, picker)
  platform_utils.py   OS, disk listing, native picker
  mp4.py              MP4/MOV atom scan, carve, and clip cache
  ddwatch.py          ddrescue dashboard
  phrec_watch.py      photorec dashboard
  scan_mp4.py         video clip finder dashboard
  video_recover.py    carve and repair videos
  organize.py         relabel and date sort
  rename.py           restore original filenames
docs/USAGE.md         step by step
docs/SAFETY.md        read only and imaging philosophy
docs/SETUP-MACOS.md   from zero macOS setup
```

Each `lib/*.py` also runs standalone, for example `python3 lib/scan_mp4.py image.img 60`.

## License

[MIT](LICENSE), 2026 Hemanth Janesh. Contributions welcome.

Built on [GNU ddrescue](https://www.gnu.org/software/ddrescue/),
[TestDisk and PhotoRec](https://www.cgsecurity.org/), [FFmpeg](https://ffmpeg.org/),
[ExifTool](https://exiftool.org/), and [untrunc](https://github.com/anthwlock/untrunc).
