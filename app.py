import streamlit as st
import pandas as pd
import numpy as np
import time
import os

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()

# === DEFAULT MATRIX AUTO-LOAD ===
default_matrix_path = "Matrix Headers.csv"
if os.path.exists(default_matrix_path):
    st.session_state['matrix_lookup'] = pd.read_csv(default_matrix_path)
else:
    st.warning("⚠️ Default matrix file not found! Please upload manually.")

# === SIDEBAR ===
with st.sidebar:
    st.subheader("📁 Matrix Upload / Download")

    matrix_file = st.file_uploader("Upload Matrix CSV (Optional)", type=["csv"])
    if matrix_file:
        df_new_matrix = pd.read_csv(matrix_file)
        required_columns = [
            'Option Code', 'Option Description',
            'Diffuser / Louvre Code', 'Diffuser / Louvre Description',
            'Driver Code', 'Wiring Code', 'Wiring Description',
            'Driver Description', 'Dimensions Code', 'Dimensions Description',
            'CRI Code', 'CRI Description', 'CCT/Colour Code', 'CCT/Colour Description'
        ]
        if all(col in df_new_matrix.columns for col in required_columns):
            st.session_state['matrix_lookup'] = df_new_matrix
        else:
            st.error("❌ Matrix upload failed: Missing required columns.")

    st.download_button(
        label="⬇️ Download Current Matrix CSV",
        data=st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8'),
        file_name="matrix_current.csv",
        mime="text/csv"
    )

# === FILE UPLOAD: IES FILE ===
uploaded_file = st.file_uploader("📄 Upload your IES file", type=["ies"])
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
    uniform_delta_horz = symmetry_range_rad / num
