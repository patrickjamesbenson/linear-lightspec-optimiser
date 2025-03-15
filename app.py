import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="LED Stack-Based Length Optimisation", layout="wide")
st.title("🔧 LED Stack-Based Length Optimisation")

# === SESSION STATE INITIALIZATION ===
if 'stack_length' not in st.session_state:
    st.session_state['stack_length'] = 46.666  # Default Stack A length for Professional

if 'tier' not in st.session_state:
    st.session_state['tier'] = "Professional"  # Default to Professional

if 'target_length' not in st.session_state:
    st.session_state['target_length'] = 280.0  # Default target length

if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

# === SIDE BAR SETTINGS ===
with st.sidebar:
    st.subheader("⚙️ Length Optimisation Settings")

    # Tier Selection (Core, Professional, Advanced, Bespoke)
    st.session_state['tier'] = st.selectbox(
        "Select Product Tier", ["Core", "Professional", "Advanced", "Bespoke"], index=1
    )

    # Display Stack A length based on tier selection
    if st.session_state['tier'] in ["Professional", "Core"]:
        st.session_state['stack_length'] = 46.666  # Fixed Stack A in Professional and Core

    elif st.session_state['tier'] in ["Advanced", "Bespoke"]:
        st.session_state['advanced_unlocked'] = st.checkbox("🔓 Unlock Advanced Settings")
        if st.session_state['advanced_unlocked']:
            st.session_state['stack_length'] = st.number_input(
                "Custom Stack A Length (mm)", min_value=30.0, max_value=100.0,
                value=st.session_state['stack_length'], step=0.1
            )

    # Target Length Input
    st.session_state['target_length'] = st.number_input(
        "Target Luminaire Length (mm)", min_value=100.0, max_value=5000.0,
        value=st.session_state['target_length'], step=0.1
    )

    st.markdown("---")
    st.markdown("### 🔧 Component Lengths")

    # End Plates (2x)
    end_plate_thickness = st.number_input(
        "End Plates (each) (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1
    )
    total_end_plates = end_plate_thickness * 2
    st.info(f"🔩 Total End Plate Length: `{total_end_plates:.1f} mm`")

    # Smart PIR
    pir_length = st.number_input(
        "Smart PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1
    )

    # Smart Spitfire
    spitfire_length = st.number_input(
        "Smart Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1
    )

    # Body Max Increment
    body_max_increment = st.number_input(
        "Body Max Increment (mm)", min_value=500.0, max_value=5000.0, value=3500.0, step=0.1
    )

# === BOARD LENGTH CALCULATIONS ===
stack_length = st.session_state['stack_length']
board_b_length = 6 * stack_length  # 280mm default
board_c_length = 12 * stack_length  # 560mm default
board_d_length = 24 * stack_length  # 1120mm default
target_length = st.session_state['target_length']

# === LENGTH OPTIMISATION FUNCTION ===
def optimise_length(target, tier):
    """
    Finds the best combination of boards to match or get as close as possible to the target length.
    - Core: Uses only B, C, D.
    - Professional: Uses B, C, D first, then adds multiple Stack A’s if needed.
    - Advanced & Bespoke: Uses everything, including flexible Stack A.
    """
    used_boards = []
    remaining_length = target

    # Core: Only uses Board B, C, D
    if tier == "Core":
        board_lengths = [board_d_length, board_c_length, board_b_length]

    # Professional: Uses Board B, C, D first, then fills with A
    elif tier == "Professional":
        board_lengths = [board_d_length, board_c_length, board_b_length]

    # Advanced & Bespoke: Uses everything, including flexible Stack A
    else:
        board_lengths = [board_d_length, board_c_length, board_b_length, stack_length]

    # Primary Board Selection (B, C, D first)
    for board in board_lengths:
        while remaining_length >= board:
            used_boards.append(board)
            remaining_length -= board

    # Professional Only: Fill remaining gap with multiple A's
    if remaining_length > 0 and tier == "Professional":
        while remaining_length >= stack_length:
            used_boards.append(stack_length)
            remaining_length -= stack_length

    return used_boards, sum(used_boards)

# Compute the optimised board selection
selected_boards, final_length = optimise_length(target_length, st.session_state['tier'])

# === MAIN DISPLAY ===
st.subheader("📏 Optimised Luminaire Build")
st.write(f"**Selected Product Tier:** `{st.session_state['tier']}`")
st.write(f"**Stack Length (A):** `{stack_length:.1f} mm`")
st.write(f"**Target Length:** `{target_length:.1f} mm`")
st.write(f"**Optimised Length Achieved:** `{final_length:.1f} mm`")

# Display selected board breakdown
df_boards = pd.DataFrame({"Board Lengths (mm)": selected_boards})
st.table(df_boards)

# === DISPLAY BOARD SIZES ===
with st.expander("📋 Board Type Reference", expanded=False):
    st.markdown("#### Board Lengths Derived from Stack A")
    board_data = [
        {"Board": "Stack A", "Formula": "Base Unit", "Length (mm)": f"{stack_length:.1f}"},
        {"Board": "Board B", "Formula": "6 x A", "Length (mm)": f"{board_b_length:.1f}"},
        {"Board": "Board C", "Formula": "12 x A", "Length (mm)": f"{board_c_length:.1f}"},
        {"Board": "Board D", "Formula": "24 x A", "Length (mm)": f"{board_d_length:.1f}"}
    ]
    board_df = pd.DataFrame(board_data)
    st.table(board_df)

st.caption("Version 3.2 - Component Lengths & Optimisation Module ✅")
