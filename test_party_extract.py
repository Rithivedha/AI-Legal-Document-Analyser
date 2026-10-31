import fitz
import re

doc = fitz.open('uploads/eb1074e5-30c7-4d0d-aa62-48f3d3c25e77_5 Land Lease Agreement.pdf')
first_pages = '\n'.join([doc[i].get_text() for i in range(min(5, len(doc)))])

def extract_parties(text):
    parties = []
    
    # 1. Look for Governor / Government / Company in preamble
    if "GOVERNOR OF ANDHRA PRADESH" in text.upper():
        parties.append("The Governor of Andhra Pradesh (Government of Andhra Pradesh / Lessor)")
    
    if "HYDERABAD INTERNATIONAL AIRPORT" in text.upper() or "HIAL" in text:
        parties.append("Hyderabad International Airport Limited (HIAL / Lessee)")
        
    # Check general patterns: "between X and Y"
    m = re.search(r'between[:\s]+([\w\s,.\'\"-]+?)(?:and|AND)\s+([\w\s,.\'\"-]+?)(?:\(hereinafter|hereinafter|dated|\n\n)', text)
    if m and not parties:
        p1 = re.sub(r'[\r\n]+', ' ', m.group(1)).strip()
        p2 = re.sub(r'[\r\n]+', ' ', m.group(2)).strip()
        if len(p1) < 120 and len(p2) < 120:
            parties.extend([p1, p2])

    return parties

parties = extract_parties(first_pages)
print("Extracted Parties:", parties)
