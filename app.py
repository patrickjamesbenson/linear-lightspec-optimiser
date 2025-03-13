import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INITIALISATION ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lmw_step_increment'] = 115.0
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
    cri_value, cct_value = "N/A", "N/A"
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

        desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
        desired_length_mm = desired_length_m * 1000
        min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
        max_length_mm = min_length_mm + st.session_state['led_pitch']

        shorter_length_m = round(min_length_mm / 1000, 3)
        longer_length_m = round(max_length_mm / 1000, 3)

        if st.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
            st.session_state['lengths_list'].append(shorter_length_m)
            st.session_state['locked'] = True
            st.rerun()

        if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
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

        if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        **115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.**
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']:.1f} lm/W")
        else:
            st.session_state['lmw_step_increment'] = st.number_input("Average lm/W Step Increment", min_value=50.0, max_value=500.0,
                                                                      value=st.session_state['lmw_step_increment'], step=1.0)

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

            tier = "Professional" if led_efficiency_gain_percent != 0 else "Core"

            luminaire_file_name = f"{luminaire_name_base}_{length:.3f}m_{tier}"

            row = {
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": efficiency_reason
            }

            table_rows.append(row)

        df_table = pd.DataFrame(table_rows)

        st.dataframe(df_table)

        st.download_button("Download CSV Summary", data=df_table.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")

        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=10.0, format="%.2f")
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=10.0, format="%.2f")

        if target_lux > 0:
            difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
            st.write(f"Difference: {difference_percent}%")

            required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
            increments_needed_raw = required_change_lm_per_m / st.session_state['lmw_step_increment']

            if increments_needed_raw < 1:
                st.warning(f"✅ No increments needed. Recommend dimming by {abs(difference_percent)}% to match target lux.")
            else:
                increments_needed = int(increments_needed_raw) + (0 if increments_needed_raw.is_integer() else 1)
                if difference_percent > 0:
                    st.warning(f"⚠️ Reduce by {increments_needed} increments or dim to match target lux.")
                elif difference_percent < 0:
                    st.warning(f"⚠️ Increase by {increments_needed} increments or consider using a higher output IES file.")
                else:
                    st.success("✅ Target lux level achieved exactly! No adjustment needed.")

    # === GENERATE IES FILES ===
    if st.button("Generate Optimised IES Files"):
        files_to_zip = {}
        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)

            updated_header = []
            for line in parsed['header']:
                if line.startswith("[TEST]"):
                    updated_header.append(f"[TEST] Export ID: {st.session_state['export_id']}")
                else:
                    updated_header.append(line)

            new_file = create_ies_file(updated_header, scaled_data)
            filename = f"{luminaire_name_base}_{length:.3f}m.ies"
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Download ZIP of IES Files", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")

else:
    st.info("Upload an IES file to begin optimisation.")
