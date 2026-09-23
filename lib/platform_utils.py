#!/usr/bin/env python3
"""
platform_utils.py - OS + device abstraction for Reclaim (macOS + Linux).

Only the "image a whole disk" flow needs real device handling; everything else
(photo/video recovery from an image) just needs a file path and is portable.
All helpers here are read-only w.r.t. the device.
"""
import sys, os, json, subprocess, plistlib, shutil

IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


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
            "internal": (d.get("tran") in (None, "sata", "nvme")) and not
                        (str(d.get("rm")) in ("1", "True", "true")),
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
    return f"udisksctl unmount -b {node}1   (repeat per partition)"


def default_image_hint():
    """A friendly default place to look for an image, per-OS."""
    home = os.path.expanduser("~")
    if IS_MAC:
        return "/Volumes/<drive>/lexar-card.img"
    return os.path.join(home, "lexar-card.img")


def os_name():
    return "macOS" if IS_MAC else ("Linux" if IS_LINUX else sys.platform)


def pick(kind="dir", prompt="Select"):
    """
    Open a native file/folder picker and return the chosen path (or "" if
    cancelled/unavailable). kind: 'file' | 'dir' | 'save'.
    macOS uses Finder via osascript; Linux uses zenity or kdialog.
    """
    prompt = prompt.replace('"', "'")
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
    return IS_MAC or have("zenity") or have("kdialog")
