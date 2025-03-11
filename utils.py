import io
import zipfile

# === PARSE FUNCTION ===
def parse_ies_file(file_content):
    lines = file_content.strip().splitlines()
    header = []
    data = []
    collecting_data = False
    tilt_found = False
    photometric_numbers = []

    for idx, line in enumerate(lines):
        line = line.strip()

        if not collecting_data:
            header.append(line)
            if line.startswith("TILT="):
                tilt_found = True
                collecting_data = True  # Start grabbing photometric data
        else:
            if tilt_found:
                # Start collecting numbers after TILT line
                numbers = line.split()
                photometric_numbers.extend(numbers)

                # Keep collecting until we have 13 numbers
                if len(photometric_numbers) >= 13:
                    # Separate photometric params from the rest
                    photometric_data = ' '.join(photometric_numbers[:13])
                    remaining_data = photometric_numbers[13:]

                    # Append the joined 13 parameters to data
                    data.append(photometric_data)

                    # Add any leftover numbers as a new line
                    if remaining_data:
                        data.append(' '.join(remaining_data))

                    # Add the remaining lines
                    for remaining_line in lines[idx + 1:]:
                        data.append(remaining_line.strip())
                    break
            else:
                data.append(line)

    return {
        'header': header,
        'data': data,
    }

# === MODIFY CANDELA DATA ===
def modify_candela_data(data_lines, efficiency_multiplier):
    modified_data = []
    header_processed = False

    for line in data_lines:
        if not header_processed:
            # Skip the photometric parameters line already processed
            header_processed = True
            modified_data.append(line)
            continue

        # Try to scale candela values in data lines
        try:
            numbers = list(map(float, line.strip().split()))
            scaled_numbers = [round(num * efficiency_multiplier, 4) for num in numbers]
            modified_line = ' '.join(map(str, scaled_numbers))
            modified_data.append(modified_line)
        except ValueError:
            # Leave non-numeric lines untouched
            modified_data.append(line)

    return modified_data

# === CREATE IES FILE ===
def create_ies_file(header_lines, data_lines):
    # Make sure 13 photometric parameters are on one line
    rebuilt_ies = "\n".join(header_lines) + "\n"

    if "TILT=" not in header_lines[-1]:
        rebuilt_ies += "TILT=NONE\n"

    # Add data block, clean spacing, and ensure single-line photometric params
    rebuilt_ies += "\n".join(data_lines) + "\n"
    return rebuilt_ies

# === CREATE ZIP FILE ===
def create_zip(file_dict):
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_data in file_dict.items():
            zip_file.writestr(file_name, file_data)

    zip_buffer.seek(0)
    return zip_buffer
