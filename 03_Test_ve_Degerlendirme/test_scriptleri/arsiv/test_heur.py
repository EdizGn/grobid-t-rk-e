import os, re

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
path = PROJE_KOK + r"\grobid\dis_veriler\segmentation_islem\makale_101823.training.segmentation.tei.xml"
with open(path, "r", encoding="utf-8") as f: text = f.read()

# Heuristic approach
# 1. Strip all <front>, </front>, <body>, </body>
text = text.replace("<front>", "").replace("</front>", "").replace("<body>", "").replace("</body>", "")
text_start = re.search(r'<text[^>]*>', text)

if text_start:
    search_text = text[text_start.end():]
    # Find "ÖZET", "ABSTRACT", "Anahtar"
    match = re.search(r'(?i)(ÖZET|ABSTRACT|Anahtar|Keywords)[\s\S]{1,1000}?<lb\s*/>\s*<lb\s*/>', search_text)
    if match:
        end_pos = text_start.end() + match.end()
        part1 = text[:text_start.end()]
        part2 = text[text_start.end():end_pos]
        part3 = text[end_pos:]
        
        part3 = part3.replace("</text>", "</body>\n\t</text>")
        final = part1 + "<front>" + part2 + "</front>\n\t<body>" + part3
        print(final[:1500])
    else:
        print("No match")
