import hashlib
import io
from datetime import datetime

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from ultralytics import YOLO

from theme import CSS, guide_html, hero_html, steps_html
from waste_utils import (
    CATEGORIES,
    CATEGORY_INFO,
    COL_CATEGORY,
    COL_PIXELS,
    COL_SHARE,
    build_category_map,
    build_report,
    extract_detections,
    recoverable_share,
    render_overlay,
    summarise,
)

st.set_page_config(page_title="Smart Waste Segregation", page_icon="♻️", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

MODEL_NAME = "yolo11n-seg.pt"
CREATED_BY = "Swarup"

if "history" not in st.session_state:
    st.session_state.history = []


@st.cache_resource
def load_model():
    # Ultralytics downloads this small pretrained segmentation model on first run.
    return YOLO(MODEL_NAME)


def colour_scale(categories):
    return alt.Scale(domain=list(categories), range=[CATEGORY_INFO[c]["color"] for c in categories])


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Detection settings")
    confidence = st.slider("Detection confidence", 0.10, 0.90, 0.25, 0.05,
                           help="Lower values find more objects but with more false detections.")
    opacity = st.slider("Mask opacity", 0.10, 0.80, 0.45, 0.05)
    show_boxes = st.checkbox("Show boxes", value=True)
    show_labels = st.checkbox("Show labels", value=True)
    st.info(
        "This demo uses a general pre-trained YOLO segmentation model. "
        "It detects common objects, not custom waste classes, so review each "
        "category before reading the results."
    )

st.markdown(hero_html(), unsafe_allow_html=True)
tab_analyse, tab_history, tab_about = st.tabs(["Analyse", "History", "About"])


# ---------------------------------------------------------------- analysis
def run_analysis(data: bytes, source: str):
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception as exc:
        st.error(f"Could not read this image: {exc}")
        return

    width, height = image.size
    sig = f"{hashlib.md5(data).hexdigest()[:12]}-{confidence}"

    # Run the model once per image/confidence, not on every widget change.
    if st.session_state.get("det_sig") != sig:
        with st.spinner("Loading the model and analysing the image..."):
            try:
                result = load_model().predict(
                    source=np.array(image), conf=confidence, imgsz=640, device="cpu", verbose=False
                )[0]
            except Exception as exc:
                st.error("The model could not run. Check your internet connection on the first run and that all requirements are installed.")
                st.code(str(exc))
                return
        st.session_state.det_sig = sig
        st.session_state.detections = extract_detections(result, width, height)

    detections = st.session_state.detections
    left, right = st.columns(2)
    with left:
        st.subheader("Your image")
        st.image(image, use_container_width=True)

    if not detections:
        with right:
            st.subheader("Segmentation")
            st.warning("No objects were detected. Try another image or lower the detection confidence in the sidebar.")
        return

    overlay = render_overlay(image, detections, opacity, show_boxes, show_labels)
    with right:
        st.subheader("Segmentation")
        st.image(overlay, use_container_width=True)

    # ---- confirm categories
    st.subheader("Confirm what each object is made of")
    st.caption("Suggestions are rough guesses from the object's name. Change any that are wrong.")
    assignments = []
    cols = st.columns(3)
    for i, det in enumerate(detections):
        with cols[i % 3]:
            assignments.append(st.selectbox(
                f"{i + 1}. {det['label']} ({det['confidence']:.0%})",
                CATEGORIES,
                index=CATEGORIES.index(det["suggested"]),
                key=f"category_{sig}_{i}",
            ))

    category_map = build_category_map(detections, assignments, height, width)
    df = summarise(category_map)
    if df.empty:
        st.warning("No visible mask pixels are available for the area calculation.")
        return
    valid_pixels = int(df[COL_PIXELS].sum())
    recoverable = recoverable_share(df)

    # ---- results
    st.subheader("Results")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Objects found", len(detections))
    m2.metric("Image size", f"{width} × {height}")
    m3.metric("Detected waste pixels", f"{valid_pixels:,}")
    m4.metric("Recoverable share", f"{recoverable:.0f}%",
              help="Share of detected area that has a clear route: recycle, compost or reuse. "
                   "Items marked 'Other / Unsure' are not counted.")

    chart_df = df.rename(columns={COL_CATEGORY: "Category", COL_SHARE: "Share"})[["Category", "Share"]]
    c1, c2 = st.columns([1, 1])
    with c1:
        donut = alt.Chart(chart_df).mark_arc(innerRadius=62).encode(
            theta=alt.Theta("Share:Q"),
            color=alt.Color("Category:N", scale=colour_scale(chart_df["Category"]),
                            legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["Category:N", alt.Tooltip("Share:Q", format=".1f", title="Share (%)")],
        ).properties(height=300)
        st.altair_chart(donut, use_container_width=True)
    with c2:
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ---- disposal guide
    st.subheader("Where each category goes")
    st.markdown(guide_html(dict(zip(df[COL_CATEGORY], df[COL_SHARE]))), unsafe_allow_html=True)
    st.caption("Bin colours follow a common colour-coded scheme. Check your local municipality's rules before sorting.")

    st.caption(
        "Areas are visible pixel estimates from segmentation masks, not weight or volume. "
        "Overlapping masks are assigned to the higher-confidence detection."
    )

    # ---- exports + history
    st.subheader("Save your results")
    png = io.BytesIO()
    overlay.save(png, format="PNG")
    report = build_report(source, width, height, detections, assignments, df, recoverable)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    d1, d2, d3, d4 = st.columns(4)
    d1.download_button("Download area report (CSV)", df.to_csv(index=False).encode("utf-8"),
                       f"waste_area_report_{stamp}.csv", "text/csv", use_container_width=True)
    d2.download_button("Download full report (JSON)", report.encode("utf-8"),
                       f"waste_report_{stamp}.json", "application/json", use_container_width=True)
    d3.download_button("Download annotated image (PNG)", png.getvalue(),
                       f"waste_segmentation_{stamp}.png", "image/png", use_container_width=True)
    if d4.button("Save to history", use_container_width=True, type="primary", key=f"save_{sig}"):
        st.session_state.history.append({
            "Time": datetime.now().strftime("%d %b %Y, %H:%M"),
            "Source": source,
            "Objects": len(detections),
            "Recoverable (%)": recoverable,
            "Largest category": df.iloc[0][COL_CATEGORY],
            "pixels": dict(zip(df[COL_CATEGORY], df[COL_PIXELS].astype(int))),
        })
        st.toast("Saved to history")


with tab_analyse:
    source = st.radio("Image source", ["Upload a file", "Use camera"], horizontal=True,
                      label_visibility="collapsed")
    if source == "Upload a file":
        picked = st.file_uploader("Upload a waste image", type=["jpg", "jpeg", "png", "webp"],
                                  label_visibility="collapsed")
    else:
        picked = st.camera_input("Take a photo of the waste", label_visibility="collapsed")

    if picked is None:
        st.markdown(steps_html(), unsafe_allow_html=True)
    else:
        run_analysis(picked.getvalue(), "Camera" if source == "Use camera" else "Upload")


# ---------------------------------------------------------------- history
with tab_history:
    history = st.session_state.history
    if not history:
        st.info("Nothing saved yet. Analyse an image and choose 'Save to history' to build a running summary here.")
    else:
        table = pd.DataFrame([{k: v for k, v in h.items() if k != "pixels"} for h in history])
        totals = {}
        for h in history:
            for category, px in h["pixels"].items():
                totals[category] = totals.get(category, 0) + px
        total_px = sum(totals.values())
        cumulative = pd.DataFrame({
            "Category": list(totals.keys()),
            "Share": [round(v / total_px * 100, 1) for v in totals.values()],
        }).sort_values("Share", ascending=False)

        h1, h2, h3 = st.columns(3)
        h1.metric("Analyses saved", len(history))
        h2.metric("Objects found", int(table["Objects"].sum()))
        h3.metric("Average recoverable share", f"{table['Recoverable (%)'].mean():.0f}%")

        st.subheader("Combined category share")
        bars = alt.Chart(cumulative).mark_bar(cornerRadiusEnd=4).encode(
            x=alt.X("Share:Q", title="Share of all detected waste area (%)"),
            y=alt.Y("Category:N", sort="-x", title=None),
            color=alt.Color("Category:N", scale=colour_scale(cumulative["Category"]), legend=None),
            tooltip=["Category:N", alt.Tooltip("Share:Q", format=".1f", title="Share (%)")],
        ).properties(height=40 * len(cumulative) + 30)
        st.altair_chart(bars, use_container_width=True)

        st.subheader("Saved analyses")
        st.dataframe(table, use_container_width=True, hide_index=True)
        b1, b2, _ = st.columns([1, 1, 3])
        b1.download_button("Download history (CSV)", table.to_csv(index=False).encode("utf-8"),
                           "waste_history.csv", "text/csv", use_container_width=True)
        if b2.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()


# ---------------------------------------------------------------- about
with tab_about:
    st.subheader("About this demo")
    st.markdown(
        f"""
This is a CPU-friendly demo for image-based waste segregation, built by **{CREATED_BY}**.

**What the model can and can't do.** It uses `{MODEL_NAME}`, a general pre-trained segmentation model.
It is not trained on a waste dataset and does not recognise custom Plastic / Metal / Paper / Cloth / Glass classes.
Category suggestions are rough, which is why you confirm each one.

**What the percentages mean.** They are visible pixel areas from the segmentation masks, not weight or volume.

**Recoverable share.** The part of the detected area whose category has a clear route: recycle, compost or reuse.
        """
    )

st.markdown(
    f'<div class="footer">Smart Waste Segregation · built by {CREATED_BY} · model: {MODEL_NAME}</div>',
    unsafe_allow_html=True,
)
