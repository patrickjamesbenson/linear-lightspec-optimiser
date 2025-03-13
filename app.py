import streamlit as st
import pandas as pd
from datetime import datetime

# === SESSION STATE INITIALIZATION ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="centered")

st.title("Linear LightSpec Optimiser")

# === BASE FILE UPLOAD ===
st.header("Upload your Base IES file")
base_ies_file = st.file_uploader("Upload Base IES File", type=["ies"])
if base_ies_file:
    st.write(f"**{base_ies_file.name}**")
    st.write("3.0KB")  # Placeholder size

    # === BASE FILE SUMMARY (STATIC FOR DEMO) ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=True):
        st.subheader("IES Metadata")
        ies_metadata = {
            "IES Version": "IESNA:LM-63-2002",
            "Test Info": "[TEST]",
            "Manufacturer": "[MANUFAC] Evolt Manufacturing",
            "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
            "Luminaire Description": "[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K",
            "Issued Date": "[ISSUEDATE] 2024-07-07"
        }
        meta_df = pd.DataFrame(ies_metadata.items(), columns=["", ""])
        st.table(meta_df)

        st.subheader("Photometric Parameters")
        photometric_params = {
            "Number of Lamps": 1,
            "Lumens per Lamp": -1,
            "Candela Multiplier": 1,
            "Vertical Angles": 91,
            "Horizontal Angles": 4,
            "Photometric Type": 1,
            "Units Type": 2,
            "Width (m)": round(0.08, 1),
            "Length (m)": round(1.0, 1),
            "Height (m)": round(0.09, 1),
            "Ballast Factor": 1,
            "Future Use": 1,
            "Input Watts": round(11.6, 1)
        }
        photo_df = pd.DataFrame(photometric_params.items(), columns=["", ""])
        st.table(photo_df)

# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    if st.session_state['locked']:
        st.markdown(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
    else:
        end_plate = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5)
        led_pitch = st.number_input("LED Series Module Pitch (mm)", min_value=0.0, value=56.0)

# === SELECT LENGTHS ===
st.markdown("### Select Lengths")

col1, col2 = st.columns(2)
desired_length = st.number_input("Desired Length (m)", min_value=0.001, step=0.001, value=1.000, format="%.3f")

if col1.button(f"Add Shorter Buildable Length: {desired_length - 0.01:.3f}m"):
    st.session_state['lengths_list'].append(desired_length - 0.01)
    st.session_state['locked'] = True

if col2.button(f"Add Longer Buildable Length: {desired_length + 0.01:.3f}m"):
    st.session_state['lengths_list'].append(desired_length + 0.01)
    st.session_state['locked'] = True

# === LED CHIPSET ADJUSTMENT ===
with st.expander("💡 LED Chipset Adjustment", expanded=False):
    led_efficiency_gain = st.number_input("LED Chipset Adjustment (%)", value=0.0)
    if led_efficiency_gain != 0.0:
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)")
        if efficiency_reason == "":
            st.warning("⚠️ Please provide a reason for the efficiency adjustment.")

# === LM/W STEP INCREMENT ===
with st.expander("🔒 Average lm/W Step Increment", expanded=False):
    st.info("115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.")
    st.markdown(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")

# === SELECTED LENGTHS TABLE ===
if st.session_state['lengths_list']:
    st.markdown("### 📏 Selected Lengths for IES Generation")
    lengths = st.session_state['lengths_list']
    table_data = []
    for idx, length in enumerate(lengths):
        # Dummy data
        luminaire_name = f"BLine 8585D Diffused Down_{length:.3f}m"
        cri = "80"
        cct = "3000K"
        total_lumens = round(400 * length, 1)
        total_watts = round(11.6 * length, 1)
        lm_w = round(total_lumens / total_watts, 1)
        comments = "Current Generation"

        row = [
            f"{length:.3f}",
            luminaire_name,
            cri,
            cct,
            f"{total_lumens:.1f}",
            f"{total_watts:.1f}",
            f"{lm_w:.1f}",
            comments
        ]

        table_data.append(row)

        delete_col = st.columns([1, 9])[0]
        if delete_col.button("🗑️", key=f"delete_{idx}"):
            st.session_state['lengths_list'].pop(idx)
            if len(st.session_state['lengths_list']) == 0:
                st.session_state['locked'] = False
            st.rerun()

    df = pd.DataFrame(table_data, columns=[
        "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"
    ])
    st.table(df)

# === DESIGN OPTIMISATION ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.subheader("Target vs Achieved Lux Levels")

    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0)

    difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
    st.write(f"Difference: {difference_percent}%")

    if difference_percent > 0:
        st.warning(f"⚠️ Consider reducing by 1 increments or dimming to match target lux.")
    elif difference_percent < 0:
        st.warning(f"⚠️ Consider increasing by 1 increments or using a different IES file.")
    else:
        st.success("✅ Target Achieved!")

    st.caption("Note: This enables theoretical model accuracy for future optimisations.")

# === GENERATE IES FILES PLACEHOLDER ===
st.success("✅ IES Files Generation Complete! (Placeholder logic)")

