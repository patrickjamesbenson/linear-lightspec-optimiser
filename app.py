import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="Luminaire Length Table", layout="wide")
st.title("📏 Luminaire Length Configuration & Build Table")

# === SESSION STATE INITIALIZATION ===
if 'length_table' not in st.session_state:
    st.session_state['length_table'] = pd.DataFrame(columns=[
        "Luminaire Length (mm)", "Tier", "Chip Scaling % (Y)", "ECG Type",
        "PIR Qty", "Spitfire Qty", "Notes / Reason"
    ])

if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"

if 'chip_scaling' not in st.session_state:
    st.session_state['chip_scaling'] = 15.0  # Professional default +15%

if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "DALI 2 Wired"

if 'pir_enabled' not in st.session_state:
    st.session_state['pir_enabled'] = True

if 'spitfire_enabled' not in st.session_state:
    st.session_state['spitfire_enabled'] = True

# === TIER RULES TABLE ===
TIER_RULES = {
    "Core": {
        "chip_scaling": 0.0,
        "ecg_type": "Fixed Output",
        "pir_enabled": False,
        "spitfire_enabled": False,
        "tooltip": "Core: 0% Chip Scaling, Fixed Output ECG, No PIR/Spitfire"
    },
    "Professional": {
        "chip_scaling": 15.0,
        "ecg_type": "DALI 2 Wired",
        "pir_enabled": True,
        "spitfire_enabled": True,
        "tooltip": "Professional: +15% Chip Scaling, DALI 2 Wired ECG, PIR/Spitfire Allowed"
    },
    "Advanced": {
        "chip_scaling": 0.0,
        "ecg_type": "DALI 2 Wireless",
        "pir_enabled": True,
        "spitfire_enabled": True,
        "tooltip": "Advanced: Custom Chip Scaling, DALI 2 Wireless ECG, PIR/Spitfire Allowed"
    },
    "Bespoke": {
        "chip_scaling": 0.0,
        "ecg_type": "Custom",
        "pir_enabled": True,
        "spitfire_enabled": True,
        "tooltip": "Bespoke: Fully Custom Tier"
    }
}

# === TIER SELECTION ===
st.sidebar.header("⚙️ Tier + System Settings")

tier_selection = st.sidebar.selectbox(
    label="Select Product Tier",
    options=["Core", "Professional", "Advanced", "Bespoke"],
    index=1,
    help="Tier determines Chip Scaling %, ECG Type, and PIR/Spitfire availability"
)

tier_settings = TIER_RULES[tier_selection]

# === APPLY TIER RULES ===
st.session_state['tier'] = tier_selection
st.session_state['chip_scaling'] = tier_settings['chip_scaling']
st.session_state['ecg_type'] = tier_settings['ecg_type']
st.session_state['pir_enabled'] = tier_settings['pir_enabled']
st.session_state['spitfire_enabled'] = tier_settings['spitfire_enabled']

st.sidebar.info(tier_settings['tooltip'])

# === OVERRIDE CHIP SCALING ===
custom_chip_scaling = st.sidebar.number_input(
    label="LED Chip Scaling % (Y)",
    min_value=-50.0, max_value=50.0, step=0.1,
    value=st.session_state['chip_scaling'],
    help="Alpha Ref: Y. Scaling from base IES lumens"
)

if custom_chip_scaling != st.session_state['chip_scaling']:
    st.warning("Custom Scaling Applied: Reason Required")
    reason_for_change = st.text_area("Mandatory Reason for Custom Scaling", key="reason_chip_scaling")
    if reason_for_change == "":
        st.error("Provide a reason to proceed.")
    st.session_state['chip_scaling'] = custom_chip_scaling
else:
    reason_for_change = ""

# === OVERRIDE ECG TYPE (Optional Custom in Advanced / Bespoke) ===
ecg_types_available = ["Fixed Output", "DALI 2 Wired", "DALI 2 Wireless", "Custom"]

ecg_selection = st.sidebar.selectbox(
    "Select ECG Type",
    options=ecg_types_available,
    index=ecg_types_available.index(st.session_state['ecg_type']),
    help="Alpha Ref: ECG Type per Tier. Overrides require Reason."
)

if ecg_selection != st.session_state['ecg_type']:
    st.warning("Custom ECG Type Selected: Reason Required")
    reason_for_ecg = st.text_area("Mandatory Reason for ECG Selection", key="reason_ecg_selection")
    if reason_for_ecg == "":
        st.error("Provide a reason to proceed.")
    st.session_state['ecg_type'] = ecg_selection
else:
    reason_for_ecg = ""

# === PIR & SPITFIRE QUANTITIES ===
pir_qty = 0
spitfire_qty = 0

if st.session_state['pir_enabled']:
    pir_qty = st.sidebar.number_input("PIR Qty", min_value=0, max_value=10, value=0, step=1)
else:
    st.sidebar.warning("PIR Disabled for Core Tier")

if st.session_state['spitfire_enabled']:
    spitfire_qty = st.sidebar.number_input("Spitfire Qty", min_value=0, max_value=10, value=0, step=1)
else:
    st.sidebar.warning("Spitfire Disabled for Core Tier")

# === TARGET LENGTH INPUT ===
target_length = st.sidebar.number_input(
    "Enter Target Luminaire Length (mm)",
    min_value=100.0, max_value=10000.0, step=10.0, value=2800.0,
    help="Defines the overall luminaire length (Alpha Ref: TL)"
)

# === ADD TO LENGTH TABLE BUTTON ===
if st.sidebar.button("Add Length to Build Table"):
    # Gather Reason Field
    combined_reason = ""
    if reason_for_change:
        combined_reason += f"Chip Scaling: {reason_for_change}. "
    if reason_for_ecg:
        combined_reason += f"ECG Selection: {reason_for_ecg}."

    new_row = pd.DataFrame([{
        "Luminaire Length (mm)": target_length,
        "Tier": st.session_state['tier'],
        "Chip Scaling % (Y)": st.session_state['chip_scaling'],
        "ECG Type": st.session_state['ecg_type'],
        "PIR Qty": pir_qty,
        "Spitfire Qty": spitfire_qty,
        "Notes / Reason": combined_reason
    }])

    st.session_state['length_table'] = pd.concat([st.session_state['length_table'], new_row], ignore_index=True)
    st.success("Luminaire length added to the build table ✅")

# === DISPLAY LENGTH TABLE ===
st.subheader("📋 Luminaire Build Length Table")

if st.session_state['length_table'].empty:
    st.info("No lengths added yet.")
else:
    st.dataframe(st.session_state['length_table'], use_container_width=True)

# === TODO APPEND ===
st.sidebar.markdown("---")
st.sidebar.markdown("✅ **TODO List**")
st.sidebar.markdown("""
- Add Base LED Chip Table for Gen1 / Gen2 scaling ✅  
- Implement CCT Selector with Scaling Factors  
- Link Build Table to LumCAT Generator (Placeholder added)  
- Build Summary / BOM Output in CSV  
- PDF Export Integration (After BOM logic finalization)
""")

st.caption("Version 3.2 - Luminaire Length Table + Tier Rule Logic ✅")
