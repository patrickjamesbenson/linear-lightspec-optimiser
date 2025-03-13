import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file  # Make sure utils.py is correct and matches this
import time

# === SESSION STATE INITIALISATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

# === UPLOAD BASE IES FILE ===
st.header("Linear LightSpec Optimiser")

uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    ies_data = parse_ies_file(uploaded_file)

    st.subheader("📂 Base File Summary (IES Metadata + Photometric Parameters)")

    # Display Metadata with 1 decimal where appropriate
    metadata_display = {
        "IES Version": ies_data.get("IESNA Version", "N/A"),
        "Test Info": ies_data.get("Test", "N/A"),
        "Manufacturer": ies_data.get("Manufacturer", "N/A"),
        "Luminaire Catalog Number": ies_data.get("Luminaire Catalog Number", "N/A"),
        "Luminaire Description": ies_data.get("Luminaire Description", "N/A"),
        "Issued Date": ies_data.get("Issued Date", "N/A"),
    }

    st.table(pd.DataFrame(metadata_display.items(), columns=["Field", "Value"]))

    # Photometric parameters example, apply 1 decimal
    photometric_params = {
        "Number of Lamps": 1,
        "Lumens per Lamp": -1,
        "Candela Multiplier": 1,
        "Vertical Angles": 91,
        "Horizontal Angles": 4,
        "Photometric Type": 1,
        "Units Type": 2,
        "Width (m)": round(0.08, 1),
        "Length (m)": round(1.0, 1),
        "Height (m)": round(0.09, 1),
        "Ballast Factor": 1,
        "Future Use": 1,
        "Input Watts": round(11.6, 1),
    }

    st.table(pd.DataFrame(photometric_params.items(), columns=["Field", "Value"]))

# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    st.markdown("🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")

# === LENGTH SELECTION ===
st.subheader("Select Lengths")
desired_length = st.number_input("Desired Length (m)", min_value=0.5, max_value=10.0, value=1.0, step=0.001, format="%.3f")

col1, col2 = st.columns(2)

if col1.button(f"➕ Add Length {desired_length:.3f}m"):
    st.session_state['lengths_list'].append(desired_length)
    st.experimental_rerun()

# === SELECTED LENGTHS TABLE ===
if st.session_state['lengths_list']:
    st.markdown("## 📏 Selected Lengths for IES Generation")

    lengths_data = []
    for idx, length in enumerate(st.session_state['lengths_list']):
        # Example values for now
        row = {
            "Delete": "",
            "Length (m)": round(length, 3),
            "Luminaire & IES File Name": f"BLine Diffused Down_{length:.3f}m_{int(time.time())}",
            "CRI": "80",
            "CCT": "3000K",
            "Total Lumens": round(400 * length, 1),
            "Total Watts": round(11.6 * length, 1),
            "Settings lm/W": round(400 / 11.6, 1),
            "Comments": "Current Generation"
        }
        lengths_data.append(row)

    df = pd.DataFrame(lengths_data)

    # Delete button per row
    for idx, row in df.iterrows():
        col_del, col_rest = st.columns([1, 9])
        if col_del.button("🗑️", key=f"delete_{idx}"):
            st.session_state['lengths_list'].pop(idx)
            st.experimental_rerun()

        col_rest.table(pd.DataFrame([row[1:]]))  # Exclude the delete column from display

# === DESIGN OPTIMISATION PLACEHOLDER ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.subheader("Target vs Achieved Lux Levels")

    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=500.0)

    difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)

    st.write(f"Difference: {difference_percent}%")

    if difference_percent > 0:
        st.warning("⚠️ Consider reducing by 1 increment or dimming to match target lux.")
    else:
        st.success("✅ No adjustment needed.")

