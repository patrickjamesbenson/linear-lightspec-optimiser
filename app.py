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
        mime='text/csv'
    )

uploaded_matrix = st.sidebar.file_uploader("Upload Updated Matrix CSV", type=["csv"])

if uploaded_matrix:
    st.session_state['matrix_lookup'] = pd.read_csv(uploaded_matrix)
    version_time = int(time.time())
    st.session_state['matrix_version'].append(version_time)
    st.sidebar.success(f"Matrix updated successfully! Version: {version_time}")

# === PROCESS AND DISPLAY FILE ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]

    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    calculated_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    calculated_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    # === DISPLAY COMPUTED BASELINE ===
    with st.expander("✨ Computed Baseline Data", expanded=False):
        baseline_data = [
            {"Description": "Total Lumens", "Value": calculated_lumens},
            {"Description": "Efficacy (lm/W)", "Value": calculated_lm_per_watt},
            {"Description": "Lumens per Meter", "Value": calculated_lm_per_m},
        ]
        baseline_df = pd.DataFrame(baseline_data)
        st.table(baseline_df)

    # === DISPLAY IES METADATA ===
    with st.expander("📄 IES Metadata", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    # === DISPLAY PHOTOMETRIC PARAMETERS ===
    with st.expander("📐 Photometric Parameters", expanded=False):
        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]} lamp(s) used"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]} lm (absolute photometry)" if photometric_params[1] < 0 else f"{photometric_params[1]} lm"},
            {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]:.1f} (multiplier applied to candela values)"},
            {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]} vertical angles measured"},
            {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]} horizontal planes"},
            {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]} (Type C)" if photometric_params[5] == 1 else f"{photometric_params[5]} (Other)"},
            {"Parameter": "Units Type", "Details": f"{photometric_params[6]} (Meters)" if photometric_params[6] == 2 else f"{photometric_params[6]} (Feet)"},
            {"Parameter": "Width", "Details": f"{photometric_params[7]:.2f} m"},
            {"Parameter": "Length", "Details": f"{photometric_params[8]:.2f} m"},
            {
