import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lm_per_watt_increment'] = 115.0
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === PARSE HEADER INFO ===
    luminaire_line = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Unknown")
    luminaire_data = luminaire_line.replace("[LUMINAIRE]", "").strip()

    # === EXTRACT NAME + OPTIC ===
    # Example luminaire string: "BLine 8585D 11.6W - 80CRI - 3000K Diffused Down"
    luminaire_parts = luminaire_data.split('-')
    if len(luminaire_parts) >= 1:
        base_name = luminaire_parts[0].strip()
    else:
        base_name = "Unknown Luminaire"

    # Find optic type (last part after hyphen or fallback)
    optic_type = luminaire_parts[-1].strip() if len(luminaire_parts) > 1 else "Unknown Optic"

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found")
        test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found")
        manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found")
        lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found")
        issuedate_info = next((line for line in parsed['header'] if line.startswith("[ISSUEDATE]")), "[ISSUEDATE] Not Found")

        metadata_dict = {
            "IES Version": ies_version,
            "Test Info": test_info,
            "Manufacturer": manufac_info,
            "Luminaire Catalog Number": lumcat_info,
            "Luminaire Description": luminaire_line,
            "Issued Date": issuedate_info
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(metadata_dict, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Base Build locked because lengths have been selected.")
        else:
            if st.session_state['locked']:
                if st.button("🔓 Unlock Base Build Methodology"):
                    st.session_state['locked'] = False
            else:
                if st.button("🔒 Lock Base Build Methodology"):
                    st.session_state['locked'] = True

        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")
    col1, col2 = st.columns(2)

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    led_pitch = st.session_state['led_pitch']
    end_plate_thickness = st.session_state['end_plate_thickness']

    min_length_mm = (int((desired_length_mm - end_plate_thickness * 2) / led_pitch)) * led_pitch + end_plate_thickness * 2
    max_length_mm = min_length_mm + led_pitch

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
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
                                                      value=st.session_state.get('led_efficiency_gain_percent', 0.0),
                                                      step=1.0)

        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)",
                                          value=st.session_state.get('efficiency_reason', 'Current Generation'))

        if led_efficiency_gain_percent != 0 and efficiency_reason.strip() == "":
            st.error("⚠️ Provide a reason for the LED Chipset Adjustment.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.")
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input("Average lm/W Step Increment",
                                                                        min_value=10.0, max_value=500.0,
                                                                        value=st.session_state.get('lm_per_watt_increment', 115.0),
                                                                        step=1.0)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Professional" if led_efficiency_gain_percent != 0 else "Core"

            luminaire_file_name = f"{base_name} {optic_type}_{length:.3f}m_{tier}"

            row = {
                "Delete": "🗑️",
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": "N/A",
                "CCT": "N/A",
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": efficiency_reason
            }

            table_rows.append(row)

        # Display Table
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for idx, row in enumerate(table_rows):
            row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

            for col, val in zip(row_cols[1:], row_data):
                col.write(val)

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=10.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=10.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int((required_change_lm_per_m / st.session_state['lm_per_watt_increment']) + 0.999)  # always round up

        if increments_needed < 1:
            st.warning("⚠️ Dimming recommended to match target lux.")
        else:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === IES FILE GENERATION ===
    if st.button("Generate Optimised IES Files"):
        st.success("✅ IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Upload an IES file to begin optimisation.")
