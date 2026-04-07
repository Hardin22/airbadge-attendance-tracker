#!/usr/bin/env python3
"""
University attendance analyzer — local OCR, no external API.

Usage:
  python3 analizza.py                   # reads from ./screenshots/ (default)
  python3 analizza.py folder/           # custom folder
  python3 analizza.py screenshot.png    # single file

Requirements: pip3 install pillow easyocr
"""

import re
import sys
from pathlib import Path

import easyocr
import numpy as np
from PIL import Image

# ─── MANUAL CORRECTIONS ──────────────────────────────────────────────────────
#
# UNCOUNTED_PRESENT: Use this when you excluded a screenshot entirely because
# the app wrongly showed absences for days before your course started
# (e.g. first week starting on Wednesday: Mon+Tue counted as missing).
# Add here ONLY the hours you were actually present in that excluded week.
# These are added to presence only — the phantom absences never entered the
# calculation since the screenshot was excluded.
# Format: list of "HH:MM" strings, one entry per excluded block.
# Example: ["12:00"]  →  adds 12 hours of presence
#
UNCOUNTED_PRESENT = [
    "12:00",   # first week (Oct 1-3): Wed+Thu+Fri presence not included
]

# WRONGLY_ABSENT: Use this when a screenshot IS included but the app logged
# hours as "Time missing" due to a system bug, even though you were present.
# These hours are moved from absent → present (subtracted from absent,
# added to present), correcting the bug without touching the raw OCR data.
# Format: list of "HH:MM" strings, one entry per corrected block.
# Example: ["04:00"]  →  moves 4 hours from absent to present
#
WRONGLY_ABSENT = [
    "04:00",   # Monday Nov 17: academy evacuated (water shortage), wrongly logged as absent
]

# ─────────────────────────────────────────────────────────────────────────────

# Crop regions calibrated for iPhone at 1179x2556 resolution.
# These define where the HH:MM values appear in the "Time done" / "Time missing" cards.
REGION_DONE    = (80,  1930, 490, 2090)
REGION_MISSING = (610, 1930, 1060, 2090)

# Expected screenshot resolution (iPhone 6.1" display)
EXPECTED_SIZE = (1179, 2556)


def parse_time(t: str) -> int:
    """Convert HH:MM string to total minutes."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def fmt(minutes: int) -> str:
    """Convert total minutes to HH:MM string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def ocr_time(reader: easyocr.Reader, img: Image.Image, region: tuple) -> str:
    """Extract a HH:MM time value from a cropped region using OCR."""
    crop = img.crop(region)
    arr = np.array(crop)
    results = reader.readtext(arr, detail=1)
    for (_, text, _) in results:
        # Normalize common OCR misreads: O/o → 0, dot separator → colon
        text = text.replace('O', '0').replace('o', '0')
        text = re.sub(r'(\d{1,2})[.,](\d{2})', r'\1:\2', text)
        match = re.search(r"\d{1,2}:\d{2}", text)
        if match:
            return match.group()
    return None


def process_screenshot(reader: easyocr.Reader, path: Path):
    """Open a screenshot and extract time_done and time_missing via OCR."""
    img = Image.open(path)

    # Resize if resolution differs from expected (e.g. compressed screenshot)
    if img.size != EXPECTED_SIZE:
        img = img.resize(EXPECTED_SIZE, Image.LANCZOS)

    done    = ocr_time(reader, img, REGION_DONE)
    missing = ocr_time(reader, img, REGION_MISSING)

    if not done or not missing:
        return None
    return {"time_done": done, "time_missing": missing}


def main():
    # Resolve input: file, folder argument, or default screenshots/ folder
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.is_file():
            images = [p]
        else:
            images = sorted(p.glob("*.png")) + sorted(p.glob("*.jpg")) + sorted(p.glob("*.jpeg"))
    else:
        folder = Path("screenshots")
        if not folder.exists():
            print("Folder 'screenshots' not found. Create it and place your screenshots inside.")
            sys.exit(1)
        images = (sorted(folder.glob("*.png")) + sorted(folder.glob("*.PNG"))
                + sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.JPG"))
                + sorted(folder.glob("*.jpeg")) + sorted(folder.glob("*.JPEG")))

    if not images:
        print("No images found.")
        sys.exit(1)

    print("Loading OCR model (first run only)...")
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    total_present = 0
    total_absent  = 0
    failed        = []

    print(f"\n{'#':<4} {'File':<22} {'Done':>6} {'Missing':>8} {'Total':>7} {'Abs%':>6}")
    print("─" * 55)

    for i, path in enumerate(images, 1):
        data = process_screenshot(reader, path)
        if not data:
            failed.append(path.name)
            print(f"{i:<4} {path.name:<22} {'OCR FAILED':>22}")
            continue

        present_min = parse_time(data["time_done"])
        absent_min  = parse_time(data["time_missing"])
        week_total  = present_min + absent_min
        abs_pct     = absent_min / week_total * 100 if week_total else 0

        total_present += present_min
        total_absent  += absent_min

        print(f"{i:<4} {path.name:<22} {data['time_done']:>6} {data['time_missing']:>8} {fmt(week_total):>7} {abs_pct:>5.1f}%")

    print("─" * 55)

    if failed:
        print(f"\nOCR failed on {len(failed)} file(s): {', '.join(failed)}")

    grand_total = total_present + total_absent
    if grand_total == 0:
        print("No valid data extracted.")
        return

    # Apply manual corrections
    uncounted_min    = sum(parse_time(t) for t in UNCOUNTED_PRESENT)
    wrongly_abs_min  = sum(parse_time(t) for t in WRONGLY_ABSENT)

    total_present += uncounted_min + wrongly_abs_min
    total_absent  -= wrongly_abs_min
    grand_total    = total_present + total_absent

    pct_present = total_present / grand_total * 100
    pct_absent  = total_absent  / grand_total * 100

    print()
    print("─" * 45)
    print("FINAL RESULT")
    print(f"  Weeks analyzed : {len(images) - len(failed)}")
    if uncounted_min or wrongly_abs_min:
        print("  Corrections applied:")
        if uncounted_min:
            print(f"    + {fmt(uncounted_min)} of uncounted presence added (UNCOUNTED_PRESENT)")
        if wrongly_abs_min:
            print(f"    + {fmt(wrongly_abs_min)} moved from absent → present (WRONGLY_ABSENT)")
    print(f"  Hours present  : {fmt(total_present)}")
    print(f"  Hours absent   : {fmt(total_absent)}")
    print(f"  Total hours    : {fmt(grand_total)}")
    print(f"  Attendance %   : {pct_present:.1f}%")
    print(f"  Absence %      : {pct_absent:.1f}%")

    threshold = 20.0
    if pct_absent <= threshold:
        print(f"  OK — absence rate is within the {threshold:.0f}% threshold")
    else:
        print(f"  WARNING — absence rate exceeds the {threshold:.0f}% threshold")
    print("─" * 45)


if __name__ == "__main__":
    main()
