import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# === STREAMLIT PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")

st.title("Linear LightSpec Optimiser")

# === UPLOAD IES FILE ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === INITIALISE SESSION STATES ===
    if 'locked' not in st.session_state:
        st.session_state['locked'] = True
    if 'lengths_list' not in st.session_state:
        st.session_state['lengths_list'] = []
    if 'end_plate_thickness' not in st.session_state:
        st.session_state['end_plate_thickness'] = 5.5
    if 'led_pitch' not in st.session_state:
        st.session_state['led_pitch'] = 56.0
    if 'led_efficiency_gain_percent' not in st.session_state:
        st.session_state['led_efficiency_gain_percent'] = 0.0
    if 'efficiency_reason' not in st.session_state:
        st.session_state['efficiency_reason'] = 'Current Generation'

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
        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build Methodology"):
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                else:
                    st.warning("You must delete all lengths before modifying base build methodology.")
        else:
            if st.button("🔒 Lock Base Build Methodology"):
                st.session_state['locked'] = True

        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
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

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state.get('led_efficiency_gain_percent', 0.0), step=1.0)
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state.get('efficiency_reason', 'Current Generation'))

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

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        product_tiers_found = set()
        table_rows = []

        # Extract CRI and CCT from luminaire_info (example extraction logic)
        try:
            cri_value = next((part for part in luminaire_info.split("-") if "CRI" in part), "CRI Unknown").replace("CRI", "").strip()
            cct_value = next((part for part in luminaire_info.split("-") if "K" in part), "CCT Unknown").strip()
        except Exception:
            cri_value = "CRI Unknown"
            cct_value = "CCT Unknown"

        for length in st.session_state['lengths_list']:
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)

            if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0:
                tier = "Bespoke"
            elif led_efficiency_gain_percent != 0:
                tier = "Professional"
            elif st.session_state['led_pitch'] % 4 != 0:
                tier = "Advanced"
            else:
                tier = "Core"

            product_tiers_found.add(tier)

            luminaire_field = f"Bline8585D_{length:.3f}m_{tier}"
            test_field = f"4000K_CRI{cri_value}_Lm/W{new_lm_per_w:.1f} | {efficiency_reason} ({led_efficiency_gain_percent:.1f}%)"

            row = {
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_field,
                "CRI": cri_value,
                "CCT": cct_value,
                "Comments": efficiency_reason if led_efficiency_gain_percent != 0 else "",
                "Lumens/m": f"{new_lm_per_m:.1f}",
                "Watts/m": f"{new_w_per_m:.1f}",
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "lm/W": f"{new_lm_per_w:.1f}",
                "Settings": test_field
            }

            table_rows.append(row)

        df = pd.DataFrame(table_rows)

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_selection('single', use_checkbox=True)
        gb.configure_grid_options(domLayout='normal')

        grid_response = AgGrid(
            df,
            gridOptions=gb.build(),
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=(len(df) * 35 + 50),
            allow_unsafe_jscode=True
        )

        selected_rows = grid_response.get('selected_rows', [])

        # DELETE FUNCTION WORKS!
        if selected_rows and isinstance(selected_rows, list) and len(selected_rows) > 0:
            selected_row = selected_rows[0]
            length_value_str = selected_row.get('Length (m)', None)

            if length_value_str:
                try:
                    length_value = float(length_value_str)
                    if st.button("🗑️ Delete Selected Length"):
                        st.session_state['lengths_list'] = [
                            l for l in st.session_state['lengths_list']
                            if round(l, 3) != round(length_value, 3)
                        ]
                        if len(st.session_state['lengths_list']) == 0:
                            st.session_state['locked'] = False
                        st.experimental_rerun()
                except ValueError:
                    st.error("Invalid length selected for deletion.")

        if len(product_tiers_found) > 1:
            st.markdown("> ⚠️ Where multiple tiers are displayed, the highest tier applies.")

        st.download_button(
            "Download CSV Summary",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name="Selected_Lengths_Summary.csv",
            mime="text/csv"
        )
    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === GENERATE IES FILES ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['lengths_list']:
        files_to_zip = {}
        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)
            new_file = create_ies_file(parsed['header'], scaled_data)
            filename = f"Bline8585D_{length:.3f}m_{tier}.ies"
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
