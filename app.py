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
    st.session_state['matrix_lookup'] = None

if 'led_efficiency_change' not in st.session_state:
    st.session_state['led_efficiency_change'] = 0

if 'led_efficiency_reason' not in st.session_state:
    st.session_state['led_efficiency_reason'] = ""

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{
        'name': uploaded_file.name,
        'content': file_content
    }]
    st.session_state['led_efficiency_change'] = 0
    st.session_state['led_efficiency_reason'] = ""

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

# === MATRIX FILE MANAGEMENT ===
def download_matrix_template():
    if st.session_state['matrix_lookup'] is not None:
        return st.session_state['matrix_lookup']
    return pd.DataFrame({
        'Option Code': [],
        'Option Description': [],
        'Diffuser Code': [],
        'Diffuser Description': [],
        'Driver Code': [],
        'Driver Description': [],
        'Wiring Code': [],
        'Wiring Description': [],
        'Dimensions Code': [],
        'Dimensions Description': [],
        'CRI Code': [],
        'CRI Description': [],
        'CCT Code': [],
        'CCT Description': []
    })

st.sidebar.markdown("### Matrix Download/Upload")
st.sidebar.caption("✅ Download current version first, keep the format, and only adjust entries as needed.")

if st.sidebar.button("Download Current Matrix"):
    csv = download_matrix_template().to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Matrix CSV",
        data=csv,
        file_name='matrix_current.csv',
        mime='text/csv'
    )

uploaded_matrix = st.sidebar.file_uploader("Upload Updated Matrix CSV", type=["csv"])

if uploaded_matrix:
    df_new_matrix = pd.read_csv(uploaded_matrix)
    required_columns = [
        'Option Code', 'Option Description',
        'Diffuser Code', 'Diffuser Description',
        'Driver Code', 'Driver Description',
        'Wiring Code', 'Wiring Description',
        'Dimensions Code', 'Dimensions Description',
        'CRI Code', 'CRI Description',
        'CCT Code', 'CCT Description'
    ]

    if all(col in df_new_matrix.columns for col in required_columns):
        st.session_state['matrix_lookup'] = df_new_matrix
        version_time = int(time.time())
        st.session_state['matrix_version'].append(version_time)
        st.sidebar.success(f"Matrix updated! Version: {version_time}")
    else:
        st.sidebar.error("Upload failed: Missing required columns.")

# === PROCESS AND DISPLAY FILE ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    baseline_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    baseline_efficiency = round(baseline_lumens / input_watts, 1) if input_watts > 0 else 0

    # === LED EFFICIENCY SCALING ===
    st.subheader("🔧 LED Chip Scaling")

    st.session_state['led_efficiency_change'] = st.slider(
        "LED Chip Efficiency Change (%)", -50, 50, st.session_state['led_efficiency_change']
    )

    if st.session_state['led_efficiency_change'] != 0:
        st.session_state['led_efficiency_reason'] = st.text_input(
            "Reason for Efficiency Change (Mandatory)",
            value=st.session_state['led_efficiency_reason']
        )
        if not st.session_state['led_efficiency_reason']:
            st.warning("⚠️ Reason is required to proceed when efficiency change ≠ 0!")

    # Apply scaling to lumens
    lumens_scaled = baseline_lumens * (1 + st.session_state['led_efficiency_change'] / 100)
    efficiency_scaled = round(lumens_scaled / input_watts, 1) if input_watts > 0 else 0

    # === COMPUTED BASELINE DATA ===
    st.subheader("✨ Computed Baseline Data")

    baseline_data = [
        {"Description": "Base Total Lumens", "Value": baseline_lumens},
        {"Description": "Base Input Watts", "Value": input_watts},
        {"Description": "Base Efficacy (lm/W)", "Value": baseline_efficiency},
        {"Description": "Lumens per Meter", "Value": round(baseline_lumens / length_m, 1) if length_m > 0 else 0},
        {"Description": "% Lumen Change", "Value": f"{st.session_state['led_efficiency_change']}%"},
        {"Description": "Scaled Total Lumens", "Value": round(lumens_scaled, 1)},
        {"Description": "Scaled Efficacy (lm/W)", "Value": efficiency_scaled},
    ]
    st.table(pd.DataFrame(baseline_data))

    # === IES METADATA ===
    with st.expander("📄 IES Metadata", expanded=False):
        meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    # === PHOTOMETRIC PARAMETERS ===
    with st.expander("📐 Photometric Parameters", expanded=False):
        photometric_data = [
            {"Parameter": "Number of Lamps", "Details": f"{photometric_params[0]}"},
            {"Parameter": "Lumens per Lamp", "Details": f"{photometric_params[1]}"},
            {"Parameter": "Input Watts", "Details": f"{photometric_params[12]}"},
            {"Parameter": "Width", "Details": f"{photometric_params[7]}"},
            {"Parameter": "Length", "Details": f"{photometric_params[8]}"},
            {"Parameter": "Height", "Details": f"{photometric_params[9]}"},
        ]
        st.table(pd.DataFrame(photometric_data))

    # === LOOKUP TABLE ===
    if st.session_state['matrix_lookup'] is not None:
        with st.expander("🔍 Lookup Table (LUMCAT Mapping)", expanded=False):
            lumcat_code = next((line for line in header_lines if "[LUMCAT]" in line), "")
            lumcat_value = lumcat_code.split("]")[-1].strip()

            # Parse based on lumcat structure
            parsed_data = {
                "Luminaire Range": lumcat_value.split('-')[0],
                "Option": lumcat_value[5:7],
                "Diffuser": lumcat_value[7:9],
                "Wiring": lumcat_value[9],
                "Driver": lumcat_value[10:12],
                "CRI": lumcat_value[12:14],
                "CCT": lumcat_value[14:16],
            }

            display_df = pd.DataFrame(parsed_data.items(), columns=["Description", "Value"])
            st.table(display_df)

# === TO-DO LIST ===
st.sidebar.subheader("📝 To-Do List")
st.sidebar.markdown("- Length Scaling (Next Module)")
st.sidebar.markdown("- Design Optimisation Module")
st.sidebar.markdown("- Password and Access Control (Revisit later)")
