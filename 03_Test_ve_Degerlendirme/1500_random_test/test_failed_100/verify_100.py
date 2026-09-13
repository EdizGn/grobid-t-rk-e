import os
import glob
import json
import re

out_dir = r"C:\Users\EG\Desktop\Tubitak___is\test_failed_100_out"
titles_map = r"C:\Users\EG\Desktop\Tubitak___is\test_failed_100\titles_map.json"

with open(titles_map, "r", encoding="utf-8") as f:
    titles = json.load(f)

def normalize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

header_errors = []
seg_errors = []

for mid, true_title in titles.items():
    xml_path = os.path.join(out_dir, f"makale_{mid}.training.header.tei.xml")
    if not os.path.exists(xml_path):
        seg_errors.append((mid, true_title))
        continue
        
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    norm_content = normalize(content)
    words = str(true_title).split()[:4]
    search_str = normalize(" ".join(words))
    
    if (search_str and search_str in norm_content) or (normalize(true_title) in norm_content):
        header_errors.append((mid, true_title))
    else:
        seg_errors.append((mid, true_title))

print(f"Header Hatalarindan İlk 3: {header_errors[:3]}")
print(f"Segmentasyon Hatalarindan İlk 3: {seg_errors[:3]}")

# Segmentasyon hatalari icinde taranmis PDF (metin yok) var mi diye bakalim
import PyPDF2
scanned = []
for mid, t in seg_errors:
    pdf_path = os.path.join(r"C:\Users\EG\Desktop\Tubitak___is\test_failed_100", f"makale_{mid}.pdf")
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                if not text or len(text.strip()) < 50:
                    scanned.append(mid)
        except:
            pass

print(f"Segmentasyon Hatasi sanilan ama aslinda taranmis (Scanned) PDF olanlarin sayisi: {len(scanned)}")
