# === Photometric Parameters ===
st.markdown("#### Photometric Parameters")

photometric_table = [
    {"Description": "Lamps", "Value": round(photometric_params[0], 1)},
    {"Description": "Lumens/Lamp", "Value": round(photometric_params[1], 1)},
    {"Description": "Candela Mult.", "Value": round(photometric_params[2], 1)},
    {"Description": "Vert Angles", "Value": round(photometric_params[3], 1)},
    {"Description": "Horiz Angles", "Value": round(photometric_params[4], 1)},
    {"Description": "Photometric Type", "Value": round(photometric_params[5], 1)},
    {"Description": "Units Type", "Value": round(photometric_params[6], 1)},
    {"Description": "Width (m)", "Value": round(photometric_params[7], 1)},
    {"Description": "Length (m)", "Value": round(photometric_params[8], 1)},
    {"Description": "Height (m)", "Value": round(photometric_params[9], 1)},
    {"Description": "Ballast Factor", "Value": round(photometric_params[10], 1)},
    {"Description": "Future Use", "Value": round(photometric_params[11], 1)},
    {"Description": "Input Watts [F]", "Value": round(photometric_params[12], 1)}
]

st.table(pd.DataFrame(photometric_table).style.format({'Value': '{:.1f}'}))
