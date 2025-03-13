import streamlit as st
import pandas as pd
from utils import parse_luminaire_description
from datetime import datetime

# === SESSION STATE INITIALISATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []

if 'locked' not in st.session_state:
    st.session_state['locked'] = False

if 'led_efficiency_gain' not in st.session_state:
    st.session_state['led_efficiency_gain'] = 0.0

if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = ""

if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0

# === HEADER ===
st.title("Linear LightSpec Optimiser")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])
if uploaded_file:
    st.success(f"{uploaded_file.name} uploaded successfully!")
    # Mock parsed data
    ies_metadata = {
        "IES Version": "IESNA:LM-63-2002",
        "Test Info": "[TEST]",
        "Manufacturer": "[MANUFAC] Evolt Manufacturing",
        "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
        "Luminaire Description": "[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K",
        "Issued Date": "[ISSUEDATE] 2024-07-07"
    }

    st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False).table(ies_metadata)

    # CRI / CCT extracted
    cri, cct = parse_luminaire_description(ies_metadata["Luminaire Description"])
else:
    st.warning("Please upload a valid IES file to proceed.")
    st.stop()

# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    if st.session_state['locked']:
        st.info(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
    else:
        end_plate = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5)
        led_pitch = st.number_input("LED Series Module Pitch (mm)", min_value=1.0, value=56.0)

# === SELECT LENGTHS ===
desired_length = st.number_input("Desired Length (m)", min_value=0.5, step=0.1, value=1.0, format="%.3f")
col1, col2 = st.columns(2)

if col1.button(f"Add Shorter Buildable Length: {desired_length - 0.02:.3f}m"):
    st.session_state['lengths_list'].append(round(desired_length - 0.02, 3))
    st.session_state['locked'] = True
    st.rerun()

if col2.button(f"Add Longer Buildable Length: {desired_length + 0.02:.3f}m"):
    st.session_state['lengths_list'].append(round(desired_length + 0.02, 3))
    st.session_state['locked'] = True
    st.rerun()

# === LED CHIPSET ADJUSTMENT ===
with st.expander("💡 LED Chipset Adjustment", expanded=True):
    st.session_state['led_efficiency_gain'] = st.number_input(
        "LED Chipset Adjustment (%)",
        value=st.session_state['led_efficiency_gain'],
        step=0.1
    )

    if st.session_state['led_efficiency_gain'] != 0:
        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )
        if not st.session_state['efficiency_reason']:
            st.warning("⚠️ Reason required when adjustment is non-zero!")

# === LM/W STEP INCREMENT ===
with st.expander("🔒 Average lm/W Step Increment", expanded=True):
    if st.session_state['lengths_list']:
        st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
    else:
        st.session_state['lm_per_watt_increment'] = st.number_input(
            "Average lm/W Step Increment",
            min_value=10.0, max_value=500.0,
            value=st.session_state['lm_per_watt_increment'],
            step=1.0
        )

# === SELECTED LENGTHS TABLE ===
if st.session_state['lengths_list']:
    st.markdown("## 📏 Selected Lengths for IES Generation")

    data_rows = []
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    efficiency_multiplier = (1 + (st.session_state['led_efficiency_gain'] / 100))
    new_lm_per_m = round(base_lm_per_m * efficiency_multiplier, 1)
    new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)

    for length in st.session_state['lengths_list']:
        total_lumens = round(new_lm_per_m * length, 1)
        total_watts = round(new_w_per_m * length, 1)
        lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0

        luminaire_name = "BLine 8585D"
        optic_type = "Diffused Down"
        length_str = f"{length:.3f}m"
        tier = "Professional"

        luminaire_file_name = f"{luminaire_name} {optic_type}_{length_str}_{tier}"

        row = [
            length,
            luminaire_file_name,
            cri,
            cct,
            total_lumens,
            total_watts,
            lm_per_w,
            st.session_state['efficiency_reason'] if st.session_state['efficiency_reason'] else "N/A"
        ]

        data_rows.append(row)

    df = pd.DataFrame(data_rows, columns=[
        "Length (m)", "Luminaire & IES File Name", "CRI", "CCT",
        "Total Lumens", "Total Watts", "Settings lm/W", "Comments"
    ])

    st.table(df)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="ies_generation_data.csv", mime="text/csv")

# === DESIGN OPTIMISATION ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.markdown("### Target vs Achieved Lux Levels")

    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0)

    difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
    st.write(f"Difference: {difference_percent}%")

    if difference_percent > 0:
        required_reduction = round((base_lm_per_m * abs(difference_percent)) / 100, 1)
        increments = max(1, int(required_reduction / st.session_state['lm_per_watt_increment']))

        st.warning(f"⚠️ Consider reducing by {increments} increments or dimming to match target lux.")
    else:
        st.success("✔️ Target Lux Achieved! You can proceed with dimming adjustments on-site if necessary.")

    st.caption("Note: This enables theoretical model accuracy for future optimisations.")

# === PLACEHOLDER GENERATE ===
if st.button("✅ Generate Optimised IES Files"):
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")

