# === BASE BUILD METHODOLOGY ===
with st.expander("📂 Base Build Methodology", expanded=False):
    # Auto-lock if lengths_list has items
    if st.session_state['lengths_list']:
        st.session_state['locked'] = True  # Ensure locked state stays synced

    if st.session_state['locked']:
        st.info(f"🔒 Base Build locked. End Plate: {st.session_state['end_plate_thickness']} mm | LED Pitch: {st.session_state['led_pitch']} mm")
    else:
        st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
        # Editable ONLY if not locked
        st.session_state['end_plate_thickness'] = st.number_input(
            "End Plate Expansion Gutter (mm)",
            min_value=0.0,
            value=st.session_state['end_plate_thickness'],
            step=0.1,
            disabled=st.session_state['locked']
        )
        st.session_state['led_pitch'] = st.number_input(
            "LED Series Module Pitch (mm)",
            min_value=14.0,
            value=st.session_state['led_pitch'],
            step=0.1,
            disabled=st.session_state['locked']
        )

    # Lock / Unlock buttons only when NO lengths exist
    if not st.session_state['lengths_list']:
        if st.session_state['locked']:
            if st.button("🔓 Unlock Base Build Methodology"):
                st.session_state['locked'] = False
        else:
            if st.button("🔒 Lock Base Build Methodology"):
                st.session_state['locked'] = True
