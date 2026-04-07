import re
import numpy as np
import streamlit as st
from PIL import Image
import easyocr

REGION_DONE    = (80,  1930, 490, 2090)
REGION_MISSING = (610, 1930, 1060, 2090)
EXPECTED_SIZE  = (1179, 2556)

st.set_page_config(page_title="Attendance Tracker", page_icon="📊", layout="centered")

st.title("📊 Attendance Tracker")
st.caption("Upload your weekly attendance screenshots to calculate your absence percentage.")

st.warning("""
**⚠️ Important — Do not include the first week of Academy (Monday Sep 29 – Friday Oct 3).**
Enter your attendance for that week manually using the "Uncounted present hours" field in **Manual corrections** below.
""")


@st.cache_resource(show_spinner="Loading OCR model...")
def load_reader():
    return easyocr.Reader(["en"], gpu=False, verbose=False)


def parse_time(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def ocr_time(reader, img: Image.Image, region: tuple):
    crop = img.crop(region)
    arr = np.array(crop)
    results = reader.readtext(arr, detail=1)
    for (_, text, _) in results:
        text = text.replace('O', '0').replace('o', '0')
        text = re.sub(r'(\d{1,2})[.,](\d{2})', r'\1:\2', text)
        m = re.search(r"\d{1,2}:\d{2}", text)
        if m:
            return m.group()
    return None


# ── Upload ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stFileUploader"] {
    border: 2px dashed #4a90d9;
    border-radius: 12px;
    padding: 12px;
}
[data-testid="stFileUploader"]:hover {
    border-color: #74b3f5;
    background-color: rgba(74, 144, 217, 0.05);
}
</style>
""", unsafe_allow_html=True)

uploaded = st.file_uploader(
    "Drag & drop screenshots here, or click Browse files",
    type=["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"],
    accept_multiple_files=True,
    label_visibility="visible",
)

# ── Manual corrections ────────────────────────────────────────────────────────
with st.expander("⚙️ Manual corrections"):
    st.markdown("""
**Uncounted present hours** — use this if you excluded a screenshot because the app
wrongly showed absences for days before your course started (e.g. first week starting
on Wednesday: Mon & Tue counted as missing). Enter only the hours you were actually present.

**Wrongly absent hours** — use this if an included screenshot contains hours logged as
"Time missing" due to a system bug (e.g. a Monday where the whole academy was marked
absent). These hours are moved from absent → present without changing the week total.
""")
    col1, col2 = st.columns(2)
    with col1:
        uncounted_str = st.text_input(
            "Uncounted present hours",
            value="12:00",
            help="Format HH:MM — e.g. 12:00"
        )
        st.caption("First week (Oct 1–3): 3 days of full attendance not included in any screenshot.")
    with col2:
        wrongly_abs_str = st.text_input(
            "Wrongly absent hours (system bug)",
            value="04:00",
            help="Format HH:MM — e.g. 04:00"
        )
        st.caption("Monday Nov 17: academy evacuated due to water shortage — wrongly logged as absent.")

# ── Analysis ──────────────────────────────────────────────────────────────────
if uploaded:
    if st.button("🔍 Analyze", type="primary", use_container_width=True):
        reader = load_reader()

        rows = []
        tot_present = 0
        tot_absent  = 0

        progress = st.progress(0, text="Analyzing screenshots...")
        for i, f in enumerate(uploaded):
            img = Image.open(f)
            if img.size != EXPECTED_SIZE:
                img = img.resize(EXPECTED_SIZE, Image.LANCZOS)

            done    = ocr_time(reader, img, REGION_DONE)
            missing = ocr_time(reader, img, REGION_MISSING)

            if done and missing:
                p = parse_time(done)
                a = parse_time(missing)
                tot = p + a
                pct_a = a / tot * 100 if tot else 0
                tot_present += p
                tot_absent  += a
                rows.append({
                    "File": f.name,
                    "Time done": done,
                    "Time missing": missing,
                    "Total": fmt(tot),
                    "Absence %": f"{pct_a:.1f}%",
                    "Status": "⚠️" if pct_a > 20 else "✅",
                })
            else:
                rows.append({
                    "File": f.name,
                    "Time done": "—",
                    "Time missing": "—",
                    "Total": "—",
                    "Absence %": "—",
                    "Status": "❌ OCR failed",
                })

            progress.progress((i + 1) / len(uploaded), text=f"Processing {i+1} of {len(uploaded)}...")

        progress.empty()

        st.subheader("Weekly breakdown")
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Apply corrections
        try:
            uncounted_min   = parse_time(uncounted_str)   if uncounted_str   != "00:00" else 0
            wrongly_abs_min = parse_time(wrongly_abs_str) if wrongly_abs_str != "00:00" else 0
        except Exception:
            st.error("Invalid correction format. Use HH:MM (e.g. 04:00).")
            st.stop()

        tot_present += uncounted_min + wrongly_abs_min
        tot_absent  -= wrongly_abs_min
        grand_total  = tot_present + tot_absent

        pct_p = tot_present / grand_total * 100
        pct_a = tot_absent  / grand_total * 100

        st.subheader("Final result")

        if uncounted_min or wrongly_abs_min:
            st.info(
                ("**Corrections applied:**\n" if (uncounted_min and wrongly_abs_min) else "**Correction applied:**\n")
                + (f"- +{fmt(uncounted_min)} of uncounted presence added\n" if uncounted_min else "")
                + (f"- {fmt(wrongly_abs_min)} moved from absent → present" if wrongly_abs_min else "")
            )

        c1, c2, c3 = st.columns(3)
        c1.metric("Hours present", fmt(tot_present))
        c2.metric("Hours absent",  fmt(tot_absent))
        c3.metric("Total hours",   fmt(grand_total))

        threshold = 20.0
        col_abs, col_pres = st.columns(2)
        col_abs.metric(
            "Absence %",
            f"{pct_a:.1f}%",
            delta=f"{threshold - pct_a:+.1f}% vs {threshold:.0f}% threshold",
            delta_color="normal" if pct_a <= threshold else "inverse",
        )
        col_pres.metric("Attendance %", f"{pct_p:.1f}%")

        if pct_a <= threshold:
            st.success(f"✅ You are within the {threshold:.0f}% absence threshold.")
        else:
            st.error(f"⚠️ You have exceeded the {threshold:.0f}% absence threshold.")
