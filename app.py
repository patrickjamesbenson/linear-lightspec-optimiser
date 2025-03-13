import streamlit as st
import pandas as pd
from datetime import datetime
from utils import parse_ies_file, modify_candela_data, create_ies_file, create_zip

# === PAGE CONFIG ===
st.set_page_config(page_title="Linear LightSpec Optimiser", layout="wide")
st.title("Linear LightSpec Optimiser")

# === SESSION STATE INITIALISE ===
if 'locked' not in st.session_state:
    st.session_state['locked'] = False
    st.session_state['lengths_list'] = []
    st.session_state['end_plate_thickness'] = 5.5
    st.session_state['led_pitch'] = 56.0
    st.session_state['led_efficiency_gain_percent'] = 0.0
    st.session_state['efficiency_reason'] = "Current Generation"
    st.session_state['lmw_increment'] = 115.0
    st.session_state['export_id'] = datetime.now().strftime("%Y%m%d%H%M%S")

# === FILE UPLOAD ===
uploaded_file = st.file_uploader("Upload your Base IES file", type=["ies"])

if uploaded_file:
    file_content = uploaded_file.read().decode('utf-8')
    parsed = parse_ies_file(file_content)

    # === EXTRACT LUMINAIRE INFO ===
    luminaire_line = next((line for line in parsed['header'] if line.startswith("[LUMINAIRE]")), None)
    luminaire_desc = luminaire_line.replace("[LUMINAIRE]", "").strip() if luminaire_line else "Unknown"

    # Parse Optic from description (placeholder if missing)
    optic = "Diffused Down" if "Diffused Down" in luminaire_desc else "Unknown Optic"

    # CRI and CCT (fallback to N/A)
    cri_value = next((val for val in luminaire_desc.split() if "CRI" in val), "N/A")
    cct_value = next((val for val in luminaire_desc.split() if "K" in val), "N/A")

    # === BASE FILE SUMMARY ===
    with st.expander("📂 Base File Summary (IES Metadata + Photometric Parameters)", expanded=False):
        ies_meta = {
            "IES Version": next((l for l in parsed['header'] if l.startswith("IESNA")), "Unknown"),
            "Test Info": next((l for l in parsed['header'] if l.startswith("[TEST]")), "Unknown"),
            "Manufacturer": next((l for l in parsed['header'] if l.startswith("[MANUFAC]")), "Unknown"),
            "Luminaire Catalog Number": next((l for l in parsed['header'] if l.startswith("[LUMCAT]")), "Unknown"),
            "Luminaire Description": luminaire_desc,
            "Issued Date": next((l for l in parsed['header'] if l.startswith("[ISSUEDATE]")), "Unknown")
        }

        st.markdown("### IES Metadata")
        st.table(pd.DataFrame.from_dict(ies_meta, orient='index', columns=['Value']))

        st.markdown("### Photometric Parameters")
        photo_params = parsed['data'][0].strip().split()
        if len(photo_params) >= 13:
            param_labels = [
                "Number of Lamps", "Lumens per Lamp", "Candela Multiplier",
                "Vertical Angles", "Horizontal Angles", "Photometric Type",
                "Units Type", "Width (m)", "Length (m)", "Height (m)",
                "Ballast Factor", "Future Use", "Input Watts"
            ]
            param_data = {label: val for label, val in zip(param_labels, photo_params)}
            st.table(pd.DataFrame.from_dict(param_data, orient='index', columns=['Value']))
        else:
            st.warning("Photometric parameters incomplete.")

    # === BASE BUILD METHODOLOGY ===
    with st.expander("📂 Base Build Methodology", expanded=False):
        # Lock/Unlock logic based on length selection
        if st.session_state['lengths_list']:
            st.session_state['locked'] = True
            st.info(f"🔒 Locked: End Plate Expansion Gutter = {st.session_state['end_plate_thickness']} mm | LED Series Module Pitch = {st.session_state['led_pitch']} mm")
        else:
            st.session_state['locked'] = False
            st.session_state['end_plate_thickness'] = st.number_input("End Plate Expansion Gutter (mm)", min_value=0.0, value=st.session_state['end_plate_thickness'], step=0.1)
            st.session_state['led_pitch'] = st.number_input("LED Series Module Pitch (mm)", min_value=14.0, value=st.session_state['led_pitch'], step=0.1)

    # === SELECT LENGTHS ===
    st.markdown("## Select Lengths")
    desired_length = st.number_input("Desired Length (m)", min_value=0.5, value=1.0, step=0.001, format="%.3f")
    pitch = st.session_state['led_pitch']
    gutter = st.session_state['end_plate_thickness']

    min_len = (int((desired_length * 1000 - gutter * 2) / pitch)) * pitch + gutter * 2
    max_len = min_len + pitch

    shorter_len = round(min_len / 1000, 3)
    longer_len = round(max_len / 1000, 3)

    col1, col2 = st.columns(2)
    if col1.button(f"Add Shorter Buildable Length: {shorter_len:.3f} m"):
        st.session_state['lengths_list'].append(shorter_len)
    if col2.button(f"Add Longer Buildable Length: {longer_len:.3f} m"):
        st.session_state['lengths_list'].append(longer_len)

    # === LED CHIPSET ADJUSTMENT ===
    with st.expander("💡 LED Chipset Adjustment", expanded=False):
        if st.session_state['lengths_list']:
            st.info("🔒 Locked: Adjustment in effect")
        else:
            adj = st.number_input("LED Chipset Adjustment (%)", min_value=-50.0, max_value=100.0, value=st.session_state['led_efficiency_gain_percent'], step=1.0)
            reason = st.text_input("Reason (e.g., Gen 2 LED +15% increase lumen output)", value=st.session_state['efficiency_reason'])
            st.session_state['led_efficiency_gain_percent'] = adj
            st.session_state['efficiency_reason'] = reason if reason else "Current Generation"

    # === AVERAGE LM/W STEP INCREMENT ===
    with st.expander("🔒 Average lm/W Step Increment", expanded=False):
        st.markdown("""
        115 lm/W is the average lumens per watt deviation across ECG driver power change increments in our current range.  
        For advanced users only.
        """)
        if st.session_state['lengths_list']:
            st.info(f"🔒 Locked at: {st.session_state['lmw_increment']} lm/W")
        else:
            st.session_state['lmw_increment'] = st.number_input("Average lm/W Step Increment", min_value=1.0, max_value=500.0, value=st.session_state['lmw_increment'], step=1.0)

    # === SELECTED LENGTHS TABLE ===
    st.markdown("## 📏 Selected Lengths for IES Generation")
    if not st.session_state['lengths_list']:
        st.warning("⚠️ No lengths selected. Please select build lengths to proceed.")
    else:
        table_rows = []
        base_lm_per_m = 400.0
        base_w_per_m = 11.6
        eff_gain = st.session_state['led_efficiency_gain_percent'] / 100.0

        for length in st.session_state['lengths_list']:
            lm_per_m = base_lm_per_m
            w_per_m = round(base_w_per_m * (1 - eff_gain), 1)

            total_lumens = round(lm_per_m * length, 1)
            total_watts = round(w_per_m * length, 1)
            lm_per_w = round(total_lumens / total_watts, 1) if total_watts else 0.0

            tier = "Core"
            if st.session_state['led_efficiency_gain_percent'] != 0:
                tier = "Professional"
            if st.session_state['led_pitch'] != 56.0 or st.session_state['end_plate_thickness'] != 5.5:
                tier = "Bespoke"

            lum_file_name = f"{luminaire_desc.split(' ')[0]} {optic} {length:.3f}m_{tier}"

            table_rows.append({
                "Length (m)": f"{length:.3f}",
                "Luminaire & IES File Name": lum_file_name,
                "CRI": cri_value,
                "CCT": cct_value,
                "Total Lumens": f"{total_lumens:.1f}",
                "Total Watts": f"{total_watts:.1f}",
                "Settings lm/W": f"{lm_per_w:.1f}",
                "Comments": st.session_state['efficiency_reason']
            })

        st.dataframe(pd.DataFrame(table_rows))

        # CSV Export
        df_export = pd.DataFrame(table_rows)
        st.download_button("📥 Download CSV Summary", data=df_export.to_csv(index=False).encode('utf-8'), file_name="Lengths_Summary.csv", mime="text/csv")

    # === DESIGN OPTIMISATION ===
    st.markdown("🎯 Design Optimisation")
    if not st.session_state['lengths_list']:
        st.warning("⚠️ No lengths selected. Optimisation disabled.")
    else:
        st.subheader("Target vs Achieved Lux Levels")
        target_lux = st.number_input("Target Lux Level", min_value=0.0, value=400.0, step=1.0)
        achieved_lux = st.number_input("Achieved Lux Level", min_value=0.0, value=405.0, step=1.0)

        diff_percent = round((achieved_lux - target_lux) / target_lux * 100, 1)
        st.write(f"Difference: {diff_percent}%")

        required_change = abs(diff_percent / 100) * base_lm_per_m
        increments_needed = (required_change / st.session_state['lmw_increment'])

        if increments_needed < 1:
            st.warning(f"⚠️ Dimming recommended to match target lux.")
        else:
            st.info(f"⚠️ Consider {'reducing' if diff_percent > 0 else 'increasing'} by {int(increments_needed + 0.9)} increments.")

        st.caption("Note: This enables theoretical model accuracy for future optimisations.")

    # === GENERATE IES FILES ===
    if st.session_state['lengths_list']:
        if st.button("Generate Optimised IES Files"):
            st.success("✅ IES Files Generation Complete! (Placeholder logic)")

else:
    st.info("Upload your Base IES file to begin optimisation.")
