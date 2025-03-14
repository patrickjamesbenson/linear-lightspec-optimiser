import streamlit as st
import pandas as pd
import numpy as np

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear Lightspec Optimiser", layout="wide")

st.title("Linear Lightspec Optimiser")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = None
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()
if 'advanced_unlocked' not in st.session_state:
    st.session_state['advanced_unlocked'] = False

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

# === SIDEBAR ===
with st.sidebar:
    with st.expander("📁 Matrix Upload / Download", expanded=False):
        matrix_file = st.file_uploader("Upload Matrix CSV", type=["csv"])
        if matrix_file:
            st.session_state['matrix_lookup'] = pd.read_csv(matrix_file)
            st.session_state['matrix_version'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            st.success(f"Matrix updated @ {st.session_state['matrix_version']}")
        
        if st.session_state['matrix_lookup'] is not None:
            csv_data = st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Current Matrix", data=csv_data, file_name="current_matrix.csv")

    with st.expander("⚙️ Advanced Settings", expanded=False):
        st.subheader("Customisation")
        led_pitch_set = st.number_input("LED Pitch Set (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        leds_per_pitch_set = st.number_input("LEDs per Pitch Set", min_value=1, max_value=12, value=6)

        end_plate_thickness = st.number_input("End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1)
        pir_length = st.number_input("PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        spitfire_length = st.number_input("Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)

        if st.button("🔓 Unlock Advanced Settings"):
            st.session_state['advanced_unlocked'] = True
            st.warning("Super Advanced Users Only: Changes require mandatory comments!")

        if st.session_state['advanced_unlocked']:
            comment = st.text_area("Mandatory Comment", placeholder="Explain why you are making changes")
            if not comment:
                st.error("Comment is mandatory to proceed with changes!")

# === MAIN PAGE ===
# === IES Metadata ===
with st.expander("📄 IES Metadata", expanded=True):
    uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])
    if uploaded_file:
        file_content = uploaded_file.read().decode('utf-8')
        st.session_state['ies_files'] = [{
            'name': uploaded_file.name,
            'content': file_content
        }]
        st.success(f"{uploaded_file.name} uploaded!")

# === Photometric Parameters ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    with st.expander("📏 Photometric Parameters", expanded=True):
        st.write(pd.DataFrame({
            "Parameter Index": list(range(len(photometric_params))),
            "Value": photometric_params
        }))

    # === Computed Baseline Data ===
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

# === LOOKUP TABLE ===
if not st.session_state['matrix_lookup'].empty:
    with st.expander("📚 Lookup Table", expanded=True):
        st.dataframe(st.session_state['matrix_lookup'].style.format(precision=1))

