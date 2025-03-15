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

# === BOARD LENGTH CALCULATIONS ===
stack_length = st.session_state['stack_length']
board_b_length = 6 * stack_length
board_c_length = 12 * stack_length
board_d_length = 24 * stack_length
target_length = st.session_state['target_length']

# === LENGTH OPTIMISATION FUNCTION ===
def optimise_length(target, tier):
    """
    Finds the best combination of boards to match or exceed the target length.
    Professional: Uses B, C, D and adds A increments if necessary.
    Advanced: Allows stack length A modifications.
    """
    if tier == "Professional":
        board_lengths = [board_d_length, board_c_length, board_b_length]
    else:  # Advanced and Bespoke
        board_lengths = [board_d_length, board_c_length, board_b_length, stack_length]

    used_boards = []
    remaining_length = target

    for board in board_lengths:
        while remaining_length >= board:
            used_boards.append(board)
            remaining_length -= board

    if remaining_length > 0 and tier == "Professional":
        used_boards.append(stack_length)

    return used_boards, sum(used_boards)

# Compute the optimised board selection
selected_boards, final_length = optimise_length(target_length, st.session_state['tier'])

# === MAIN DISPLAY ===
st.subheader("📏 Optimised Luminaire Build")
st.write(f"**Selected Product Tier:** `{st.session_state['tier']}`")
st.write(f"**Stack Length (A):** `{stack_length:.1f}mm`")
st.write(f"**Target Length:** `{target_length:.1f}mm`")
st.write(f"**Optimised Length Achieved:** `{final_length:.1f}mm`")

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

st.caption("Version 3.0 - Length Optimisation Module Implemented ✅")
