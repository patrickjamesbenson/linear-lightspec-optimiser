import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="LED Length Optimisation Table", layout="wide")
st.title("🛠️ LED Length Optimisation Table - Build Module")

# === SESSION STATE INITIALIZATION ===
if 'build_table' not in st.session_state:
    st.session_state['build_table'] = pd.DataFrame(columns=[
        'Project Name (P)', 'Product Tier (T)', 'Input Length (L)',
        'Final Length (FL)', 'LED Scaling (%) (Y)', 'ECG Type (ET)',
        'PIR Qty (PQ)', 'Spitfire Qty (SQ)', 'Comment (CM)', 'Timestamp (TS)'
    ])
if 'project_name' not in st.session_state:
    st.session_state['project_name'] = ""

if 'tier_selection' not in st.session_state:
    st.session_state['tier_selection'] = "Professional"  # Default Tier

if 'led_scaling' not in st.session_state:
    st.session_state['led_scaling'] = 15.0  # Default LED scaling for Professional

if 'ecg_type' not in st.session_state:
    st.session_state['ecg_type'] = "DALI2 Standard"

if 'admin_threshold' not in st.session_state:
    st.session_state['admin_threshold'] = 50.0  # mm threshold for optimal logic

# === ADMIN PANEL ===
with st.sidebar:
    st.header("🔧 Admin Controls")

    st.session_state['admin_threshold'] = st.number_input(
        "Threshold for Closest Longer/Shorter (mm) [Z]",
        min_value=10.0, max_value=200.0, value=st.session_state['admin_threshold'], step=5.0,
        help="Defines when the system recommends longer/shorter lengths. Alpha ref: Z"
    )

    st.write(f"**LED Scaling Defaults:** Core 0%, Pro 15%, Adv 15%, Bespoke Editable")
    st.write(f"**ECG Type Defaults:** Core: Fixed, Pro: DALI2, Adv: DALI2, Bespoke Editable")

# === PROJECT NAME ===
if not st.session_state['project_name']:
    st.session_state['project_name'] = st.text_input("Enter Project Name (P) to Start")

# === TIER SELECTION ===
tier = st.selectbox(
    "Select Product Tier (T)",
    options=["Core", "Professional", "Advanced", "Bespoke"],
    index=["Core", "Professional", "Advanced", "Bespoke"].index(st.session_state['tier_selection']),
    help="Defines defaults for LED Scaling, ECG Type and other build parameters. Alpha ref: T"
)

# === TIER LOCK ===
tier_locked = False
if not st.session_state['build_table'].empty:
    tier_locked = True
    st.warning(f"Tier locked to: {st.session_state['tier_selection']} (T) for this project (P).")
else:
    st.session_state['tier_selection'] = tier

# === APPLY DEFAULTS BASED ON TIER ===
if tier == "Core":
    st.session_state['led_scaling'] = 0
    st.session_state['ecg_type'] = "Fixed Output"
elif tier == "Professional":
    st.session_state['led_scaling'] = 15
    st.session_state['ecg_type'] = "DALI2 Standard"
elif tier == "Advanced":
    st.session_state['led_scaling'] = 15
    st.session_state['ecg_type'] = "DALI2 Wireless"
elif tier == "Bespoke":
    # Allow manual entry
    st.session_state['led_scaling'] = st.number_input(
        "Custom LED Chip Scaling (Y) %",
        min_value=-50.0, max_value=50.0, value=st.session_state['led_scaling'], step=1.0,
        help="Alpha ref: Y"
    )
    st.session_state['ecg_type'] = st.selectbox(
        "Select ECG Type (ET)",
        ["Fixed Output", "DALI2 Standard", "DALI2 Wireless", "Custom"],
        index=["Fixed Output", "DALI2 Standard", "DALI2 Wireless", "Custom"].index(st.session_state['ecg_type']),
        help="Alpha ref: ET"
    )

# === INPUT TARGET LENGTH ===
target_length = st.number_input(
    "Input Target Length (L) in mm",
    min_value=100.0, max_value=20000.0, value=1000.0, step=50.0,
    help="Alpha ref: L"
)

# === CALCULATE LENGTH OPTIONS ===
optimal_length = target_length
closest_shorter = target_length - st.session_state['admin_threshold']
closest_longer = target_length + st.session_state['admin_threshold']

# === DISPLAY BUILD OPTIONS ===
st.subheader("📏 Build Length Options")

if closest_shorter < 0:
    closest_shorter = 0  # Avoid negative lengths

if (abs(optimal_length - closest_shorter) <= 1e-6) or (abs(optimal_length - closest_longer) <= 1e-6):
    st.success("Spot on! No alternatives required.")
    if st.button("➕ Add Optimal Length"):
        timestamp = time.time()
        st.session_state['build_table'] = st.session_state['build_table'].append({
            'Project Name (P)': st.session_state['project_name'],
            'Product Tier (T)': st.session_state['tier_selection'],
            'Input Length (L)': target_length,
            'Final Length (FL)': optimal_length,
            'LED Scaling (%) (Y)': st.session_state['led_scaling'],
            'ECG Type (ET)': st.session_state['ecg_type'],
            'PIR Qty (PQ)': 0 if tier == "Core" else 1,
            'Spitfire Qty (SQ)': 0 if tier == "Core" else 1,
            'Comment (CM)': "Optimal length",
            'Timestamp (TS)': timestamp
        }, ignore_index=True)
else:
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f"➕ Add Shorter ({closest_shorter:.1f}mm)"):
            timestamp = time.time()
            st.session_state['build_table'] = st.session_state['build_table'].append({
                'Project Name (P)': st.session_state['project_name'],
                'Product Tier (T)': st.session_state['tier_selection'],
                'Input Length (L)': target_length,
                'Final Length (FL)': closest_shorter,
                'LED Scaling (%) (Y)': st.session_state['led_scaling'],
                'ECG Type (ET)': st.session_state['ecg_type'],
                'PIR Qty (PQ)': 0 if tier == "Core" else 1,
                'Spitfire Qty (SQ)': 0 if tier == "Core" else 1,
                'Comment (CM)': "Shorter option",
                'Timestamp (TS)': timestamp
            }, ignore_index=True)

    with col2:
        if st.button(f"➕ Add Optimal ({optimal_length:.1f}mm)"):
            timestamp = time.time()
            st.session_state['build_table'] = st.session_state['build_table'].append({
                'Project Name (P)': st.session_state['project_name'],
                'Product Tier (T)': st.session_state['tier_selection'],
                'Input Length (L)': target_length,
                'Final Length (FL)': optimal_length,
                'LED Scaling (%) (Y)': st.session_state['led_scaling'],
                'ECG Type (ET)': st.session_state['ecg_type'],
                'PIR Qty (PQ)': 0 if tier == "Core" else 1,
                'Spitfire Qty (SQ)': 0 if tier == "Core" else 1,
                'Comment (CM)': "Optimal option",
                'Timestamp (TS)': timestamp
            }, ignore_index=True)

    with col3:
        if st.button(f"➕ Add Longer ({closest_longer:.1f}mm)"):
            timestamp = time.time()
            st.session_state['build_table'] = st.session_state['build_table'].append({
                'Project Name (P)': st.session_state['project_name'],
                'Product Tier (T)': st.session_state['tier_selection'],
                'Input Length (L)': target_length,
                'Final Length (FL)': closest_longer,
                'LED Scaling (%) (Y)': st.session_state['led_scaling'],
                'ECG Type (ET)': st.session_state['ecg_type'],
                'PIR Qty (PQ)': 0 if tier == "Core" else 1,
                'Spitfire Qty (SQ)': 0 if tier == "Core" else 1,
                'Comment (CM)': "Longer option",
                'Timestamp (TS)': timestamp
            }, ignore_index=True)

# === DISPLAY CURRENT BUILD TABLE ===
st.subheader("🗂️ Build Table (Per Project)")

if not st.session_state['build_table'].empty:
    st.dataframe(st.session_state['build_table'].style.format({
        'Input Length (L)': '{:.1f} mm',
        'Final Length (FL)': '{:.1f} mm',
        'LED Scaling (%) (Y)': '{:.1f} %',
    }))

    # CSV EXPORT
    csv = st.session_state['build_table'].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Build Table CSV", csv, file_name=f"{st.session_state['project_name']}_build_table.csv")

else:
    st.info("No builds added yet.")

# === FOOTER ===
st.caption("Version 3.3 - Length Optimisation Table with Admin Tier Lock and Alpha Tracing ✅")

