import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from gsheetsdb import connect

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === GOOGLE SHEETS CONNECTION ===
connect_url = 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/edit?usp=sharing'
conn = connect()

@st.cache_data(ttl=600)
def load_google_sheet(query):
    rows = conn.execute(query, headers=1)
    return pd.DataFrame(rows)

# === LOAD DATA FROM GOOGLE SHEET ===
def load_dataset():
    st.session_state['dataset'] = {
        'LumCAT_Config': load_google_sheet(f'SELECT * FROM "{connect_url}" WHERE A = "LumCAT_Config"'),
        'Build_Data': load_google_sheet(f'SELECT * FROM "{connect_url}" WHERE A = "Build_Data"'),
        'Customer_View_Config': load_google_sheet(f'SELECT * FROM "{connect_url}" WHERE A = "Customer_View_Config"')
    }

load_dataset()

# === TOOLTIP HELPER ===
def get_tooltip(field_name):
    df = st.session_state['dataset']['Customer_View_Config']
    if field_name in df['Field'].values:
        return df.loc[df['Field'] == field_name, 'Tooltip'].values[0]
    return ""

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

    st.markdown("### 📏 Parameters + Metadata + Derived Values")
    meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
    st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    photometric_table = [
        {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
        {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}"},
        {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}"},
        {"Description": "Input Watts [F]", "Value": f"{input_watts:.1f}"}
    ]
    st.table(pd.DataFrame(photometric_table))

    st.markdown("### 🔎 LumCAT Lookup")
    lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
    lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

    lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)

    if lumcat_input:
        parsed_codes = parse_lumcat(lumcat_input)
        if parsed_codes:
            lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
            if lumcat_desc:
                st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === CUSTOMER LUMINAIRE BUILDER ===
st.subheader("🔨 Customer Luminaire Builder")

with st.form("luminaire_entry_form"):
    luminaire_name = st.text_input("Luminaire Name")
    length_input = st.number_input("Enter Required Length (mm)", min_value=280, step=10)
    notes_input = st.text_input("Notes (e.g., Room Name, Mounting Type)")
    submitted = st.form_submit_button("Compare Tiers")

    if submitted:
        # Placeholder: compare_tiers(length_input)
        st.success("Comparison table generated. Select Tier to proceed.")

# === FOOTER ===
st.caption("Version 5 - Google Sheets + Unified Dataset + Customer Builder")
