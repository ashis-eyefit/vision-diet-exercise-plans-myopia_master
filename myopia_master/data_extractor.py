import re
import fitz  # PyMuPDF

def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_fields(text):
    data = {
        "name": None, "age": None, "gender": None, "ethnicity": None,
        "axial_length_right": None, "axial_length_left": None,
        "spherical_eq_right": None, "spherical_eq_left": None,
        "keratometry_right": None, "keratometry_left": None,
        "al_percentile_right": None, "al_percentile_left": None,
        "cylinder_right": None, "cylinder_left": None
    }

    lines = text.splitlines()
    full_text = " ".join(lines)

    # Name
    name_match = re.search(r"Name\s+([A-Z ]{3,})", text)
    if name_match:
        data["name"] = name_match.group(1).strip()

    # Age
    age_match = re.search(r"Age\s*.*?(\d{1,2}(?:\.\d)?)\s*[Yy]", text)
    if age_match:
        data["age"] = float(age_match.group(1))

    # Gender
    gender_match = re.search(r"Gender\s+(\w+)", text)
    if gender_match:
        data["gender"] = gender_match.group(1).strip().lower()

    # Ethnicity
    ethnicity_match = re.search(r"Ethnicity\s+(\w+)", text)
    if ethnicity_match:
        data["ethnicity"] = ethnicity_match.group(1).strip()

    # SEQ (signed values)
    seq_matches = re.findall(r"SEQ\s*([+-]?[0-9.]+)\s*D", text)
    if len(seq_matches) >= 2:
        data["spherical_eq_right"] = float(seq_matches[0])
        data["spherical_eq_left"] = float(seq_matches[1])

    # Cylinder (signed values)
    cyl_matches = re.findall(r"Cylinder\s*([+-]?[0-9.]+)\s*D", text)
    if len(cyl_matches) >= 2:
        data["cylinder_right"] = float(cyl_matches[0])
        data["cylinder_left"] = float(cyl_matches[1])

    # Axial Length
    axial_matches = re.findall(r"Axial length\s*([0-9.]+)", text)
    if len(axial_matches) >= 2:
        data["axial_length_right"] = float(axial_matches[0])
        data["axial_length_left"] = float(axial_matches[1])

    # Keratometry
    kerato_matches = re.findall(r"Keratometric\s+Power\s*([0-9.]+)\s*D", text)
    if len(kerato_matches) >= 2:
        data["keratometry_right"] = float(kerato_matches[0])
        data["keratometry_left"] = float(kerato_matches[1])

    # AL Percentile (from full text narrative)
    al_percentile_match = re.search(
        r"located at the (\d{1,3}).. and (\d{1,3}).. percentile", full_text, re.IGNORECASE)
    if al_percentile_match:
        data["al_percentile_right"] = int(al_percentile_match.group(1))
        data["al_percentile_left"] = int(al_percentile_match.group(2))

    return data

def parse_myopia_data(pdf_path):
    text = extract_text(pdf_path)
    return extract_fields(text)

# ===================== Manual Trigger =====================
if __name__ == "__main__":
    pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\MM005.pdf"
    result = parse_myopia_data(pdf_path)
    print(result)
