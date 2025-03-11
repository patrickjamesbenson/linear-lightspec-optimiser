import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

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
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")

            st.session_state['end_plate_thickness'] = st.number_input(
                "End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1
            )

            st.session_state['led_pitch'] = st.number_input(
                "LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1
            )

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
    st.markdown("## LED Chipset Adjustment")

    led_efficiency_gain_percent = st.number_input(
        "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
        value=st.session_state.get('led_efficiency_gain_percent', 0.0), step=1.0
    )

    efficiency_reason = st.text_input(
        "Reason (e.g., Gen 2 LED +15% increase lumen output)",
        value=st.session_state.get('efficiency_reason', 'Current Generation')
    )

    if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
        st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
        st.stop()

    st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
    st.session_state['efficiency_reason'] = efficiency_reason

    # === BASE LUMENS/WATTS FROM IES ===
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
    new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
    new_lm_per_m = round(base_lm_per_m, 1)
    new_lm_per_w = round(new_lm_per_m / new_w_per_m, 1) if new_w_per_m != 0 else 0.0

    # === SELECTED LENGTHS TABLE WITH DELETE BUTTONS (LEFT SIDE) ===
    if st.session_state['lengths_list']:
        st.markdown("### Selected Lengths for IES Generation")

        length_table_data = []
        product_tiers_found = set()

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)

            if (st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0):
                tier = "Bespoke"
            elif led_efficiency_gain_percent != 0:
                tier = "Professional"
            elif st.session_state['led_pitch'] % 4 != 0:
                tier = "Advanced"
            else:
                tier = "Core"

            product_tiers_found.add(tier)

            cols = st.columns([1, 8])
            with cols[0]:
                if st.button("🗑️", key=f"delete_{idx}"):
                    st.session_state['lengths_list'].pop(idx)
                    st.experimental_rerun()

            with cols[1]:
                row = {
                    "Length (m)": f"{length:.3f}",
                    "Lumens/m": f"{new_lm_per_m:.1f}",
                    "Watts/m": f"{new_w_per_m:.1f}",
                    "Total Lumens": f"{total_lumens:.1f}",
                    "Total Watts": f"{total_watts:.1f}",
                    "lm/W": f"{new_lm_per_w:.1f}",
                    "Product Tier": tier
                }

                if led_efficiency_gain_percent != 0:
                    row["Chipset Adj. (%)"] = f"{led_efficiency_gain_percent:.1f}"
                    row["Reason"] = efficiency_reason

                if (st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0):
                    row["End Plate (mm)"] = f"{st.session_state['end_plate_thickness']:.1f}"
                    row["LED Series Pitch (mm)"] = f"{st.session_state['led_pitch']:.1f}"

                st.write(pd.DataFrame([row]).style.format(precision=1))

        if len(product_tiers_found) > 1:
            st.markdown("> ⚠️ Where multiple tiers are displayed, the highest tier applies.")

        # Rebuild dataframe for CSV download
        length_table_data_csv = []
        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)

            if (st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0):
                tier = "Bespoke"
            elif led_efficiency_gain_percent != 0:
                tier = "Professional"
            elif st.session_state['led_pitch'] % 4 != 0:
                tier = "Advanced"
            else:
                tier = "Core"

            row_csv = {
                "Length (m)": f"{length:.3f}",
                "Lumens/m": f"{new_lm_per_m:.1f}",
                "Watts/m": f"{new_w_per_m:.1f}",
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "lm/W": f"{new_lm_per_w:.1f}",
                "Product Tier": tier
            }

            length_table_data_csv.append(row_csv)

        lengths_df_csv = pd.DataFrame(length_table_data_csv)

        st.download_button(
            "Download CSV Summary",
            data=lengths_df_csv.to_csv(index=False).encode('utf-8'),
            file_name="Selected_Lengths_Summary.csv",
            mime="text/csv"
        )

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === GENERATE IES FILES & DOWNLOAD ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['lengths_list']:
        files_to_zip = {}

        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)
            new_file = create_ies_file(parsed['header'], scaled_data)
            filename = f"Optimised_{length:.3f}m.ies"
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button(
            label="Generate IES Files & Download ZIP",
            data=zip_buffer,
            file_name="Optimised_IES_Files.zip",
            mime="application/zip"
        )

else:
    st.info("Upload an IES file to begin optimisation.")
