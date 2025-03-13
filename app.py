import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file  # Ensure utils.py is in sync!

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

# === SESSION STATE INITIALISATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = ""
if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0

# === FILE UPLOAD ===
st.title("Linear LightSpec Optimiser")
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    ies_data = parse_ies_file(uploaded_file)

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=True):
        st.subheader("IES Metadata")
        metadata_df = pd.DataFrame({
            "Field": ["IES Version", "Test Info", "Manufacturer", "Luminaire Catalog Number", "Luminaire Description", "Issued Date"],
            "Value": [
                ies_data.get('IESNA Version', ''),
                ies_data.get('Test', ''),
                ies_data.get('Manufacturer', ''),
                ies_data.get('Luminaire Catalog Number', ''),
                ies_data.get('Luminaire Description', ''),
                ies_data.get('Issued Date', '')
            ]
        })
        st.table(metadata_df)

        st.subheader("Photometric Parameters")
        photometric_df = pd.DataFrame({
            "Parameter": [
                "Number of Lamps", "Lumens per Lamp", "Candela Multiplier", "Vertical Angles",
                "Horizontal Angles", "Photometric Type", "Units Type", "Width (m)", "Length (m)",
                "Height (m)", "Ballast Factor", "Future Use", "Input Watts"
            ],
            "Value": [
                1, -1, 1, 91, 4, 1, 2,
                round(0.08, 1), round(1.0, 1), round(0.09, 1), 1, 1, 11.6
            ]
        })
        st.table(photometric_df)

    # Base values used in calculations
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
        else:
            end_plate = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5)
            led_pitch = st.number_input("LED Series Module Pitch (mm)", min_value=0.0, value=56.0)

    # === SELECT LENGTHS ===
    st.markdown("### Select Lengths")
    desired_length = st.number_input("Desired Length (m)", min_value=0.001, value=1.0, step=0.001)

    col1, col2 = st.columns(2)
    if col1.button(f"Add Shorter Buildable Length: {desired_length - 0.01:.3f} m"):
        st.session_state['lengths_list'].append(round(desired_length - 0.01, 3))
        st.session_state['locked'] = True
        st.rerun()
    if col2.button(f"Add Longer Buildable Length: {desired_length + 0.01:.3f} m"):
        st.session_state['lengths_list'].append(round(desired_length + 0.01, 3))
        st.session_state['locked'] = True
        st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    st.markdown("### 💡 LED Chipset Adjustment")
    st.session_state['led_efficiency_gain_percent'] = st.number_input("LED Chipset Adjustment (%)", value=st.session_state['led_efficiency_gain_percent'])
    if st.session_state['led_efficiency_gain_percent'] != 0:
        st.session_state['efficiency_reason'] = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])
        if st.session_state['efficiency_reason'].strip() == "":
            st.warning("⚠️ Please provide a reason for the LED efficiency adjustment.")
    else:
        st.session_state['efficiency_reason'] = "Current Generation"

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    st.markdown("### 🔒 Average lm/W Step Increment")
    st.info(f"{st.session_state['lm_per_watt_increment']} lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.")

    # === SELECTED LENGTHS TABLE ===
    if st.session_state['lengths_list']:
        st.markdown("## 📏 Selected Lengths for IES Generation")
        table_rows = []
        efficiency_multiplier = 1 + (st.session_state['led_efficiency_gain_percent'] / 100)
        new_lm_per_m = round(base_lm_per_m * efficiency_multiplier, 1)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts > 0 else 0

            # Delete button inline
            delete_col, *_ = st.columns([1, 10, 1, 1, 1, 1, 1, 1, 1])
            if delete_col.button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            # Add row data
            row = [
                f"{length:.3f}",
                f"BLine 8585D Diffused Down_{length:.3f}m_{'Professional'}",
                "80",
                "3000K",
                f"{total_lumens:.1f}",
                f"{total_watts:.1f}",
                f"{lm_per_w:.1f}",
                st.session_state['efficiency_reason']
            ]
            table_rows.append(row)

        df = pd.DataFrame(table_rows, columns=[
            "Length (m)",
            "Luminaire & IES File Name",
            "CRI",
            "CCT",
            "Total Lumens",
            "Total Watts",
            "Settings lm/W",
            "Comments"
        ])
        st.table(df)

    # === DESIGN OPTIMISATION SECTION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")

        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        if difference_percent > 0:
            required_reduction = round(base_lm_per_m * abs(difference_percent) / 100, 1)
            increments_needed = max(1, int(required_reduction / st.session_state['lm_per_watt_increment']))

            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        else:
            st.success("✅ Target achieved or under target. No increments needed.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES PLACEHOLDER ===
    if st.button("✅ Generate Optimised IES Files"):
        st.success("IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Please upload a valid IES file to begin.")
