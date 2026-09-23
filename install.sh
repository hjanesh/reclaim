#!/usr/bin/env bash
#
# install.sh — install Reclaim's dependencies on macOS or Linux.
#
#   ddrescue   imaging
#   photorec   (from testdisk) file carving
#   ffmpeg     video remux/repair fallback
#   exiftool   capture-date sorting
#   python3    the toolkit itself
#   untrunc    fragmented-video reconstruction (best-effort build)
#
# Safe to re-run. untrunc is optional — the rest of the toolkit works without it.

set -u
REPO="$(cd "$(dirname "$0")" && pwd)"

c()  { printf "\033[38;2;%sm%s\033[0m" "$1" "$2"; }
ok() { printf "  \033[38;2;46;204;113m✔\033[0m %s\n" "$1"; }
inf(){ printf "  \033[38;2;26;232;255m›\033[0m %s\n" "$1"; }
wrn(){ printf "  \033[38;2;241;196;15m⚠\033[0m %s\n" "$1"; }
err(){ printf "  \033[38;2;231;76;60m✖\033[0m %s\n" "$1"; }
hdr(){ printf "\n\033[1m\033[38;2;236;240;245m%s\033[0m\n" "$1"; }

OS="$(uname -s)"
hdr "Reclaim installer — detected: $OS"

# ---------------------------------------------------------------------------
install_mac() {
  if ! command -v brew >/dev/null 2>&1; then
    wrn "Homebrew not found."
    read -r -p "  install Homebrew now? [y/N] " a
    if [[ "$a" =~ ^[Yy]$ ]]; then
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
      err "Homebrew is required on macOS. Aborting."; exit 1
    fi
  fi
  inf "installing core tools via Homebrew …"
  brew install ddrescue testdisk ffmpeg exiftool python || wrn "some brew installs failed"
}

install_linux() {
  if command -v apt-get >/dev/null 2>&1; then
    inf "installing core tools via apt …"
    sudo apt-get update -y
    sudo apt-get install -y gddrescue testdisk ffmpeg libimage-exiftool-perl \
                            python3 build-essential git pkg-config || wrn "some apt installs failed"
  else
    wrn "no apt-get found — install manually: ddrescue testdisk ffmpeg exiftool python3"
  fi
}

# ---------------------------------------------------------------------------
install_untrunc() {
  hdr "untrunc (fragmented-video repair) — best-effort"
  if command -v untrunc >/dev/null 2>&1; then ok "untrunc already installed"; return; fi
  for t in git make; do
    command -v "$t" >/dev/null 2>&1 || { wrn "missing '$t' — skipping untrunc build"; return; }
  done
  local work; work="${TMPDIR:-/tmp}/reclaim-untrunc"
  rm -rf "$work"
  inf "cloning anthwlock/untrunc …"
  git clone --depth 1 https://github.com/anthwlock/untrunc "$work" >/dev/null 2>&1 || {
    wrn "clone failed — skipping untrunc"; return; }
  ( cd "$work"
    if [ -f build.sh ]; then bash build.sh >/dev/null 2>&1 || true; fi
    [ -x untrunc ] || make >/dev/null 2>&1 || true )
  if [ -x "$work/untrunc" ]; then
    if sudo cp "$work/untrunc" /usr/local/bin/ 2>/dev/null; then
      ok "untrunc installed to /usr/local/bin"
    else
      mkdir -p "$REPO/bin"; cp "$work/untrunc" "$REPO/bin/"
      ok "untrunc built → $REPO/bin/untrunc  (add $REPO/bin to your PATH)"
    fi
  else
    wrn "untrunc build failed — that's OK: complete-clip carving + ffmpeg remux still work."
    inf "to build it later, see: https://github.com/anthwlock/untrunc"
  fi
}

# ---------------------------------------------------------------------------
case "$OS" in
  Darwin) install_mac ;;
  Linux)  install_linux ;;
  *) err "unsupported OS: $OS (macOS/Linux only)"; exit 1 ;;
esac
install_untrunc

# ---------------------------------------------------------------------------
hdr "readiness check"
allgood=1
for tool in python3 ddrescue photorec ffmpeg exiftool; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool"; else err "$tool  (missing)"; allgood=0; fi
done
if command -v untrunc >/dev/null 2>&1 || [ -x "$REPO/bin/untrunc" ]; then
  ok "untrunc"
else
  wrn "untrunc  (optional — broken-video repair limited to ffmpeg)"
fi

echo
if [ "$allgood" -eq 1 ]; then
  ok "all core tools ready — run:  python3 reclaim.py"
else
  wrn "some core tools are missing — re-run this script or install them manually."
fi
