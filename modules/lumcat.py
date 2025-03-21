import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any

def parse_lumcat(lumcat_code: str) -> Optional[Dict[str, Any]]:
    try:
        range_code, rest = lumcat_code.split('-')
        parsed = {
            "Range": range_code,
            "Option Code": rest[0:2],
            "Diffuser Code": rest[2:4],
            "Wiring Code": rest[4],
            "Driver Code": rest[5:7],
            "Lumens Code": rest[7:10],
            "CRI Code": rest[10:12],
            "CCT Code": rest[12:14]
        }
        parsed['Lumens Derived Display'] = round(float(parsed["Lumens Code"]) * 10, 1)
        return parsed
    except Exception as e:
        st.error(f"Error parsing LUMCAT: {e}")
        return None

def lookup_lumcat_descriptions(parsed_codes: Dict[str, Any], matrix_df: pd.DataFrame) -> Optional[Dict[str, str]]:
    if matrix_df.empty or parsed_codes is None:
        return None

    matrix_df.columns = matrix_df.columns.str.strip()
    matrix_df['CRI Code'] = matrix_df['CRI Code'].astype(str).str.strip()
    matrix_df['CCT/Colour Code'] = matrix_df['CCT/Colour Code'].astype(str).str.strip()

    parsed_codes['CRI Code'] = str(parsed_codes['CRI Code']).strip()
    parsed_codes['CCT Code'] = str(parsed_codes['CCT Code']).strip()

    result = {'Range': parsed_codes['Range']}

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
    result['Lumens (Display Only)'] = f"{parsed_codes['Lumens Derived Display']} lm"
    result['CRI Description'] = cri_match['CRI Description'].values[0] if not cri_match.empty else "⚠️ Not Found"
    result['CCT Description'] = cct_match['CCT/Colour Description'].values[0] if not cct_match.empty else "⚠️ Not Found"

    return result
