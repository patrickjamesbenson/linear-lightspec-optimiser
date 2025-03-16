import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="ECG BOM + Power Load Distribution", layout="wide")
st.title("🚀 ECG BOM + Power Load Distribution & Luminaire Build Table")

# === SESSION STATE INITIALIZATION ===
if 'stack_length' not in st.session_state:
    st.session_state['stack_length'] = 46.666
if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"
if 'target_length' not in st.session_state:
    st.session_state['target_length'] = 280.0
if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "DALI2"
if 'ecg_custom' not in st.session_state:
    st.session_state['ecg_custom'] = False
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

# === ECG Defaults ===
ECG_WATTS = {
    "Fixed Output": 100,
    "DALI2": 80,
    "Wireless DALI2": 60
}

# === PARAMETERS ===
BPSL = st.session_state['stack_length']  # Base Parallel Segment Length (A)
BODY_MAX = 3500  # mm aluminium extrusion length
END_PLATE = 5.5  # mm per endplate
PIR_LENGTH = BPSL if BPSL >= 30 else 30  # PIR replacement length
SPITFIRE_LENGTH = BPSL if BPSL >= 30 else 30  # Spitfire replacement length

board_b_length = 6 * BPSL
board_c_length = 12 * BPSL
board_d_length = 24 * BPSL
target_length = st.session_state['target_length']

# === ECG Power Handling ===
ecg_choice = st.session_state['ecg_type']
if ecg_choice == "Custom":
    ecg_max_watt = st.number_input("Custom ECG Max Output (W)", min_value=10, max_value=500, value=100, step=1)
else:
    ecg_max_watt = ECG_WATTS[ecg_choice]

# === LENGTH OPTIMISATION ===
def optimise_length(target, tier):
    used_boards = []
    remaining_length = target
    if tier == "Core":
        board_lengths = [board_d_length, board_c_length, board_b_length]
    elif tier == "Professional":
        board_lengths = [board_d_length, board_c_length, board_b_length]
    else:
        board_lengths = [board_d_length, board_c_length, board_b_length, BPSL]
    for board in board_lengths:
        while remaining_length >= board:
            used_boards.append(board)
            remaining_length -= board
    if remaining_length > 0 and tier == "Professional":
        while remaining_length >= BPSL:
            used_boards.append(BPSL)
            remaining_length -= BPSL
    return used_boards, sum(used_boards)

selected_boards, final_length = optimise_length(target_length, st.session_state['tier'])

# === SEGMENT & ECG DISTRIBUTION ===
def allocate_segments(total_length, tier, ecg_max_watt):
    segments = []
    current_pos = 0
    segment_id = 1
    while current_pos < total_length:
        remaining = total_length - current_pos
        segment_length = min(BODY_MAX, remaining)
        
        # Calculate LED Segments Per Segment
        led_segments = int(segment_length // BPSL)
        led_power_per_segment = 12  # Dummy value, typically derived from LED scaling
        total_led_power = led_segments * led_power_per_segment
        
        # ECG Calculation
        ecg_required = np.ceil(total_led_power / ecg_max_watt)
        
        segments.append({
            "Segment ID": segment_id,
            "Segment Length (mm)": segment_length,
            "LED Segments": led_segments,
            "ECG Count": ecg_required,
            "Total Power (W)": total_led_power
        })
        
        current_pos += segment_length
        segment_id += 1
    return segments

segments_allocated = allocate_segments(final_length, st.session_state['tier'], ecg_max_watt)

# === DISPLAY RESULTS ===
st.subheader("📏 Optimised Luminaire Build Summary")
st.write(f"**Product Tier:** `{st.session_state['tier']}`")
st.write(f"**Base Parallel Segment Length (BPSL A):** `{BPSL:.1f}mm`")
st.write(f"**Target Length:** `{target_length:.1f}mm`")
st.write(f"**Optimised Length Achieved:** `{final_length:.1f}mm`")
st.write(f"**ECG Type:** `{ecg_choice}` | **ECG Max Output:** `{ecg_max_watt}W`")

# Board Breakdown
df_boards = pd.DataFrame({"Board Lengths (mm)": selected_boards})
st.subheader("📦 Board Selection Breakdown")
st.table(df_boards)

# Segment Allocation
df_segments = pd.DataFrame(segments_allocated)
st.subheader("🛠️ Segment & ECG Allocation Table")
st.table(df_segments)

# Board Reference
with st.expander("📋 Board Type Reference", expanded=False):
    board_data = [
        {"Board": "Base Parallel Segment (A)", "Formula": "BPSL", "Length (mm)": f"{BPSL:.1f}"},
        {"Board": "Board B", "Formula": "6 x A", "Length (mm)": f"{board_b_length:.1f}"},
        {"Board": "Board C", "Formula": "12 x A", "Length (mm)": f"{board_c_length:.1f}"},
        {"Board": "Board D", "Formula": "24 x A", "Length (mm)": f"{board_d_length:.1f}"}
    ]
    board_df = pd.DataFrame(board_data)
    st.table(board_df)

# === FOOTER ===
st.caption("Version 3.2 - ECG BOM + Segment Distribution ✅")
