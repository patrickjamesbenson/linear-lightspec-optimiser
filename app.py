import streamlit as st
import pandas as pd
import math
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
    st.session_state['lmw_increment'] = 115  # Default lm/W increment

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE NAME ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

    # Extract Optic Name instead of WATT
    optic_name = "Diffused down" if "Diffused down" in luminaire_name_base else "Unknown Optic"

    # === EXTRACT CRI & CCT ===
    cri_value = "N/A"
    cct_value = "N/A"
    parts = luminaire_name_base.split('-')
    if len(parts) >= 4:
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Base Build locked. End Plate: "
                    f"{st.session_state['end_plate_thickness']} mm | LED Pitch: {st.session_state['led_pitch']} mm")
        else:
            if st.session_state['locked']:
                if st.button("🔓 Unlock Base Build Methodology"):
                    st.session_state['locked'] = False
            else:
                if st.button("🔒 Lock Base Build Methodology"):
                    st.session_state['locked'] = True

        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | "
                    f"LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)",
                                                                      min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)",
                                                            min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * \
                    st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if st.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True  # Lock after adding

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True

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

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

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

            luminaire_file_name = f"BLine 5690D {optic_name}_{length:.3f}m_{tier}"

            row = {
                "Delete": "🗑️",
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

        # Display Table Headers
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        # Display Rows
        for idx, row in enumerate(table_rows):
            row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

            for col, val in zip(row_cols[1:], row_data):
                col.write(val)

        export_df = pd.DataFrame([{
            "Length (m)": r["Length (m)"],
            "Luminaire & IES File Name": r["Luminaire & IES File Name"],
            "CRI": r["CRI"],
            "CCT": r["CCT"],
            "Total Lumens": r["Total Lumens"],
            "Total Watts": r["Total Watts"],
            "Settings lm/W": r["Settings lm/W"],
            "Comments": r["Comments"]
        } for r in table_rows])

        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION SECTION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")

        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=700.0, step=1.0)

        if target_lux > 0:
            difference_percent = round(((achieved_lux - target_lux) / target_lux) * 100, 1)

            st.markdown(f"**Difference:** {difference_percent:+.1f}%")

            current_lm_per_m = 400.0
            required_adjustment = round(abs(current_lm_per_m * (difference_percent / 100.0)), 1)
            increments_needed = math.ceil(required_adjustment / st.session_state['lmw_increment'])

            if difference_percent > 0:
                st.warning(f"⚠️ Achieved lux is higher than target by {difference_percent:.1f}%.")
                st.info(f"Recommend reducing output by dimming **{abs(difference_percent):.1f}%**, "
                        f"or selecting an IES file approximately **{increments_needed} increments lower** than the current.")
            elif difference_percent < 0:
                st.warning(f"⚠️ Achieved lux is lower than target by {abs(difference_percent):.1f}%.")
                st.info(f"Recommend increasing output by selecting an IES file approximately **{increments_needed} increments higher** than the current.")
            else:
                st.success("✅ Achieved lux matches target precisely.")

            st.markdown("### Upload New Optimised IES File (optional)")
            alt_ies_file = st.file_uploader("Upload Alternative IES File", type=["ies"])

            st.markdown("""
            > 💡 *For future theoretical model optimisations, install and dim precisely to your simulation target.  
            On-site readings will show how close your modelling is to reality.*
            """)

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

            filename = f"BLine 5690D {optic_name}_{length:.3f}m.ies"
            new_file = create_ies_file(updated_header, scaled_data)
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Generate IES Files & Download ZIP", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")

else:
    st.info("Upload an IES file to begin optimisation.")
