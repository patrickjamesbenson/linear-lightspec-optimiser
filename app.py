import streamlit as st
import pandas as pd
import numpy as np
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5 - Google Sheets Edition")

# === GOOGLE SHEETS CONNECTION ===
@st.cache_resource(show_spinner=False)
def load_google_sheet(sheet_url):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(sheet_url)
    return spreadsheet

sheet_url = "https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/edit"

try:
    spreadsheet = load_google_sheet(sheet_url)
    st.success("\u2705 Successfully loaded Google Sheets data")
    lumcat_sheet = spreadsheet.worksheet("LumCAT_Config")
    build_data_sheet = spreadsheet.worksheet("Build_Data")

    lumcat_df = pd.DataFrame(lumcat_sheet.get_all_records())
    build_data_df = pd.DataFrame(build_data_sheet.get_all_records())

    st.session_state['dataset'] = {
        'LumCAT_Config': lumcat_df,
        'Build_Data': build_data_df
    }
except Exception as e:
    st.error(f"\u274C Failed to load dataset: {e}")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("\ud83d\udcc4 Upload IES file", type=["ies"])
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

    meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

    st.markdown("#### IES Metadata")
    st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    st.markdown("#### IES Parameters")
    photometric_table = [
        {"Description": "Lamps", "Value": photometric_params[0]},
        {"Description": "Lumens/Lamp", "Value": photometric_params[1]},
        {"Description": "Candela Mult.", "Value": photometric_params[2]},
        {"Description": "Vert Angles", "Value": photometric_params[3]},
        {"Description": "Horiz Angles", "Value": photometric_params[4]},
        {"Description": "Photometric Type", "Value": photometric_params[5]},
        {"Description": "Units Type", "Value": photometric_params[6]},
        {"Description": "Width (m)", "Value": photometric_params[7]},
        {"Description": "Length (m)", "Value": photometric_params[8]},
        {"Description": "Height (m)", "Value": photometric_params[9]},
        {"Description": "Ballast Factor", "Value": photometric_params[10]},
        {"Description": "Future Use", "Value": photometric_params[11]},
        {"Description": "Input Watts [F]", "Value": photometric_params[12]}
    ]
    st.table(pd.DataFrame(photometric_table))

    st.markdown("#### IES Derived Values")
    base_values = [
        {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
        {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}"},
        {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}"},
    ]
    st.table(pd.DataFrame(base_values))

    # === LumCAT Lookup ===
    st.markdown("#### \ud83d\udd0e LumCAT Lookup")
    lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
    lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

    lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)

    if lumcat_input:
        parsed_codes = parse_lumcat(lumcat_input)
        if parsed_codes:
            lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
            if lumcat_desc:
                st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === FOOTER ===
st.caption("Version 5 - Google Sheets Connected - LumCAT Lookup - Customer Builder")
