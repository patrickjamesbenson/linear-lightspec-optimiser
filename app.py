import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

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
GOOGLE_SHEET_ID = '19r5hWEnQtBIGphGhpQhsXgPVWT2TJ1jWYjbDphNzFMs'

# === LOAD DATASET FROM GOOGLE SHEETS ===
def load_google_sheet_data():
    try:
        lumcat_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=LumCAT_Config'
        build_data_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Build_Data'
        view_config_url = f'https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Customer_View_Config'

        st.session_state['dataset'] = {
            'LumCAT_Config': pd.read_csv(lumcat_url),
            'Build_Data': pd.read_csv(build_data_url),
            'Customer_View_Config': pd.read_csv(view_config_url)
        }
        st.success("✅ Successfully loaded Google Sheets data")
    except Exception as e:
        st.error(f"❌ Failed to load dataset: {e}")

load_google_sheet_data()

# === HELPER FUNCTION: TOOLTIP LOOKUP ===
def get_tooltip(field):
    tooltips_df = st.session_state['dataset'].get('Customer_View_Config')
    if tooltips_df is not None:
        if 'Field' in tooltips_df.columns and 'Tooltip' in tooltips_df.columns:
            match = tooltips_df[tooltips_df['Field'].str.strip() == field.strip()]
            if not match.empty:
                return match['Tooltip'].values[0]
    return ""

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === PARSE IES FILE ===
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

# === LUMEN CALCULATION ===
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

# === LUMCAT PARSE FUNCTION ===
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
            "CCT Code": rest[12:14]
        }
        parsed['Lumens Derived Display'] = round(float(parsed["Lumens Code"]) * 10, 1)
        return parsed
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

# === LUMCAT LOOKUP FUNCTION ===
def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

    matrix_df.columns = matrix_df.columns.str.strip()
    matrix_df['CRI Code'] = matrix_df['CRI Code'].astype(str).str.strip()
    matrix_df['CCT/Colour Code'] = matrix_df['CCT/Colour Code'].astype(str).str.strip()

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

    build_data = st.session_state['dataset']['Build_Data']
    if 'Description' in build_data.columns:
        build_data = build_data.set_index('Description')
    else:
        st.error("The 'Description' column is missing in Build_Data")

    default_tier = 'V1'  # You can adjust based on user selection later

    with st.expander("📏 Parameters + Metadata + Derived Values", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### IES Parameters")
        photometric_table = [
                        {"Description": "Lamps", "Value": f"{photometric_params[0]}", "Tooltip": get_tooltip("Lamps")},
            {"Description": "Lumens/Lamp", "Value": f"{photometric_params[1]}", "Tooltip": get_tooltip("Lumens/Lamp")},
            {"Description": "Candela Mult.", "Value": f"{photometric_params[2]}", "Tooltip": get_tooltip("Candela Mult.")},
            {"Description": "Vert Angles", "Value": f"{photometric_params[3]}", "Tooltip": get_tooltip("Vert Angles")},
            {"Description": "Horiz Angles", "Value": f"{photometric_params[4]}", "Tooltip": get_tooltip("Horiz Angles")},
            {"Description": "Photometric Type", "Value": f"{photometric_params[5]}", "Tooltip": get_tooltip("Photometric Type")},
            {"Description": "Units Type", "Value": f"{photometric_params[6]}", "Tooltip": get_tooltip("Units Type")},
            {"Description": "Width (m)", "Value": f"{photometric_params[7]}", "Tooltip": get_tooltip("Width (m)")},
            {"Description": "Length (m)", "Value": f"{photometric_params[8]}", "Tooltip": get_tooltip("Length (m)")},
            {"Description": "Height (m)", "Value": f"{photometric_params[9]}", "Tooltip": get_tooltip("Height (m)")},
            {"Description": "Ballast Factor", "Value": f"{photometric_params[10]}", "Tooltip": get_tooltip("Ballast Factor")},
            {"Description": "Future Use", "Value": f"{photometric_params[11]}", "Tooltip": get_tooltip("Future Use")},
            {"Description": "Input Watts [F]", "Value": f"{photometric_params[12]}", "Tooltip": get_tooltip("Input Watts [F]")},
        ]
        st.table(pd.DataFrame(photometric_table))

        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}", "Tooltip": get_tooltip("Total Lumens")},
            {"Description": "Efficacy (lm/W)", "Value": f"{base_lm_per_watt:.1f}", "Tooltip": get_tooltip("Efficacy (lm/W) ")},
            {"Description": "Lumens per Meter", "Value": f"{base_lm_per_m:.1f}", "Tooltip": get_tooltip("Lumens per Meter")},
            {"Description": "Default Tier / Chip", "Value": f"Core / {build_data.loc['Chip_Name', default_tier]}", "Tooltip": get_tooltip("Default Tier / Chip")},
            {"Description": "Max LED Load (mA)", "Value": f"{build_data.loc['LED_Load_(mA)', default_tier]:.1f}", "Tooltip": get_tooltip("Max LED Load (mA)")},
            {"Description": "LED Pitch (mm)", "Value": f"{build_data.loc['LED_Group_Pitch_(mm)', default_tier]:.1f}", "Tooltip": get_tooltip("LED Pitch (mm)")},
            {"Description": "Actual LED Current (mA)", "Value": f"{(input_watts / build_data.loc['Vf_(Volts)', default_tier]) * 1000:.1f}", "Tooltip": get_tooltip("Actual LED Current (mA)")},
            {"Description": "TM30 Code", "Value": f"{build_data.loc['TM30-report_No.', default_tier]}", "Tooltip": get_tooltip("TM30 Code")}
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

# === FOOTER ===
st.caption("Version 5 - Google Sheets Connected - Tooltips Added")
