import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === VERSION CHECK ===
st_version = st.__version__
if int(st_version.split('.')[1]) >= 32:
    rerun = st.rerun
else:
    rerun = st.experimental_rerun

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INITIALISATION ===
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
    st.session_state['efficiency_reason'] = 'Current Generation'
if 'lm_per_watt_increment' not in st.session_state:
    st.session_state['lm_per_watt_increment'] = 115.0
if 'export_id' not in st.session_state:
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === Extract Luminaire Info ===
    luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
    luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()
    
    # Extract CRI and CCT
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

        metadata = {
            "IES Version": ies_version,
            "Test Info": test_info,
            "Manufacturer": manufac_info,
            "Luminaire Catalog Number": lumcat_info,
            "Luminaire Description": luminaire_info,
            "Issued Date": issuedate_info
        }
        st.table(pd.DataFrame(list(metadata.items()), columns=["", "Value"]))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, step=0.1, key='end_plate_thickness')
            st.number_input("LED Series Module Pitch (mm)", min_value=14.0, step=0.1, key='led_pitch')

    # === SELECT LENGTHS ===
    st.markdown("### Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']
    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    col1, col2 = st.columns(2)
    if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True
        rerun()

    if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        st.session_state['led_efficiency_gain_percent'] = st.number_input(
            "LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0,
            step=1.0, value=st.session_state['led_efficiency_gain_percent']
        )
        st.session_state['efficiency_reason'] = st.text_input(
            "Reason (e.g., Gen 2 LED +15% increase lumen output)",
            value=st.session_state['efficiency_reason']
        )

    # === LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.info("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range. For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input(
                "Average lm/W Step Increment",
                min_value=10.0, max_value=500.0,
                value=st.session_state['lm_per_watt_increment'],
                step=5.0
            )

    # === SELECTED LENGTHS TABLE ===
    st.markdown("### 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        eff_multiplier = 1 + (st.session_state['led_efficiency_gain_percent'] / 100)
        new_lm_per_m = base_lm_per_m * eff_multiplier
        new_w_per_m = base_w_per_m * eff_multiplier

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            optic_type = "Diffused Down"
            luminaire_file_name = f"{luminaire_name_base} {optic_type}_{length:.3f}m_{tier}"

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

        # === DISPLAY TABLE ===
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        for col, header in zip(header_cols, headers):
            col.markdown(f"**{header}**")

        for idx, row in enumerate(table_rows):
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
            if cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                rerun()
            data_fields = list(row.values())[1:]
            for col, field in zip(cols[1:], data_fields):
                col.write(field)

        export_df = pd.DataFrame([row for row in table_rows])
        export_df.drop(columns=["Delete"], inplace=True)
        st.download_button("Download CSV Summary", export_df.to_csv(index=False), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION SECTION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        st.subheader("Target vs Achieved Lux Levels")
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=10.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=10.0)
        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1) if target_lux else 0.0
        st.write(f"Difference: {difference_percent}%")

        required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
        increments_needed = int((required_change_lm_per_m / st.session_state['lm_per_watt_increment']) + 0.999)

        if abs(difference_percent) < 5:
            st.success("✅ No increment change needed. Fine-tune dimming if required.")
        else:
            if difference_percent > 0:
                st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
            else:
                st.info(f"⬆️ Consider increasing by {increments_needed} increments or uploading a higher output IES file.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES (PLACEHOLDER) ===
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")
else:
    st.info("Please upload an IES file to begin.")
