import streamlit as st
import pandas as pd
import os

# === SESSION STATE INITIALIZATION ===
if 'matrix_lookup' not in st.session_state:
    st.session_state['matrix_lookup'] = pd.DataFrame()

# === LOAD MATRIX ===
default_matrix_path = './data/Matrix Headers.csv'
if os.path.exists(default_matrix_path):
    st.session_state['matrix_lookup'] = pd.read_csv(default_matrix_path)
else:
    st.warning("⚠️ Matrix file not found! Please upload manually.")

# === FUNCTION TO PARSE LUMCAT ===
def parse_lumcat(lumcat_code):
    try:
        # Split by hyphen
        range_code, rest = lumcat_code.split('-')
        
        # Extract each code segment
        option_code = rest[0:2]
        diffuser_code = rest[2:4]
        wiring_code = rest[4]
        driver_code = rest[5:7]
        lumens_code = rest[7:10]
        cri_code = rest[10:12]
        cct_code = rest[12:14]

        # Convert lumens_code (divide by 10 and round 3 decimals)
        lumens_derived = round(float(lumens_code) / 10, 3)

        return {
            "Range": range_code,
            "Option Code": option_code,
            "Diffuser Code": diffuser_code,
            "Wiring Code": wiring_code,
            "Driver Code": driver_code,
            "Lumens Derived": lumens_derived,
            "CRI Code": cri_code,
            "CCT Code": cct_code
        }

    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

# === FUNCTION TO LOOKUP DESCRIPTIONS FROM MATRIX ===
def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    if matrix_df.empty or parsed_codes is None:
        return None

    result = {}

    # Find descriptions in the matrix dataframe
    result['Range'] = parsed_codes['Range']  # Direct mapping (manual description if needed)

    option_match = matrix_df.loc[matrix_df['Option Code'] == parsed_codes['Option Code']]
    diffuser_match = matrix_df.loc[matrix_df['Diffuser / Louvre Code'] == parsed_codes['Diffuser Code']]
    wiring_match = matrix_df.loc[matrix_df['Wiring Code'] == parsed_codes['Wiring Code']]
    driver_match = matrix_df.loc[matrix_df['Driver Code'] == parsed_codes['Driver Code']]
    cri_match = matrix_df.loc[matrix_df['CRI Code'] == parsed_codes['CRI Code']]
    cct_match = matrix_df.loc[matrix_df['CCT/Colour Code'] == parsed_codes['CCT Code']]

    result['Option Description'] = option_match['Option Description'].values[0] if not option_match.empty else "⚠️ Not Found"
    result['Diffuser Description'] = diffuser_match['Diffuser / Louvre Description'].values[0] if not diffuser_match.empty else "⚠️ Not Found"
    result['Wiring Description'] = wiring_match['Wiring Description'].values[0] if not wiring_match.empty else "⚠️ Not Found"
    result['Driver Description'] = driver_match['Driver Description'].values[0] if not driver_match.empty else "⚠️ Not Found"
    result['Lumens (Derived)'] = f"{parsed_codes['Lumens Derived']} lm"
    result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
    result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

    return result

# === MAIN DISPLAY ===
st.title("🔎 LumCAT Reverse Lookup (v4.4)")

# EXAMPLE LUMCAT INPUT FIELD
lumcat_input = st.text_input("Enter LumCAT Code", value="B852-BSA3AAA1488030ZZ")

# Parse and Lookup
parsed_codes = parse_lumcat(lumcat_input)
description_result = lookup_lumcat_descriptions(parsed_codes, st.session_state['matrix_lookup'])

if description_result:
    st.markdown("### Reverse Lookup Results")
    desc_df = pd.DataFrame(description_result.items(), columns=["Field", "Value"])
    st.table(desc_df)
else:
    st.info("Please enter a valid LumCAT code.")

# === FOOTER ===
st.caption("Version 4.4 - LumCAT Reverse Lookup Update ✅")
