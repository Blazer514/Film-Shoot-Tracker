
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, date

st.set_page_config(page_title="Film Shoot Planner & Roll Logger", layout="wide")
st.title("🎥 Film Shoot Planner & Roll Logger")

DATA_DIR = "roll_library"
os.makedirs(DATA_DIR, exist_ok=True)

# -------------------------
# Constants & helpers
# -------------------------
STANDARD_SHUTTERS = [
    30, 15, 8, 4, 2, 1,
    1/2, 1/4, 1/8, 1/15, 1/30, 1/60,
    1/125, 1/250, 1/500, 1/1000, 1/2000, 1/4000
]
F_STOPS = [1.0, 1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0, 22.0, 32.0]

def fmt_shutter(t):
    return f"{int(t)}s" if t >= 1 else f"1/{int(round(1/t))}s"

SHUTTER_CHOICES = [fmt_shutter(t) for t in STANDARD_SHUTTERS]
APERTURE_CHOICES = [f"f/{a:g}" for a in F_STOPS]

def list_roll_files():
    return sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".csv")])

def save_roll_csv(df_with_meta, project_name, camera, roll_date, film_type, film_iso, iso_set, frames):
    safe_name = project_name.strip().replace(" ", "_")
    camera_name = camera.strip().replace(" ","_")
    film_name = film_type.strip().replace(" ","_")
    date_str = roll_date.strftime("%Y-%m-%d") if isinstance(roll_date, (date, datetime)) else str(roll_date)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}__{date_str}__{safe_name}__{camera_name}__{film_name}__{frames}f.csv"
    path = os.path.join(DATA_DIR, fname)

    export_df = df_with_meta.copy()
    export_df.insert(0, "Project", project_name)
    export_df.insert(1, "Camera", camera)
    export_df.insert(2, "Date Shot", date_str)
    export_df.insert(3, "Film", film_type)
    export_df.insert(4, "Film ISO", film_iso)
    export_df.insert(5, "ISO Set", iso_set)
    export_df.to_csv(path, index=False)
    return fname

def load_roll_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    return pd.read_csv(path)

# -------------------------
# Session init
# -------------------------
if "lenses" not in st.session_state:
    st.session_state.lenses = pd.DataFrame(columns=["Brand/Name", "Focal Length (mm)", "Max Aperture"])

if "roll_df" not in st.session_state:
    st.session_state.roll_df = None

# -------------------------
# Project Setup (Sidebar)
# -------------------------
with st.sidebar:
    st.header("📁 Project Setup")
    project_name = st.text_input("Project name", "Untitled Project")
    camera = st.text_input("Camera", "My Camera")
    roll_date = st.date_input("Date shot", value=date.today())
    frames = st.selectbox("Number of frames", [12, 24, 27, 36], index=3)
    film_type = st.text_input("Film (type/stock)", "Kodak Tri-X 400")
    film_iso = st.number_input("Film ISO (box speed)", min_value=6, max_value=12800, value=400, step=1)
    iso_set = st.number_input("ISO set on camera (rating)", min_value=6, max_value=12800, value=400, step=1)

    st.markdown("---")
    st.subheader("📚 Roll Library")
    # Import a previously exported CSV into the library
    uploaded = st.file_uploader("Import CSV to library", type=["csv"])
    if uploaded is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_name = f"{timestamp}__imported_{uploaded.name}"
        dest_path = os.path.join(DATA_DIR, dest_name)
        with open(dest_path, "wb") as f:
            f.write(uploaded.getvalue())
        st.success(f"Imported as {dest_name}")
    lib_files = list_roll_files()
    if lib_files:
        sel = st.selectbox("Open a saved roll", ["— select —"] + lib_files)
        if sel != "— select —":
            loaded_df = load_roll_csv(sel)
            st.caption(f"Loaded: **{sel}**")
            st.dataframe(loaded_df.head(3), use_container_width=True)
            if st.button("Load into editor", key="load_into_editor"):
                editor_cols = ["Frame #", "ISO", "Shutter", "Aperture", "Lens", "Notes"]
                if all(col in loaded_df.columns for col in editor_cols):
                    st.session_state.roll_df = loaded_df[editor_cols].copy()
                    st.success("Loaded into editor below.")
                else:
                    st.warning("This CSV does not match the expected roll format.")

# -------------------------
# Lens Library (optional)
# -------------------------
st.header("🔭 Lens Library (optional)")
with st.expander("Add a lens", expanded=False):
    lc1, lc2, lc3, lc4 = st.columns([2,1,1,1])
    with lc1:
        lens_name = st.text_input("Brand/Name", placeholder="Nikkor 50mm f/1.8")
    with lc2:
        lens_focal = st.number_input("Focal Length (mm)", min_value=5, max_value=1000, value=50, step=1, key="lens_focal_add")
    with lc3:
        lens_max = st.selectbox("Max Aperture", F_STOPS, index=1, key="lens_max_add")
    with lc4:
        if st.button("➕ Add Lens"):
            st.session_state.lenses = pd.concat([
                st.session_state.lenses,
                pd.DataFrame([{"Brand/Name": lens_name, "Focal Length (mm)": lens_focal, "Max Aperture": lens_max}])
            ], ignore_index=True)
            st.success("Lens added")
if not st.session_state.lenses.empty:
    st.dataframe(st.session_state.lenses, use_container_width=True)

st.markdown("---")

# -------------------------
# Roll Sheet Builder
# -------------------------
st.header("🧾 Roll Sheet")

default_iso = iso_set
default_shutter = "1/125s"
default_aperture = "f/8"
lens_options = [""] + st.session_state.lenses["Brand/Name"].tolist()

cbuild, csave, cexport = st.columns([1,1,1])
with cbuild:
    if st.button("🛠️ Build / Reset roll sheet"):
        st.session_state.roll_df = pd.DataFrame({
            "Frame #": list(range(1, frames + 1)),
            "ISO": [default_iso] * frames,
            "Shutter": [default_shutter] * frames,
            "Aperture": [default_aperture] * frames,
            "Lens": [""] * frames,
            "Notes": [""] * frames,
        })
with csave:
    if st.session_state.roll_df is not None and st.button("💾 Save to library"):
        export_df = st.session_state.roll_df.copy()
        fname = save_roll_csv(export_df, project_name, camera, roll_date, film_type, film_iso, iso_set, frames)
        st.success(f"Saved as {fname} in roll library")
with cexport:
    if st.session_state.roll_df is not None and st.button("⬇️ Download CSV"):
        export_df = st.session_state.roll_df.copy()
        export_df.insert(0, "Project", project_name)
        export_df.insert(1, "Camera", camera)
        export_df.insert(2, "Date Shot", roll_date.strftime("%Y-%m-%d"))
        export_df.insert(3, "Film", film_type)
        export_df.insert(4, "Film ISO", film_iso)
        export_df.insert(5, "ISO Set", iso_set)
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Save CSV file", data=csv, file_name=f"{project_name.replace(' ', '_').lower()}_roll.csv", mime="text/csv", key="dlbtn")

if st.session_state.roll_df is None:
    st.info("Click **Build / Reset roll sheet** to initialize the frame grid.")
else:
    cfg = {
        "Frame #": st.column_config.NumberColumn(disabled=True, width="small"),
        "ISO": st.column_config.NumberColumn(min_value=6, max_value=12800, step=1, width="small"),
        "Shutter": st.column_config.SelectboxColumn(options=SHUTTER_CHOICES, width="small"),
        "Aperture": st.column_config.SelectboxColumn(options=APERTURE_CHOICES, width="small"),
        "Lens": st.column_config.SelectboxColumn(options=[""] + st.session_state.lenses["Brand/Name"].tolist(), width="medium"),
        "Notes": st.column_config.TextColumn(width="large"),
    }
    st.caption(f"Project: **{project_name}** · Camera: **{camera}** · Date: **{roll_date.strftime('%Y-%m-%d')}** · Film: **{film_type}** · Box ISO: **{film_iso}** · ISO Set: **{iso_set}** · Frames: **{frames}**")
    edited = st.data_editor(
        st.session_state.roll_df,
        column_config=cfg,
        use_container_width=True,
        num_rows="fixed"
    )
    st.session_state.roll_df = edited

# -------------------------
# Library Browser
# -------------------------
st.markdown("---")
st.header("📂 Roll Library (Browse Previous Rolls)")
files = list_roll_files()
if not files:
    st.info("No saved rolls yet. Use **Save to library** above to store a roll here.")
else:
    # Simple search/filter
    f1, f2, f3 = st.columns([2,1,1])
    with f1:
        q = st.text_input("Search (filename contains)", "")
    with f2:
        sort_new_first = st.checkbox("Newest first", value=True)
    with f3:
        filter_date = st.text_input("Filter by date (YYYY-MM-DD, optional)", "")

    filtered = [f for f in files if q.lower() in f.lower()]
    if filter_date:
        filtered = [f for f in filtered if f"__{filter_date}__" in f]

    if sort_new_first:
        filtered = sorted(filtered, reverse=True)

    if filtered:
        st.write(f"Found {len(filtered)} roll(s).")
        for fname in filtered[:200]:
            with st.expander(fname, expanded=False):
                df = load_roll_csv(fname)
                # Show metadata row summary
                needed = ["Project","Camera","Date Shot","Film","Film ISO","ISO Set"]
                if all(k in df.columns for k in needed):
                    meta = df.iloc[0][needed].to_dict()
                    st.caption(f"**{meta['Project']}** — {meta['Camera']} — {meta['Film']} — Date {meta['Date Shot']} — ISO {int(meta['Film ISO'])} (set {int(meta['ISO Set'])})")
                st.dataframe(df, use_container_width=True)
    else:
        st.info("No rolls match your search.")
