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
