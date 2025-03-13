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
    st.session_state['lm_per_watt_increment'] = 115.0
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
    parts = luminaire_name_base.split('-')
    if len(parts) >= 3:
        cri_value = parts[-2].strip()
        cct_value = parts[-1].strip()

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=True):
        st.markdown("### IES Metadata")

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

        st.table(pd.DataFrame(list(metadata_dict.items()), columns=["Field", "Value"]))

        st.markdown("### Photometric Parameters")
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

            st.table(pd.DataFrame(list(param_data.items()), columns=["Field", "Value"]))
        else:
            st.warning("Photometric Parameters not found or incomplete.")

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Locked: End Plate Expansion Gutter = {:.1f} mm | LED Series Module Pitch = {:.1f} mm".format(
                st.session_state['end_plate_thickness'],
                st.session_state['led_pitch']
            ))
        else:
            st.session_state['end_plate_thickness'] = st.number_input(
                "End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input(
                "LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("### Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")

    # Short/long length calc
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

    # === SELECTED LENGTHS TABLE (Moved Up Under Lengths Section) ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        table_rows = []

        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            luminaire_file_name = f"{luminaire_name_base} Diffused Down_{length:.3f}m_{tier}"

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

        # Display headers
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        for col, header in zip(header_cols, headers):
            col.markdown(f"**{header}**")

        # Display rows
        for idx, row in enumerate(table_rows):
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if not st.session_state['lengths_list']:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]
            for col, val in zip(cols[1:], row_data):
                col.write(val)

        export_df = pd.DataFrame(table_rows).drop(columns=['Delete'])
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'),
                           file_name="Selected_Lengths_Summary.csv", mime="text/csv")
    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        st.session_state['led_efficiency_gain_percent'] = st.number_input(
            "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
            value=st.session_state['led_efficiency_gain_percent'], step=1.0)

        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

        if st.session_state['led_efficiency_gain_percent'] != 0 and st.session_state['efficiency_reason'].strip() == '':
            st.error("⚠️ Provide a reason for LED Chipset Adjustment before proceeding.")
            st.stop()

    # === SYSTEM LM/W EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.  
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']:.1f} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input(
                "Average lm/W Step Increment", min_value=10.0, max_value=500.0,
                value=st.session_state['lm_per_watt_increment'], step=1.0)

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int(required_change_lm_per_m // st.session_state['lm_per_watt_increment'])

        if difference_percent > 0:
            if increments_needed < 1:
                st.warning("⚠️ Dimming recommended to match target lux.")
            else:
                st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        else:
            if increments_needed < 1:
                st.success("✅ No increment adjustment required.")
            else:
                st.success(f"✅ Consider increasing by {increments_needed} increments to meet target lux.")

        st.info("Note: This enables theoretical model accuracy for future optimisations.")

