import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("🔧 Linear Lightspec Optimiser v4.0 Alpha")

# === SESSION STATE INITIALIZATION ===
if 'project_name' not in st.session_state:
    st.session_state['project_name'] = ""

if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"

if 'led_scaling' not in st.session_state:
    st.session_state['led_scaling'] = 15.0  # Default for Professional

if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "DALI2"

if 'project_lengths' not in st.session_state:
    st.session_state['project_lengths'] = []

if 'ancillary_positions' not in st.session_state:
    st.session_state['ancillary_positions'] = {}

# === ALPHA CODES ===
ALPHA = {
    "F": "Watts (Photometric Params Line 8)",
    "Y": "LED Scaling % (Advanced Settings)",
    "A": "LED in Series Length mm (Board Config)",
    "S": "Series Count",
    "P": "Parallel Count",
    "W": "ECG Max Watt Output",
}

# === TIER DEFAULTS ===
TIER_DEFAULTS = {
    "Core": {"LED Scaling": 0, "ECG Stress": 100, "LED Stress": 350, "ECG Type": "Fixed Output"},
    "Professional": {"LED Scaling": 15, "ECG Stress": 85, "LED Stress": 300, "ECG Type": "DALI2"},
    "Advanced": {"LED Scaling": 15, "ECG Stress": 75, "LED Stress": 250, "ECG Type": "Wireless"},
    "Bespoke": {"LED Scaling": 0, "ECG Stress": 75, "LED Stress": 250, "ECG Type": "Custom"}
}

# === PROJECT SETUP ===
st.sidebar.subheader("📁 Project Setup")

st.session_state['project_name'] = st.sidebar.text_input("Enter Project Name", st.session_state['project_name'])

# Product Tier Selection
st.session_state['tier'] = st.sidebar.selectbox("Select Product Tier", list(TIER_DEFAULTS.keys()), index=1)

tier_defaults = TIER_DEFAULTS[st.session_state['tier']]

# === DISPLAY SELECTED TIER CONFIG ===
with st.sidebar.expander(f"ℹ️ Tier Settings ({st.session_state['tier']})", expanded=True):
    st.write(f"LED Scaling %: {tier_defaults['LED Scaling']}")
    st.write(f"ECG Type: {tier_defaults['ECG Type']}")
    st.write(f"ECG Stress Limit: {tier_defaults['ECG Stress']}%")
    st.write(f"LED Stress Limit: {tier_defaults['LED Stress']}mA")

# === FILE UPLOAD (IES PARSING) ===
st.subheader("📄 Upload & Parse IES File")
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_file'] = {'name': uploaded_file.name, 'content': file_content}
    st.success(f"Uploaded: {uploaded_file.name}")

def parse_ies_file(content):
    lines = content.splitlines()
    header_lines, data_lines = [], []
    reading_data = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            reading_data = True
        elif not reading_data:
            header_lines.append(stripped)
        else:
            data_lines.append(stripped)

    photometric_raw = " ".join(data_lines[:2]).split()
    photometric_params = [float(x) if '.' in x or 'e' in x.lower() else int(x) for x in photometric_raw]

    return header_lines, photometric_params

if 'ies_file' in st.session_state:
    header_lines, photometric_params = parse_ies_file(st.session_state['ies_file']['content'])
    watts_f = photometric_params[12]
    lumens_f = photometric_params[1] * photometric_params[0]

    st.info(f"Parsed IES File Watts [F]: {watts_f}W | Lumens: {lumens_f}")

# === BOARD CONFIGURATION ===
st.subheader("📐 LED Board Configuration")

bpsl_a = st.number_input("LED in Series Length (A)", min_value=30.0, max_value=100.0, value=46.666, step=0.1, help="Typically 280mm Zhaga Board / Parallel Count (P)")

series_count_s = st.number_input("Series LEDs (S)", min_value=1, max_value=12, value=6)
parallel_count_p = st.number_input("Parallel Circuits (P)", min_value=1, max_value=12, value=4)

ecg_wattage_w = st.number_input("ECG Max Wattage (W)", min_value=10.0, max_value=200.0, value=50.0, step=1.0)

# === LENGTH OPTIMISATION ===
st.subheader("📏 Length Optimisation & Build")

target_length = st.number_input("Target Length (m)", min_value=0.1, max_value=10.0, value=2.8, step=0.001)

board_b_length = 6 * bpsl_a
board_c_length = 12 * bpsl_a
board_d_length = 24 * bpsl_a

def optimise_length(target_m, tier):
    target_mm = target_m * 1000
    boards = []
    remaining = target_mm

    board_lengths = [board_d_length, board_c_length, board_b_length]
    if tier in ["Advanced", "Bespoke"]:
        board_lengths.append(bpsl_a)

    for bl in board_lengths:
        while remaining >= bl:
            boards.append(bl)
            remaining -= bl

    if tier == "Professional" and remaining >= bpsl_a:
        boards.append(bpsl_a)

    return boards, sum(boards)

selected_boards, final_length = optimise_length(target_length, st.session_state['tier'])

st.write(f"Closest Longer Length: {final_length/1000:.3f}m")
st.button("Add Length", on_click=lambda: st.session_state['project_lengths'].append({
    'Tier': st.session_state['tier'],
    'Target Length': target_length,
    'Selected Length': final_length / 1000,
    'Boards': selected_boards,
    'LED Scaling': tier_defaults['LED Scaling'],
    'ECG Type': tier_defaults['ECG Type'],
    'PIR Count': 0,
    'Spitfire Count': 0,
}))

# === DISPLAY LENGTH TABLE ===
if st.session_state['project_lengths']:
    df_lengths = pd.DataFrame(st.session_state['project_lengths'])
    st.table(df_lengths)

# === ADMIN PANEL ===
with st.sidebar.expander("🔐 Admin Panel"):
    st.write("⚙️ Manage Tier Defaults (WIP)")
    for t in TIER_DEFAULTS.keys():
        st.write(f"Tier: {t}")
        TIER_DEFAULTS[t]['LED Scaling'] = st.number_input(f"{t} - LED Scaling", value=TIER_DEFAULTS[t]['LED Scaling'])
        TIER_DEFAULTS[t]['ECG Stress'] = st.number_input(f"{t} - ECG Stress", value=TIER_DEFAULTS[t]['ECG Stress'])
        TIER_DEFAULTS[t]['LED Stress'] = st.number_input(f"{t} - LED Stress", value=TIER_DEFAULTS[t]['LED Stress'])

# === FOOTER ===
st.caption("Version 4.0 Alpha - Unified App ✅")

