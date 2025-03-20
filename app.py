import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5")

# === GOOGLE SHEET CONFIG ===
SHEET_KEY = '19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs'

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === GOOGLE SHEET AUTH ===
def load_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('gspread_creds.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SHEET_KEY)
    lumcat_data = pd.DataFrame(sheet.worksheet('LumCAT_Config').get_all_records())
    build_data = pd.DataFrame(sheet.worksheet('Build_Data').get_all_records())
    view_config = pd.DataFrame(sheet.worksheet('Customer_View_Config').get_all_records())

    st.session_state['dataset'] = {
        'LumCAT_Config': lumcat_data,
        'Build_Data': build_data,
        'Customer_View_Config': view_config
    }

# === INITIAL DATA LOAD ===
load_google_sheet()

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Upload IES File")
    uploaded_file = st.file_uploader("Upload IES file", type=["ies"])
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

# === LUMEN CALC FUNCTION ===
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

# === TOOLTIP FETCHER ===
def get_tooltip(label):
    tooltips = st.session_state['dataset']['Customer_View_Config']
    tip = tooltips[tooltips['Field'] == label]['Tooltip'].values
    return tip[0] if len(tip) > 0 else ""

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

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
            {"Description": "Input Watts", "Value": f"{photometric_params[12]}"}
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
        ]
        st.table(pd.DataFrame(base_values))

# === FOOTER ===
st.caption("Version 5 - Google Sheet Integrated + Unified Base Info")
