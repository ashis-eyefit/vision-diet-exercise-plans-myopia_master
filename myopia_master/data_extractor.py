from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import pdfplumber
import os
import re


## Extractin text from the scanned OCR document
def extract_text_from_pdf(pdf_path, dpi=300):
    """
    Converting scanned PDF pages to images and extracts text using OCR.
    Returns combined raw text for all pages.
    """
    poppler_path = r"C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin"
    pages = convert_from_path(pdf_path, dpi=dpi, poppler_path= poppler_path)
    full_text = ""

    for i, page in enumerate(pages):
        image_path = f"page_{i+1}.png"
        page.save(image_path, "PNG")
        
        # OCR using Tesseract
        text = pytesseract.image_to_string(Image.open(image_path))
        full_text += f"\n\n--- Page {i+1} ---\n\n{text}"
        # Clean up image files after OCR
        os.remove(image_path)  

    return full_text


def extract_text_with_pdfplumber(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join([page.extract_text() or '' for page in pdf.pages])
        return full_text
    except Exception as e:
        print("pdfplumber extraction failed:", e)
        return None

### Parsing the data from the extracted text using regex
import re

def parse_myopia_data(pdf_path):
    text_ract = extract_text_from_pdf(pdf_path)
    text_plumb = extract_text_with_pdfplumber(pdf_path)
    text = text_ract + text_plumb

    ## Keratometry
    #  Search lines around 'keratometric' for patterns like 42.4 D and 42.3 D
    lines = text.splitlines()
    kerato_right, kerato_left = None, None

    for i, line in enumerate(lines):
        if "keratometric" in line.lower():
            for j in range(i, min(i + 5, len(lines))):
                match = re.findall(r"([0-9]{2}\.[0-9])\s*D", lines[j])
                if len(match) >= 2:
                    kerato_right, kerato_left = float(match[0]), float(match[1])
                    break
            break

    def extract_single(pattern, text, dtype=float):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return dtype(match.group(1))
            except:
                return match.group(1)  # for name/ethnicity/gender etc.
        return None

    def extract_pair(pattern, text, dtype=float):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return dtype(match.group(1)), dtype(match.group(2))
            except:
                return None, None
        return None, None

    # Axial Length
    axial_lengths = re.findall(r"Axial length\s*([0-9]{2}\.[0-9]+)", text)
    axial_right = float(axial_lengths[0]) if len(axial_lengths) > 0 else None
    axial_left = float(axial_lengths[1]) if len(axial_lengths) > 1 else None

    # Cylinder
    cylinders = re.findall(r"Cylinder\s*(-?[0-9.]+)\s*D", text)
    cylinder_right = float(cylinders[0]) if len(cylinders) > 0 else None
    cylinder_left = float(cylinders[1]) if len(cylinders) > 1 else cylinder_right

    # ✅ AL Percentile
    match = re.search(
        r"located at the\s+(\d{1,3})\w{2}\s+and\s+(\d{1,3})\w{2}\s+percentile", text, re.IGNORECASE)
    al_percentile_right = int(match.group(1)) if match else None
    al_percentile_left = int(match.group(2)) if match else None

    # SEQ (Spherical Equivalent)
    seqs = re.findall(r"SEQ\s*(-?[0-9.]+)\s*D", text)
    spherical_eq_right = float(seqs[0]) if len(seqs) > 0 else None
    spherical_eq_left = float(seqs[1]) if len(seqs) > 1 else None

    # AL Percentiles
    match = re.search(r"located at the\s+(\d{1,3})[a-z]{2}\s+and\s+(\d{1,3})[a-z]{2}\s+percentile", text, re.IGNORECASE)
    al_percentile_right = int(match.group(1)) if match else None
    al_percentile_left = int(match.group(2)) if match else None

    return {
        "name": extract_single(r"Name\s*\n*([A-Za-z ]+)", text, str),
        "age": extract_single(r"Date of birth, Age\s*[\n:]*\d{2}/\d{2}/\d{4},\s*([0-9.]+)", text),
        "gender": extract_single(r"Gender\s*([A-Za-z]+)", text, str),
        "ethnicity": extract_single(r"Ethnicity\s*([A-Za-z ]+)", text, str),

        "axial_length_right": axial_right,
        "axial_length_left": axial_left,

        "spherical_eq_right": spherical_eq_right,
        "spherical_eq_left": spherical_eq_left,

        "keratometry_right": kerato_right,
        "keratometry_left": kerato_left,

        "al_percentile_right": al_percentile_right,
        "al_percentile_left": al_percentile_left,

        "cylinder_right": cylinder_right,
        "cylinder_left": cylinder_left,
    }




# Absolute path for scanned PDF
#pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\myopia_master.pdf"
#pdf_path = r"C:\Users\DELL\Desktop\R1_Project\Vision_Exercise_Project\data\raw\Myopia-Report-sample.pdf"


#data = parse_myopia_data(pdf_path)
#print(data)