import streamlit as st
import pandas as pd
import numpy as np
import time

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Metadata & Baseline Lumen Calculator", layout="wide")
st.title("IES Metadata & Computed Baseline Display")

# === SESSION STATE INITIALIZATION ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []

if 'matrix_version' not in st.session_state:
    st.session_state['matrix_version'] = []

if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame({
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

# === SIDEBAR MAINTENANCE SECTION ===
with st.sidebar.expander("⚙️ Maintenance", expanded=False):
    pwd = st.text_input("Enter Author DOB (DDMM) to Unlock", type="password")
    if pwd == "YOURDOB":  # Replace 'YOURDOB' with actual author DDMM
        st.caption("✅ Download current version first. Adjust and re-upload if needed.")

        # Download button for matrix
        csv = st.session_state['matrix_lookup'].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Current Matrix CSV",
            data=csv,
            file_name='matrix_current.csv',
            mime='text/csv'
        )

        # Upload button for matrix
        uploaded_matrix = st.file_uploader("Upload Updated Matrix CSV", type=["csv"])

        if uploaded_matrix:
            df_new_matrix = pd.read_csv(uploaded_matrix)
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
                st.success(f"Matrix updated successfully! Version: {version_time}")
            else:
                st.error("Matrix upload failed. Missing required columns.")
    else:
        st.info("PWD Hint - Author DOB DDMM")

# === MAIN DISPLAY SECTION ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]

    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    calculated_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    calculated_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    # Computed Baseline Data
    st.markdown("### ✨ Computed Baseline Data")
    baseline_data = [
        {"Description": "Total Lumens", "Value": f"{calculated_lumens:.1f}"},
        {"Description": "Efficacy (lm/W)", "Value": f"{calculated_lm_per_watt:.1f}"},
        {"Description": "Lumens per Meter", "Value": f"{calculated_lm_per_m:.1f}"},
    ]
    st.table(pd.DataFrame(baseline_data))

    # IES Metadata
    st.markdown("### 📄 IES Metadata")
    meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
    st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    # Photometric Parameters
    st.markdown("### 📐 Photometric Parameters")
    photometric_data = [
        {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]} lamp(s) used"},
        {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]} lm (absolute photometry)" if photometric_params[1] < 0 else f"{photometric_params[1]} lm"},
        {"Parameter": "Candela Multiplier", "Details": f"{photometric_params[2]:.1f}"},
        {"Parameter": "Vertical Angles Count", "Details": f"{photometric_params[3]}"},
        {"Parameter": "Horizontal Angles Count", "Details": f"{photometric_params[4]}"},
        {"Parameter": "Photometric Type", "Details": f"{photometric_params[5]} (Type C)" if photometric_params[5] == 1 else f"{photometric_params[5]} (Other)"},
        {"Parameter": "Units Type", "Details": f"{photometric_params[6]} (Meters)" if photometric_params[6] == 2 else f"{photometric_params[6]} (Feet)"},
        {"Parameter": "Width", "Details": f"{photometric_params[7]:.2f} m"},
        {"Parameter": "Length", "Details": f"{photometric_params[8]:.2f} m"},
        {"Parameter": "Height", "Details": f"{photometric_params[9]:.2f} m"},
        {"Parameter": "Ballast Factor", "Details": f"{photometric_params[10]:.1f}"},
        {"Parameter": "Future Use", "Details": f"{photometric_params[11]}"},
        {"Parameter": "Input Watts", "Details": f"{photometric_params[12]:.1f} W"}
    ]
    st.table(pd.DataFrame(photometric_data))

    # Lookup Tables (Individual Tables)
    lookup_table = st.session_state['matrix_lookup']

    st.markdown("### 🔎 Lookup Tables")

    # Diffuser Table
    st.markdown("#### Diffuser")
    diffuser_table = lookup_table[['Diffuser Code', 'Diffuser Description']].drop_duplicates()
    st.table(diffuser_table)

    # Wiring Table
    st.markdown("#### Wiring")
    wiring_table = lookup_table[['Wiring Code', 'Wiring Description']].drop_duplicates()
    st.table(wiring_table)

    # Driver Table
    st.markdown("#### Driver")
    driver_table = lookup_table[['Driver Code', 'Driver Description']].drop_duplicates()
    st.table(driver_table)

    # CRI Table
    st.markdown("#### CRI")
    cri_table = lookup_table[['CRI Code', 'CRI Description']].drop_duplicates()
    st.table(cri_table)

    # CCT Table
    st.markdown("#### CCT")
    cct_table = lookup_table[['CCT Code', 'CCT Description']].drop_duplicates()
    st.table(cct_table)

else:
    st.warning("Please upload an IES file to proceed.")
