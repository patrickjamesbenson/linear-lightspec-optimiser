import streamlit as st
import pandas as pd
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = True
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = 'Current Generation'
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")
    st.session_state['uploaded_files'] = {}  # Holds all IES files
    st.session_state['active_file'] = None   # Active file key

# === BASE FILE UPLOAD (TOP) ===
st.header("Upload Base IES File")
base_uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if base_uploaded_file:
    file_content = base_uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === Add to uploaded_files if not already ===
    base_file_key = f"{base_uploaded_file.name}_{datetime.now().strftime('%H%M%S')}"
    st.session_state['uploaded_files'][base_file_key] = {
        'name': base_uploaded_file.name,
        'content': file_content,
        'parsed': parsed,
        'export_id': datetime.now().strftime("%Y%m%d%H%M%S")
    }

    # Auto-set the first uploaded file as active if none selected
    if not st.session_state['active_file']:
        st.session_state['active_file'] = base_file_key

# === DESIGN OPTIMISATION SECTION ===
st.markdown("## 🔧 Design Optimisation: Upload Alternative IES Files")

alt_uploaded_files = st.file_uploader("Upload Additional IES Files", type=["ies"], accept_multiple_files=True)

if alt_uploaded_files:
    for file in alt_uploaded_files:
        content = file.read().decode('utf-8')
        parsed = parse_ies_file(content)
        key = f"{file.name}_{datetime.now().strftime('%H%M%S')}"

        st.session_state['uploaded_files'][key] = {
            'name': file.name,
            'content': content,
            'parsed': parsed,
            'export_id': datetime.now().strftime("%Y%m%d%H%M%S")
        }

# === DISPLAY FILES TABLE WITH RADIO BUTTONS ===
st.markdown("### Uploaded IES Files for Comparison & Selection")

if st.session_state['uploaded_files']:
    files_df_data = []
    for key, data in st.session_state['uploaded_files'].items():
        parsed = data['parsed']
        # For lm/W: simplistic from static values (replace with parsed values if available)
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        lm_per_w = round(base_lm_per_m / base_w_per_m, 1)

        files_df_data.append({
            'File Key': key,
            'File Name': data['name'],
            'lm/W': lm_per_w,
            'Export ID': data['export_id'],
            'Active': key == st.session_state['active_file']
        })

    files_df = pd.DataFrame(files_df_data)

    for i, row in files_df.iterrows():
        cols = st.columns([4, 2, 3, 2, 1])

        cols[0].write(row['File Name'])
        cols[1].write(f"{row['lm/W']} lm/W")
        cols[2].write(row['Export ID'])

        if cols[3].radio("Active?", options=[True, False], index=int(row['Active']), key=f"radio_{i}"):
            st.session_state['active_file'] = row['File Key']

# === ACTIVE FILE LOGIC ===
active_file_data = st.session_state['uploaded_files'].get(st.session_state['active_file'])

if not active_file_data:
    st.warning("Please upload and select at least one IES file to proceed.")
    st.stop()

# === BASE FILE SUMMARY ===
parsed = active_file_data['parsed']
luminaire_info = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), "[LUMINAIRE] Not Found")
luminaire_name_base = luminaire_info.replace("[LUMINAIRE]", "").strip()

# === Extract CRI & CCT ===
cri_value = "N/A"
cct_value = "N/A"
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
        st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
    else:
        st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
        st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=5.5, step=0.1)
        st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=56.0, step=0.1)

# === SELECT LENGTHS ===
st.markdown("## Select Lengths")
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
        lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

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

    header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
    headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    for idx, row in enumerate(table_rows):
        row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

        if row_cols[0].button("🗑️", key=f"delete_{idx}"):
            st.session_state['lengths_list'].pop(idx)
            st.rerun()

        row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                    row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

        for col, val in zip(row_cols[1:], row_data):
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

    st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'),
                       file_name="Selected_Lengths_Summary.csv", mime="text/csv")

else:
    st.info("No lengths selected yet. Click buttons above to add.")

# === GENERATE IES FILES WITH CONFIRMATION ===
st.markdown("## Generate Optimised IES Files")

if st.session_state['lengths_list']:

    confirm = st.checkbox(f"✅ Confirm generation of files for: {active_file_data['name']} (Export ID: {active_file_data['export_id']})")

    if confirm and st.button("Generate IES Files & Download ZIP"):
        files_to_zip = {}

        for length in st.session_state['lengths_list']:
            scaled_data = modify_candela_data(parsed['data'], 1.0)

            updated_header = []
            for line in parsed['header']:
                if line.startswith("[TEST]"):
                    updated_header.append(f"[TEST] Export ID: {active_file_data['export_id']}")
                else:
                    updated_header.append(line)

            filename = f"{luminaire_name_base}_{length:.3f}m.ies"
            new_file = create_ies_file(updated_header, scaled_data)
            files_to_zip[filename] = new_file

        zip_buffer = create_zip(files_to_zip)

        st.download_button("Download Optimised IES Files ZIP", data=zip_buffer,
                           file_name="Optimised_IES_Files.zip", mime="application/zip")

        # Clean up other files not selected
        st.session_state['uploaded_files'] = {st.session_state['active_file']: active_file_data}

else:
    st.info("Select at least one length to enable IES generation.")
