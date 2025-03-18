import streamlit as st
import pandas as pd
import numpy as np
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser v4.7 Clean")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'led_chips' not in st.session_state:
    st.session_state['led_chips'] = pd.DataFrame()
if 'led_boards' not in st.session_state:
    st.session_state['led_boards'] = pd.DataFrame()
if 'ecg_drivers' not in st.session_state:
    st.session_state['ecg_drivers'] = pd.DataFrame()

# === FUNCTION TO LOAD EXCEL ===
def load_excel_file(file_path):
    try:
        xl = pd.ExcelFile(file_path)
        st.session_state['matrix_lookup'] = xl.parse(xl.sheet_names[0])
        st.session_state['led_chips'] = xl.parse(xl.sheet_names[1])
        st.session_state['led_boards'] = xl.parse(xl.sheet_names[2])
        st.session_state['ecg_drivers'] = xl.parse(xl.sheet_names[3])
        return True
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return False

# === DEFAULT DATA LOAD ===
default_excel_path = "Linear_Lightspec_Data.xlsx"
if os.path.exists(default_excel_path):
    load_excel_file(default_excel_path)
else:
    st.warning("⚠️ Default dataset not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Linear Lightspec Dataset Upload")

    uploaded_excel = st.file_uploader("Upload Dataset Excel (Recommended: Linear_Lightspec_Data.xlsx)", type=["xlsx"])
    if uploaded_excel:
        with open("Linear_Lightspec_Data.xlsx", "wb") as f:
            f.write(uploaded_excel.getbuffer())
        if load_excel_file("Linear_Lightspec_Data.xlsx"):
            st.success("✅ Dataset loaded successfully!")

    st.download_button(
        label="⬇️ Download Current Dataset Excel",
        data=open("Linear_Lightspec_Data.xlsx", "rb").read(),
        file_name="Linear_Lightspec_Data.xlsx"
    )

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"✅ {uploaded_file.name} uploaded!")

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

# === DISPLAY PARSED IES DATA ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    with st.expander("📏 Photometric Parameters + Metadata + Base Values", expanded=False):
        # IES Metadata
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # Photometric Parameters
        st.markdown("#### Photometric Parameters")
        photometric_data = [
            {"Param [A]": "Lamps", "Value": f"{photometric_params[0]}"},
            {"Param [B]": "Lumens/Lamp", "Value": f"{photometric_params[1]}"},
            {"Param [C]": "Candela Mult.", "Value": f"{photometric_params[2]}"},
            {"Param [D]": "Vert Angles", "Value": f"{photometric_params[3]}"},
            {"Param [E]": "Horiz Angles", "Value": f"{photometric_params[4]}"},
            {"Param [F]": "Photometric Type", "Value": f"{photometric_params[5]}"},
            {"Param [G]": "Units Type", "Value": f"{photometric_params[6]}"},
            {"Param [H]": "Width (m)", "Value": f"{photometric_params[7]}"},
            {"Param [I]": "Length (m)", "Value": f"{photometric_params[8]}"},
            {"Param [J]": "Height (m)", "Value": f"{photometric_params[9]}"},
            {"Param [K]": "Ballast Factor", "Value": f"{photometric_params[10]}"},
            {"Param [L]": "Future Use", "Value": f"{photometric_params[11]}"},
            {"Param [M]": "Input Watts [F]", "Value": f"{photometric_params[12]}"}
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

# === FOOTER ===
st.caption("Version 4.7 Clean - Dataset Upload + Unified Base Info ✅")
