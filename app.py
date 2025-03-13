import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lmw_increment'] = 115.0  # ✅ Average lm/W increment
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE NAME ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

    # === EXTRACT CRI & CCT ===
    cri_value = "N/A"
    cct_value = "N/A"
    if luminaire_name_base != "Not Found":
        parts = luminaire_name_base.split('-')
        if len(parts) >= 3:
            cri_value = parts[-2].strip()
            cct_value = parts[-1].strip()

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

        if len(photometric_params) >= 13:
            param_labels = [
                "Number of Lamps", "Lumens per Lamp", "Candela Multiplier",
                "Vertical Angles", "Horizontal Angles", "Photometric Type",
                "Units Type", "Width (m)", "Length (m)", "Height (m)",
                "Ballast Factor", "Future Use", "Input Watts"
            ]

            param_data = {label: value for label, value in zip(param_labels, photometric_params[:13])}
            st.markdown("### Photometric Parameters")
            st.table(pd.DataFrame.from_dict(param_data, orient='index', columns=['Value']))
        else:
            st.warning("Photometric Parameters not found or incomplete.")

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.session_state['locked'] = True
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            if st.session_state['locked']:
                if st.button("🔓 Unlock Base Build Methodology"):
                    st.session_state['locked'] = False
            else:
                if st.button("🔒 Lock Base Build Methodology"):
                    st.session_state['locked'] = True

        if not st.session_state['locked']:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

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

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)

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

    # === lm/W INCREMENT (NEW FEATURE - ROLLED UP) ===
    with st.expander("🔒 Average Lumens per Watt Step Increment (across ECG power changes)", expanded=False):
        st.markdown("""
        **115 lm/W is the average step increment across ECG driver power changes in our range.**  
        This field is editable and should only be adjusted by advanced users who understand its impact.
        """)
        if not st.session_state['lengths_list']:
            st.session_state['lmw_increment'] = st.number_input(
                "System lm/W Step Increment", min_value=50.0, max_value=300.0,
                value=st.session_state['lmw_increment'], step=1.0
            )
        else:
            st.info(f"🔒 Locked at: {st.session_state['lmw_increment']} lm/W (lengths exist)")

else:
    st.info("Upload an IES file to begin optimisation.")
