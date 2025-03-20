import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v4.8")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === DEFAULT DATASET LOAD ===
default_excel_path = 'Linear_Data.xlsx'
if os.path.exists(default_excel_path):
    workbook = pd.ExcelFile(default_excel_path)
    st.session_state['dataset'] = {
        'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
        'LED_and_Board_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
        'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
        'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
    }
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Data Upload")

    uploaded_excel = st.file_uploader("Upload Data Excel", type=["xlsx"])
    if uploaded_excel:
        workbook = pd.ExcelFile(uploaded_excel)
        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_excel(workbook, 'LumCAT_Config'),
            'LED_and_Board_Config': pd.read_excel(workbook, 'LED_Chip_Config'),
            'ECG_Config': pd.read_excel(workbook, 'ECG_Config'),
            'Tier_Rules_Config': pd.read_excel(workbook, 'Tier_Rules_Config')
        }

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === PARSE FUNCTIONS ===
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

def corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix, symmetry_factor=4):
    vert_rad = np.radians(vertical_angles)
    delta_vert = np.diff(vert_rad)
    delta_vert = np.append(delta_vert, delta_vert[-1])

    symmetry_range_rad = np.radians(horizontal_angles[-1] - horizontal_angles[0])
    num_horz_segments = len(horizontal_angles)
    uniform_delta_horz = symmetry_range_rad / num_horz_segments

    total_flux = 0.0
    for h_idx in range(num_horz_segments):
        candela_row = candela_matrix[h_idx]
        for v_idx, cd in enumerate(candela_row):
            theta = vert_rad[v_idx]
            d_theta = delta_vert[v_idx]
            flux = cd * np.sin(theta) * d_theta * uniform_delta_horz
            total_flux += flux

    return round(total_flux * symmetry_factor, 1)

# === TIER LOOKUP FUNCTION ===
def get_tier_values():
    tier_rules = st.session_state['dataset']['Tier_Rules_Config']
    led_chip_config = st.session_state['dataset']['LED_and_Board_Config']

    tier_row_rules = tier_rules[tier_rules['Default'].astype(str).str.lower() == 'yes']
    led_chip_row = led_chip_config[led_chip_config['Default'].astype(str).str.lower() == 'yes']

    if tier_row_rules.empty or led_chip_row.empty:
        st.error("Default row not found in Tier_Rules_Config or LED_Chip_Config")
        return {}

    tier_row_rules = tier_row_rules.iloc[0]
    led_chip_row = led_chip_row.iloc[0]

    return {
        'Default Tier': tier_row_rules['Tier'],
        'Chip Name': led_chip_row['Chip_Name'],
        'Max LED Load (mA)': led_chip_row['Max_LED_Load_(mA)'],
        'Internal Code / TM30': led_chip_row['Internal_Code_TM30'],
        'Board Segment LED Pitch': tier_row_rules['Series_LED_Pitch_(mm)'],
        'LED Strip Voltage': led_chip_row['LED_Strip_Voltage_(SELV)']
    }

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content']
    )

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    tier_values = get_tier_values()

    if tier_values:
        actual_led_current_ma = round(
            (input_watts / tier_values['LED Strip Voltage']) /
            tier_values['Board Segment LED Pitch'] * 1000, 1
        )

        with st.expander("📏 Parameters + Metadata + Derived Values", expanded=False):
            meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

            st.markdown("#### IES Metadata")
            st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

            st.markdown("#### IES Parameters")
            photometric_table = [
                {"Description": "Lamps", "Value": f"{photometric_params[0]}"},
                {"Description": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
                {"Description": "Candela Mult.", "Value": f"{photometric_params[2]}"},
                {"Description": "Vert Angles", "Value": f"{photometric_params[3]}"},
                {"Description": "Horiz Angles", "Value": f"{photometric_params[4]}"},
                {"Description": "Photometric Type", "Value": f"{photometric_params[5]}"},
                {"Description": "Units Type", "Value": f"{photometric_params[6]}"},
                {"Description": "Width (m)", "Value": f"{photometric_params[7]}"},
                {"Description": "Length (m)", "Value": f"{photometric_params[8]}"},
                {"Description": "Height (m)", "Value": f"{photometric_params[9]}"},
                {"Description": "Ballast Factor", "Value": f"{photometric_params[10]}"},
                {"Description": "Future Use", "Value": f"{photometric_params[11]}"},
                {"Description": "Input Watts [F]", "Value": f"{photometric_params[12]}"}
            ]
            st.table(pd.DataFrame(photometric_table))

            st.markdown("#### IES Derived Values")
            base_values = [
                {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
                {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
                {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
                {"Description": "Default Tier / Chip", "LED Base": f"{tier_values['Default Tier']} / {tier_values['Chip Name']}"},
                {"Description": "Max LED Load (mA)", "LED Base": f"{tier_values['Max LED Load (mA)']:.1f}"},
                {"Description": "LED Pitch (mm)", "LED Base": f"{tier_values['Board Segment LED Pitch']:.1f}"},
                {"Description": "Actual LED Current (mA)", "LED Base": f"{actual_led_current_ma:.1f}"},
                {"Description": "TM30 Code", "LED Base": f"{tier_values['Internal Code / TM30']}"}
            ]
            st.table(pd.DataFrame(base_values))

# === FOOTER ===
st.caption("Version 4.8 - Unified Base Info + LumCAT Lookup + Customer Builder")
