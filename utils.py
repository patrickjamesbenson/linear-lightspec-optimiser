import io
import zipfile

def parse_ies_file(uploaded_file):
    # Dummy data for demo - parse your actual IES here
    return {
        "luminaire_name": "BLine 8585D 11.6W - 80CRI - 3000K",
        "length_m": 1.0,
        "lumens_per_m": 1500.0,
        "watts_per_m": 11.6,
        "efficacy": 129.31
    }

def validate_lengths(desired_length_m, end_plate_mm, led_pitch_mm):
    min_length_mm = 571
    end_total_mm = end_plate_mm * 2
    usable_length_mm = desired_length_m * 1000 - end_total_mm
    board_count = round(usable_length_mm / led_pitch_mm)

    shorter_mm = (board_count - 1) * led_pitch_mm + end_total_mm
    longer_mm = (board_count + 1) * led_pitch_mm + end_total_mm

    return shorter_mm / 1000, longer_mm / 1000

def calculate_recommendations(ies_data, achieved_lux, target_lux, efficiency_gain, length_choice_m):
    lux_ratio = target_lux / achieved_lux
    adjusted_lm_m = ies_data["lumens_per_m"] * lux_ratio
    adjusted_lm_m *= (1 + efficiency_gain / 100)

    new_efficacy = ies_data["efficacy"] * (1 + efficiency_gain / 100)
    new_watts_m = adjusted_lm_m / new_efficacy

    return {
        "lumens_per_m": adjusted_lm_m,
        "watts_per_m": new_watts_m,
        "efficacy": new_efficacy,
        "length_m": length_choice_m
    }

def generate_ies_files_zip(rec, end_plate_mm, led_pitch_mm):
    # Placeholder for actual IES generation
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
        for length in [1.0, 2.0, 4.5]:
            filename = f"BLine_{length:.3f}m_Optimised.ies"
            content = f"""IESNA:LM-63-2002
[MANUFAC] Evolt
[LUMINAIRE] BLine Optimised
TILT=NONE
1 1500 -1 91 4 1 2 0.08 {length:.3f} 0.09 1 1 {rec['watts_per_m'] * length:.2f}
90 0 30 60
0 100 200 300 400
"""
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer
