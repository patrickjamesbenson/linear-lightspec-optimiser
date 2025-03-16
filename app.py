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
    st.session_state['ecg_max_output'] = 140  # Default for DALI-2

if 'ecg_stress_limit' not in st.session_state:
    st.session_state['ecg_stress_limit'] = 85  # %

if 'led_stress_limit' not in st.session_state:
    st.session_state['led_stress_limit'] = 300  # mA

if 'legend_show' not in st.session_state:
    st.session_state['legend_show'] = True

# === ADMIN PANEL ===
st.sidebar.header("🔒 Admin Mode Controls")
st.sidebar.toggle("Admin Mode", key='admin_mode')

if st.session_state['admin_mode']:
    st.subheader("🔧 System Voltage Control")
    st.session_state['voltage'] = st.number_input(
        "System Voltage (V)", min_value=24.0, max_value=48.0,
        value=st.session_state['voltage'], step=0.1,
        help="Default 36V for SELV compliance. Changes apply system-wide."
    )

    st.subheader("⚡ ECG Configuration")
    ecg_options = {
        "Fixed Output": 150,
        "DALI-2": 140,
        "Wireless DALI-2": 120,
        "Custom (Editable)": None
    }

    st.session_state['ecg_type'] = st.selectbox("Select ECG Type", list(ecg_options.keys()))

    if st.session_state['ecg_type'] == "Custom (Editable)":
        st.session_state['ecg_max_output'] = st.number_input(
            "Custom ECG Max Output (W)", min_value=10, max_value=300,
            value=150, step=1, help="Custom maximum output for ECG"
        )
    else:
        st.session_state['ecg_max_output'] = ecg_options[st.session_state['ecg_type']]

    st.session_state['ecg_stress_limit'] = st.slider(
        "ECG Stress Loading (%)", min_value=50, max_value=100,
        value=st.session_state['ecg_stress_limit'],
        help="Engineering safety factor for ECG loading. Default varies by Tier."
    )

    st.subheader("💡 LED Stress & Current")
    st.session_state['led_stress_limit'] = st.slider(
        "LED Max Current per Chip (mA)", min_value=100, max_value=400,
        value=st.session_state['led_stress_limit'],
        help="Defines maximum allowable LED current for product tiers."
    )

    st.subheader("📝 Defaults by Tier (Reference Table)")
    default_data = [
        {"Tier": "Core", "ECG Stress (%)": 100, "LED Stress (mA)": 350},
        {"Tier": "Professional", "ECG Stress (%)": 85, "LED Stress (mA)": 300},
        {"Tier": "Advanced", "ECG Stress (%)": 75, "LED Stress (mA)": 250},
        {"Tier": "Bespoke", "ECG Stress (%)": "Custom", "LED Stress (mA)": "Custom"}
    ]
    default_df = pd.DataFrame(default_data)
    st.table(default_df)

    # === LEGEND & TOOLTIP REFERENCE ===
    if st.toggle("Show Calculation Legend", key='legend_show'):
        st.subheader("📚 Legend - Variable Sources & Formulas (Admin View)")
        legend_data = [
            {"Letter": "A", "Description": "LED Stack Length", "Source": "Advanced Settings → Stack Length (mm)"},
            {"Letter": "P", "Description": "Parallel Modules", "Source": "LED Stack Config Table"},
            {"Letter": "S", "Description": "LEDs in Series", "Source": "LED Stack Config Table"},
            {"Letter": "Y", "Description": "LED Chip Scaling (%)", "Source": "Advanced Settings → Chip Scaling"},
            {"Letter": "W", "Description": "IES Input Watts", "Source": "IES File → Photometric Params Line 12"},
            {"Letter": "L", "Description": "Total Lumens", "Source": "Computed Baseline → Line 3 Lumens"}
        ]
        legend_df = pd.DataFrame(legend_data)
        st.table(legend_df)

st.caption("Admin Panel v1.0 - ECG & LED Stress Controls ✅")
