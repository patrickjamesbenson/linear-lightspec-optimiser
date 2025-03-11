import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === Base File Summary ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found")
        test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found")
        manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found")
        lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found")
        luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
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

    # === Base Build Methodology (Expander with Toggle Lock) ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        
        # Initialise session state (run once)
        if 'locked' not in st.session_state:
            st.session_state['locked'] = False
            st.session_state['lengths_list'] = []
            st.session_state['end_plate_thickness'] = 5.5
            st.session_state['led_pitch'] = 56.0

        # Toggle Button Logic: Lock/Unlock
        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build Methodology"):
                st.session_state['locked'] = False
        else:
            if st.button("🔒 Lock Base Build Methodology"):
                st.session_state['locked'] = True

        # If UNLOCKED, show inputs and warning
        if not st.session_state['locked']:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")

            end_plate_thickness = st.number_input(
                "End Plate Expansion Gutter (mm)",
                min_value=0.0,
                value=st.session_state['end_plate_thickness'],
                step=0.1
            )

            led_pitch = st.number_input(
                "LED Series Module Pitch (mm)",
                min_value=14.0,  # ✅ Set min pitch to 14mm
                value=st.session_state['led_pitch'],
                step=0.1
            )

            # Save values into session state
            st.session_state['end_plate_thickness'] = end_plate_thickness
            st.session_state['led_pitch'] = led_pitch

        # If LOCKED, show info only
        else:
            end_plate_thickness = st.session_state['end_plate_thickness']
            led_pitch = st.session_state['led_pitch']

            st.info(f"🔒 Locked: End Plate Expansion Gutter = {end_plate_thickness} mm | LED Series Module Pitch = {led_pitch} mm")

    # === Remaining Sections ===
    # Length Validation, Optimisation Inputs, Tier Feedback, etc.
    # (unchanged and working as previously agreed)
