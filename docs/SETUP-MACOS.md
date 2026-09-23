# Reclaim — macOS setup from scratch (Apple Silicon: M1/M2/M3/M4)

This is for a **brand-new Mac with nothing installed** — no git, no dev tools. Follow it top to
bottom. You'll paste commands into **Terminal**.

> Open Terminal: press **⌘ Space**, type `Terminal`, press **Return**.
>
> When a command asks for your **Mac login password**, type it and press Return — the characters
> stay invisible as you type. That's normal.

---

## 1. Install Apple's Command Line Tools  (gives you `git`, `make`, compilers)

```bash
xcode-select --install
```

A dialog appears → click **Install** → agree → wait (5–15 min). When it's done, verify:

```bash
git --version
```

You should see a version number. (If it says "command not found", the install didn't finish —
re-run the command.)

---

## 2. Install Homebrew  (the macOS package manager)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Enter your password when asked and let it finish. Then **add Homebrew to your shell** (Apple
Silicon installs to `/opt/homebrew`):

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

---

## 3. Download Reclaim

```bash
cd ~
git clone https://github.com/hjanesh/reclaim
cd reclaim
```

---

## 4. Install Reclaim's tools

```bash
./install.sh
```

This installs everything Reclaim needs:

| Tool | Purpose |
|------|---------|
| `ddrescue` | disk/card imaging |
| `testdisk` / `photorec` | photo & file carving |
| `ffmpeg` | video remux/repair |
| `exiftool` | sort photos by capture date |
| `python3` | runs the toolkit |
| `untrunc` | rebuild broken videos (best-effort build; optional) |

Takes a few minutes. At the end it prints a **readiness check** — every core tool should show a
green ✔. `untrunc` may show a yellow ⚠ (that's fine; complete clips still carve and `ffmpeg`
handles remux).

---

## 5. (Optional) A nicer terminal for the colours

Reclaim uses 24-bit colour. macOS Terminal works, but **iTerm2** looks best:

```bash
brew install --cask iterm2
```

Then reopen these steps inside iTerm2.

---

## 6. Connect the SSD and find the image

1. Plug the **SanDisk SSD** into a **direct USB-C / Thunderbolt port** (not a cheap hub — hubs can
   stall large reads).
2. Find the `lexar-card.img` on it:

```bash
ls -lh /Volumes/*/lexar-card.img
```

Copy the full path it prints (e.g. `/Volumes/Untitled1/lexar-card.img`). You'll paste it into the
menu.

---

## 7. Run Reclaim

```bash
python3 reclaim.py
```

You'll get the menu. For finishing this recovery, go in this order:

1. **3) Detect videos** → paste the image path → scan `60` GB. See how many clips are
   **COMPLETE** vs **truncated**.
2. **4) Recover videos** → image path → an **output folder** (e.g. `/Volumes/Untitled1/recovered-video`)
   → optionally **reference clip(s)** (see below). Reuses the Detect scan (no re-scan). Complete
   clips carve straight to playable `.mp4`; broken ones are repaired.
3. **2) Recover photos & files** → image path → output folder — only if you want to re-run the
   photo carve (your stills were already recovered earlier).
4. **5) Organize photos** → point it at the recovered folder → it relabels Sony RAW `.sr2/.tif` →
   `.arw` and sorts everything into `YYYY-MM-DD/` folders (dry-run first, then apply).
5. **6) Rename to original names** (optional) → gives files their original names where the camera
   embedded them, otherwise clean timestamp-based names.

---

## Reference clip (makes broken videos recoverable)

For truncated/fragmented clips, `untrunc` rebuilds them using a **known-good clip from the same
camera in the same mode**. On the **Sony A7III**, shoot a ~15 s throwaway clip in **each mode you
used** (e.g. 4K 25p, and the other).

- **One mode** → give the single reference file's path when menu 4 asks.
- **Multiple modes** → put all the reference clips in **one folder** and give the **folder** path;
  Reclaim tries each reference against each broken clip until one rebuilds it.

Copy the reference clip(s) anywhere on the Mac (e.g. `~/refs/`) first, then give that file/folder
path in menu 4.

---

## Troubleshooting

- **`xcode-select: command not found`** → your macOS is very old; update it in
  System Settings → General → Software Update, then retry step 1.
- **Homebrew "command not found" after install** → you skipped the `~/.zprofile` lines in step 2;
  run them, or just close and reopen Terminal.
- **untrunc "cannot be opened because the developer cannot be verified"** → run
  `xattr -d com.apple.quarantine ./bin/untrunc` (or System Settings → Privacy & Security →
  **Allow Anyway**). Not needed if untrunc didn't build — `ffmpeg` still handles remux.
- **"Permission denied" reading a device** → recovering from the **image file** needs no `sudo`.
  Only imaging a live disk (menu 1) needs `sudo` + Terminal granted **Full Disk Access** in
  System Settings → Privacy & Security.
- **Colours look broken / boxes misaligned** → use iTerm2, or widen the window; the panels
  auto-fit but need a 24-bit-colour terminal.
- **`python3: command not found`** → step 1 (Command Line Tools) provides it; if still missing,
  `brew install python`.

---

## One-shot version (for the confident)

```bash
xcode-select --install                                            # then finish the GUI installer
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile && eval "$(/opt/homebrew/bin/brew shellenv)"
git clone https://github.com/hjanesh/reclaim && cd reclaim
./install.sh
python3 reclaim.py
```
