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
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'end_plate_thickness' not in st.session_state:
    st.session_state['end_plate_thickness'] = 5.5
if 'led_pitch' not in st.session_state:
    st.session_state['led_pitch'] = 56.0
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = "Current Generation"
if 'export_id' not in st.session_state:
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
if 'lmw_step_increment' not in st.session_state:
    st.session_state['lmw_step_increment'] = 115.0
if 'base_lm_per_m' not in st.session_state:
    st.session_state['base_lm_per_m'] = 400.0
if 'base_w_per_m' not in st.session_state:
    st.session_state['base_w_per_m'] = 11.6

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === Extract Luminaire Info ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

    # === Extract CRI & CCT ===
    cri_value = "N/A"
    cct_value = "N/A"
    if luminaire_name_base != "Not Found":
        parts = luminaire_name_base.split('-')
        if len(parts) >= 3:
            cri_value = parts[-2].strip()
            cct_value = parts[-1].strip()

    # === Base File Summary ===
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

    # === Base Build Methodology ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

    # === Select Lengths ===
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
        st.rerun()

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        st.rerun()

    # === LED Chipset Adjustment ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        efficiency_reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if led_efficiency_gain_percent != 0 and efficiency_reason.strip() == "":
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === Average lm/W Step Increment ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        **115 is the ave. lm/W step increment mA change.**

        This field is editable and should only be adjusted by advanced users.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']} lm/W")
        else:
            st.session_state['lmw_step_increment'] = st.number_input("Average lm/W Step Increment", min_value=50.0, max_value=300.0, value=st.session_state['lmw_step_increment'], step=5.0)

    # === Selected Lengths Table ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = st.session_state['base_lm_per_m']
        base_w_per_m = st.session_state['base_w_per_m']
        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(base_lm_per_m * length, 1)
            total_watts = round(base_w_per_m * length * efficiency_multiplier, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            luminaire_file_name = f"{luminaire_name_base}_{length:.3f}m_{tier}"

            row = {
                "Delete": "🗑️",
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": st.session_state['efficiency_reason'] if st.session_state['led_efficiency_gain_percent'] != 0 else ""
            }

            table_rows.append(row)

        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for idx, row in enumerate(table_rows):
            row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"], row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]
            for col, val in zip(row_cols[1:], row_data):
                col.write(val)

        # Export CSV
        export_df = pd.DataFrame(table_rows).drop(columns=["Delete"])
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")
    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === Design Optimisation ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=10.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=700.0, step=10.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1) if target_lux != 0 else 0
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(st.session_state['base_lm_per_m'] * abs(difference_percent) / 100, 1)
        increments_needed = int(required_change_lm_per_m / st.session_state['lmw_step_increment'])
        if required_change_lm_per_m % st.session_state['lmw_step_increment'] != 0:
            increments_needed += 1

        if difference_percent > 0:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        elif difference_percent < 0:
            st.warning(f"⚠️ Consider increasing by {increments_needed} increments or selecting a different IES file.")
        else:
            st.success("✅ Target achieved. Fine-tune with dimming on site.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === Generate IES Files ===
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

            new_file = create_ies_file(updated_header, scaled_data)
            filename = f"{luminaire_name_base}_{length:.3f}m.ies"
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Generate IES Files & Download ZIP", data=zip_buffer, file_name="Optimised_IES_Files.zip", mime="application/zip")
else:
    st.info("Upload an IES file to begin optimisation.")
