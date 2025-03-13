import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = "Current Generation"
    st.session_state['lm_per_watt_increment'] = 115.0  # default step increment
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    luminaire_line = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "")
    luminaire_name_base = luminaire_line.replace("[LUMINAIRE]", "").strip()

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_version = next((line for line in parsed['header'] if line.startswith("IESNA")), "N/A")
        test_info = next((line for line in parsed['header'] if line.startswith("[TEST]")), "N/A")
        manufac_info = next((line for line in parsed['header'] if line.startswith("[MANUFAC]")), "N/A")
        lumcat_info = next((line for line in parsed['header'] if line.startswith("[LUMCAT]")), "N/A")
        issuedate_info = next((line for line in parsed['header'] if line.startswith("[ISSUEDATE]")), "N/A")

        metadata_table = {
            "IES Version": ies_version,
            "Test Info": test_info,
            "Manufacturer": manufac_info,
            "Luminaire Catalog Number": lumcat_info,
            "Luminaire Description": luminaire_line,
            "Issued Date": issuedate_info
        }

        st.table(pd.DataFrame.from_dict(metadata_table, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=10.0, value=st.session_state['led_pitch'], step=0.1)

    # === SELECT LENGTHS ===
    st.subheader("Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    led_pitch = st.session_state['led_pitch']
    end_plate = st.session_state['end_plate_thickness']

    min_length_mm = (int((desired_length_mm - end_plate * 2) / led_pitch)) * led_pitch + end_plate * 2
    max_length_mm = min_length_mm + led_pitch

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    col1, col2 = st.columns(2)
    if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)
        st.session_state['locked'] = True
        st.rerun()

    if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)
        st.session_state['locked'] = True
        st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_gain = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if led_gain != 0 and reason.strip() == "Current Generation":
            st.warning("⚠️ Please specify the reason for adjustment.")
        st.session_state['led_efficiency_gain_percent'] = led_gain
        st.session_state['efficiency_reason'] = reason

    # === SYSTEM LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lm_per_watt_increment']} lm/W")
        else:
            st.session_state['lm_per_watt_increment'] = st.number_input("Average lm/W Step Increment", min_value=10.0, max_value=500.0, value=115.0, step=1.0)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if st.session_state['lengths_list']:
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        gain_factor = 1 + (st.session_state['led_efficiency_gain_percent'] / 100.0)

        table_data = []
        for idx, length in enumerate(st.session_state['lengths_list']):
            lumens = round(base_lm_per_m * length * gain_factor, 1)
            watts = round(base_w_per_m * length * (1 / gain_factor), 1)
            lm_w = round(lumens / watts, 1) if watts != 0 else 0.0

            luminaire_file = f"{luminaire_name_base}_{length:.3f}m_Professional"

            row = {
                "Delete": "🗑️",
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file,
                "CRI": "80CRI",  # static placeholder
                "CCT": "3000K",  # static placeholder
                "Total Lumens": f"{lumens:.1f}",
                "Total Watts": f"{watts:.1f}",
                "Settings lm/W": f"{lm_w:.1f}",
                "Comments": st.session_state['efficiency_reason']
            }
            table_data.append(row)

        # Table display
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        for idx, row in enumerate(table_data):
            row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if row_cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if not st.session_state['lengths_list']:
                    st.session_state['locked'] = False
                st.rerun()

            for col, val in zip(row_cols[1:], list(row.values())[1:]):
                col.write(val)

        export_df = pd.DataFrame(table_data).drop(columns=["Delete"])
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False), file_name="Selected_Lengths_Summary.csv")

    # === DESIGN OPTIMISATION ===
    with st.expander("🎯 Design Optimisation", expanded=False):
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {difference_percent}%")

        required_change = round(abs(difference_percent) * 400 / 100, 1)
        increments_needed = int(required_change // st.session_state['lm_per_watt_increment'])

        if difference_percent > 0:
            st.warning(f"⚠️ Consider reducing by {increments_needed} increments or dimming to match target lux.")
        elif difference_percent < 0:
            st.success(f"✅ Consider increasing by {increments_needed} increments or boosting output.")
        else:
            st.info("Lux levels match target. No changes needed.")

    # === GENERATE IES FILES ===
    if st.session_state['lengths_list']:
        st.success("✅ IES Files Generation Complete! (Placeholder logic)")
