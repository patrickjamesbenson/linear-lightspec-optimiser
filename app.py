import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Metadata & Baseline Lumen Calculator", layout="wide")
st.title("IES Metadata & Computed Baseline Display")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

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

# === SIDEBAR CUSTOMISATION PANEL ===
with st.sidebar:
    st.header("Customisation")

    st.subheader("Advanced LED Parameters")
    led_pitch_set = st.number_input(
        "LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1
    )
    leds_per_pitch_set = st.number_input(
        "LEDs per Pitch Set", min_value=1, max_value=12, value=6
    )
    series_number = st.number_input(
        "LED Series Number", min_value=1, max_value=12, value=3
    )

    st.subheader("Component Lengths")
    end_plate_thickness = st.number_input(
        "End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1
    )
    pir_length = st.number_input(
        "PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1
    )
    spitfire_length = st.number_input(
        "Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1
    )

    if not st.session_state['advanced_unlocked']:
        if st.button("Unlock Advanced Settings"):
            st.session_state['advanced_unlocked'] = True
            st.warning("Super Advanced Users Only! Mandatory comments required on changes.")

    if st.session_state['advanced_unlocked']:
        comment = st.text_area("Mandatory Comment", placeholder="Explain why you are making changes")
        if not comment:
            st.error("Comment is mandatory to proceed with changes.")

# === COMPUTED BASELINE DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    calculated_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    calculated_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    st.subheader("✨ Computed Baseline Data")
    baseline_data = [
        {"Description": "Total Lumens", "Value": calculated_lumens},
        {"Description": "Input Watts", "Value": input_watts},
        {"Description": "Efficacy (lm/W)", "Value": calculated_lm_per_watt},
        {"Description": "Lumens per Meter", "Value": calculated_lm_per_m}
    ]
    baseline_df = pd.DataFrame(baseline_data)
    st.table(baseline_df.style.format({"Value": "{:.1f}"}))
