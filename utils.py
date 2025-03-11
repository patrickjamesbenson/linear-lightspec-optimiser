import pandas as pd
import numpy as np
import io
import zipfile

def parse_ies_file(file_content):
    # Simplified parser, replace with your existing or advanced parser later
    lines = file_content.splitlines()
    header_lines = []
    data_start = 0
    for i, line in enumerate(lines):
        header_lines.append(line)
        if line.strip().isdigit():
            data_start = i
            break
    return {
        "header": header_lines,
        "data": lines[data_start:]
    }

def modify_candela_data(data_lines, efficiency_gain=1.0):
    # Simplified candela scaling, apply efficiency multiplier
    modified_data = []
    for line in data_lines:
        try:
            numbers = [float(n) * efficiency_gain for n in line.split()]
            modified_line = ' '.join([str(round(num, 3)) for num in numbers])
            modified_data.append(modified_line)
        except:
            modified_data.append(line)
    return modified_data

def create_ies_file(header, data):
    return "\n".join(header + data)

def create_zip(files_dict):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for filename, content in files_dict.items():
            zf.writestr(filename, content)
    buffer.seek(0)
    return buffer
