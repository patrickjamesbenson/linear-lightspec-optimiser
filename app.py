import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("🔧 LED Stack-Based Length Optimisation + BOM + PDF Export")

# === SESSION STATE INITIALIZATION ===
if 'stack_length' not in st.session_state:
    st.session_state['stack_length'] = 46.666  # Default Stack A length for Professional
if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"
if 'target_length' not in st.session_state:
    st.session_state['target_length'] = 280.0
if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "Fixed Output"
if 'ecg_custom' not in st.session_state:
    st.session_state['ecg_custom'] = False
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

# === ECG Default WATTS ===
ECG_WATTS = {
    "Fixed Output": 100,
    "DALI2": 80,
    "Wireless DALI2": 60
}

# === SIDE BAR SETTINGS ===
with st.sidebar:
    st.subheader("⚙️ Length Optimisation Settings")
    
    st.session_state['tier'] = st.selectbox(
        "Select Product Tier", ["Core", "Professional", "Advanced", "Bespoke"], index=1
    )
    
    # ECG TYPE
    ecg_list = ["Fixed Output", "DALI2", "Wireless DALI2", "Custom"]
    ecg_choice = st.selectbox("Select ECG Type", ecg_list, index=1)
    
    if ecg_choice == "Custom":
        st.session_state['ecg_custom'] = True
        custom_ecg_power = st.number_input("Enter Custom ECG Max Output (W)", min_value=10, max_value=500, value=100, step=1)
        ECG_MAX_WATT = custom_ecg_power
        reason = st.text_input("Reason for Custom ECG Selection (Mandatory):")
        if reason == "":
            st.warning("Reason required for Custom ECG before proceeding!")
    else:
        ECG_MAX_WATT = ECG_WATTS[ecg_choice]
    
    # Base Segment Length
    if st.session_state['tier'] in ["Professional", "Core"]:
        st.session_state['stack_length'] = 46.666
    elif st.session_state['tier'] in ["Advanced", "Bespoke"]:
        st.session_state['advanced_unlocked'] = st.checkbox("🔓 Unlock Advanced Settings")
        if st.session_state['advanced_unlocked']:
            st.session_state['stack_length'] = st.number_input(
                "Custom BPSL (mm)", min_value=30.0, max_value=100.0,
                value=st.session_state['stack_length'], step=0.1
            )
    
    # Target Length
    st.session_state['target_length'] = st.number_input(
        "Target Luminaire Length (mm)", min_value=100.0, max_value=10000.0,
        value=st.session_state['target_length'], step=0.1
    )

# === PARAMETERS ===
BPSL = st.session_state['stack_length']  # Base Parallel Segment Length (mm)
END_PLATE = 5.5  # mm
BODY_MAX = 3500  # mm aluminium length (max body segment length)
PIR_REPLACE = True  # Replaces 1 LED segment
SPITFIRE_REPLACE = True

board_b_length = 6 * BPSL
board_c_length = 12 * BPSL
board_d_length = 24 * BPSL
target_length = st.session_state['target_length']

# === LENGTH OPTIMISATION FUNCTION ===
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

# === SEGMENT + ECG ALLOCATION FUNCTION ===
def allocate_segments(total_length, tier, ecg_max_watt):
    segments = []
    current_pos = 0
    while current_pos < total_length:
        remaining = total_length - current_pos
        segment_length = min(BODY_MAX, remaining)
        led_segments = int(segment_length // BPSL)
        
        # Power per LED segment (dummy for now: 12W per board segment @36V)
        led_power_per_segment = 12  # Dummy for now
        
        total_led_power = led_power_per_segment * led_segments
        
        ecg_required = np.ceil(total_led_power / (ecg_max_watt))
        
        segments.append({
            "Segment ID": len(segments) + 1,
            "Length (mm)": segment_length,
            "LED Segments": led_segments,
            "ECG Count": ecg_required
        })
        
        current_pos += segment_length
    
    return segments

# === CALCULATIONS ===
selected_boards, final_length = optimise_length(target_length, st.session_state['tier'])
segments_allocated = allocate_segments(final_length, st.session_state['tier'], ECG_MAX_WATT)

# === MAIN DISPLAY ===
st.subheader("📏 Optimised Luminaire Build")
st.write(f"**Selected Product Tier:** `{st.session_state['tier']}`")
st.write(f"**BPSL (Base Parallel Segment Length):** `{BPSL:.1f}mm`")
st.write(f"**Target Length:** `{target_length:.1f}mm`")
st.write(f"**Optimised Length Achieved:** `{final_length:.1f}mm`")

# Boards Selected
df_boards = pd.DataFrame({"Board Lengths (mm)": selected_boards})
st.table(df_boards)

# Segments + ECG Allocation Table
df_segments = pd.DataFrame(segments_allocated)
st.subheader("📦 Segment & ECG Allocation")
st.table(df_segments)

# === DISPLAY BOARD SIZES ===
with st.expander("📋 Board Type Reference", expanded=False):
    board_data = [
        {"Board": "Base Segment (A)", "Formula": "BPSL", "Length (mm)": f"{BPSL:.1f}"},
        {"Board": "Board B", "Formula": "6 x A", "Length (mm)": f"{board_b_length:.1f}"},
        {"Board": "Board C", "Formula": "12 x A", "Length (mm)": f"{board_c_length:.1f}"},
        {"Board": "Board D", "Formula": "24 x A", "Length (mm)": f"{board_d_length:.1f}"}
    ]
    board_df = pd.DataFrame(board_data)
    st.table(board_df)

# === PDF EXPORT FUNCTION ===
def export_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Linear Lightspec Optimiser Engineering Report", ln=True, align='C')
    
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.cell(200, 10, f"Product Tier: {st.session_state['tier']}", ln=True)
    pdf.cell(200, 10, f"Target Length: {target_length:.1f}mm", ln=True)
    pdf.cell(200, 10, f"Optimised Length: {final_length:.1f}mm", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Segment & ECG Allocation", ln=True)
    
    for seg in segments_allocated:
        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 8, f"Segment {seg['Segment ID']}: Length {seg['Length (mm)']}mm | LED Segments {seg['LED Segments']} | ECG Count {seg['ECG Count']}", ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Board Reference", ln=True)
    
    for row in board_data:
        pdf.set_font("Arial", "", 12)
        pdf.cell(200, 8, f"{row['Board']}: {row['Formula']} = {row['Length (mm)']}mm", ln=True)
    
    return pdf.output(dest='S').encode('latin-1')

# === PDF DOWNLOAD BUTTON ===
st.subheader("📄 Export Engineering Report")
if st.button("Download PDF Report"):
    pdf_bytes = export_pdf_report()
    st.download_button("📥 Download PDF", data=pdf_bytes, file_name="engineering_report.pdf", mime='application/pdf')

# === FOOTER ===
st.caption("Version 3.2 - ECG Power BOM + PDF Export ✅")
