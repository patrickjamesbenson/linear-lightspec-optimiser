import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = 'Current Generation'
if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT HEADER INFO ===
    ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found")
    test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found")
    manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found")
    lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found")
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    issuedate_info = next((line for line in parsed['header'] if line.startswith("[ISSUEDATE]")), "[ISSUEDATE] Not Found")

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=True):
        metadata_dict = {
            "IES Version": ies_version,
            "Test Info": test_info,
            "Manufacturer": manufac_info,
            "Luminaire Catalog Number": lumcat_info,
            "Luminaire Description": luminaire_info,
            "Issued Date": issuedate_info
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(metadata_dict, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=True):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=10.0, value=56.0, step=1.0)

    # === LENGTH SELECTION ===
    st.markdown("### Select Lengths")

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")

    col1, col2 = st.columns(2)
    desired_length_mm = desired_length_m * 1000
    pitch = st.session_state.get('led_pitch', 56.0)
    end_plate = st.session_state.get('end_plate_thickness', 5.5)

    min_length_mm = (int((desired_length_mm - end_plate * 2) / pitch)) * pitch + end_plate * 2
    max_length_mm = min_length_mm + pitch

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True
        st.rerun()

    if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=True):
        st.session_state['led_efficiency_gain_percent'] = st.number_input(
            "LED Chipset Adjustment (%)", 
            min_value=-50.0, 
            max_value=100.0, 
            value=st.session_state['led_efficiency_gain_percent'], 
            step=1.0
        )

        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

        if st.session_state['led_efficiency_gain_percent'] != 0 and st.session_state['efficiency_reason'] == "Current Generation":
            st.warning("⚠️ You must provide a reason if you adjust the LED chipset efficiency!")

    # === SYSTEM LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=True):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']:.1f} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input(
                "Average lm/W Step Increment", 
                min_value=10.0, 
                max_value=500.0, 
                value=st.session_state['lm_per_watt_increment'], 
                step=1.0
            )

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 + (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_lm_per_m = round(base_lm_per_m * efficiency_multiplier, 1)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts > 0 else 0

            luminaire_name = luminaire_info.replace("[LUMINAIRE]", "").strip()
            luminaire_file_name = f"{luminaire_name} Diffused Down_{length:.3f}m_Professional"

            row = {
                "delete": idx,
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": "80CRI",
                "CCT": "3000K",
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": st.session_state['efficiency_reason']
            }

            table_rows.append(row)

        for row in table_rows:
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
            delete_button = cols[0].button("🗑️", key=f"delete_{row['delete']}")
            if delete_button:
                st.session_state['lengths_list'].pop(row['delete'])
                st.rerun()

            cols[1].write(row["Length (m)"])
            cols[2].write(row["Luminaire & IES File Name"])
            cols[3].write(row["CRI"])
            cols[4].write(row["CCT"])
            cols[5].write(row["Total Lumens"])
            cols[6].write(row["Total Watts"])
            cols[7].write(row["Settings lm/W"])
            cols[8].write(row["Comments"])

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int((required_change_lm_per_m / st.session_state['lm_per_watt_increment']) + 0.99)

        if increments_needed < 1:
            st.warning(f"⚠️ Dimming recommended to match target lux.")
        else:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

else:
    st.info("Upload an IES file to begin optimisation.")
