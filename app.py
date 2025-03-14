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
if 'chip_scaling' not in st.session_state:
    st.session_state['chip_scaling'] = 0.0

# === SIDEBAR ===
with st.sidebar:
    st.subheader("⚙️ Advanced Settings")

    with st.expander("Customisation", expanded=False):
        st.markdown("### 📁 Matrix Upload / Download")

        matrix_file = st.file_uploader("Upload Matrix CSV", type=["csv"])
        if matrix_file:
            df_new_matrix = pd.read_csv(matrix_file)
            required_columns = [
                'Option Code', 'Option Description', 'Diffuser Code', 'Diffuser Description',
                'Driver Code', 'Driver Description', 'Wiring Code', 'Wiring Description',
                'Dimensions Code', 'Dimensions Description', 'CRI Code', 'CRI Description',
                'CCT Code', 'CCT Description'
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
        end_plate_thickness = st.number_input("End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1)
        pir_length = st.number_input("PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        spitfire_length = st.number_input("Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)

        st.session_state['chip_scaling'] = st.number_input("LED Version 'Chip Scaling' (%)", min_value=-50.0, max_value=50.0, value=0.0, step=0.1)

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

def parse_lumcat(lumcat_code, lookup_matrix):
    try:
        diffuser_code = lumcat_code[6:8]
        wiring_code = lumcat_code[8:9]
        driver_code = lumcat_code[9:11]
        cri_code = lumcat_code[14:16]
        cct_code = lumcat_code[16:18]

        diffuser_desc = lookup_matrix.loc[lookup_matrix['Diffuser Code'] == diffuser_code, 'Diffuser Description'].values
        wiring_desc = lookup_matrix.loc[lookup_matrix['Wiring Code'] == wiring_code, 'Wiring Description'].values
        driver_desc = lookup_matrix.loc[lookup_matrix['Driver Code'] == driver_code, 'Driver Description'].values
        cri_desc = lookup_matrix.loc[lookup_matrix['CRI Code'] == cri_code, 'CRI Description'].values
        cct_desc = lookup_matrix.loc[lookup_matrix['CCT Code'] == cct_code, 'CCT Description'].values

        return [
            {"Type": "Diffuser / Louvre", "Value": diffuser_desc[0] if len(diffuser_desc) else "Unknown"},
            {"Type": "Wiring", "Value": wiring_desc[0] if len(wiring_desc) else "Unknown"},
            {"Type": "Driver", "Value": driver_desc[0] if len(driver_desc) else "Unknown"},
            {"Type": "CRI", "Value": cri_desc[0] if len(cri_desc) else "Unknown"},
            {"Type": "CCT", "Value": cct_desc[0] if len(cct_desc) else "Unknown"}
        ]
    except Exception as e:
        return [{"Type": "Error", "Value": str(e)}]

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(
        ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    scaled_factor = 1 + st.session_state['chip_scaling'] / 100
    scaled_lumens = round(calculated_lumens * scaled_factor, 1)
    scaled_lm_per_watt = round(scaled_lumens / input_watts, 1) if input_watts > 0 else 0
    scaled_lm_per_m = round(scaled_lumens / length_m, 1) if length_m > 0 else 0

    # === Photometric Parameters + Metadata ===
    with st.expander("📏 Photometric Parameters + Metadata", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]}"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]}"},
            {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]:.1f}"},
            {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]}"},
            {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]}"},
            {"Parameter": "Width", "Details": f"{photometric_params[7]:.2f} m"},
            {"Parameter": "Length", "Details": f"{photometric_params[8]:.2f} m"},
            {"Parameter": "Height", "Details": f"{photometric_params[9]:.2f} m"},
            {"Parameter": "Input Watts", "Details": f"{photometric_params[12]:.1f} W"}
        ]
        st.table(pd.DataFrame(photometric_data))

    # === Mapped LUMCAT Values ===
    lumcat_code = next((line.split(']')[-1].strip() for line in header_lines if "[LUMCAT]" in line), None)
    if lumcat_code and not st.session_state['matrix_lookup'].empty:
        mapped_values = parse_lumcat(lumcat_code, st.session_state['matrix_lookup'])
        with st.expander("🔎 Mapped LUMCAT Values", expanded=False):
            st.table(pd.DataFrame(mapped_values))

    # === Computed Baseline and Scaled ===
    with st.expander("✨ Computed Baseline + Scaled Values", expanded=True):
        baseline_data = [
            {"Metric": "LED Base Total Lumens", "Value": f"{calculated_lumens:.1f}"},
            {"Metric": "LED Base Efficacy (lm/W)", "Value": f"{round(calculated_lumens / input_watts, 1):.1f}"},
            {"Metric": "LED Base Lumens per Meter", "Value": f"{round(calculated_lumens / length_m, 1):.1f}"},
            {"Metric": f"LED Version 'Chip Scaling' ({st.session_state['chip_scaling']}%)", "Value": ""},
            {"Metric": "Scaled Total Lumens", "Value": f"{scaled_lumens:.1f}"},
            {"Metric": "Scaled Efficacy (lm/W)", "Value": f"{scaled_lm_per_watt:.1f}"},
            {"Metric": "Scaled Lumens per Meter", "Value": f"{scaled_lm_per_m:.1f}"}
        ]
        st.table(pd.DataFrame(baseline_data))

else:
    st.info("📄 Upload your IES file to proceed.")

# === FOOTER ===
st.caption("Version 2.2 - Advanced Settings, Mapped LUMCAT & Computed Scaling Tables")
