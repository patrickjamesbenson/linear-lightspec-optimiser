import streamlit as st
import pandas as pd
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INIT SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['lmw_step_increment'] = 115.0
    st.session_state['base_lm_per_m'] = 400.0
    st.session_state['base_w_per_m'] = 11.6

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])
if uploaded_file:
    file_name = uploaded_file.name
    st.success(f"Uploaded: {file_name}")
    
    luminaire_name_base = "BLine 8585D"
    optic_type = "Diffused Down"
    cri_value = "80CRI"
    cct_value = "3000K"
    
    st.divider()

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        st.markdown("### IES Metadata")
        st.table({
            "IES Version": ["IESNA:LM-63-2002"],
            "Test Info": ["[TEST]"],
            "Manufacturer": ["[MANUFAC] Evolt Manufacturing"],
            "Luminaire Catalog Number": ["[LUMCAT] B852-__A3___1488030ZZ"],
            "Luminaire Description": ["[LUMINAIRE] BLine 8585D 11.6W - 80CRI - 3000K"],
            "Issued Date": ["[ISSUEDATE] 2024-07-07"]
        })

# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    if st.session_state['lengths_list']:
        st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
    else:
        st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
        st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

# === SELECT LENGTHS ===
desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.000, step=0.001, format="%.3f")
desired_length_mm = desired_length_m * 1000
min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
max_length_mm = min_length_mm + st.session_state['led_pitch']

shorter_length_m = round(min_length_mm / 1000, 3)
longer_length_m = round(max_length_mm / 1000, 3)

col1, col2 = st.columns(2)
if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
    st.session_state['lengths_list'].append(shorter_length_m)
    st.session_state['locked'] = True
if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
    st.session_state['lengths_list'].append(longer_length_m)
    st.session_state['locked'] = True

# === LED CHIPSET ADJUSTMENT ===
with st.expander("💡 LED Chipset Adjustment", expanded=False):
    st.session_state['led_efficiency_gain_percent'] = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
    st.session_state['efficiency_reason'] = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

# === AVERAGE LM/W INCREMENT ===
with st.expander("🔒 Average lm/W Step Increment", expanded=False):
    st.info("115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.\nFor advanced users only.")
    if st.session_state['lengths_list']:
        st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']:.1f} lm/W")
    else:
        st.session_state['lmw_step_increment'] = st.number_input("Average lm/W Step Increment", min_value=50.0, max_value=500.0, value=st.session_state['lmw_step_increment'], step=5.0)

# === SELECTED LENGTHS TABLE ===
st.markdown("## 📏 Selected Lengths for IES Generation")
if st.session_state['lengths_list']:
    table_rows = []
    
    efficiency_multiplier = 1 - (st.session_state['led_efficiency_gain_percent'] / 100.0)
    new_w_per_m = round(st.session_state['base_w_per_m'] * efficiency_multiplier, 1)
    new_lm_per_m = round(st.session_state['base_lm_per_m'], 1)

    for idx, length in enumerate(st.session_state['lengths_list']):
        total_lumens = round(new_lm_per_m * length, 1)
        total_watts = round(new_w_per_m * length, 1)
        lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0
        
        tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
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

    header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
    headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    for idx, row in enumerate(table_rows):
        cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        if cols[0].button("🗑️", key=f"delete_{idx}"):
            st.session_state['lengths_list'].pop(idx)
            if len(st.session_state['lengths_list']) == 0:
                st.session_state['locked'] = False
            st.rerun()
        for col, val in zip(cols[1:], row.values()):
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

# === DESIGN OPTIMISATION ===
with st.expander("🎯 Design Optimisation", expanded=False):
    st.subheader("Target vs Achieved Lux Levels")
    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)
    
    difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1) if target_lux > 0 else 0
    st.write(f"Difference: {difference_percent}%")

    required_change_lm_per_m = round(st.session_state['base_lm_per_m'] * abs(difference_percent) / 100, 1)
    increments_needed = int((required_change_lm_per_m / st.session_state['lmw_step_increment']) + 0.999)

    if abs(difference_percent) < 5:
        recommendation = "⚠️ Dimming recommended to match target lux."
    else:
        recommendation = f"⚠️ Consider {'reducing' if difference_percent > 0 else 'increasing'} by {increments_needed} increments or dimming to match target lux."

    st.warning(recommendation)
    st.caption("Note: This enables theoretical model accuracy for future optimisations.")

st.success("✅ IES Files Generation Complete! (Placeholder logic)")
