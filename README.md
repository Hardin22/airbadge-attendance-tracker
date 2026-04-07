# AirBadge Attendance Tracker

Calculates your absence percentage from weekly screenshots of the **AirBadge** attendance app. Drag & drop your screenshots into a local web interface — no coding required.

---

## Requirements

- macOS
- Python 3 — if you don't have it, download it from [python.org](https://www.python.org/downloads/)

---

## How to run

1. Clone or download this repository
2. Double-click **`Avvia.command`**
3. The first time it will install dependencies automatically (~2 minutes)
4. A browser window opens at `http://localhost:8501`

---

## How to take screenshots

For each week of the academic year:

1. Open the **AirBadge** app on your iPhone
2. Tap the calendar icon → select **Week** view
3. Scroll to the bottom until you see the **"This week"** summary with **Time done** and **Time missing**
4. Take a screenshot (side button + volume up)

One screenshot per week. Do this at the **end of the week** (Friday), so all 5 days are recorded.

> ⚠️ **Do not include the screenshot for the first week (Sep 29 – Oct 3).** Enter your attendance for that week manually in the *Manual corrections* section.

---

## How to use the interface

1. Drag & drop all your weekly screenshots onto the upload area (or click **Browse files**)
2. Click **Analyze**
3. Review the per-week breakdown table to verify OCR accuracy
4. Check the **Final result** section for your overall absence percentage

### Manual corrections

Expand the **Manual corrections** section if you need to adjust for:

- **Uncounted present hours** — hours you were present but excluded from screenshots (default: `12:00` for the first week)
- **Wrongly absent hours** — hours the app logged as missing due to a system bug (default: `04:00` for the Nov 17 evacuation)

---

## Absence threshold

The app flags you if your absence rate exceeds **20%**.
