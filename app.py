# === LUMCAT REVERSE LOOKUP ===
st.markdown("🔎 LumCAT Reverse Lookup (Matrix)")

def parse_lumcat(lumcat_code):
    try:
        range_code, rest = lumcat_code.split('-')
        option_code = rest[0:2]
        diffuser_code = rest[2:4]
        wiring_code = rest[4]
        driver_code = rest[5:7]
        lumens_code = rest[7:10]
        cri_code = rest[10:12]
        cct_code = rest[12:14]
        lumens_derived = round(float(lumens_code) * 10, 1)

        return {
            "Range": range_code,
            "Option Code": option_code,
            "Diffuser Code": diffuser_code,
            "Wiring Code": wiring_code,
            "Driver Code": driver_code,
            "Lumens (Derived)": lumens_derived,
            "CRI Code": cri_code,
            "CCT Code": cct_code
        }
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes, matrix_df):
    # ✅ Confirm dataset is not empty
    if matrix_df.empty or parsed_codes is None:
        st.warning("LumCAT Matrix data is empty or parsing failed!")
        return None
    
    # ✅ Clean column headers (trim spaces)
    matrix_df.columns = matrix_df.columns.str.strip()

    # ✅ Header check before lookup
    required_cols = [
        'Option Code', 'Option Description',
        'Diffuser / Louvre Code', 'Diffuser / Louvre Description',
        'Wiring Code', 'Wiring Description',
        'Driver Code', 'Driver Description',
        'CRI Code', 'CRI Description',
        'CCT/Colour Code', 'CCT/Colour Description'
    ]

    missing_cols = [col for col in required_cols if col not in matrix_df.columns]
    if missing_cols:
        st.error(f"❌ Missing columns in LumCAT Matrix: {missing_cols}")
        return None

    def get_value(df, code_col, desc_col, code):
        match = df.loc[df[code_col] == code]
        return match[desc_col].values[0] if not match.empty else "⚠️ Not Found"

    # ✅ Perform reverse lookup
    result = {
        'Range': parsed_codes['Range'],
        'Option Description': get_value(matrix_df, 'Option Code', 'Option Description', parsed_codes['Option Code']),
        'Diffuser Description': get_value(matrix_df, 'Diffuser / Louvre Code', 'Diffuser / Louvre Description', parsed_codes['Diffuser Code']),
        'Wiring Description': get_value(matrix_df, 'Wiring Code', 'Wiring Description', parsed_codes['Wiring Code']),
        'Driver Description': get_value(matrix_df, 'Driver Code', 'Driver Description', parsed_codes['Driver Code']),
        'Lumens (Derived)': parsed_codes['Lumens (Derived)'],
        'CRI Description': get_value(matrix_df, 'CRI Code', 'CRI Description', parsed_codes['CRI Code']),
        'CCT Description': get_value(matrix_df, 'CCT/Colour Code', 'CCT/Colour Description', parsed_codes['CCT Code'])
    }

    return result

lumcat_input = st.text_input("Enter LumCAT Code", value="B852-BSA3AAA1488030ZZ")
parsed_codes = parse_lumcat(lumcat_input)

if parsed_codes:
    lumcat_matrix_df = st.session_state['dataset'].get('LumCAT_Config', pd.DataFrame())
    lumcat_desc = lookup_lumcat_descriptions(parsed_codes, lumcat_matrix_df)

    if lumcat_desc:
        st.table(pd.DataFrame(lumcat_desc.items(), columns=["Field", "Value"]))
