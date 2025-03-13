Understood. Initiating the development process now. I'll provide the complete code once Phase 1 is finalized.

# Clean Base Code Implementation

import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

# === SESSION STATE INITIALISATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'locked' not in st.session_state:
    st.session_state['locked'] = False

# === BASE FILE UPLOAD ===
st.title("Linear LightSpec Optimiser")
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    ies_data = parse_ies_file(uploaded_file)
    st.session_state['ies_data'] = ies_data
    
    st.markdown("### 📂 Base File Summary (IES Metadata + Photometric Parameters)")
    st.write(pd.DataFrame.from_dict(ies_data['metadata'], orient='index', columns=['Value']).round(1))

# === BASE BUILD METHODOLOGY ===
st.markdown("### 📂 Base Build Methodology")

col1, col2 = st.columns(2)
with col1:
    gutter = st.number_input("End Plate Expansion Gutter (mm)", value=5.5, step=0.1, disabled=st.session_state['locked'])
with col2:
    led_pitch = st.number_input("LED Series Module Pitch (mm)", value=56.0, step=0.1, disabled=st.session_state['locked'])

# === LENGTH SELECTION ===
st.markdown("### Select Lengths")
desired_length = st.number_input("Desired Length (m)", min_value=0.5, max_value=5.0, step=0.001, format="%.3f")

shorter_length = round(desired_length - (desired_length % 0.028), 3)
longer_length = round(shorter_length + 0.028, 3)

col1, col2 = st.columns(2)
if col1.button(f"Add Shorter Buildable Length: {shorter_length}"):
    st.session_state['lengths_list'].append(shorter_length)
    st.session_state['locked'] = True
if col2.button(f"Add Longer Buildable Length: {longer_length}"):
    st.session_state['lengths_list'].append(longer_length)
    st.session_state['locked'] = True

# === LED CHIPSET ADJUSTMENT ===
st.markdown("### 💡 LED Chipset Adjustment")
led_adjustment = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=50.0, step=0.1)
efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)")
if led_adjustment != 0 and not efficiency_reason:
    st.warning("⚠️ A reason must be provided when adjustment is made!")

# === AVERAGE LM/W STEP INCREMENT ===
st.markdown("### 🔒 Average lm/W Step Increment")
st.info("115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.")
st.session_state['lm_per_watt_increment'] = 115.0

# === SELECTED LENGTHS TABLE ===
st.markdown("### 📏 Selected Lengths for IES Generation")
if st.session_state['lengths_list']:
    table_data = []
    for length in st.session_state['lengths_list']:
        table_data.append([length, "BLine 8585D Diffused Down", "3000K", "N/A", round(length * 400, 1), round(length * 11.6, 1), 34.5])
    df = pd.DataFrame(table_data, columns=["Length (m)", "Luminaire & IES File Name", "CCT", "CRI", "Total Lumens", "Total Watts", "Settings lm/W"])
    st.table(df)

# === DESIGN OPTIMISATION ===
with st.expander("🎯 Design Optimisation", expanded=False):
    target_lux = st.number_input("Target Lux Level", min_value=100.0, max_value=1000.0, step=1.0, value=400.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=100.0, max_value=1000.0, step=1.0, value=405.0)
    difference = round((achieved_lux - target_lux) / target_lux * 100, 1)
    st.write(f"Difference: {difference}%")
    if difference > 0:
        st.warning(f"⚠️ Consider reducing by {max(1, int(difference / 5))} increments or dimming to match target lux.")
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")
