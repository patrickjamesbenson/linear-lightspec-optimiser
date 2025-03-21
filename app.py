import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5 - Google Sheets Integration")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}
if 'customer_entries' not in st.session_state:
    st.session_state['customer_entries'] = []

# === GOOGLE SHEET CONFIGURATION ===
GOOGLE_SHEET_CSV_URLS = {
    'LumCAT_Config': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=0',
    'Build_Data': 'https://docs.google.com/spreadsheets/d/19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs/export?format=csv&gid=123456' # replace gid with actual
}

# === DEFAULT DATASET LOAD ===
def load_dataset():
    try:
        st.session_state['dataset'] = {
            name: pd.read_csv(url)
            for name, url in GOOGLE_SHEET_CSV_URLS.items()
        }
        st.success("✅ Data loaded from Google Sheets")
    except Exception as e:
        st.error(f"❌ Failed to load dataset: {e}")

load_dataset()

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

# === TOOLTIP LOOKUP ===
def get_tooltip(field):
    config_df = st.session_state['dataset'].get('Customer_View_Config', pd.DataFrame())
    if config_df.empty:
        return ""
    row = config_df[config_df['Field'] == field]
    return row['Tooltip'].values[0] if not row.empty else ""

# === LUMCAT PARSE FUNCTIONS ===
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
            {"Description": "Input Watts [F]", "Value": f"{photometric_params[12]}"}
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}"}
        ]
        st.table(pd.DataFrame(base_values))

        st.markdown("#### 🔎 LumCAT Lookup")
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
    tier_selection = st.selectbox("Select Tier", ["Core", "Professional", "Advanced"])
    length_input = st.number_input("Enter Required Length (mm)", min_value=280, step=10)
    notes_input = st.text_input("Notes (e.g., Room Name, Mounting Type)")
    submitted = st.form_submit_button("Add to Table")

    if submitted:
        new_entry = {
            'Luminaire Name': luminaire_name,
            'Tier': tier_selection,
            'Selected Length (mm)': length_input,
            'Notes': notes_input,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state['customer_entries'].append(new_entry)
        st.success("Luminaire added to table.")

st.markdown("### Current Luminaire Selections")
if st.session_state['customer_entries']:
    customer_df = pd.DataFrame(st.session_state['customer_entries'])
    st.dataframe(customer_df)

    csv = customer_df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"luminaire_selections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.info("No luminaires added yet.")

# === FOOTER ===
st.caption("Version 5 - Google Sheets + Unified Base Info + LumCAT Lookup + Customer Builder")
