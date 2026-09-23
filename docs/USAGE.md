# Reclaim — Usage

Run the menu:

```bash
python3 reclaim.py
```

Every option opens read-only on the source and asks for an output location on a **different**
drive. You can also run any module standalone (handy for scripting) — shown under each section.

---

## 1) Image a disk / card  (ddrescue)

Clones the whole device to an `.img` file plus a resumable `.map`, with a live dashboard.

- Pick the **source** from the list (or type `/dev/sdX` / `/dev/diskN`).
- Pick a **destination image** on another drive.
- The source is unmounted, then `ddrescue --no-scrape` runs. The dashboard reads the image/map
  only (no load on ddrescue). Green = rescued, cyan = current head, red = bad sector.

Standalone dashboard for an existing run:
```bash
python3 lib/ddwatch.py /path/to/card.map /path/to/card.img
```

**Tip:** use a direct USB-C/Thunderbolt port. Slow hubs can stall large reads.

---

## 2) Recover photos & files  (photorec)

Signature-carves files from an **image or device** into an output folder, with a live haul
dashboard (RAW/JPEG/Video/Audio rollups + per-format table).

- Source can be `card.img` or `/dev/sdX` (device needs sudo).
- Files land in `<out>/recup.1/`, `recup.2/`, …
- Sony A7III RAW is carved as `.sr2`/`.tif` here — menu 5 relabels them to `.arw`.

Standalone dashboard (point at the output folder while photorec runs):
```bash
python3 lib/phrec_watch.py /path/to/output 50     # 50 = expected GB, for the bar
```

---

## 3) Detect videos  (scan_mp4)

Scans an image for MP4/MOV clips and prints a table: each clip's offset, size, and state —
**COMPLETE** (has `moov`+`mdat`, will play) vs **truncated/fragment** (needs repair).

```bash
python3 lib/scan_mp4.py card.img 60      # scan the first 60 GB
```

---

## 4) Recover videos  (video_recover)

- **Complete** clips are carved straight to `<out>/videos/clip_NNN.mp4` and play immediately.
- **Broken** clips are carved raw to `<out>/videos_broken/`, then repaired:
  1. `untrunc <reference> <broken>` — needs a short reference clip shot on the **same camera in
     the same mode** (resolution/frame-rate/codec).
  2. `ffmpeg -c copy` remux as a fallback.

```bash
python3 lib/video_recover.py card.img /out/dir reference.mp4 60
```
Omit the reference to carve complete clips only.

---

## 5) Organize photos  (organize)

Relabels Sony RAW `.sr2/.tif` → `.arw` and sorts media into `<out>/YYYY-MM-DD/` by EXIF capture
date (falls back to file modification time if `exiftool` isn't present).

```bash
python3 lib/organize.py /recovered/dir /organized/dir            # dry-run (preview)
python3 lib/organize.py /recovered/dir /organized/dir --apply    # actually move
```

Dry-run first — it prints the per-day counts and a few example renames before you commit.

---

## 6) Show disks

Lists attached drives (internal vs external) so you can confirm identifiers before imaging.
