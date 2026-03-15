# app.py — Streamlit UI
# Run: streamlit run app.py

import os
import json
import tempfile
import traceback
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads GROQ_API_KEY from .env

from extractor   import extract_text, extract_images, split_thermal_images
from ai_analyzer import analyze
from pdf_builder import build_pdf


st.set_page_config(
    page_title="DDR Report Generator",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Simple dark theme CSS
st.markdown("""
<style>
    .stApp { background-color: #111111; color: #EEEEEE; }
    .block-container { padding-top: 2rem; }

    h1, h2, h3 { color: #FFFFFF; }

    /* Buttons */
    .stButton > button {
        background-color: #333333;
        color: white;
        border: 1px solid #555555;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button:hover { background-color: #444444; }
    .stDownloadButton > button {
        background-color: #222222;
        color: white;
        border: 1px solid #555555;
        border-radius: 6px;
        font-weight: 600;
        width: 100%;
        padding: 0.6rem;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #1A1A1A;
        border: 1px solid #444444;
        border-radius: 6px;
    }

    /* Progress bar */
    .stProgress > div > div { background-color: #888888; }

    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #1A1A1A;
        border: 1px solid #333333;
        border-radius: 6px;
        padding: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)


def get_api_key() -> str:
    """Read GROQ_API_KEY from .env. Stop with error if missing."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        st.error(
            "**GROQ_API_KEY not found.**\n\n"
            "Create a `.env` file next to `app.py` with:\n"
            "```\nGROQ_API_KEY=gsk_your_key_here\n```\n"
            "Free key at [console.groq.com/keys](https://console.groq.com/keys)"
        )
        st.stop()
    return key


def upload_files():
    """Two side-by-side PDF upload boxes. Returns (inspection, thermal)."""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📋 Inspection Report**")
        inspection = st.file_uploader("Inspection PDF", type=["pdf"],
                                      key="inspection", label_visibility="collapsed")
        if inspection:
            st.success(f"✅ {inspection.name}")
    with col2:
        st.markdown("**🌡️ Thermal Report**")
        thermal = st.file_uploader("Thermal PDF", type=["pdf"],
                                   key="thermal", label_visibility="collapsed")
        if thermal:
            st.success(f"✅ {thermal.name}")
    return inspection, thermal


def show_results(ddr: dict, pdf_bytes: bytes):
    """Display summary info and download button."""
    st.markdown("---")
    st.markdown("### Report Summary")

    ps = ddr.get("property_summary", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score",   ps.get("overall_score", "N/A"))
    c2.metric("Flagged", ps.get("flagged_items",  "N/A"))
    c3.metric("Areas",   str(len(ddr.get("area_observations",   []))))
    c4.metric("Actions", str(len(ddr.get("recommended_actions", []))))

    st.markdown("**Issue Summary**")
    st.info(ddr.get("issue_summary", ""))

    with st.expander("Area Observations"):
        for obs in ddr.get("area_observations", []):
            st.markdown(f"**{obs.get('area','')}**")
            st.write(f"Problem: {obs.get('problem','')}")
            st.write(f"Source: {obs.get('source','')}")
            st.write(f"Thermal: {obs.get('thermal_reading','')}")
            st.divider()

    with st.expander("Root Causes"):
        for i, cause in enumerate(ddr.get("root_causes", []), 1):
            st.write(f"{i}. {cause}")

    st.markdown("---")
    st.download_button(
        label="⬇️ Download DDR Report (PDF)",
        data=pdf_bytes,
        file_name="DDR_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


def run_pipeline(inspection_file, thermal_file, api_key: str):
    """Run the 4-step DDR pipeline with progress updates."""
    with tempfile.TemporaryDirectory() as tmp:
        insp_path   = os.path.join(tmp, "inspection.pdf")
        therm_path  = os.path.join(tmp, "thermal.pdf")
        output_path = os.path.join(tmp, "DDR_Report.pdf")

        with open(insp_path,  "wb") as f: f.write(inspection_file.read())
        with open(therm_path, "wb") as f: f.write(thermal_file.read())

        bar    = st.progress(0)
        status = st.empty()

        try:
            status.write("Step 1/4 — Extracting text…")
            insp_text    = extract_text(insp_path)
            thermal_text = extract_text(therm_path)
            bar.progress(20)

            status.write("Step 2/4 — Extracting images…")
            site_photos  = extract_images(insp_path,  os.path.join(tmp, "site"),  "site")
            therm_photos = extract_images(therm_path, os.path.join(tmp, "therm"), "therm")
            ir_photos    = split_thermal_images(therm_photos)
            bar.progress(45)

            status.write("Step 3/4 — AI analysing with Groq…")
            ddr = analyze(insp_text, thermal_text, api_key)
            bar.progress(75)

            status.write("Step 4/4 — Building PDF…")
            build_pdf(ddr, site_photos, ir_photos, output_path)
            bar.progress(100)
            status.success("✅ Done!")

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            show_results(ddr, pdf_bytes)

        except json.JSONDecodeError:
            st.error("AI returned invalid JSON. Click Generate again.")
        except Exception as e:
            err = str(e)
            if "authentication" in err.lower() or "api_key" in err.lower():
                st.error("Invalid API key. Check GROQ_API_KEY in .env")
            else:
                st.error(f"Error: {err}")
                with st.expander("Details"):
                    st.code(traceback.format_exc())


def main():
    st.title("🏗️ DDR Report Generator")
    st.caption("Upload Inspection + Thermal PDFs → get a Detailed Diagnostic Report")
    st.divider()

    api_key = get_api_key()

    inspection, thermal = upload_files()
    st.markdown("")

    ready = bool(inspection and thermal)
    if not ready:
        if not inspection: st.warning("Upload the Inspection Report PDF")
        if not thermal:    st.warning("Upload the Thermal Report PDF")

    if st.button("Generate DDR Report", disabled=not ready, use_container_width=True):
        run_pipeline(inspection, thermal, api_key)

    st.divider()
    st.caption("Powered by Groq · Llama 3.3 70B")


if __name__ == "__main__":
    main()