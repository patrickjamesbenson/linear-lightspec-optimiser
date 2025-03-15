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
    st.session_state['led_scaling'] = 0.0
if 'scaling_comment' not in st.session_state:
    st.session_state['scaling_comment'] = ""

# === SIDEBAR ===
with st.sidebar:
    st.subheader("⚙️ Advanced Settings")

    with st.expander("Customisation", expanded=False):

        st.markdown("### 🔧 LED Version 'Chip Scaling' (%)")
        scaling = st.number_input("LED Version 'Chip Scaling'", min_value=-50.0, max_value=50.0,
                                  value=st.session_state['led_scaling'], step=0.1)
        st.session_state['led_scaling'] = scaling

        st.markdown("### Component Lengths")
        end_plate_thickness = st.number_input("End Plate Thickness (mm)", min_value=1.0, max_value=20.0, value=5.5, step=0.1)
        pir_length = st.number_input("PIR Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)
        spitfire_length = st.number_input("Spitfire Length (mm)", min_value=10.0, max_value=100.0, value=46.0, step=0.1)

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

def parse_lumcat_and_lookup(header_lines, matrix_lookup):
    lumcat_line = next((line for line in header_lines if "[LUMCAT]" in line), None)
    if not lumcat_line:
        return [{"Type": "LUMCAT", "Value": "Not Found"}]

    lumcat_code = lumcat_line.split(']')[-1].strip()

    prefix = lumcat_code.split('-')[0]
    suffix = lumcat_code.split('-')[1] if '-' in lumcat_code else ""

    # Extract segments based on agreed logic
    diffuser_code = suffix[0:2] if len(suffix) >= 2 else ""
    wiring_code = suffix[2:4] if len(suffix) >= 4 else ""
    driver_code = suffix[4:6] if len(suffix) >= 6 else ""
    cri_code = suffix[10:12] if len(suffix) >= 12 else ""
    cct_code = suffix[12:14] if len(suffix) >= 14 else ""

    # Lookup
    df = matrix_lookup

    diffuser_desc = df.loc[df['Diffuser / Louvre Code'] == diffuser_code, 'Diffuser / Louvre Description'].values
    wiring_desc = df.loc[df['Wiring Code'] == wiring_code, 'Wiring Description'].values
    driver_desc = df.loc[df['Driver Code'] == driver_code, 'Driver Description'].values
    cri_desc = df.loc[df['CRI Code'] == cri_code, 'CRI Description'].values
    cct_desc = df.loc[df['CCT/Colour Code'] == cct_code, 'CCT/Colour Description'].values

    return [
        {"Type": "Diffuser / Louvre", "Value": diffuser_desc[0] if len(diffuser_desc) else "Unknown"},
        {"Type": "Wiring", "Value": wiring_desc[0] if len(wiring_desc) else "Unknown"},
        {"Type": "Driver", "Value": driver_desc[0] if len(driver_desc) else "Unknown"},
        {"Type": "CRI", "Value": cri_desc[0] if len(cri_desc) else "Unknown"},
        {"Type": "CCT", "Value": cct_desc[0] if len(cct_desc) else "Unknown"}
    ]

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

    scaling_factor = 1 + (st.session_state['led_scaling'] / 100)
    scaled_lumens = round(calculated_lumens * scaling_factor, 1)
    scaled_lm_per_watt = round(scaled_lumens / input_watts, 1) if input_watts > 0 else 0
    scaled_lm_per_m = round(scaled_lumens / length_m, 1) if length_m > 0 else 0

    # === DISPLAY LOOKUP TABLE ===
    lookup_table = parse_lumcat_and_lookup(header_lines, st.session_state['matrix_lookup'])

    with st.expander("🔍 LUMCAT Lookup Details", expanded=False):
        st.table(pd.DataFrame(lookup_table))

    # === DISPLAY PHOTOMETRIC + METADATA ===
    with st.expander("📏 Photometric Parameters + Metadata", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        st.markdown("#### Photometric Parameters")
        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]}"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]}"},
            {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]}"},
            {"Parameter": "Input Watts", "Details": f"{input_watts} W"}
        ]
        st.table(pd.DataFrame(photometric_data))

    # === COMPUTED BASELINE + SCALED ===
    with st.expander("✨ Computed Baseline + Scaled Values", expanded=False):
        baseline_data = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}", "Scaled": f"{scaled_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}", "Scaled": f"{scaled_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}", "Scaled": f"{scaled_lm_per_m:.1f}"}
        ]
        st.table(pd.DataFrame(baseline_data))

        # Mandatory comment when scaling is applied
        if st.session_state['led_scaling'] != 0.0:
            st.session_state['scaling_comment'] = st.text_area("Mandatory Reason for LED Scaling Adjustment", value=st.session_state['scaling_comment'])
            if not st.session_state['scaling_comment']:
                st.warning("⚠️ Reason for scaling adjustment is mandatory.")

else:
    st.info("📄 Upload your IES file to proceed.")

# === FOOTER ===
st.caption("Version 2.1f - LUMCAT Mapping & Scaling Logic Update")
