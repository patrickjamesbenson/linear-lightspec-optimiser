import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

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
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state['lmw_step_increment'] = 115.0

# === UPLOAD BASE IES FILE ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE NAME ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

    # === EXTRACT CRI, CCT, OPTIC ===
    cri_value = "N/A"
    cct_value = "N/A"
    optic_description = "Unknown Optic"

    if luminaire_name_base != "Not Found":
        parts = luminaire_name_base.split('-')
        if len(parts) >= 4:
            optic_description = parts[1].strip()
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.session_state['locked'] = True  # Lock it if lengths exist
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            col1, col2 = st.columns(2)
            st.session_state['end_plate_thickness'] = col1.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = col2.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

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
        st.session_state['locked'] = True  # Auto lock after add

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True  # Auto lock after add

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === SYSTEM LM/W INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.info(f"""
        To provide a quick reference, each mA power increment adjustment typically corresponds to an average efficacy of {st.session_state['lmw_step_increment']} lm/W.  
        For advanced users only.
        """)
        st.warning(f"🔒 Locked at: {st.session_state['lmw_step_increment']:.1f} lm/W")

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        # These should be global across session to avoid errors in optimisation!
        base_lm_per_m = 400.0
        base_w_per_m = 11.6

        table_rows = []
        efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Bespoke" if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0 else "Professional" if led_efficiency_gain_percent != 0 else "Core"

            luminaire_file_name = f"{luminaire_name_base.split('-')[0].strip()} {optic_description}_{length:.3f}m_{tier}"

            table_rows.append({
                "idx": idx,
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": efficiency_reason if led_efficiency_gain_percent != 0 else ""
            })

        for row in table_rows:
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
            if cols[0].button("🗑️", key=f"delete_{row['idx']}"):
                st.session_state['lengths_list'].pop(row['idx'])
                if not st.session_state['lengths_list']:
                    st.session_state['locked'] = False  # Unlock when list is empty
                st.rerun()

            cols[1].write(row["Length (m)"])
            cols[2].write(row["Luminaire & IES File Name"])
            cols[3].write(row["CRI"])
            cols[4].write(row["CCT"])
            cols[5].write(row["Total Lumens"])
            cols[6].write(row["Total Watts"])
            cols[7].write(row["Settings lm/W"])
            cols[8].write(row["Comments"])

        export_df = pd.DataFrame(table_rows)
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet.")

    # === DESIGN OPTIMISATION SECTION ===
    st.markdown("## 🎯 Design Optimisation")

    if st.session_state['lengths_list']:
        target_lux = st.number_input("Target Lux Level", min_value=100, max_value=10000, value=400, step=50)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=100, max_value=10000, value=700, step=50)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int(required_change_lm_per_m // st.session_state['lmw_step_increment']) + 1

        if difference_percent > 0:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        elif difference_percent < 0:
            st.success(f"✅ Consider increasing by {increments_needed} increments or uploading a higher-output IES file.")
        else:
            st.info("🎯 Target Lux achieved! No adjustment needed.")

        st.markdown("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES ===
    st.markdown("## Generate Optimised IES Files")

    if st.session_state['lengths_list']:
        files_to_zip = {}
        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)

            updated_header = []
            for line in parsed['header']:
                if line.startswith("[TEST]"):
                    updated_header.append(f"[TEST] Export ID: {st.session_state['export_id']}")
                else:
                    updated_header.append(line)

            filename = f"{luminaire_name_base.split('-')[0].strip()}_{length:.3f}m.ies"
            new_file = create_ies_file(updated_header, scaled_data)
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Generate IES Files & Download ZIP", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")

else:
    st.info("Upload an IES file to begin optimisation.")
