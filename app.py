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
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lm_per_watt_increment'] = 115.0  # NEW for increment logic
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Base Build locked because lengths have been selected.")
        else:
            col1, col2 = st.columns(2)
            st.session_state['end_plate_thickness'] = col1.number_input(
                "End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = col2.number_input(
                "LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

    # === SELECT LENGTHS ===
    st.subheader("Select Lengths")
    col1, col2 = st.columns(2)
    desired_length_m = col1.number_input(
        "Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000

    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.rerun()

    if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input(
            "LED Chipset Adjustment (%)",
            min_value=-50.0, max_value=100.0,
            value=st.session_state.get('led_efficiency_gain_percent', 0.0),
            step=1.0
        )
        efficiency_reason = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state.get('efficiency_reason', 'Current Generation')
        )
        if led_efficiency_gain_percent != 0 and efficiency_reason.strip() == "":
            st.error("⚠️ You must provide a reason for the LED Chipset Adjustment before proceeding.")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === LUMENS/WATT INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input(
                "Average lm/W Step Increment",
                min_value=10.0, max_value=500.0,
                value=st.session_state['lm_per_watt_increment'], step=5.0
            )

    # === SELECTED LENGTHS TABLE ===
    st.subheader("📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        table_rows = []
        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
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
                "Comments": st.session_state['efficiency_reason']
            }

            table_rows.append(row)

        # Display Table Headers and Rows
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

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

            for col, val in zip(row_cols[1:], row_data):
                col.write(val)

        # Export CSV (excluding Delete column)
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

        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'),
                           file_name=f"Selected_Lengths_Summary_{st.session_state['export_id']}.csv", mime="text/csv")

else:
    st.info("Upload an IES file to begin optimisation.")
