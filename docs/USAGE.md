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

The results are **cached** next to the image as `card.img.clips.json`, so **Recover videos** can
reuse them later without re-scanning (see [Running steps on different days](#running-steps-on-different-days)).

---

## 4) Recover videos  (video_recover)

- Reuses the cached clip table from **Detect** if present — otherwise it scans and caches it.
- **Complete** clips are carved straight to `<out>/videos/clip_NNN.mp4` and play immediately.
- **Broken** clips are carved raw to `<out>/videos_broken/`, then repaired:
  1. `untrunc <reference> <broken>` — needs a short reference clip shot on the **same camera in
     the same mode** (resolution/frame-rate/codec).
  2. `ffmpeg -c copy` remux as a fallback.

### Reference clips (for broken videos)

You can pass **either a single reference file or a whole folder of references**. If you shot in
**more than one mode** (e.g. 4K 25p *and* 4K 24p), put one short clip per mode in a folder and
point the tool at that folder — for each broken clip it **tries every reference** until one
rebuilds it.

```bash
python3 lib/video_recover.py card.img /out/dir reference.mp4          # one reference
python3 lib/video_recover.py card.img /out/dir /path/to/references/   # a folder of references
python3 lib/video_recover.py card.img /out/dir "" 60                  # no reference (carve complete only)
```

In the menu, option 4 asks *"do you have reference clip(s)?"* — answer yes and give the file **or
folder** path. Copy your reference clips to the Mac first (anywhere), then give that path.

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

## 6) Rename to original names  (rename)

Restores original filenames from embedded metadata. Some cameras store the on-card filename in
metadata (tags like `OriginalFileName`/`PreservedFileName`) — where present, the exact name is
restored. Many Sony bodies **don't** embed it, so those files get a clean, meaningful name built
from the capture timestamp + model (e.g. `DSC_20260921_143512.arw`). Also relabels `.sr2/.tif` → `.arw`.

```bash
python3 lib/rename.py /recovered/dir /named/dir            # dry-run (preview)
python3 lib/rename.py /recovered/dir /named/dir --apply    # actually rename/move
```

The output tells you how many names were **restored from metadata** vs **rebuilt from capture
time**. Run this *or* Organize (5) — Organize sorts into date folders; Rename gives friendly names.

---

## 7) Show disks

Lists attached drives (internal vs external) so you can confirm identifiers before imaging.

---

## Running steps on different days

**Yes — you can run steps separately and come back later.** Nothing has to be done in one sitting:

- **Detect (3) → Recover video (4):** Detect writes a cache (`<image>.clips.json`) next to the
  image. Recover reuses it automatically, so you can scan today and carve/repair tomorrow with **no
  re-scan**. (Delete that `.json` to force a fresh scan, e.g. after scanning more GB.)
- **Recover photos (2):** each run writes to its own output folder and completes in one pass. If
  `photorec` is interrupted, re-running continues from its saved session (`photorec.ses`).
- **Image a disk (1):** `ddrescue` is fully resumable via its `.map` file — re-run the same command
  to continue where it stopped.
- **Organize (5) / Rename (6):** stateless — they read a recovered folder and produce output; run
  them anytime, as many times as you like (they preview first, apply only when you confirm).

Each option is **independent** — you never have to re-run earlier steps to make a later one work.
