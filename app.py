import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="Luminaire Length Table Builder", layout="wide")
st.title("🛠️ Luminaire Build Length Table")

# === SESSION STATE INITIALIZATION ===
if 'length_table' not in st.session_state:
    st.session_state['length_table'] = pd.DataFrame(columns=[
        "Target Length (m)",
        "Optimised Length (mm)",
        "Tier",
        "LED Chip Scaling (%) [Y]",
        "ECG Type [E]",
        "Boards Used",
        "PIR Qty",
        "Spitfire Qty",
        "Product Code (LUMCAT)",
        "Notes/Comments"
    ])

# === INPUTS SECTION ===
st.header("➕ Add New Length")

# Target Length Input (m)
target_length_m = st.number_input("Target Luminaire Length (m)", min_value=0.1, max_value=50.0, value=2.4, step=0.1)

# Tier Selection
tier = st.selectbox("Select Tier", ["Core", "Professional", "Advanced", "Bespoke"], index=1)

# LED Chip Scaling % (from Advanced Settings) - [Y]
led_chip_scaling = st.number_input("LED Chip Scaling (%) [Y]",
                                   min_value=-50.0, max_value=50.0, value=15.0, step=0.1,
                                   help="Admin Controlled: Scaling compared to base LED. Defaults to +15% Professional Gen2.")

# ECG Selection [E]
ecg_type = st.selectbox("ECG Type [E]", ["Fixed Output", "DALI2", "DALI2 Wireless", "Custom"], index=1)
if ecg_type == "Custom":
    ecg_reason = st.text_input("Mandatory Reason for Custom ECG Selection")
    if not ecg_reason:
        st.warning("Reason required for Custom ECG Type")

# Ancillaries
pir_qty = st.number_input("Qty of PIR Devices", min_value=0, max_value=10, value=0)
spitfire_qty = st.number_input("Qty of Spitfire Devices", min_value=0, max_value=10, value=0)

# === BOARD OPTIMISATION (Pulled from Optimisation Function) ===
# For demonstration, assume function returns these:
optimised_length_mm = round(target_length_m * 1000)  # Placeholder
boards_used = "B + B + A + A"  # Placeholder, will be from optimise_length()

# Product Code (Placeholder)
product_code = f"PRO-{int(target_length_m*1000)}-{tier[:3].upper()}"

# Notes / Comments
notes = st.text_area("Notes / Comments", placeholder="Explain deviations or special requirements")

# === ADD TO LENGTH TABLE BUTTON ===
if st.button("✅ Add Length to Build Table"):
    # Validation for Custom ECG Reason
    if ecg_type == "Custom" and not ecg_reason:
        st.error("Please provide a reason for selecting Custom ECG")
    else:
        new_entry = {
            "Target Length (m)": target_length_m,
            "Optimised Length (mm)": optimised_length_mm,
            "Tier": tier,
            "LED Chip Scaling (%) [Y]": led_chip_scaling,
            "ECG Type [E]": ecg_type,
            "Boards Used": boards_used,
            "PIR Qty": pir_qty,
            "Spitfire Qty": spitfire_qty,
            "Product Code (LUMCAT)": product_code,
            "Notes/Comments": notes if notes else "-"
        }
        st.session_state['length_table'] = st.session_state['length_table'].append(new_entry, ignore_index=True)
        st.success(f"Added {target_length_m:.2f}m build to table.")

# === LENGTH TABLE DISPLAY ===
st.header("📋 Current Length Build Table")
st.dataframe(st.session_state['length_table'], use_container_width=True)

# === EXPORT TABLE ===
csv_export = st.session_state['length_table'].to_csv(index=False).encode('utf-8')
st.download_button("📥 Download Length Table CSV", csv_export, "length_build_table.csv", "text/csv")

# === FOOTER ===
st.caption("Version 3.2 - Length Table Module ✅")
