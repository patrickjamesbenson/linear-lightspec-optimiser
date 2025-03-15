import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")
st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = []
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False
if 'led_scaling' not in st.session_state:
    st.session_state['led_scaling'] = 0.0  # Default to 0%

# === SIDEBAR ===
with st.sidebar:
    st.subheader("⚙️ Advanced Settings")

    with st.expander("Customisation", expanded=False):
        st.markdown("### 📁 Matrix Upload / Download")

        matrix_file = st.file_uploader("Upload Matrix CSV", type=["csv"])
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
                version_time = int(time.time())
                st.session_state['matrix_version'].append(version_time)
                st.success(f"Matrix uploaded! Version timestamp: {version_time}")
            else:
                st.error("Matrix upload failed: Missing required columns.")

        if st.button("Download Current Matrix"):
            current_matrix = st.session_state['matrix_lookup']
            csv = current_matrix.to_csv(index=False).encode('utf-8')
            st.download_button("Download Matrix CSV", csv, "matrix_current.csv", "text/csv")

        st.markdown("### 🛠️ Advanced LED Parameters")
        led_pitch_set = st.number_input("LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        leds_per_pitch_set = st.number_input("LEDs per Pitch Set", min_value=1, max_value=12, value=6)

        st.markdown("### Component Lengths")
        
        # **End Plates (2x)**
        end_plate_thickness = st.number_input("End Plates (each) (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1)
        total_end_plate_length = end_plate_thickness * 2

        # **Smart PIR & Spitfire**
        pir_length = st.number_input("Smart PIR (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        spitfire_length = st.number_input("Smart Spitfire (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)

        # **Body Max Increment**
        body_max_increment = st.number_input("Body Max Increment (mm)", min_value=500.0, max_value=5000.0, value=3500.0, step=0.1)

        st.markdown("### 🔧 LED Version 'Chip Scaling' (%)")
        scaling = st.number_input("LED Version 'Chip Scaling'", min_value=-50.0, max_value=50.0, value=st.session_state['led_scaling'], step=0.1)
        st.session_state['led_scaling'] = scaling

        if st.button("Unlock Advanced Settings"):
            st.session_state['advanced_unlocked'] = True
            st.warning("Super Advanced Users Only: Mandatory comment required.")

        if st.session_state['advanced_unlocked']:
            comment = st.text_area("Mandatory Comment", placeholder="Explain why you are making changes")
            if not comment:
                st.error("Comment is mandatory to proceed with changes!")

# === FILE UPLOAD ON MAIN PAGE ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]
    st.success(f"{uploaded_file.name} uploaded!")

# === FUNCTIONS ===
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

    return header_lines, photometric_params

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

# === FOOTER ===
st.caption("Version 3.2 - Smart PIR, Spitfire, End Plates, Body Max Increment Added ✅")
