import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from urllib.parse import quote

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5 - Google Sheets Edition")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === GOOGLE SHEETS CONFIG ===
SHEET_ID = "19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs"
BUILD_DATA_SHEET = "Build_Data"
LUMCAT_CONFIG_SHEET = "LumCAT_Config"

# === DATASET LOAD FUNCTION ===
def load_dataset():
    try:
        base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
        build_data_url = base_url + quote(BUILD_DATA_SHEET)
        lumcat_config_url = base_url + quote(LUMCAT_CONFIG_SHEET)
        
        build_data_df = pd.read_csv(build_data_url)
        lumcat_config_df = pd.read_csv(lumcat_config_url)

        st.session_state['dataset'] = {
            'Build_Data': build_data_df,
            'LumCAT_Config': lumcat_config_df
        }
        st.success("✅ Successfully loaded Google Sheets data")
    except Exception as e:
        st.error(f"❌ Failed to load dataset: {e}")

load_dataset()

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
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

# === SIMPLE LUMEN CALC ===
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

# === DISPLAY IES DATA ===
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

    with st.expander("📏 Parameters + Metadata + Derived Values", expanded=True):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### IES Parameters")
        photometric_table = [
            {"Description": "Lamps", "Value": f"{photometric_params[0]}"},
            {"Description": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
            {"Description": "Input Watts [F]", "Value": f"{photometric_params[12]}"},
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}"},
        ]
        st.table(pd.DataFrame(base_values))

# === LUMCAT LOOKUP ===
def parse_lumcat(lumcat_code):
    try:
        range_code, rest = lumcat_code.split('-')
        parsed = {
            "Range": range_code,
            "Option Code": rest[0:2],
            "Diffuser Code": rest[2:4],
            "Wiring Code": rest[4],
            "Driver Code": rest[5:7],
            "Lumens Code": rest[7:10],
            "CRI Code": rest[10:12],
            "CCT Code": rest[12:14],
        }
        parsed['Lumens Derived Display'] = round(float(parsed["Lumens Code"]) * 10, 1)
        return parsed
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

    matrix_df.columns = matrix_df.columns.str.strip()
    parsed_codes['CRI Code'] = str(parsed_codes['CRI Code']).strip()
    parsed_codes['CCT Code'] = str(parsed_codes['CCT Code']).strip()

    result = {}
    result['Range'] = parsed_codes['Range']

    option_match = matrix_df.loc[matrix_df['Option Code'] == parsed_codes['Option Code']]
    diffuser_match = matrix_df.loc[matrix_df['Diffuser / Louvre Code'] == parsed_codes['Diffuser Code']]
    wiring_match = matrix_df.loc[matrix_df['Wiring Code'] == parsed_codes['Wiring Code']]
    driver_match = matrix_df.loc[matrix_df['Driver Code'] == parsed_codes['Driver Code']]
    cri_match = matrix_df.loc[matrix_df['CRI Code'] == parsed_codes['CRI Code']]
    cct_match = matrix_df.loc[matrix_df['CCT/Colour Code'] == parsed_codes['CCT Code']]

    result['Option Description'] = option_match['Option Description'].values[0] if not option_match.empty else "⚠️ Not Found"
    result['Diffuser Description'] = diffuser_match['Diffuser / Louvre Description'].values[0] if not diffuser_match.empty else "⚠️ Not Found"
    result['Wiring Description'] = wiring_match['Wiring Description'].values[0] if not wiring_match.empty else "⚠️ Not Found"
    result['Driver Description'] = driver_match['Driver Description'].values[0] if not driver_match.empty else "⚠️ Not Found"
    result['Lumens (Display Only)'] = f"{parsed_codes['Lumens Derived Display']} lm"
    result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
    result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

    return result

# === LUMCAT INPUT ===
if 'dataset' in st.session_state and 'LumCAT_Config' in st.session_state['dataset']:
    lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
    lumcat_input = st.text_input("Enter LumCAT Code", value="")

    if lumcat_input:
        parsed_codes = parse_lumcat(lumcat_input)
        if parsed_codes:
            lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
            if lumcat_desc:
                st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === FOOTER ===
st.caption("Version 5 - Google Sheets Connected - LumCAT Lookup - Customer Builder Ready")
