import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser v4.1", layout="wide")
st.title("🔧 Linear Lightspec Optimiser v4.1")

# === SESSION STATE INITIALIZATION ===
if 'project_name' not in st.session_state:
    st.session_state['project_name'] = ""

if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"

if 'led_scaling' not in st.session_state:
    st.session_state['led_scaling'] = 15  # Professional default

if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "DALI2"

if 'ecg_stress' not in st.session_state:
    st.session_state['ecg_stress'] = 85  # Professional default

if 'led_stress' not in st.session_state:
    st.session_state['led_stress'] = 300  # Professional default

if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

# === PROJECT SETUP ===
st.sidebar.header("📁 Project Setup")

st.session_state['project_name'] = st.sidebar.text_input("Enter Project Name", placeholder="Project Name Required")
if not st.session_state['project_name']:
    st.sidebar.warning("Please enter a project name to continue.")

# === TIER SELECTION ===
tiers = ["Core", "Professional", "Advanced", "Bespoke"]
tier = st.sidebar.selectbox("Select Product Tier", tiers, index=tiers.index(st.session_state['tier']))

# === APPLY TIER DEFAULTS ===
def apply_tier_defaults(selected_tier):
    if selected_tier == "Core":
        st.session_state['led_scaling'] = 0
        st.session_state['ecg_stress'] = 100
        st.session_state['led_stress'] = 350
        st.session_state['ecg_type'] = "Fixed Output"
    elif selected_tier == "Professional":
        st.session_state['led_scaling'] = 15
        st.session_state['ecg_stress'] = 85
        st.session_state['led_stress'] = 300
        st.session_state['ecg_type'] = "DALI2"
    elif selected_tier == "Advanced":
        st.session_state['led_scaling'] = 15
        st.session_state['ecg_stress'] = 75
        st.session_state['led_stress'] = 250
        st.session_state['ecg_type'] = "Wireless"
    elif selected_tier == "Bespoke":
        st.session_state['led_scaling'] = 0
        st.session_state['ecg_stress'] = 75
        st.session_state['led_stress'] = 250
        st.session_state['ecg_type'] = "Custom"

apply_tier_defaults(tier)
st.session_state['tier'] = tier

# === DISPLAY TIER INFO ===
st.sidebar.markdown(f"### ℹ️ Tier Settings ({tier})")
st.sidebar.write(f"**LED Scaling %:** {st.session_state['led_scaling']}")
st.sidebar.write(f"**ECG Type:** {st.session_state['ecg_type']}")
st.sidebar.write(f"**ECG Stress Limit:** {st.session_state['ecg_stress']}%")
st.sidebar.write(f"**LED Stress Limit:** {st.session_state['led_stress']}mA")

# === ADMIN PANEL ===
with st.sidebar.expander("🔐 Admin Panel", expanded=False):
    st.markdown("⚙️ Manage Tier Defaults (WIP)")

    for t in tiers:
        st.markdown(f"#### Tier: {t}")
        st.number_input(f"{t} - LED Scaling", value=st.session_state['led_scaling'], key=f"{t}_led_scaling")
        st.number_input(f"{t} - ECG Stress", value=st.session_state['ecg_stress'], key=f"{t}_ecg_stress")
        st.number_input(f"{t} - LED Stress", value=st.session_state['led_stress'], key=f"{t}_led_stress")

# === MAIN SECTION ===
st.subheader("📄 Upload & Parse IES File")

uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{
        'name': uploaded_file.name,
        'content': file_content
    }]
    st.success(f"Uploaded: {uploaded_file.name}")

# === PARSE IES FILE ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    photometric_params = []
    reading_data = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            reading_data = True
        if reading_data:
            data = " ".join(lines[lines.index(line)+1:]).split()
            photometric_params = [float(x) for x in data[:13]]
            break
    return photometric_params

if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    photometric_params = parse_ies_file(ies_file['content'])

    watts_f = photometric_params[12] if len(photometric_params) > 12 else 0
    lumens_l = photometric_params[1] if len(photometric_params) > 1 else 0

    st.info(f"Parsed IES File Watts **[F]**: {watts_f}W | Lumens **[L]**: {lumens_l}")

# === LED BOARD CONFIG ===
st.subheader("📐 LED Board Configuration")

led_in_series_length_a = st.number_input("LED in Series Length (A)", min_value=30.0, max_value=100.0, value=46.666, step=0.1)
series_leds_s = st.number_input("Series LEDs (S)", min_value=1, max_value=12, value=6)
parallel_circuits_p = st.number_input("Parallel Circuits (P)", min_value=1, max_value=12, value=4)
ecg_max_w = st.number_input("ECG Max Wattage (W)", min_value=1.0, max_value=200.0, value=50.0, step=1.0)

# === FOOTER ===
st.caption("Version 4.1 - Unified App Start ✅")
