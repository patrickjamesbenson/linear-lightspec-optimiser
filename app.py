import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === STREAMLIT PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

# === UPLOAD IES FILE ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === BASE FILE SUMMARY ===
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):

        if 'locked' not in st.session_state:
            st.session_state['locked'] = True
            st.session_state['lengths_list'] = []
            st.session_state['end_plate_thickness'] = 5.5
            st.session_state['led_pitch'] = 56.0

        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build Methodology"):
                st.session_state['locked'] = False
        else:
            if st.button("🔒 Lock Base Build Methodology"):
                st.session_state['locked'] = True

        if st.session_state['locked']:
            end_plate_thickness = st.session_state['end_plate_thickness']
            led_pitch = st.session_state['led_pitch']
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {end_plate_thickness} mm | LED Series Module Pitch = {led_pitch} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")

            end_plate_thickness = st.number_input(
                "End Plate Expansion Gutter (mm)",
                min_value=0.0,
                value=st.session_state['end_plate_thickness'],
                step=0.1
            )

            led_pitch = st.number_input(
                "LED Series Module Pitch (mm)",
                min_value=14.0,
                value=st.session_state['led_pitch'],
                step=0.1
            )

            st.session_state['end_plate_thickness'] = end_plate_thickness
            st.session_state['led_pitch'] = led_pitch

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")

    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.1)
    desired_length_mm = desired_length_m * 1000

    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    # === STACKED BUTTONS ===
    if st.button(f"Add Shorter Buildable Length: {shorter_length_m} m", key=f"short_{shorter_length_m}"):
        st.session_state['lengths_list'].append(shorter_length_m)

    if st.button(f"Add Longer Buildable Length: {longer_length_m} m", key=f"long_{longer_length_m}"):
        st.session_state['lengths_list'].append(longer_length_m)

    # === LED CHIPSET ADJUSTMENT ===
    st.markdown("## LED Chipset Adjustment")

    led_efficiency_gain_percent = st.number_input(
        "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
        value=st.session_state.get('led_efficiency_gain_percent', 0.0), step=1.0
    )

    efficiency_reason = st.text_input(
        "Reason (e.g., Gen 2 LED +15% increase lumen output)",
        value=st.session_state.get('efficiency_reason', '')
    )

    # FORCE reason if adjustment is not zero
    if led_efficiency_gain_percent != 0 and efficiency_reason.strip() == "":
        st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
        st.stop()
    else:
        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === Base lumens/watts from IES ===
    base_lm_per_m = 400  # Example; replace with actual extracted value
    base_w_per_m = 11.6  # Example; replace with actual extracted value from param_data["Input Watts"]

    # === Efficiency Gain Reduces Watts ===
    efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100)
    st.session_state['efficiency_multiplier'] = efficiency_multiplier

    new_w_per_m = base_w_per_m * efficiency_multiplier
    new_lm_per_m = base_lm_per_m  # Stays the same
    new_lm_per_w = new_lm_per_m / new_w_per_m if new_w_per_m else 0

    # === SELECTED LENGTHS TABLE ===
    if st.session_state['lengths_list']:
        st.markdown("### Selected Lengths for IES Generation")

        length_table_data = []

        for length in st.session_state['lengths_list']:
            total_lumens = new_lm_per_m * length
            total_watts = new_w_per_m * length

            length_table_data.append({
                "Length (m)": length,
                "Lumens per Metre": f"{new_lm_per_m:.2f}",
                "Watts per Metre": f"{new_w_per_m:.2f}",
                "Total Lumens (lm)": f"{total_lumens:.2f}",
                "Total Watts (W)": f"{total_watts:.2f}",
                "lm/W": f"{new_lm_per_w:.2f}",
                "End Plate (mm)": st.session_state['end_plate_thickness'],
                "LED Series Pitch (mm)": st.session_state['led_pitch'],
                "LED Chipset Adjustment": f"{led_efficiency_gain_percent:.2f}%",
                "LED Multiplier Reason": efficiency_reason,
                "Product Tier": "Professional"
            })

        lengths_df = pd.DataFrame(length_table_data)

        st.table(lengths_df)

        st.download_button(
            "Download CSV Summary",
            data=lengths_df.to_csv(index=False).encode('utf-8'),
            file_name="Selected_Lengths_Summary.csv",
            mime="text/csv"
        )
    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === COMPARISON TABLE ===
    st.markdown("## Comparison Table: Base vs Optimised")

    comparison_df = pd.DataFrame({
        "Metric": ["Lumens per Metre", "Watts per Metre", "lm/W"],
        "Base": [f"{base_lm_per_m:.2f}", f"{base_w_per_m:.2f}", f"{base_lm_per_m / base_w_per_m:.2f}"],
        "Optimised": [f"{new_lm_per_m:.2f}", f"{new_w_per_m:.2f}", f"{new_lm_per_w:.2f}"]
    })

    st.table(comparison_df)

    # === GENERATE OPTIMISED IES FILES ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['lengths_list']:
        if st.button("Generate IES Files & Download ZIP"):
            files_to_zip = {}

            for length in st.session_state['lengths_list']:
                scaled_data = modify_candela_data(parsed['data'], 1.0)  # No candela change right now
                new_file = create_ies_file(parsed['header'], scaled_data)
                filename = f"Optimised_{length:.2f}m.ies"
                files_to_zip[filename] = new_file

            zip_buffer = create_zip(files_to_zip)

            st.download_button(
                "Download ZIP of IES Files",
                zip_buffer,
                file_name="Optimised_IES_Files.zip",
                mime="application/zip"
            )

else:
    st.info("Upload an IES file to begin optimisation.")
