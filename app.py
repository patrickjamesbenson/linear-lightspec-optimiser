import streamlit as st
import pandas as pd

# === PAGE CONFIG ===
st.set_page_config(page_title="Admin Panel - Linear Lightspec Optimiser", layout="wide")
st.title("🛠️ Admin Panel - Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'admin_mode' not in st.session_state:
    st.session_state['admin_mode'] = True
if 'voltage' not in st.session_state:
    st.session_state['voltage'] = 36.0
if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "Professional (DALI-2)"
if 'ecg_max_output' not in st.session_state:
    st.session_state['ecg_max_output'] = 140
if 'ecg_stress_limit' not in st.session_state:
    st.session_state['ecg_stress_limit'] = 85
if 'led_stress_limit' not in st.session_state:
    st.session_state['led_stress_limit'] = 300
if 'legend_show' not in st.session_state:
    st.session_state['legend_show'] = False
if 'body_max_increment' not in st.session_state:
    st.session_state['body_max_increment'] = 3500.0

# === ADMIN PANEL ===
st.sidebar.header("🔒 Admin Mode Controls")
st.sidebar.toggle("Admin Mode", key='admin_mode')

if st.session_state['admin_mode']:

    st.subheader("🔧 System Voltage Control")
    st.session_state['voltage'] = st.number_input(
        "System Voltage (V)", min_value=24.0, max_value=48.0,
        value=st.session_state['voltage'], step=0.1,
        help="Company mandate is 36V SELV. Changes will affect system-wide calculations."
    )

    st.subheader("⚡ ECG Configuration")
    ecg_defaults = {
        "Fixed Output": {"max_output": 150, "stress_limit": 100},
        "DALI-2": {"max_output": 140, "stress_limit": 85},
        "Wireless DALI-2": {"max_output": 120, "stress_limit": 75},
        "Custom (Editable)": {"max_output": None, "stress_limit": None}
    }

    ecg_selection = st.selectbox("Select ECG Type", list(ecg_defaults.keys()))
    st.session_state['ecg_type'] = ecg_selection

    if ecg_selection == "Custom (Editable)":
        st.session_state['ecg_max_output'] = st.number_input(
            "Custom ECG Max Output (W)", min_value=10, max_value=300,
            value=st.session_state['ecg_max_output'], step=1
        )
        st.session_state['ecg_stress_limit'] = st.slider(
            "Custom ECG Stress Loading (%)", min_value=50, max_value=100,
            value=st.session_state['ecg_stress_limit']
        )
        # Force reason field
        reason = st.text_area("Reason for Custom ECG Settings")
        if not reason:
            st.error("You must provide a reason for Custom ECG Settings.")
    else:
        st.session_state['ecg_max_output'] = ecg_defaults[ecg_selection]["max_output"]
        st.session_state['ecg_stress_limit'] = ecg_defaults[ecg_selection]["stress_limit"]

    st.subheader("💡 LED Stress & Current Limits")
    st.session_state['led_stress_limit'] = st.slider(
        "LED Max Current per Chip (mA)", min_value=100, max_value=400,
        value=st.session_state['led_stress_limit'],
        help="Defines maximum allowable LED current for product tiers."
    )

    st.subheader("📏 Mechanical Limits")
    st.session_state['body_max_increment'] = st.number_input(
        "Max Body Segment Length (mm)", min_value=1000.0, max_value=5000.0,
        value=st.session_state['body_max_increment'], step=50.0,
        help="Max aluminium extrusion length. Default 3.5m."
    )

    st.subheader("📝 Calculation Legend")
    if st.toggle("Show Legend", key='legend_show'):
        legend_data = [
            {"Letter": "A", "Description": "LED Stack Length (mm)", "Source": "Advanced Settings → Stack Length"},
            {"Letter": "P", "Description": "Parallel Modules (Stacks)", "Source": "LED Board Config"},
            {"Letter": "S", "Description": "LEDs in Series per Stack", "Source": "LED Board Config"},
            {"Letter": "Y", "Description": "LED Chip Scaling (%)", "Source": "Advanced Settings → Chip Scaling"},
            {"Letter": "W", "Description": "IES Input Watts", "Source": "IES File → Photometric Params"},
            {"Letter": "E", "Description": "ECG Max Output (W)", "Source": "Admin Panel → ECG Type"},
            {"Letter": "F", "Description": "ECG Stress Loading (%)", "Source": "Admin Panel → ECG Stress Limit"}
        ]
        legend_df = pd.DataFrame(legend_data)
        st.table(legend_df)

st.caption("Admin Panel v1.2 - ECG / LED / Body Segment Controls ✅")
