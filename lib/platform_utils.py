#!/usr/bin/env python3
"""
platform_utils.py - OS + device abstraction for Reclaim (macOS + Linux).

Only the "image a whole disk" flow needs real device handling; everything else
(photo/video recovery from an image) just needs a file path and is portable.
All helpers here are read-only w.r.t. the device.
"""
import sys, os, re, json, subprocess, plistlib, shutil

IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_WIN   = sys.platform.startswith("win")


def have(cmd):
    return shutil.which(cmd) is not None


def _run(args):
    return subprocess.run(args, capture_output=True, text=True)


def list_disks():
    """
    Return a list of dicts: {node, size, model, removable, mount}.
    Best-effort; returns [] if the platform tool is unavailable.
    """
    if IS_MAC:
        return _list_disks_mac()
    if IS_LINUX:
        return _list_disks_linux()
    if IS_WIN:
        return _list_disks_windows()
    return []


def _list_disks_mac():
    out = _run(["diskutil", "list", "-plist", "physical"])
    disks = []
    if out.returncode != 0:
        return disks
    try:
        data = plistlib.loads(out.stdout.encode())
    except Exception:
        return disks
    for ident in data.get("WholeDisks", []):
        info = _run(["diskutil", "info", "-plist", ident])
        try:
            d = plistlib.loads(info.stdout.encode())
        except Exception:
            continue
        disks.append({
            "node": f"/dev/{ident}",
            "size": int(d.get("TotalSize", 0)),
            "model": d.get("MediaName", "?"),
            "removable": bool(d.get("RemovableMedia", False)) or bool(d.get("Ejectable", False)),
            "mount": d.get("MountPoint", "") or "",
            "internal": bool(d.get("Internal", False)),
        })
    return disks


def _list_disks_linux():
    out = _run(["lsblk", "-J", "-b", "-o",
                "NAME,SIZE,MODEL,TYPE,RM,MOUNTPOINT,TRAN"])
    disks = []
    if out.returncode != 0:
        return disks
    try:
        data = json.loads(out.stdout)
    except Exception:
        return disks
    for d in data.get("blockdevices", []):
        if d.get("type") != "disk":
            continue
        mount = d.get("mountpoint") or ""
        if not mount:
            for c in d.get("children", []) or []:
                if c.get("mountpoint"):
                    mount = c["mountpoint"]; break
        disks.append({
            "node": f"/dev/{d['name']}",
            "size": int(d.get("size") or 0),
            "model": (d.get("model") or "?").strip(),
            "removable": str(d.get("rm")) in ("1", "True", "true"),
            "mount": mount,
            "internal": (d.get("tran") in (None, "sata", "nvme")) and str(d.get("rm")) not in ("1", "True", "true"),
        })
    return disks


def _powershell(script):
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def _list_disks_windows():
    # Imaging on Windows is best done from WSL2 (ddrescue is not native); this
    # listing is still useful for picking the right device. Best-effort.
    out = _powershell(
        "Get-Disk | Select-Object Number,FriendlyName,Size,BusType,IsSystem | ConvertTo-Json")
    disks = []
    if out.returncode != 0 or not out.stdout.strip():
        return disks
    try:
        data = json.loads(out.stdout)
    except Exception:
        return disks
    if isinstance(data, dict):
        data = [data]          # a single disk isn't wrapped in a list
    for d in data:
        bus = (d.get("BusType") or "")
        disks.append({
            "node": f"\\\\.\\PHYSICALDRIVE{d.get('Number', '?')}",
            "size": int(d.get("Size") or 0),
            "model": (d.get("FriendlyName") or "?").strip(),
            "removable": bus == "USB" or bus == "SD",
            "mount": "",
            "internal": bool(d.get("IsSystem")) or bus in ("SATA", "NVMe", "RAID", "SAS"),
        })
    return disks


def raw_node(node):
    """
    Fast raw device path for imaging.
    macOS: /dev/diskN -> /dev/rdiskN (character device, much faster with ddrescue).
    Linux: unchanged.
    """
    if IS_MAC and node.startswith("/dev/disk"):
        return node.replace("/dev/disk", "/dev/rdisk", 1)
    return node


def unmount(node):
    """Unmount a whole disk (all its volumes). Returns (ok, message)."""
    if IS_MAC:
        r = _run(["diskutil", "unmountDisk", node])
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    # Linux: try udisksctl per-partition, then umount fallback
    msgs = []
    ok = True
    # unmount the whole-disk mount if any, plus partitions
    r = _run(["lsblk", "-nro", "NAME,MOUNTPOINT", node])
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1]:
            dev = "/dev/" + parts[0]
            u = _run(["udisksctl", "unmount", "-b", dev])
            if u.returncode != 0:
                u = _run(["sudo", "umount", dev])
            ok = ok and (u.returncode == 0)
            msgs.append((u.stdout + u.stderr).strip())
    return ok, "\n".join(m for m in msgs if m) or "unmounted"


def unmount_hint(node):
    """Human hint for how to unmount, for display."""
    if IS_MAC:
        return f"diskutil unmountDisk {node}"
    if IS_WIN:
        return "eject the drive from Explorer, or image from WSL2"
    return f"udisksctl unmount -b {node}1   (repeat per partition)"


def default_image_hint():
    """A friendly default place to look for an image, per-OS."""
    home = os.path.expanduser("~")
    if IS_MAC:
        return "/Volumes/<drive>/lexar-card.img"
    return os.path.join(home, "lexar-card.img")


def os_name():
    if IS_MAC:
        return "macOS"
    if IS_LINUX:
        return "Linux"
    if IS_WIN:
        return "Windows"
    return sys.platform


def pick(kind="dir", prompt="Select"):
    """
    Open a native file/folder picker and return the chosen path (or "" if
    cancelled/unavailable). kind: 'file' | 'dir' | 'save'.
    macOS uses Finder via osascript; Linux uses zenity or kdialog.
    """
    prompt = prompt.replace('"', "'")
    if IS_WIN:
        if kind == "dir":
            ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                  "$d=New-Object System.Windows.Forms.FolderBrowserDialog;"
                  "if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}")
        else:
            cls = "SaveFileDialog" if kind == "save" else "OpenFileDialog"
            ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                  f"$d=New-Object System.Windows.Forms.{cls};"
                  "if($d.ShowDialog() -eq 'OK'){$d.FileName}")
        r = _powershell(ps)
        return r.stdout.strip() if r.returncode == 0 else ""
    if IS_MAC:
        if kind == "file":
            script = f'POSIX path of (choose file with prompt "{prompt}")'
        elif kind == "save":
            script = f'POSIX path of (choose file name with prompt "{prompt}")'
        else:
            script = f'POSIX path of (choose folder with prompt "{prompt}")'
        r = _run(["osascript", "-e", script])
        return r.stdout.strip() if r.returncode == 0 else ""
    if have("zenity"):
        args = ["zenity", "--file-selection", "--title", prompt]
        if kind == "dir":
            args.append("--directory")
        if kind == "save":
            args += ["--save", "--confirm-overwrite"]
        r = _run(args)
        return r.stdout.strip() if r.returncode == 0 else ""
    if have("kdialog"):
        flag = {"file": "--getopenfilename", "dir": "--getexistingdirectory",
                "save": "--getsavefilename"}[kind]
        r = _run(["kdialog", flag, os.path.expanduser("~")])
        return r.stdout.strip() if r.returncode == 0 else ""
    return ""


def has_picker():
    return IS_MAC or IS_WIN or have("zenity") or have("kdialog")


# ---------------------------------------------------------------------------
# Destination guards for imaging/carving: never write onto the source disk,
# and warn before a destination that can't hold the data.
# ---------------------------------------------------------------------------
def _whole_disk_id(node):
    """Normalize a /dev node to its whole-disk id: sdb1->sdb, disk4s2->disk4."""
    name = node.replace("/dev/r", "").replace("/dev/", "")
    if IS_MAC:
        m = re.match(r"(disk\d+)", name)
        return m.group(1) if m else name
    r = _run(["lsblk", "-no", "PKNAME", "/dev/" + name])
    for ln in r.stdout.splitlines():
        if ln.strip():
            return ln.strip()          # partition -> parent disk
    return name                        # already a whole disk


def backing_device(path):
    """The /dev source backing a filesystem path, or '' if not a real disk
    (network/tmpfs/unknown). Best-effort via `df`."""
    d = path if os.path.isdir(path) else (os.path.dirname(path) or ".")
    r = _run(["df", "-P", d])
    lines = r.stdout.splitlines()
    if len(lines) < 2:
        return ""
    dev = lines[1].split()[0] if lines[1].split() else ""
    return dev if dev.startswith("/dev/") else ""


def same_device(source_node, dest_path):
    """True if dest_path physically resides on source_node's disk (the classic
    'imaging a card back onto itself' footgun). Conservative: False if unknown."""
    dev = backing_device(dest_path)
    if not dev:
        return False
    return _whole_disk_id(dev) == _whole_disk_id(source_node)


def free_space(path):
    """Free bytes on the filesystem holding `path` (its nearest existing parent),
    or None if it can't be determined."""
    p = path if os.path.exists(path) else (os.path.dirname(path) or ".")
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(p or ".").free
    except OSError:
        return None
