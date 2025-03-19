import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 ✅")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}

# === DEFAULT DATASET LOAD ===
default_excel_path = 'Linear_Lightspec_Data.xlsx'
if os.path.exists(default_excel_path):
    workbook = pd.ExcelFile(default_excel_path)
    st.session_state['dataset'] = {
        'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
        'LED_and_Board_Config': pd.read_excel(workbook, 'LED_and_Board_Config'),
        'ECG_Config': pd.read_excel(workbook, 'ECG_Config')
    }
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")

    uploaded_excel = st.file_uploader("Upload Dataset Excel", type=["xlsx"])
    if uploaded_excel:
        workbook = pd.ExcelFile(uploaded_excel)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_and_Board_Config': pd.read_excel(workbook, 'LED_and_Board_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config')
        }

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === PARSE IES FUNCTION ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    header_lines, data_lines = [], []
    reading_data = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            reading_data = True
        elif not reading_data:
            header_lines.append(stripped)
        else:
            data_lines.append(stripped)

    photometric_raw = " ".join(data_lines[:2]).split()
    photometric_params = [float(x) if '.' in x or 'e' in x.lower() else int(x) for x in photometric_raw]
    n_vert = int(photometric_params[3])
    n_horz = int(photometric_params[4])

    remaining_data = " ".join(data_lines[2:]).split()
    vertical_angles = [float(x) for x in remaining_data[:n_vert]]
    horizontal_angles = [float(x) for x in remaining_data[n_vert:n_vert + n_horz]]

    candela_values = remaining_data[n_vert + n_horz:]
    candela_matrix = []
    idx = 0
    for _ in range(n_horz):
        row = [float(candela_values[idx + i]) for i in range(n_vert)]
        candela_matrix.append(row)
        idx += n_vert

    return header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content'])

    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=True):
        # === IES Metadata ===
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # === Photometric Parameters ===
        st.markdown("#### Photometric Parameters")
        photometric_table = [
            {"Description": "Lamps", "Value": round(photometric_params[0], 1)},
            {"Description": "Lumens/Lamp", "Value": round(photometric_params[1], 1)},
            {"Description": "Candela Mult.", "Value": round(photometric_params[2], 1)},
            {"Description": "Vert Angles", "Value": round(photometric_params[3], 1)},
            {"Description": "Horiz Angles", "Value": round(photometric_params[4], 1)},
            {"Description": "Photometric Type", "Value": round(photometric_params[5], 1)},
            {"Description": "Units Type", "Value": round(photometric_params[6], 1)},
            {"Description": "Width (m)", "Value": round(photometric_params[7], 1)},
            {"Description": "Length (m)", "Value": round(photometric_params[8], 1)},
            {"Description": "Height (m)", "Value": round(photometric_params[9], 1)},
            {"Description": "Ballast Factor", "Value": round(photometric_params[10], 1)},
            {"Description": "Future Use", "Value": round(photometric_params[11], 1)},
            {"Description": "Input Watts [F]", "Value": round(photometric_params[12], 1)}
        ]
        st.table(pd.DataFrame(photometric_table).style.format({'Value': '{:.1f}'}))

# === Base Values ===
st.markdown("#### Base Values")

# Pull default LED and board configuration
default_led_df = st.session_state['dataset']['LED_and_Board_Config']
default_led = default_led_df.iloc[0]

# Extract fields
default_tier = default_led['Default Tier']
chip_name = default_led['Chip Name']
max_led_load_ma = default_led['Max LED Load (mA)']
internal_code_tm30 = default_led['Internal Code / TM30']

# Actual LED current calculation
input_watts = round(photometric_params[12], 1)
length_m = round(photometric_params[8], 1)
led_pitch_mm = default_led['LED Pitch (mm)']
actual_led_current_ma = round((input_watts / length_m) * (led_pitch_mm / 1000), 1)

base_values = [
    {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
    {"Description": "Efficacy (lm/W)", "LED Base": f"{calculated_lumens / input_watts:.1f}"},
    {"Description": "Lumens per Meter", "LED Base": f"{calculated_lumens / length_m:.1f}"},
    {"Description": "Default Tier", "LED Base": default_tier},
    {"Description": "Chip Name", "LED Base": chip_name},
    {"Description": "Internal Code / TM30", "LED Base": internal_code_tm30},
    {"Description": "Max LED Load (mA)", "LED Base": f"{max_led_load_ma:.1f}"},
    {"Description": "Actual LED Current (mA)", "LED Base": f"{actual_led_current_ma:.1f}"}
]

st.table(pd.DataFrame(base_values))

# === FOOTER ===
st.caption("Version 4.7 Clean ✅ - Dataset Upload + Unified Base Info")
