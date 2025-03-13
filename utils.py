import re

def parse_luminaire_description(description):
    """
    Extracts CRI and CCT from luminaire description.
    Expected format: "BLine 8585D 11.6W - 80CRI - 3000K"
    """
    try:
        cri_match = re.search(r'(\d{2})CRI', description)
        cct_match = re.search(r'(\d{4})K', description)

        cri = f"{cri_match.group(1)}CRI" if cri_match else "N/A"
        cct = f"{cct_match.group(1)}K" if cct_match else "N/A"

        return cri, cct
    except Exception as e:
        print(f"Error parsing description: {e}")
        return "N/A", "N/A"
