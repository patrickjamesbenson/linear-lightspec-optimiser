import streamlit as st
import pandas as pd
from modules.google_sheets import load_google_sheet_data, get_tooltip
from modules.ies_parser import parse_ies_file, corrected_simple_lumen_calculation, extract_meta_dict
from modules.lumcat import parse_lumcat, lookup_lumcat_descriptions

st.set_page_config(page_title="Evolt Linear Optimiser", layout="wide")
st.title("Evolt Linear Optimiser v5 - Google Sheets Edition")

# === SESSION STATE ===
if 'ies_files' not in st.session_state:
    st.session_state['ies_files'] = []
if 'dataset' not in st.session_state:
    st.session_state['dataset'] = {}

# === LOAD DATA ===
load_google_sheet_data()

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("📄 Upload IES file", type=["ies"])
if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    st.session_state['ies_files'] = [{'name': uploaded_file.name, 'content': file_content}]

# === MAIN DISPLAY ===
if st.session_state['ies_files']:
    ies_file = st.session_state['ies_files'][0]
    header_lines, photometric_params, vertical_angles, horizontal_angles, candela_matrix = parse_ies_file(ies_file['content'])

    # === LUMEN CALCULATIONS ===
    calculated_lumens = corrected_simple_lumen_calculation(vertical_angles, horizontal_angles, candela_matrix)
    input_watts = photometric_params[12]
    length_m = photometric_params[8]

    base_lm_per_watt = round(calculated_lumens / input_watts, 1) if input_watts > 0 else 0
    base_lm_per_m = round(calculated_lumens / length_m, 1) if length_m > 0 else 0

    # === BUILD DATA LOOKUP ===
    build_data = st.session_state['dataset']['Build_Data']
    if 'Description' in build_data.columns:
        build_data = build_data.set_index('Description')
    else:
        st.error("The 'Description' column is missing in Build_Data")

    default_tier = 'V1'
    tier_values = {
        "Default Tier": default_tier,
        "Chip Name": build_data.loc['Chip_Name', default_tier],
        "Max LED Load (mA)": build_data.loc['LED_Load_(mA)', default_tier],
        "Board Segment LED Pitch": build_data.loc['LED_Group_Pitch_(mm)', default_tier],
        "Vf (Volts)": build_data.loc['Vf_(Volts)', default_tier],
        "Internal Code / TM30": build_data.loc['TM30-report_No.', default_tier]
    }

    actual_led_current_ma = (input_watts / tier_values['Vf (Volts)']) * 1000

    # === DISPLAY ===
    with st.expander("📏 Parameters + Metadata + Derived Values", expanded=True):
        meta_dict = extract_meta_dict(header_lines)

        # === IES METADATA ===
        st.markdown("#### IES Metadata")
        st.table(pd.DataFrame.from_dict(meta_dict, orient='index', columns=['Value']))

        # === IES PARAMETERS ===
        st.markdown("#### IES Parameters")
        photometric_table = [
            {"Description": desc, "LED Base": f"{photometric_params[idx]}"} for idx, desc in enumerate([
                "Lamps", "Lumens/Lamp", "Candela Mult.", "Vert Angles", "Horiz Angles", "Photometric Type", "Units Type",
                "Width (m)", "Length (m)", "Height (m)", "Ballast Factor", "Future Use", "Input Watts [F]"
            ])
        ]
        st.table(pd.DataFrame(photometric_table))

        # === IES DERIVED VALUES ===
        st.markdown("#### IES Derived Values")
        base_values = [
            {"Description": "Total Lumens", "LED Base": f"{calculated_lumens:.1f}"},
            {"Description": "Efficacy (lm/W)", "LED Base": f"{base_lm_per_watt:.1f}"},
            {"Description": "Lumens per Meter", "LED Base": f"{base_lm_per_m:.1f}"},
            {"Description": "Default Tier / Chip", "LED Base": f"{tier_values['Default Tier']} / {tier_values['Chip Name']}"},
            {"Description": "Max LED Load (mA)", "LED Base": f"{tier_values['Max LED Load (mA)']:.1f}"},
            {"Description": "LED Pitch (mm)", "LED Base": f"{tier_values['Board Segment LED Pitch']:.1f}"},
            {"Description": "Actual LED Current (mA)", "LED Base": f"{actual_led_current_ma:.1f}"},
            {"Description": "TM30 Code", "LED Base": f"{tier_values['Internal Code / TM30']}"}
        ]
        st.table(pd.DataFrame(base_values))

        # === LUMCAT LOOKUP ===
        st.markdown("#### 🔎 LumCAT Lookup")
        lumcat_matrix_df = st.session_state['dataset']['LumCAT_Config']
        lumcat_from_meta = meta_dict.get("[LUMCAT]", "")

        lumcat_input = st.text_input("Enter LumCAT Code", value=lumcat_from_meta)
        if lumcat_input:
            parsed_codes = parse_lumcat(lumcat_input)
            if parsed_codes:
                lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)
                if lumcat_desc:
                    st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))

st.caption("Version 5 - Google Sheets Connected - Tooltips Added")
