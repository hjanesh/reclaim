# Reclaim - Safety & Philosophy

Data recovery is mostly about **not making things worse**. Reclaim is built around a few hard
rules learned the practical way.

## The rules

1. **Never write to the source.** Every source is opened read-only in code
   (`open(path, 'rb')`, `ddrescue` only reads its input, `photorec` opens read-only). Reclaim
   never runs a repair/format/`fsck`/`chkdsk` on your media.
2. **Output must differ from the source.** The tool refuses if you point output at the source
   path. Recovered data always lands on a *different* drive.
3. **Image first, then work from the copy.** Imaging touches the failing media exactly once. All
   scanning/carving then reads the safe image, so repeated passes never stress the original.
4. **Stop using the media the moment you notice loss.** Don't shoot more frames, don't "repair"
   it, don't let the OS write thumbnails/indexes to it. Unmount it.

## SD cards vs SSDs (this matters a lot)

- **SD/microSD cards generally do _not_ support TRIM.** A quick or in-camera format only rewrites
  the filesystem's directory/FAT - the actual photo/video bytes stay in the flash. This is why a
  "formatted" card is usually **very recoverable**, and why Reclaim exists.
- **SSDs _do_ support TRIM.** A quick reformat of an SSD often issues TRIM/UNMAP, and the
  controller then returns deterministic zeros for those blocks - the data is gone at the block
  level and **not recoverable by software**. Image it and check (all-zeros past the new metadata =
  TRIMmed), but temper expectations.

## Gotchas we actually hit

- **Slow/flaky USB port → stalls.** Reading a large image *and* writing recovered files over one
  cheap USB link can stall a drive into an uninterruptible I/O wait. Use a direct
  USB-C/Thunderbolt port; the image-first flow minimises source stress.
- **"Target is busy" on unmount.** Usually a file manager (Nautilus/Finder), a background indexer
  (Tracker/Spotlight), a leftover loop device, or a shell sitting inside the mount. Close those,
  detach loop devices, then unmount.
- **PhotoRec loses filenames.** Carving reconstructs *content*, not the original names - but RAW
  and video keep their EXIF/creation timestamps, so menu 5 can re-sort them by capture date.
- **Video is the hard part.** Large clips are the most likely to be fragmented; a fragmented clip
  carves as a short/broken file. `untrunc` + a same-camera reference clip rebuilds them.

## Verifying a recovery

- Open a few RAW files in your editor and check EXIF looks right.
- Play the recovered videos end-to-end (not just the first second).
- Keep the original image until you've confirmed the recovery - it's your safety net.
