import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser - Veronica V4 Beta")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

# === SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state['lmw_increment'] = 115  # Default lm/W Increment
    st.session_state['lux_tolerance'] = 5     # Default Lux tolerance in %

# === LM/W Efficiency Increment ===
with st.expander("🔒 System lm/W Efficiency Increment", expanded=False):
    st.markdown("""
    **115 lm/W is the standard deviation in lumen output between ECG driver current increments in our current range.**
    
    This field is editable, aligns with our current product range, and should only be changed by qualified personnel.
    """)
    st.session_state['lmw_increment'] = st.number_input(
        "System lm/W Increment", 
        min_value=50, 
        max_value=300, 
        value=st.session_state['lmw_increment'], 
        step=5
    )

# === Lux Tolerance Threshold ===
with st.expander("🎯 Target Lux Tolerance", expanded=False):
    st.markdown("""
    Set the allowable tolerance (%) between your **Target Lux** and the **Actual Design Lux**.
    
    If your achieved lux is outside this range, an optimisation recommendation will be provided.
    """)
    st.session_state['lux_tolerance'] = st.number_input(
        "Lux Tolerance (%)", 
        min_value=1, 
        max_value=20, 
        value=st.session_state['lux_tolerance'], 
        step=1
    )

# === Proceed only after IES is uploaded ===
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

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Base Build locked because lengths have been selected.")
        else:
            if st.session_state['locked']:
                if st.button("🔓 Unlock Base Build Methodology"):
                    st.session_state['locked'] = False
            else:
                if st.button("🔒 Lock Base Build Methodology"):
                    st.session_state['locked'] = True

        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate = {st.session_state['end_plate_thickness']} mm | LED Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate (mm)", min_value=0.0, value=5.5, step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("## ➕ Select Lengths")
    desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
    desired_length_mm = desired_length_m * 1000
    min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
    max_length_mm = min_length_mm + st.session_state['led_pitch']

    shorter_length_m = round(min_length_mm / 1000, 3)
    longer_length_m = round(max_length_mm / 1000, 3)

    if st.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
        st.session_state['lengths_list'].append(shorter_length_m)

    if st.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
        st.session_state['lengths_list'].append(longer_length_m)

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        efficiency_reason = st.text_input("Reason", value=st.session_state['efficiency_reason'])

        if led_efficiency_gain_percent != 0 and (efficiency_reason.strip() == "" or efficiency_reason == "Current Generation"):
            st.error("⚠️ Provide a reason for LED Chipset Adjustment!")
            st.stop()

        st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
        st.session_state['efficiency_reason'] = efficiency_reason

    # === BASE LUMENS/WATTS ===
    base_lm_per_m = 400.0
    base_w_per_m = 11.6
    efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
    new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
    new_lm_per_m = round(base_lm_per_m, 1)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []

        for length in st.session_state['lengths_list']:
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0.0

            # Determine Tier
            if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0:
                tier = "Bespoke"
            elif led_efficiency_gain_percent != 0:
                tier = "Professional"
            elif st.session_state['led_pitch'] % 4 != 0:
                tier = "Advanced"
            else:
                tier = "Core"

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

        # CSV Export (No delete column)
        export_df = pd.DataFrame(table_rows).drop(columns=["Delete"])
        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

    # === OPTIMISATION RECOMMENDATION ===
    st.markdown("## 🔍 Optimisation Recommendation")

    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=300.0, step=10.0)
    achieved_lux = st.number_input("Achieved Lux (from DIALux or AGi32)", min_value=0.0, value=300.0, step=10.0)

    if target_lux and achieved_lux:
        difference = achieved_lux - target_lux
        difference_percent = (difference / target_lux) * 100

        if abs(difference_percent) <= st.session_state['lux_tolerance']:
            st.success(f"✅ Within {st.session_state['lux_tolerance']}% tolerance. No optimisation needed.")
        else:
            st.error(f"❗ Outside tolerance by {difference_percent:.2f}%.")
            recommended_steps = int(abs(difference_percent) / st.session_state['lmw_increment'] * 100)
            if recommended_steps < 1:
                recommended_steps = 1

            st.info(f"Recommendation: Adjust by {recommended_steps} increments of {st.session_state['lmw_increment']} lm/W, or dim the luminaire by {difference_percent:.2f}%.")

    # === GENERATE OPTIMISED IES FILES ===
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
