# === SELECTED LENGTHS TABLE ===
st.markdown("## 📏 Selected Lengths for IES Generation")

delete_index = None  # <== Initialize delete index before loop

if st.session_state['lengths_list']:
    # HEADERS
    header_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 2])
    headers = ["", "Length (m)", "Luminaire & IES File Name", "CRI", "CCT", "Total Lumens", "Total Watts", "Settings lm/W", "Comments"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    # DATA ROWS
    for idx, length in enumerate(st.session_state['lengths_list']):
        total_lumens = round(new_lm_per_m * length, 1)
        total_watts = round(new_w_per_m * length, 1)
        lm_per_w = round(total_lumens / total_watts, 1) if total_watts != 0 else 0.0

        # Product Tier Logic
        if st.session_state['end_plate_thickness'] != 5.5 or st.session_state['led_pitch'] != 56.0:
            tier = "Bespoke"
        elif led_efficiency_gain_percent != 0:
            tier = "Professional"
        elif st.session_state['led_pitch'] % 4 != 0:
            tier = "Advanced"
        else:
            tier = "Core"

        luminaire_file_name = f"{luminaire_name_base}_{length:.3f}m_{tier}"
        comments = efficiency_reason if led_efficiency_gain_percent != 0 else ""

        row_cols = st.columns([1, 2, 4, 1, 1, 2, 2, 2, 2])

        if row_cols[0].button("🗑️", key=f"del_{idx}"):
            delete_index = idx  # <-- Collect delete index instead of deleting immediately

        row_cols[1].write(f"{length:.3f}")
        row_cols[2].write(luminaire_file_name)
        row_cols[3].write(cri_value)
        row_cols[4].write(cct_value)
        row_cols[5].write(f"{total_lumens:.1f}")
        row_cols[6].write(f"{total_watts:.1f}")
        row_cols[7].write(f"{lm_per_w:.1f}")
        row_cols[8].write(comments)

    # After table rendering, process the deletion
    if delete_index is not None:
        st.session_state['lengths_list'].pop(delete_index)
        st.experimental_rerun()

else:
    st.info("No lengths selected yet. Click above to add lengths.")
