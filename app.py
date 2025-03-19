import streamlit as st
import pandas as pd
import numpy as np
import time
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 Clean ✅")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}

# === LOAD DATASET FUNCTION ===
def load_dataset(file_path):
    try:
        xls = pd.ExcelFile(file_path)
        st.session_state['dataset']['LumCAT_Config'] = pd.read_excel(xls, 'LumCAT_Config')
        st.session_state['dataset']['LED_and_Board_Config'] = pd.read_excel(xls, 'LED_and_Board_Config')
        st.session_state['dataset']['ECG_Config'] = pd.read_excel(xls, 'ECG_Config')
        st.success("✅ Dataset loaded successfully!")
    except Exception as e:
        st.error(f"❌ Error loading Excel: {e}")

# === DEFAULT DATASET AUTO-LOAD ===
default_dataset_path = 'Linear_Lightspec_Data.xlsx'
if os.path.exists(default_dataset_path):
    load_dataset(default_dataset_path)
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR: DATASET UPLOAD ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")
    dataset_file = st.file_uploader("Upload Dataset Excel (Recommended: Linear_Lightspec_Data.xlsx)", type=["xlsx"])
    if dataset_file:
        load_dataset(dataset_file)

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"{uploaded_file.name} uploaded!")

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
        ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    # === DISPLAY ===
    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=True):
        # Metadata
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # Photometric Parameters
        st.markdown("#### Photometric Parameters")
        photometric_data = [
            {"Param [A]": "Lamps", "Value": photometric_params[0]},
            {"Param [B]": "Lumens/Lamp", "Value": photometric_params[1]},
            {"Param [C]": "Candela Mult.", "Value": photometric_params[2]},
            {"Param [D]": "Vert Angles", "Value": photometric_params[3]},
            {"Param [E]": "Horiz Angles", "Value": photometric_params[4]},
            {"Param [F]": "Photometric Type", "Value": photometric_params[5]},
            {"Param [G]": "Units Type", "Value": photometric_params[6]},
            {"Param [H]": "Width (m)", "Value": photometric_params[7]},
            {"Param [I]": "Length (m)", "Value": photometric_params[8]},
            {"Param [J]": "Height (m)", "Value": photometric_params[9]},
            {"Param [K]": "Ballast Factor", "Value": photometric_params[10]},
            {"Param [L]": "Future Use", "Value": photometric_params[11]},
            {"Param [M]": "Input Watts [F]", "Value": photometric_params[12]}
        ]
        st.table(pd.DataFrame(photometric_data))

        # Base Values
        st.markdown("#### Base Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Base LED Chip", "LED Base": "G1 (Gen1 Spec: TM30 Report XXX)"},
            {"Description": "Base Design", "LED Base": "6S/4P/14.4W/280mm/400mA/G1/DR12w"}
        ]
        st.table(pd.DataFrame(base_values))

    # === LUMCAT REVERSE LOOKUP ===
    st.markdown("🔎 LumCAT Reverse Lookup (Matrix)")

    def parse_lumcat(lumcat_code):
        try:
            range_code, rest = lumcat_code.split('-')
            option_code = rest[0:2]
            diffuser_code = rest[2:4]
            wiring_code = rest[4]
            driver_code = rest[5:7]
            lumens_code = rest[7:10]
            cri_code = rest[10:12]
            cct_code = rest[12:14]
            lumens_derived = round(float(lumens_code) * 10, 1)

            return {
                "Range": range_code,
                "Option Code": option_code,
                "Diffuser Code": diffuser_code,
                "Wiring Code": wiring_code,
                "Driver Code": driver_code,
                "Lumens (Derived)": lumens_derived,
                "CRI Code": cri_code,
                "CCT Code": cct_code
            }
        except Exception as e:
            st.error(f"Error parsing LUMCAT: {e}")
            return None

    def lookup_lumcat_descriptions(parsed_codes, matrix_df):
        if matrix_df.empty or parsed_codes is None:
            return None

        result = {}

        option_match = matrix_df.loc[matrix_df['Option Code'] == parsed_codes['Option Code']]
        diffuser_match = matrix_df.loc[matrix_df['Diffuser / Louvre Code'] == parsed_codes['Diffuser Code']]
        wiring_match = matrix_df.loc[matrix_df['Wiring Code'] == parsed_codes['Wiring Code']]
        driver_match = matrix_df.loc[matrix_df['Driver Code'] == parsed_codes['Driver Code']]
        cri_match = matrix_df.loc[matrix_df['CRI Code'] == parsed_codes['CRI Code']]
        cct_match = matrix_df.loc[matrix_df['CCT/Colour Code'] == parsed_codes['CCT Code']]

        result['Range'] = parsed_codes['Range']
        result['Option Description'] = option_match['Option Description'].values[0] if not option_match.empty else "⚠️ Not Found"
        result['Diffuser Description'] = diffuser_match['Diffuser / Louvre Description'].values[0] if not diffuser_match.empty else "⚠️ Not Found"
        result['Wiring Description'] = wiring_match['Wiring Description'].values[0] if not wiring_match.empty else "⚠️ Not Found"
        result['Driver Description'] = driver_match['Driver Description'].values[0] if not driver_match.empty else "⚠️ Not Found"
        result['Lumens (Derived)'] = parsed_codes['Lumens (Derived)']
        result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
        result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

        return result

    lumcat_input = st.text_input("Enter LumCAT Code", value="B852-BSA3AAA1488030ZZ")
    parsed_codes = parse_lumcat(lumcat_input)
    lumcat_desc = lookup_lumcat_descriptions(parsed_codes, st.session_state['dataset']['LumCAT_Config'])

    if lumcat_desc:
        st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

# === FOOTER ===
st.caption("Version 4.7 Clean - Dataset Excel Integration ✅")
