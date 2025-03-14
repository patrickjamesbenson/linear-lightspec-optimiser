import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'lmw_step_increment' not in st.session_state:
    st.session_state['lmw_step_increment'] = 115.0
if 'export_id' not in st.session_state:
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE INFO ===
    luminaire_line = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_full = luminaire_line.replace("[LUMINAIRE]", "").strip()

    # Split into name, wattage, optic, CRI, CCT (Flexible split logic)
    parts = luminaire_name_full.split(" - ")
    luminaire_series = parts[0].strip() if len(parts) > 0 else "Unknown Series"
    optic_type = parts[2].strip() if len(parts) > 2 else "Unknown Optic"
    cri_value = parts[-2].strip() if len(parts) > 2 else "N/A"
    cct_value = parts[-1].strip() if len(parts) > 1 else "N/A"

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        metadata = {
            "IES Version": next((line for line in parsed['header'] if line.startswith("IESNA")), "Not Found"),
            "Test Info": next((line for line in parsed['header'] if line.startswith("[TEST]")), "[TEST] Not Found"),
            "Manufacturer": next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "[MANUFAC] Not Found"),
            "Luminaire Catalog Number": next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "[LUMCAT] Not Found"),
            "Luminaire Description": luminaire_line,
            "Issued Date": next((line for line in parsed['header'] if line.startswith("[ISSUEDATE]")), "[ISSUEDATE] Not Found")
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(metadata, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = 5.5 mm | LED Series Module Pitch = 56.0 mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("### Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.001, format="%.3f")
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
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=0.0, step=1.0)
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value="Current Generation")

        if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.  
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']} lm/W")
        else:
            st.session_state['lmw_step_increment'] = st.number_input("Average lm/W Step Increment", min_value=50.0, max_value=200.0, value=115.0, step=1.0)

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
            luminaire_file_name = f"{luminaire_series} {optic_type}_{length:.3f}m_{tier}"

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

        df = pd.DataFrame(table_rows)
        st.table(df)

    # === DESIGN OPTIMISATION ===
    st.markdown("## 🎯 Design Optimisation")
    with st.expander("Target vs Achieved Lux Levels", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        if target_lux > 0:
            difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
            st.write(f"Difference: {difference_percent}%")

            required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
            increments_needed = int((required_change_lm_per_m / st.session_state['lmw_step_increment']) + 0.99)

            if difference_percent > 0:
                st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
            elif difference_percent < 0:
                st.info(f"✅ Consider increasing by {increments_needed} increments or uploading a higher output IES file.")
            else:
                st.success("🎯 Target lux achieved exactly!")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE OPTIMISED IES FILES ===
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

            filename = f"{luminaire_series}_{length:.3f}m.ies"
            new_file = create_ies_file(updated_header, scaled_data)
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)
        st.download_button("Download IES Files ZIP", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")

else:
    st.info("Upload an IES file to begin optimisation.")
