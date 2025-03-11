import io
import zipfile

def parse_ies_file(file_content):
    lines = file_content.splitlines()

    # Find the TILT= line
    tilt_index = next((i for i, line in enumerate(lines) if line.strip().startswith("TILT=")), None)
    if tilt_index is None:
        raise ValueError("TILT= line not found, invalid IES file")

    header_lines = lines[:tilt_index + 1]
    data_lines = lines[tilt_index + 1:]

    return {
        'header': header_lines,
        'data': data_lines
    }

def modify_candela_data(data, multiplier):
    modified_data = []
    for line in data:
        numbers = line.strip().split()
        try:
            scaled = [str(float(n) * multiplier) for n in numbers]
            modified_data.append(' '.join(scaled))
        except ValueError:
            # If it isn't a number line, just append it untouched
            modified_data.append(line)
    return modified_data

def create_ies_file(header, data):
    # Join header and data sections
    content = '\n'.join(header + data)
    return content

def create_zip(file_dict):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for filename, content in file_dict.items():
            zip_file.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer
