import streamlit as st
import pandas as pd

# === PAGE CONFIG ===
st.set_page_config(page_title="IES Metadata & Baseline Lumen Calculator", layout="wide")
st.title("IES Metadata & Computed Baseline Display")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')

    # === SIMPLE PARSER (BASIC STRUCTURE) ===
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

    # === EXTRACT FIELDS ===
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

    # === COMPUTATION ===
    def corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix, symmetry_factor=4):
        import numpy as np

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

        return round(total_flux * symmetry_factor, 2)

    # Calculate total lumens
    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)

    # Extract input watts (13th photometric param)
    input_watts = photometric_params[12]

    # Calculate lumens per watt
    calculated_lm_per_watt = round(calculated_lumens / input_watts, 2) if input_watts > 0 else 0

    # === DISPLAY SECTION ===
    st.markdown("## 📄 IES Metadata")
    meta_dict = {line.split(']')[0] + "]": line.split(']')[-1].strip() for line in header_lines if ']' in line}

    st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

    st.markdown("## ✨ Computed Baseline Data")
    st.metric(label="Calculated Total Lumens (lm)", value=f"{calculated_lumens}")
    st.metric(label="Calculated Lumens per Watt (lm/W)", value=f"{calculated_lm_per_watt}")

    st.info("All displayed computed values are generated dynamically based on the uploaded IES file and serve as a verification baseline.")

else:
    st.warning("Please upload an IES file to proceed.")
