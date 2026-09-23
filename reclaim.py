#!/usr/bin/env python3
"""
reclaim.py - Reclaim, a terminal-native data-recovery toolkit.

A themed menu over the pieces we use to recover photos & video from a damaged
or reformatted card/SSD:

  1) Image a disk/card   (ddrescue + live dashboard)
  2) Recover photos      (photorec + live dashboard)
  3) Detect videos       (MP4/MOV clip finder)
  4) Recover videos      (carve complete + repair broken)
  5) Organize photos     (relabel Sony RAW + sort by date)
  6) Rename to original names (restore filenames from metadata)
  7) Show disks

Design rule: sources are ALWAYS opened read-only; output must differ from the
source. Prefer imaging first, then recover from the image.
"""
import sys, os, subprocess, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lib")
sys.path.insert(0, LIB)

import theme as T            # noqa: E402
import platform_utils as P   # noqa: E402

OUTPUT_ROOT = os.path.join(HERE, "output")


def default_out(name):
    """Default output location inside the repo. Users can type/pick another."""
    return os.path.join(OUTPUT_ROOT, name)


def have(cmd): return shutil.which(cmd) is not None


def need(cmd):
    if not have(cmd):
        T.err(f"'{cmd}' is not installed.")
        T.info("run  ./install.sh  first to install dependencies.")
        T.pause()
        return False
    return True


def run_py(script, *args):
    subprocess.run([sys.executable, os.path.join(LIB, script), *args])


def sudo_prefix(source):
    """Return ['sudo'] if the source is a raw device (needs root), else []."""
    return ["sudo"] if str(source).startswith("/dev/") else []


def diff_paths(a, b):
    return os.path.abspath(a) != os.path.abspath(b)


# ---------------------------------------------------------------------------
def do_image():
    T.clear(); T.banner("Image a disk / card", "ddrescue → image file (source read-only)")
    if not need("ddrescue"):
        return
    disks = P.list_disks()
    if disks:
        W = min(T.term()[0] - 2, 78)
        print(T.panel_sep(W))
        for i, d in enumerate(disks, 1):
            tag = T.fg(T.YELLOW) + "internal" + T.RESET if d.get("internal") else T.fg(T.GREEN) + "external" + T.RESET
            print(T.panel_row(f"  {T.fg(T.CYAN)}{i}{T.RESET})  {d['node']:<14} "
                              f"{T.human_t(d['size']):>9}  {tag}  {d.get('model','')}", W))
        print(T.panel_bot(W))
        T.warn("pick the SOURCE to image. Double-check - never pick your system disk.")
        sel = T.ask("source disk number (or blank to type a /dev path)")
        source = ""
        if sel.isdigit() and 1 <= int(sel) <= len(disks):
            source = disks[int(sel) - 1]["node"]
    else:
        T.warn("could not auto-list disks; enter the device path manually.")
        source = ""
    if not source:
        source = T.ask("source device path (e.g. /dev/sdb or /dev/disk4)")
    if not source:
        return
    img = T.ask_path("destination image file (on ANOTHER drive)", must_exist=False,
                     default=default_out("card.img"), pick_kind="save")
    if not img:
        return
    if not diff_paths(source, img):
        T.err("destination must differ from source."); T.pause(); return
    mapf = img[:-4] + ".map" if img.endswith(".img") else img + ".map"
    raw = P.raw_node(source)
    os.makedirs(os.path.dirname(img) or ".", exist_ok=True)

    T.info(f"source (read-only): {raw}")
    T.info(f"image  : {img}")
    T.info(f"mapfile: {mapf}")
    T.warn(f"the source will be unmounted first ({P.unmount_hint(source)}).")
    if not T.confirm("start imaging?", default=False):
        return
    ok, msg = P.unmount(source)
    if not ok:
        T.warn(f"unmount reported: {msg}")
        if not T.confirm("continue anyway?", default=False):
            return

    cmd = sudo_prefix(raw) + ["ddrescue", "--no-scrape", raw, img, mapf]
    if cmd and cmd[0] == "sudo":
        subprocess.run(["sudo", "-v"])   # cache credentials so the dashboard isn't interrupted
    T.info("launching ddrescue (detached) + live dashboard … (Ctrl-C the dashboard to detach)")
    # detach from the terminal so ddrescue's progress can't corrupt the dashboard
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        run_py("ddwatch.py", mapf, img)
    except KeyboardInterrupt:
        pass
    if proc.poll() is None:
        if T.confirm("dashboard closed - wait for ddrescue to finish?", default=True):
            proc.wait()
    T.ok("imaging step done."); T.pause()


def do_photorec():
    T.clear(); T.banner("Recover photos & files", "photorec (source read-only) → output dir")
    if not need("photorec"):
        return
    source = T.ask_path("source: image file OR device (e.g. lexar-card.img / /dev/sdb)",
                        must_exist=not_dev())
    if not source:
        return
    out = T.ask_path("output directory (on ANOTHER drive)", must_exist=False,
                     default=default_out("photos"))
    if not out:
        return
    if not diff_paths(source, out):
        T.err("output must differ from source."); T.pause(); return
    os.makedirs(out, exist_ok=True)
    exp = T.ask("approx expected data size in GB (for the progress bar)", default="50")

    cmd = sudo_prefix(source) + [
        "photorec", "/log", "/d", os.path.join(out, "recup"),
        "/cmd", source, "partition_none,fileopt,everything,enable,search"]
    if cmd and cmd[0] == "sudo":
        subprocess.run(["sudo", "-v"])
    logpath = os.path.join(out, "photorec_run.log")
    T.info("launching photorec (detached) + live dashboard …")
    T.info(f"photorec's own output is logged to {logpath} (kept off the dashboard).")
    T.info("photorec runs to completion; Ctrl-C the dashboard when it's done.")
    T.pause("press enter to start")
    # Detach photorec from the terminal so its text UI can't corrupt the dashboard:
    # new session (no controlling tty) + output to a log file + no stdin.
    lf = open(logpath, "wb")
    proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, start_new_session=True)
    lf.close()
    try:
        run_py("phrec_watch.py", out, exp or "50")
    except KeyboardInterrupt:
        pass
    if proc.poll() is None:
        T.warn("dashboard closed but photorec is still running.")
        if T.confirm("wait for photorec to finish?", default=True):
            proc.wait()
    T.ok(f"photo recovery done → {out}"); T.pause()


def not_dev():
    # photorec source may be a device (won't exist as a file) - allow non-file too
    return False


def do_scan_video():
    T.clear(); T.banner("Detect videos", "scan an image for MP4/MOV clips (read-only)")
    img = T.ask_path("image file to scan", want="file")
    if not img:
        return
    gb = T.ask("how many GB from the start to scan", default="60")
    run_py("scan_mp4.py", img, gb or "60")
    T.pause()


def do_recover_video():
    T.clear(); T.banner("Recover videos", "carve complete clips + repair broken (read-only source)")
    img = T.ask_path("image file", want="file")
    if not img:
        return
    out = T.ask_path("output directory (on ANOTHER drive)", must_exist=False,
                     default=default_out("videos"))
    if not out:
        return
    if not diff_paths(img, out):
        T.err("output must differ from the image."); T.pause(); return
    ref = ""
    if T.confirm("do you have reference clip(s) to repair broken videos?", default=False):
        T.info("give a single .mp4/.mov file, OR a FOLDER containing several references")
        T.info("(one per recording mode - e.g. 4K 25p and 4K 24p; the tool tries each).")
        ref = T.ask_path("reference file or folder", must_exist=True, want="any", default="")
    gb = T.ask("how many GB from the start to scan", default="60")
    run_py("video_recover.py", img, out, ref or "", gb or "60")
    T.pause()


def do_organize():
    T.clear(); T.banner("Organize photos", "relabel Sony RAW + sort by capture date")
    root = T.ask_path("folder of recovered files", want="dir")
    if not root:
        return
    out = T.ask_path("output folder for dated structure", must_exist=False,
                     default=default_out("organized"))
    if not out:
        return
    if not diff_paths(root, out):
        T.err("output must differ from the source folder."); T.pause(); return
    run_py("organize.py", root, out)     # dry-run first
    if T.confirm("apply these moves now?", default=False):
        run_py("organize.py", root, out, "--apply")
    T.pause()


def do_rename():
    T.clear(); T.banner("Rename to original names",
                        "restore filenames from embedded metadata (best-effort)")
    if not need("exiftool"):
        return
    root = T.ask_path("folder of recovered files", want="dir")
    if not root:
        return
    out = T.ask_path("output folder for renamed files", must_exist=False,
                     default=default_out("renamed"))
    if not out:
        return
    if not diff_paths(root, out):
        T.err("output must differ from the source folder."); T.pause(); return
    run_py("rename.py", root, out)     # dry-run first
    if T.confirm("apply these renames now?", default=False):
        run_py("rename.py", root, out, "--apply")
    T.pause()


def do_disks():
    T.clear(); T.banner("Disks", P.os_name())
    disks = P.list_disks()
    if not disks:
        T.warn("could not list disks on this platform."); T.pause(); return
    W = min(T.term()[0] - 2, 78)
    print(T.panel_row(f"  {'NODE':<16}{'SIZE':>10}  {'TYPE':<9} MOUNT / MODEL", W))
    print(T.panel_sep(W))
    for d in disks:
        tag = "internal" if d.get("internal") else "external"
        col = T.YELLOW if d.get("internal") else T.GREEN
        info = d.get("mount") or d.get("model") or ""
        print(T.panel_row(f"  {d['node']:<16}{T.human_t(d['size']):>10}  "
                          f"{T.fg(col)}{tag:<9}{T.RESET} {info}", W))
    print(T.panel_bot(W))
    T.pause()


MENU = [
    ("1", "Image a disk / card", "ddrescue → image file, with live dashboard"),
    ("2", "Recover photos & files", "photorec carve, with live haul dashboard"),
    ("3", "Detect videos", "find MP4/MOV clips in an image"),
    ("4", "Recover videos", "carve complete clips + repair broken ones"),
    ("5", "Organize photos", "relabel Sony RAW + sort by capture date"),
    ("6", "Rename to original names", "restore filenames from embedded metadata"),
    ("7", "Show disks", "list attached drives"),
    ("q", "Quit", ""),
]

ACTIONS = {
    "1": do_image, "2": do_photorec, "3": do_scan_video,
    "4": do_recover_video, "5": do_organize, "6": do_rename, "7": do_disks,
}


def main():
    while True:
        key = T.menu("RECLAIM · data recovery toolkit",
                     MENU, subtitle=f"{P.os_name()} · sources are read-only")
        if key == "q":
            print(); T.ok("bye - your sources were never modified."); break
        try:
            ACTIONS[key]()
        except KeyboardInterrupt:
            print(); T.warn("cancelled - back to menu.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
