import streamlit as st
import pandas as pd
from datetime import datetime

# === SESSION STATE INITIALISATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === FILE UPLOAD ===
st.header("Upload your Base IES file")
base_ies_file = st.file_uploader("Upload Base IES File", type=["ies"], help="Limit 200MB per file • IES")

if base_ies_file:
    st.success(f"Uploaded file: {base_ies_file.name} ({base_ies_file.size/1024:.1f}KB)")
    
    # === SIMULATED METADATA EXTRACTION ===
    metadata = {
        "IES Version": "IESNA:LM-63-2002",
        "Test Info": "[TEST]",
        "Manufacturer": "[MANUFAC] Evolt Manufacturing",
        "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
        "Luminaire Description": "[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K",
        "Issued Date": "[ISSUEDATE] 2024-07-07"
    }
    photometric_params = {
        "Number of Lamps": 1,
        "Lumens per Lamp": -1,
        "Candela Multiplier": 1,
        "Vertical Angles": 91,
        "Horizontal Angles": 4,
        "Photometric Type": 1,
        "Units Type": 2,
        "Width (m)": 0.08,
        "Length (m)": 1.0,
        "Height (m)": 0.09,
        "Ballast Factor": 1,
        "Future Use": 1,
        "Input Watts": 11.6
    }

    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        st.subheader("IES Metadata")
        st.table(pd.DataFrame(metadata.items(), columns=["", "Value"]))

        st.subheader("Photometric Parameters")
        st.table(pd.DataFrame(photometric_params.items(), columns=["", "Value"]))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=True):
        st.write(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")

        # Select Length Inputs
        desired_length = st.number_input("Desired Length (m)", min_value=0.1, value=1.000, step=0.001, format="%.3f")
        col1, col2 = st.columns(2)
        if col1.button(f"Add Shorter Buildable Length: {desired_length - 0.02:.3f}m"):
            st.session_state['lengths_list'].append(round(desired_length - 0.02, 3))
        if col2.button(f"Add Longer Buildable Length: {desired_length + 0.02:.3f}m"):
            st.session_state['lengths_list'].append(round(desired_length + 0.02, 3))

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=True):
        led_adjustment = st.number_input("LED Chipset Adjustment (%)", value=0.00, step=0.01, format="%.2f")
        reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)")
        if led_adjustment != 0 and not reason:
            st.warning("⚠️ Please provide a reason for the adjustment!")

    # === AVERAGE LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=True):
        st.info("115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.")
        st.write("🔒 Locked at: 115.0 lm/W")

    # === SELECTED LENGTHS TABLE ===
    st.subheader("📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        table_data = []
        for length in st.session_state['lengths_list']:
            row = [
                f"BLine 8585D Diffused Down_{length:.3f}m_Professional",
                "80CRI",
                "3000K",
                round(400 * length, 1),  # Simulated Total Lumens
                round(11.6 * length, 1),  # Simulated Total Watts
                round((400 * length) / (11.6 * length), 1),  # Settings lm/W
                reason if reason else ""
            ]
            table_data.append(row)

        df_table = pd.DataFrame(table_data, columns=[
            "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"])

        st.dataframe(df_table.style.format({
            "Total Lumens": "{:.1f}",
            "Total Watts": "{:.1f}",
            "Settings lm/W": "{:.1f}"
        }))

        for i, length in enumerate(st.session_state['lengths_list']):
            if st.button(f"🗑️ Delete {length:.3f}m", key=f"delete_{i}"):
                st.session_state['lengths_list'].pop(i)
                st.experimental_rerun()

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        if difference_percent > 0:
            st.warning("⚠️ Dimming recommended to match target lux.")
        elif difference_percent < 0:
            st.info("✅ Increase output or adjust design to achieve target lux.")
        else:
            st.success("🎉 Target lux achieved!")

    # === PLACEHOLDER FILE GENERATION ===
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")
