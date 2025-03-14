import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Metadata & Baseline Lumen Calculator", layout="wide")
st.title("IES Metadata & Computed Baseline Display")

# === SESSION STATE INITIALISATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = []

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{
        'name': uploaded_file.name,
        'content': file_content
    }]

# === FUNCTION DEFINITIONS ===
def parse_ies_file(file_content):
    lines = file_content.splitlines()
    header_lines = []
    tilt_line = ''
    data_lines = []
    reading_data = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("TILT"):
            tilt_line = stripped
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

# === PLACEHOLDER LOOKUP MATRIX ===
def get_matrix_lookup():
    return {
        'Option': 'No Special Option',
        'Diffuser': 'None',
        'Driver': 'Standard Fixed Output Driver',
        'Wiring': 'Hardwired',
        'CRI': '90',
        'CCT': '4000K'
    }

# === MATRIX FILE MANAGEMENT ===
def download_matrix_template():
    df_template = pd.DataFrame({
        'Option Code': ['NS'],
        'Option Description': ['No Special Option'],
        'Diffuser Code': ['AA'],
        'Diffuser Description': ['None'],
        'Driver Code': ['AA'],
        'Driver Description': ['Standard Fixed Output Driver'],
        'Wiring Code': ['A'],
        'Wiring Description': ['Hardwired'],
        'Dimensions Code': ['AA'],
        'Dimensions Description': ['265mm x 265mm'],
        'CRI Code': ['80'],
        'CRI Description': ['80'],
        'CCT Code': ['27'],
        'CCT Description': ['2700K']
    })
    return df_template

st.sidebar.markdown("### Matrix Download/Upload")
if st.sidebar.button("Download Matrix Template"):
    csv = download_matrix_template().to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Template CSV",
        data=csv,
        file_name='matrix_template.csv',
        mime
