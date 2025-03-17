import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="Length Optimisation Table", layout="wide")
st.title("🛠️ Length Optimisation Table")

# === SESSION STATE INITIALIZATION ===
if 'build_table' not in st.session_state:
    st.session_state['build_table'] = []

if 'project_name' not in st.session_state:
    st.session_state['project_name'] = ""

if 'tier_locked' not in st.session_state:
    st.session_state['tier_locked'] = False

if 'show_alpha_labels' not in st.session_state:
    st.session_state['show_alpha_labels'] = False

# === DEFAULT VALUES BY TIER ===
TIER_DEFAULTS = {
    "Core": {
        "LED Scaling %": 0,
        "ECG Type": "Fixed Output",
        "PIR": "N/A",
        "Spitfire": "N/A"
    },
    "Professional": {
        "LED Scaling %": 15,
        "ECG Type": "DALI-2",
        "PIR": "Available",
        "Spitfire": "Available"
    },
    "Advanced": {
        "LED Scaling %": 15,
        "ECG Type": "DALI-2 Wireless",
        "PIR": "Available",
        "Spitfire": "Available"
    },
    "Bespoke": {
        "LED Scaling %": 15,
        "ECG Type": "Custom",
        "PIR": "Available",
        "Spitfire": "Available"
    }
}

# === FUNCTION: Calculate Optimised Lengths ===
def calculate_lengths(target_length, BPSL):
    """
    Given a target length and BPSL, calculate:
    - Optimal (nearest buildable)
    - Closest Shorter
    - Closest Longer
    """
    # Available board lengths in mm for calculations
    board_b = 6 * BPSL
    board_c = 12 * BPSL
    board_d = 24 * BPSL
    board_lengths = [board_d, board_c, board_b, BPSL]

    current_length = 0
    build = []
    remaining = target_length

    for board in board_lengths:
        while remaining >= board:
            build.append(board)
            current_length += board
            remaining -= board

    # Closest Shorter is current_length
    closest_shorter = current_length

    # Closest Longer adds another smallest board
    closest_longer = current_length
    if remaining > 0:
        closest_longer += min(board_lengths)

    # Check for exact match
    if abs(target_length - current_length) < 0.01:
        optimal_text = "Optimal Achieved"
    else:
        optimal_text = ""

    return closest_shorter, closest_longer, optimal_text

# === MAIN INPUTS ===
with st.expander("🔨 Project Setup", expanded=True):
    # Project Name
    st.session_state['project_name'] = st.text_input("Project Name (for CSV export)", value=st.session_state['project_name'])

    # Product Tier Selection
    if not st.session_state['tier_locked']:
        tier_selection = st.selectbox("Select Product Tier", options=["Core", "Professional", "Advanced", "Bespoke"], index=1)
        lock_tier = st.button("Lock Tier")
        if lock_tier:
            st.session_state['tier'] = tier_selection
            st.session_state['tier_locked'] = True
            st.success(f"Tier '{tier_selection}' locked for this project.")
    else:
        st.info(f"✅ Product Tier Locked: {st.session_state['tier']}")

    # Target Length Input (in mm)
    target_length = st.number_input("Target Luminaire Length (mm)", min_value=100.0, max_value=10000.0, step=1.0)

# === Tier Defaults ===
selected_tier = st.session_state.get('tier', 'Professional')
tier_config = TIER_DEFAULTS[selected_tier]
BPSL = 46.666 if selected_tier in ['Core', 'Professional'] else 46.666  # Can update from advanced settings

# === CALCULATE LENGTH OPTIONS ===
shorter, longer, optimal_flag = calculate_lengths(target_length, BPSL)

# === BUTTONS ===
col1, col2, col3 = st.columns(3)

if optimal_flag:
    with col2:
        if st.button("✅ Optimal Build"):
            st.session_state['build_table'].append({
                "Project Name": st.session_state['project_name'],
                "Target Length (mm)": target_length,
                "Optimised Length (mm)": target_length,
                "Tier": selected_tier,
                "LED Scaling %": tier_config['LED Scaling %'],
                "ECG Type": tier_config['ECG Type'],
                "PIR": tier_config['PIR'],
                "Spitfire": tier_config['Spitfire'],
                "Timestamp": time.time()
            })
else:
    with col1:
        if st.button("⬅️ Closest Shorter"):
            st.session_state['build_table'].append({
                "Project Name": st.session_state['project_name'],
                "Target Length (mm)": target_length,
                "Optimised Length (mm)": shorter,
                "Tier": selected_tier,
                "LED Scaling %": tier_config['LED Scaling %'],
                "ECG Type": tier_config['ECG Type'],
                "PIR": tier_config['PIR'],
                "Spitfire": tier_config['Spitfire'],
                "Timestamp": time.time()
            })
    with col3:
        if st.button("➡️ Closest Longer"):
            st.session_state['build_table'].append({
                "Project Name": st.session_state['project_name'],
                "Target Length (mm)": target_length,
                "Optimised Length (mm)": longer,
                "Tier": selected_tier,
                "LED Scaling %": tier_config['LED Scaling %'],
                "ECG Type": tier_config['ECG Type'],
                "PIR": tier_config['PIR'],
                "Spitfire": tier_config['Spitfire'],
                "Timestamp": time.time()
            })

# === BUILD TABLE DISPLAY ===
if st.session_state['build_table']:
    st.subheader("📋 Length Build Table")
    df_builds = pd.DataFrame(st.session_state['build_table'])
    st.table(df_builds)

    # CSV Export
    csv_file = df_builds.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download CSV", data=csv_file, file_name=f"{st.session_state['project_name']}_length_builds.csv", mime='text/csv')

# === ADMIN PANEL ===
with st.expander("🛠️ Admin Controls", expanded=False):
    st.markdown("### Tier Defaults Setup")
    selected_tier_admin = st.selectbox("Edit Tier Defaults", options=list(TIER_DEFAULTS.keys()))

    for key in ["LED Scaling %", "ECG Type", "PIR", "Spitfire"]:
        new_value = st.text_input(f"{selected_tier_admin} - {key}", value=str(TIER_DEFAULTS[selected_tier_admin][key]))
        TIER_DEFAULTS[selected_tier_admin][key] = new_value

    st.session_state['show_alpha_labels'] = st.checkbox("🔡 Show Alpha Labels in UI")
    if st.session_state['show_alpha_labels']:
        st.info("Alpha Labels enabled for all values.")

# === FOOTER ===
st.caption("Version 3.2 - Length Optimisation Table ✅")
