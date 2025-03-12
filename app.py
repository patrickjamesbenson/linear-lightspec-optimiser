import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INIT ===
if 'lengths_list' not in st.session_state:
    st.session_state['lengths_list'] = []
if 'led_pitch' not in st.session_state:
    st.session_state['led_pitch'] = 56.0
if 'end_plate_thickness' not in st.session_state:
    st.session_state['end_plate_thickness'] = 5.5
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
if 'led_efficiency_gain_percent' not in st.session_state:
    st.session_state['led_efficiency_gain_percent'] = 0.0
if 'efficiency_reason' not in st.session_state:
    st.session_state['efficiency_reason'] = 'Current Generation'
if 'export_id' not in st.session_state:
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
st.markdown("## Upload IES Files")
uploaded_files = st.file_uploader("Upload one or more IES files", type=["ies"], accept_multiple_files=True)

if uploaded_files:
    files_data = []
    
    # Parse each uploaded file
    for uploaded_file in uploaded_files:
        file_content = uploaded_file.read().decode('utf-8')
        parsed = parse_ies_file(file_content)

        # Get basic luminaire info for display
        luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
        luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

        # Extract CRI / CCT
        cri_value = "N/A"
        cct_value = "N/A"
        if luminaire_name_base != "Not Found":
            parts = luminaire_name_base.split('-')
            if len(parts) >= 3:
                cri_value = parts[-2].strip()
                cct_value = parts[-1].strip()

        # Placeholder lumens/watt - can be parsed or calculated later
        base_lm_per_w = 34.5
        
        files_data.append({
            'name': uploaded_file.name,
            'parsed': parsed,
            'luminaire_name': luminaire_name_base,
            'cri': cri_value,
            'cct': cct_value,
            'lm_w': base_lm_per_w,
            'timestamp': datetime.now().strftime("%Y%m%d%H%M%S")
        })

    # Store parsed files in session state
    st.session_state['uploaded_files_data'] = files_data

if 'uploaded_files_data' in st.session_state:
    st.markdown("### Uploaded IES Files")
    
    for idx, file_data in enumerate(st.session_state['uploaded_files_data']):
        col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 2, 2])
        with col1:
            st.write(file_data['name'])
        with col2:
            st.write(file_data['lm_w'], "lm/W")
        with col3:
            st.write(file_data['cri'])
        with col4:
            st.write(file_data['cct'])
        with col5:
            activate = st.button("Select", key=f"select_{idx}")
            if activate:
                st.session_state['active_file'] = idx
                st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
                st.success(f"{file_data['name']} selected as active base file.")

# === ACTIVE FILE CHECK ===
if 'active_file' not in st.session_state:
    st.warning("⚠️ Please select an active IES file to proceed.")
    st.stop()

active_file_data = st.session_state['uploaded_files_data'][st.session_state['active_file']]
parsed = active_file_data['parsed']
luminaire_name_base = active_file_data['luminaire_name']
cri_value = active_file_data['cri']
cct_value = active_file_data['cct']
base_lm_per_m = 400.0
base_w_per_m = 11.6

# === BASE FILE SUMMARY ===
with st.expander("📂 Base File Summary", expanded=False):
    st.write(f"**Luminaire:** {luminaire_name_base}")
    st.write(f"**CRI:** {cri_value} | **CCT:** {cct_value}")
    st.write(f"**Lm/W:** {active_file_data['lm_w']}")

# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    if st.session_state['lengths_list']:
        st.info("🔒 Locked: Base Build cannot be edited once lengths are added.")
    else:
        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build"):
                st.session_state['locked'] = False
        else:
            if st.button("🔒 Lock Base Build"):
                st.session_state['locked'] = True

        if not st.session_state['locked']:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", value=st.session_state['led_pitch'], step=0.1)

# === SELECT LENGTHS ===
st.markdown("## Select Lengths")
desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.001)
desired_length_mm = desired_length_m * 1000

min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
max_length_mm = min_length_mm + st.session_state['led_pitch']

shorter_length_m = round(min_length_mm / 1000, 3)
longer_length_m = round(max_length_mm / 1000, 3)

if st.button(f"Add Shorter Buildable Length: {shorter_length_m} m"):
    st.session_state['lengths_list'].append(shorter_length_m)

if st.button(f"Add Longer Buildable Length: {longer_length_m} m"):
    st.session_state['lengths_list'].append(longer_length_m)

# === LED CHIPSET ADJUSTMENT ===
with st.expander("💡 LED Chipset Adjustment", expanded=False):
    led_efficiency_gain_percent = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state.get('led_efficiency_gain_percent', 0.0))
    efficiency_reason = st.text_input("Reason for adjustment", value=st.session_state.get('efficiency_reason', 'Current Generation'))

    if led_efficiency_gain_percent != 0 and efficiency_reason.strip() == "":
        st.error("⚠️ You must provide a reason for the adjustment.")
        st.stop()

    st.session_state['led_efficiency_gain_percent'] = led_efficiency_gain_percent
    st.session_state['efficiency_reason'] = efficiency_reason

# === SELECTED LENGTHS TABLE ===
st.markdown("## 📏 Selected Lengths for IES Generation")

if st.session_state['lengths_list']:
    st.markdown(f"### Export ID: {st.session_state['export_id']}")
    table_rows = []
    efficiency_multiplier = 1 - (led_efficiency_gain_percent / 100.0)
    new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
    new_lm_per_m = base_lm_per_m
    for length in st.session_state['lengths_list']:
        total_lumens = round(new_lm_per_m * length, 1)
        total_watts = round(new_w_per_m * length, 1)
        lm_per_w = round(total_lumens / total_watts, 1)

        if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0:
            tier = "Bespoke"
        elif led_efficiency_gain_percent != 0:
            tier = "Professional"
        elif st.session_state['led_pitch'] % 4 != 0:
            tier = "Advanced"
        else:
            tier = "Core"

        luminaire_file_name = f"{luminaire_name_base}_{length:.3f}m_{tier}"

        table_rows.append({
            "Length (m)": length,
            "Luminaire & IES File Name": luminaire_file_name,
            "CRI": cri_value,
            "CCT": cct_value,
            "Total Lumens": total_lumens,
            "Total Watts": total_watts,
            "Settings lm/W": lm_per_w,
            "Comments": efficiency_reason if led_efficiency_gain_percent != 0 else ""
        })

    df = pd.DataFrame(table_rows)
    st.table(df)

    st.download_button("Download CSV Summary", data=df.to_csv(index=False).encode('utf-8'), file_name="Selected_Lengths_Summary.csv", mime="text/csv")

# === GENERATE IES FILES ===
st.markdown("## Generate Optimised IES Files")

if st.session_state['lengths_list']:
    files_to_zip = {}

    for length in st.session_state['lengths_list']:
        scaled_data = modify_candela_data(parsed['data'], 1.0)

        # Add export ID to [TEST]
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
    st.info("No lengths selected yet. Add lengths before generating IES files.")

