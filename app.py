import streamlit as st
import pandas as pd
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

# === SESSION STATE INITIALIZATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0

# === BASE DEFAULTS ===
DEFAULT_END_PLATE = 5.5
DEFAULT_LED_PITCH = 56.0
BASE_LM_PER_M = 400.0
BASE_W_PER_M = 11.6

# === APP ===
st.title("Linear LightSpec Optimiser")

# === FILE UPLOAD ===
st.header("Upload your Base IES file")
uploaded_file = st.file_uploader("Upload Base IES file", type=['ies'])

if uploaded_file:
    st.success(f"Uploaded: {uploaded_file.name}")

    # === IES Metadata ===
    st.subheader("📂 Base File Summary (IES Metadata + Photometric Parameters)")
    ies_metadata = {
        "IES Version": "IESNA:LM-63-2002",
        "Test Info": "[TEST]",
        "Manufacturer": "[MANUFAC] Evolt Manufacturing",
        "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
        "Luminaire Description": "[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K",
        "Issued Date": "[ISSUEDATE] 2024-07-07"
    }

    photometric_params = {
        "Number of Lamps": 1,
        "Lumens per Lamp": -1,
        "Candela Multiplier": 1,
        "Vertical Angles": 91,
        "Horizontal Angles": 4,
        "Photometric Type": 1,
        "Units Type": 2,
        "Width (m)": 0.08,
        "Length (m)": 1.0,
        "Height (m)": 0.09,
        "Ballast Factor": 1,
        "Future Use": 1,
        "Input Watts": 11.6
    }

    meta_df = pd.DataFrame(ies_metadata.items(), columns=["Field", "Value"])
    photometric_df = pd.DataFrame(photometric_params.items(), columns=["Field", "Value"])
    photometric_df["Value"] = photometric_df["Value"].apply(lambda x: round(x, 1) if isinstance(x, (int, float)) else x)

    st.table(meta_df)
    st.table(photometric_df)

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.warning(f"🔒 Locked: End Plate Expansion Gutter = {DEFAULT_END_PLATE} mm | LED Series Module Pitch = {DEFAULT_LED_PITCH} mm")
        else:
            end_plate = st.number_input("End Plate Expansion Gutter (mm)", value=DEFAULT_END_PLATE)
            led_pitch = st.number_input("LED Series Module Pitch (mm)", value=DEFAULT_LED_PITCH)

    # === SELECT LENGTHS ===
    st.subheader("Select Lengths")
    desired_length = st.number_input("Desired Length (m)", min_value=0.001, format="%.3f", value=1.000)

    shorter_length_m = round(desired_length - 0.02, 3)
    longer_length_m = round(desired_length + 0.02, 3)

    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Add Shorter Buildable Length: {shorter_length_m} m"):
            st.session_state['lengths_list'].append(shorter_length_m)
            st.session_state['locked'] = True
            st.rerun()

    with col2:
        if st.button(f"Add Longer Buildable Length: {longer_length_m} m"):
            st.session_state['lengths_list'].append(longer_length_m)
            st.session_state['locked'] = True
            st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    st.subheader("💡 LED Chipset Adjustment")

    st.session_state['led_efficiency_gain_percent'] = st.number_input(
        "LED Chipset Adjustment (%)", value=st.session_state['led_efficiency_gain_percent'], step=0.1, format="%.2f"
    )

    efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value="")
    if st.session_state['led_efficiency_gain_percent'] != 0 and not efficiency_reason:
        st.warning("Please provide a reason for the LED Chipset Adjustment.")

    # === AVERAGE LM/W STEP INCREMENT ===
    st.subheader("🔒 Average lm/W Step Increment")
    if st.session_state['lengths_list']:
        st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
    else:
        st.session_state['lm_per_watt_increment'] = st.number_input(
            "Average lm/W Step Increment",
            min_value=10.0, max_value=500.0,
            value=st.session_state['lm_per_watt_increment'],
            step=1.0
        )

    # === SELECTED LENGTHS TABLE ===
    if st.session_state['lengths_list']:
        st.subheader("📏 Selected Lengths for IES Generation")

        efficiency_multiplier = (1 + st.session_state['led_efficiency_gain_percent'] / 100)
        new_lm_per_m = round(BASE_LM_PER_M * efficiency_multiplier, 1)
        new_w_per_m = round(BASE_W_PER_M * efficiency_multiplier, 1)

        table_rows = []
        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0

            luminaire_file_name = f"BLine 8585D Diffused Down_{length:.3f}m_Professional"

            row_cols = st.columns([0.1, 1, 1, 1, 1, 1, 1, 1])
            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            row_cols[1].write(f"{length:.3f}")
            row_cols[2].write(luminaire_file_name)
            row_cols[3].write("80")
            row_cols[4].write("3000K")
            row_cols[5].write(f"{total_lumens:.1f}")
            row_cols[6].write(f"{total_watts:.1f}")
            row_cols[7].write(f"{lm_per_w:.1f}")

# === DESIGN OPTIMISATION PLACEHOLDER ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.info("Design Optimisation will be implemented in the next phase.")

