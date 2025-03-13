import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state['lm_per_watt_increment'] = 115  # Default increment for lm/W

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE INFO ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_desc = luminaire_info.replace("[LUMINAIRE]", "").strip()

    # Parse description
    lum_parts = luminaire_desc.split('-')
    lum_base_name = lum_parts[0].strip() if len(lum_parts) > 0 else "Unknown Base"
    lum_watt = lum_parts[1].strip() if len(lum_parts) > 1 else "Unknown Watt"
    lum_optic = lum_parts[2].strip() if len(lum_parts) > 2 else "Unknown Optic"
    cri_value = lum_parts[-2].strip() if len(lum_parts) >= 3 else "N/A"
    cct_value = lum_parts[-1].strip() if len(lum_parts) >= 3 else "N/A"

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
            "Luminaire Description": luminaire_info,
            "Issued Date": issuedate_info
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(metadata_dict, orient='index', columns=['Value']))

        photometric_line = parsed['data'][0] if parsed['data'] else ""
        photometric_params = photometric_line.strip().split()

        param_labels = [
            "Number of Lamps", "Lumens per Lamp", "Candela Multiplier",
            "Vertical Angles", "Horizontal Angles", "Photometric Type",
            "Units Type", "Width (m)", "Length (m)", "Height (m)",
            "Ballast Factor", "Future Use", "Input Watts"
        ]

        if len(photometric_params) >= 13:
            param_data = {label: value for label, value in zip(param_labels, photometric_params[:13])}
            st.markdown("### Photometric Parameters")
            st.table(pd.DataFrame.from_dict(param_data, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']
    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if st.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True
        st.experimental_rerun()

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        st.experimental_rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
                                                      value=st.session_state.get('led_efficiency_gain_percent', 0.0),
                                                      step=1.0)
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)",
                                          value=st.session_state.get('efficiency_reason', 'Current Generation'))

        if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        **115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.**

        This field is editable and should only be adjusted by advanced users who understand the impact on system calibration and design targets.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input("Average lm/W Step Increment", min_value=50, max_value=200,
                                                                        value=st.session_state.get('lm_per_watt_increment', 115),
                                                                        step=1)

    # === BASE LUMENS/WATTS FROM IES ===
    base_lm_per_m = 400.0
    base_w_per_m = 11.6
    efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
    new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
    new_lm_per_m = round(base_lm_per_m, 1)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []

        for length in st.session_state['lengths_list']:
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0:
                tier = "Bespoke"
            elif led_efficiency_gain_percent != 0:
                tier = "Professional"
            elif st.session_state['led_pitch'] % 4 != 0:
                tier = "Advanced"
            else:
                tier = "Core"

            luminaire_file_name = f"{lum_base_name} {lum_watt} {lum_optic}_{length:.3f}m_{tier}"

            row = {
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": efficiency_reason if led_efficiency_gain_percent != 0 else ""
            }

            table_rows.append(row)

        # DISPLAY TABLE
        for idx, row in enumerate(table_rows):
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.experimental_rerun()

            cols[1].write(row["Length (m)"])
            cols[2].write(row["Luminaire & IES File Name"])
            cols[3].write(row["CRI"])
            cols[4].write(row["CCT"])
            cols[5].write(row["Total Lumens"])
            cols[6].write(row["Total Watts"])
            cols[7].write(row["Settings lm/W"])
            cols[8].write(row["Comments"])

    else:
        st.info("No lengths selected yet. Click above to add lengths.")

else:
    st.warning("⚠️ Upload an IES file to begin optimisation.")

