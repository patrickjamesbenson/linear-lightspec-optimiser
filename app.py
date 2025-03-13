import streamlit as st
import pandas as pd
from datetime import datetime

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === INITIALISE SESSION STATE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = "Current Generation"
    st.session_state['lmw_step_increment'] = 115.0
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode("utf-8")
    
    # Mock parse (replace with real parser later)
    luminaire_name_base = "BLine 8585D"
    optic_description = "Diffused Down"
    cri_value = "80CRI"
    cct_value = "3000K"
    watt_value = "11.6W"
    base_lm_per_m = 400.0
    base_w_per_m = 11.6

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        st.markdown("### IES Metadata")
        metadata_dict = {
            "IES Version": "IESNA:LM-63-2002",
            "Test Info": "[TEST]",
            "Manufacturer": "[MANUFAC] Evolt Manufacturing",
            "Luminaire Catalog Number": "[LUMCAT] B852-__A3___1488030ZZ",
            "Luminaire Description": f"[LUMINAIRE] {luminaire_name_base} {watt_value} - {cri_value} - {cct_value}",
            "Issued Date": "[ISSUEDATE] 2024-07-07"
        }
        st.table(pd.DataFrame.from_dict(metadata_dict, orient='index', columns=['Value']))

        st.markdown("### Photometric Parameters")
        photometric_params = {
            "Number of Lamps": "1",
            "Lumens per Lamp": "-1",
            "Candela Multiplier": "1",
            "Vertical Angles": "91",
            "Horizontal Angles": "4",
            "Photometric Type": "1",
            "Units Type": "2",
            "Width (m)": "0.08",
            "Length (m)": "1",
            "Height (m)": "0.09",
            "Ballast Factor": "1",
            "Future Use": "1",
            "Input Watts": base_w_per_m
        }
        st.table(pd.DataFrame.from_dict(photometric_params, orient='index', columns=['Value']))

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        if st.session_state['locked']:
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

        st.markdown("#### Select Lengths")
        desired_length_m = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.001, format="%.3f")

        # Calculate buildable lengths
        desired_length_mm = desired_length_m * 1000
        min_length_mm = (int((desired_length_mm - st.session_state['end_plate_thickness'] * 2) / st.session_state['led_pitch'])) * st.session_state['led_pitch'] + st.session_state['end_plate_thickness'] * 2
        max_length_mm = min_length_mm + st.session_state['led_pitch']

        shorter_length_m = round(min_length_mm / 1000, 3)
        longer_length_m = round(max_length_mm / 1000, 3)

        col1, col2 = st.columns(2)

        if col1.button(f"Add Shorter Buildable Length: {shorter_length_m:.3f} m"):
            st.session_state['lengths_list'].append(shorter_length_m)
            st.session_state['locked'] = True
            st.rerun()

        if col2.button(f"Add Longer Buildable Length: {longer_length_m:.3f} m"):
            st.session_state['lengths_list'].append(longer_length_m)
            st.session_state['locked'] = True
            st.rerun()

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        st.session_state['led_efficiency_gain_percent'] = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
        st.session_state['efficiency_reason'] = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])

        if st.session_state['led_efficiency_gain_percent'] != 0 and (st.session_state['efficiency_reason'].strip() == "" or st.session_state['efficiency_reason'] == "Current Generation"):
            st.warning("⚠️ Please provide a reason for LED Chipset Adjustment!")

    # === SYSTEM LMW EFFICIENCY INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.
        For advanced users only.
        """)
        st.info(f"🔒 Locked at: {st.session_state['lmw_step_increment']} lm/W")

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")

    if st.session_state['lengths_list']:
        table_rows = []
        efficiency_multiplier = 1 + (st.session_state['led_efficiency_gain_percent'] / 100.0)
        new_w_per_m = round(base_w_per_m * efficiency_multiplier, 1)
        new_lm_per_m = round(base_lm_per_m, 1)

        for idx, length in enumerate(st.session_state['lengths_list']):
            total_lumens = round(new_lm_per_m * length, 1)
            total_watts = round(new_w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

            tier = "Professional" if st.session_state['led_efficiency_gain_percent'] != 0 else "Core"
            luminaire_file_name = f"{luminaire_name_base} {watt_value} {optic_description}_{length:.3f}m_{tier}"

            row = {
                "Delete": "🗑️",
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": luminaire_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": st.session_state['efficiency_reason'] if st.session_state['led_efficiency_gain_percent'] != 0 else ""
            }

            table_rows.append(row)

        # Table Headers
        header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])
        headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
        for col, h in zip(header_cols, headers):
            col.markdown(f"**{h}**")

        # Table Rows
        for idx, row in enumerate(table_rows):
            cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 3])

            if cols[0].button("🗑️", key=f"delete_{idx}"):
                st.session_state['lengths_list'].pop(idx)
                if len(st.session_state['lengths_list']) == 0:
                    st.session_state['locked'] = False
                st.rerun()

            row_data = [row["Length (m)"], row["Luminaire & IES File Name"], row["CRI"], row["CCT"],
                        row["Total Lumens"], row["Total Watts"], row["Settings lm/W"], row["Comments"]]

            for col, val in zip(cols[1:], row_data):
                col.write(val)

        # CSV Export
        export_df = pd.DataFrame([{
            "Length (m)": r["Length (m)"],
            "Luminaire & IES File Name": r["Luminaire & IES File Name"],
            "CRI": r["CRI"],
            "CCT": r["CCT"],
            "Total Lumens": r["Total Lumens"],
            "Total Watts": r["Total Watts"],
            "Settings lm/W": r["Settings lm/W"],
            "Comments": r["Comments"]
        } for r in table_rows])

        st.download_button("Download CSV Summary", data=export_df.to_csv(index=False).encode('utf-8'),
                           file_name=f"Selected_Lengths_Summary_{st.session_state['export_id']}.csv", mime="text/csv")
    else:
        st.info("No lengths selected yet. Click a button above to add lengths.")

    # === DESIGN OPTIMISATION ===
    st.markdown("🎯 **Design Optimisation**")
    target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
    achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

    difference_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
    st.write(f"Difference: {difference_percent}%")

    required_change_lm_per_m = round(base_lm_per_m * abs(difference_percent) / 100, 1)
    increments_needed = int(required_change_lm_per_m / st.session_state['lmw_step_increment'])

    if increments_needed < 1:
        st.warning("⚠️ Dimming recommended to match target lux.")
    else:
        st.warning(f"⚠️ Consider {'reducing' if difference_percent > 0 else 'increasing'} by {increments_needed} increments.")

    st.info("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE FILES ===
    st.success("✅ IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Upload an IES file to begin optimisation.")
