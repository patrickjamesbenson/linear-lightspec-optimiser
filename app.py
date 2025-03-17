import streamlit as st
import pandas as pd
import math

# === PAGE CONFIG ===
st.set_page_config(page_title="Length Optimisation & Ancillary Positions", layout="wide")
st.title("📏 Luminaire Length Optimiser + Ancillary Positions")

# === SESSION STATE INITIALIZATION ===
if 'project_name' not in st.session_state:
    st.session_state['project_name'] = ""

if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"

if 'target_length' not in st.session_state:
    st.session_state['target_length'] = 2400.0

if 'length_table' not in st.session_state:
    st.session_state['length_table'] = pd.DataFrame(columns=[
        "Selected Length (mm)", "Tier", "LED Chip Type", "ECG Type", "Ancillary Positions"
    ])

if 'ancillary_mode' not in st.session_state:
    st.session_state['ancillary_mode'] = False

if 'remaining_pirs' not in st.session_state:
    st.session_state['remaining_pirs'] = 0

if 'remaining_spitfires' not in st.session_state:
    st.session_state['remaining_spitfires'] = 0

if 'ancillary_positions' not in st.session_state:
    st.session_state['ancillary_positions'] = []

# === DEFAULTS PER TIER ===
TIER_DEFAULTS = {
    "Core": {
        "LED Scaling": "G1 (0%)",
        "ECG Type": "Fixed ECG",
        "ECG Stress (%)": 100,
        "LED Max Stress (mA)": 350,
        "Allow Ancillaries": False
    },
    "Professional": {
        "LED Scaling": "G2 (15%)",
        "ECG Type": "DALI ECG",
        "ECG Stress (%)": 85,
        "LED Max Stress (mA)": 300,
        "Allow Ancillaries": True
    },
    "Advanced": {
        "LED Scaling": "Custom",
        "ECG Type": "Wireless ECG",
        "ECG Stress (%)": 75,
        "LED Max Stress (mA)": 250,
        "Allow Ancillaries": True
    },
    "Bespoke": {
        "LED Scaling": "Custom",
        "ECG Type": "Custom ECG",
        "ECG Stress (%)": 75,
        "LED Max Stress (mA)": 250,
        "Allow Ancillaries": True
    }
}

# === CONSTANTS ===
BPSL = 46.666  # Base Parallel Segment Length (mm)
END_PLATE_LENGTH = 5.5  # mm per plate

# === PROJECT INFO ===
st.subheader("🔧 Project Setup")
project_name = st.text_input("Enter Project Name", st.session_state['project_name'])
st.session_state['project_name'] = project_name

# === PRODUCT TIER SELECTION ===
st.session_state['tier'] = st.selectbox("Select Product Tier", ["Core", "Professional", "Advanced", "Bespoke"], index=1)

tier_info = TIER_DEFAULTS[st.session_state['tier']]

# === DISPLAY TIER CONFIG ===
st.markdown(f"""
#### Product Tier: **{st.session_state['tier']}**
| Parameter         | Value                  |
|-------------------|------------------------|
| LED Chip Type     | {tier_info['LED Scaling']} |
| ECG Type          | {tier_info['ECG Type']} |
| ECG Stress (%)    | {tier_info['ECG Stress (%)']}% |
| LED Max Stress    | {tier_info['LED Max Stress (mA)']}mA |
""")

# === TARGET LENGTH INPUT ===
target_length_m = st.number_input(
    label="Target Luminaire Length [m]",
    min_value=0.100,
    max_value=7.000,
    step=0.001,
    format="%.3f"
)
target_length_mm = target_length_m * 1000
st.session_state['target_length'] = target_length_mm

# === LENGTH CALCULATION ===
def calculate_closest_lengths(target):
    segment_count = math.floor(target / BPSL)
    optimal_length = segment_count * BPSL
    shorter = optimal_length if optimal_length < target else optimal_length - BPSL
    longer = optimal_length if optimal_length >= target else optimal_length + BPSL
    return shorter, longer, optimal_length

shorter_len, longer_len, optimal_len = calculate_closest_lengths(target_length_mm)

# === BUILD BUTTONS ===
st.subheader("📐 Length Optimisation Options")
if optimal_len == target_length_mm:
    if st.button(f"Optimal Length {optimal_len:.1f}mm"):
        selected_length = optimal_len
else:
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"Closest Shorter Length {shorter_len:.1f}mm"):
            selected_length = shorter_len
    with col2:
        if st.button(f"Closest Longer Length {longer_len:.1f}mm"):
            selected_length = longer_len

# === ADD LENGTH TO TABLE ===
def add_length_to_table(length_mm):
    new_row = {
        "Selected Length (mm)": round(length_mm, 1),
        "Tier": st.session_state['tier'],
        "LED Chip Type": tier_info['LED Scaling'],
        "ECG Type": tier_info['ECG Type'],
        "Ancillary Positions": ""  # To be populated
    }
    st.session_state['length_table'] = pd.concat([st.session_state['length_table'], pd.DataFrame([new_row])], ignore_index=True)

if 'selected_length' in locals():
    add_length_to_table(selected_length)

# === DISPLAY LENGTH BUILD TABLE ===
st.subheader("📊 Luminaire Length Build Table")
st.dataframe(st.session_state['length_table'])

# === ANCILLARY POSITION ASSISTANT ===
if tier_info['Allow Ancillaries']:
    with st.expander("🔧 Ancillary Position Assistant", expanded=False):
        pir_count = st.number_input("Number of PIRs", min_value=0, step=1)
        spitfire_count = st.number_input("Number of Spitfires", min_value=0, step=1)

        if pir_count > 0 or spitfire_count > 0:
            if st.button("Begin Ancillary Position Assignment"):
                st.session_state['remaining_pirs'] = pir_count
                st.session_state['remaining_spitfires'] = spitfire_count
                st.session_state['ancillary_mode'] = True
                st.session_state['ancillary_positions'] = []

# === ANCILLARY POSITION INPUT ===
def process_ancillaries():
    total_segments = math.floor(selected_length / BPSL)
    st.info(f"Total Segments Available: {total_segments}")

    # PIR Handling
    if st.session_state['remaining_pirs'] > 0:
        pir_index = pir_count - st.session_state['remaining_pirs'] + 1
        pir_pos = st.number_input(f"Enter position (mm) for PIR {pir_index}", min_value=0.0, max_value=selected_length, step=1.0)
        segment_no = math.ceil(pir_pos / BPSL)
        if st.button(f"Confirm PIR {pir_index} at Segment {segment_no}"):
            st.session_state['ancillary_positions'].append(f"PIR-{pir_index}/{segment_no}")
            st.session_state['remaining_pirs'] -= 1

    # Spitfire Handling
    elif st.session_state['remaining_spitfires'] > 0:
        spitfire_index = spitfire_count - st.session_state['remaining_spitfires'] + 1
        spitfire_pos = st.number_input(f"Enter position (mm) for Spitfire {spitfire_index}", min_value=0.0, max_value=selected_length, step=1.0)
        segment_no = math.ceil(spitfire_pos / BPSL)
        if st.button(f"Confirm Spitfire {spitfire_index} at Segment {segment_no}"):
            st.session_state['ancillary_positions'].append(f"SPITFIRE-{spitfire_index}/{segment_no}")
            st.session_state['remaining_spitfires'] -= 1

    # Finish and Update Table
    if st.session_state['remaining_pirs'] == 0 and st.session_state['remaining_spitfires'] == 0:
        st.success("All Ancillaries Positioned!")
        ancillary_col = " | ".join(st.session_state['ancillary_positions'])

        # Update the ancillary column in the length table
        idx = st.session_state['length_table'].index[-1]
        st.session_state['length_table'].at[idx, "Ancillary Positions"] = ancillary_col
        st.session_state['ancillary_mode'] = False

if st.session_state['ancillary_mode']:
    process_ancillaries()

# === FOOTER ===
st.caption("Version 3.3 - Length Optimisation + Ancillary Positions + Tier-Based Defaults")
