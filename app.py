# === Base Build Methodology (Expander with Toggle Lock) ===
with st.expander("📂 Base Build Methodology", expanded=False):
    
    # Initialize state
    if 'locked' not in st.session_state:
        st.session_state['locked'] = False
        st.session_state['lengths_list'] = []

    # Toggle Button for Lock/Unlock
    if st.session_state['locked']:
        if st.button("🔓 Unlock Base Build Methodology"):
            st.session_state['locked'] = False
    else:
        if st.button("🔒 Lock Base Build Methodology"):
            st.session_state['locked'] = True

    # Display warning if UNLOCKED
    if not st.session_state['locked']:
        st.warning("⚠️ Adjust these only if you understand the impact on manufacturability.")
        
        # Editable fields when UNLOCKED
        end_plate_thickness = st.number_input(
            "End Plate Expansion Gutter (mm)", 
            min_value=0.0, 
            value=5.5, 
            step=0.1
        )

        led_pitch = st.number_input(
            "LED Series Module Pitch (mm)", 
            min_value=14.0,  # Updated minimum pitch
            value=56.0, 
            step=0.1
        )

        # Store in session_state once locked
        if st.session_state['locked']:
            st.session_state['end_plate_thickness'] = end_plate_thickness
            st.session_state['led_pitch'] = led_pitch

    else:
        # When LOCKED, show the fixed values
        end_plate_thickness = st.session_state.get('end_plate_thickness', 5.5)
        led_pitch = st.session_state.get('led_pitch', 56.0)

        st.info(f"🔒 Locked: End Plate Expansion Gutter = {end_plate_thickness} mm | LED Series Module Pitch = {led_pitch} mm")
