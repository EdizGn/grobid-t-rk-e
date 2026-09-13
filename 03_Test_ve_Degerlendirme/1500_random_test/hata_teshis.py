import os
import requests
from bs4 import BeautifulSoup
import concurrent.futures

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PDF_DIR = PROJE_KOK + r"\1500_random_test\makaleler"
GROBID_URL = "http://localhost:8070/api"

SAMPLE_IDS = [
    "14635","1302465","59465","301108","63585","337526","609016","142539","1292235",
    "1268152","1224788","411980","172783","1394398","532256","1246114","485532","1189889",
    "77751","369151","1414299","158246","206803","1253198","445474","1120026","1176894",
    "1402732","1325219","316018","1162752","1335235","1336929","247103","335545","240441",
    "318514","164997","409920","1239422","1404493","610956","95899","1257234","285465",
    "105839","1127957","142416","489933","166594"
]

def analyze_pdf(makale_id):
    pdf_path = os.path.join(PDF_DIR, f"makale_{makale_id}.pdf")
    if not os.path.exists(pdf_path):
        return "DOSYA_YOK"
        
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
            
        # 1. Segmentation Testi
        files = {'input': (f"makale_{makale_id}.pdf", pdf_bytes, 'application/pdf')}
        seg_res = requests.post(f"{GROBID_URL}/processSegmentation", files=files, timeout=60)
        
        if seg_res.status_code != 200:
            return "GROBID_ÇÖKTÜ"
            
        seg_soup = BeautifulSoup(seg_res.text, "lxml-xml")
        
        # Eğer text tamamen boşsa (veya 100 karakterden kısaysa) scanned PDF'dir
        raw_text = seg_soup.get_text().strip()
        if len(raw_text) < 150:
            return "TARANMIŞ_PDF_METİN_YOK"
            
        # Segmentasyon modelinde <front> tagi var mı?
        front_tag = seg_soup.find("front")
        if not front_tag or len(front_tag.get_text(strip=True)) < 10:
            return "SEGMENTASYON_HATASI" # Model başlığı tamamen Body veya Note sanmış
            
        # 2. Header Model Testi
        files = {'input': (f"makale_{makale_id}.pdf", pdf_bytes, 'application/pdf')}
        hdr_res = requests.post(f"{GROBID_URL}/processHeaderDocument", files=files, timeout=60)
        
        hdr_soup = BeautifulSoup(hdr_res.text, "lxml-xml")
        title_tag = hdr_soup.find("title", type="main")
        
        if not title_tag or not title_tag.get_text(strip=True):
            return "HEADER_MODEL_HATASI" # Segmentasyon başlığı buldu, ama Header Modeli bunu <title> olarak işaretleyemedi
            
        return "DİĞER_HATA"
        
    except Exception as e:
        return f"HATA: {e}"

def main():
    print(f"Toplam {len(SAMPLE_IDS)} örnek üzerinde Grobid Teşhis Röntgeni başlatılıyor...\n")
    
    sonuclar = {
        "TARANMIŞ_PDF_METİN_YOK": 0,
        "SEGMENTASYON_HATASI": 0,
        "HEADER_MODEL_HATASI": 0,
        "GROBID_ÇÖKTÜ": 0,
        "DİĞER_HATA": 0
    }
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_id = {executor.submit(analyze_pdf, mid): mid for mid in SAMPLE_IDS}
        for future in concurrent.futures.as_completed(future_to_id):
            mid = future_to_id[future]
            try:
                res = future.result()
                if res in sonuclar:
                    sonuclar[res] += 1
                else:
                    print(f"Beklenmeyen Sonuç ({mid}): {res}")
            except Exception as e:
                print(f"Çöktü ({mid}): {e}")
                
    print("=== TEŞHİS RAPORU ===")
    total = len(SAMPLE_IDS)
    for k, v in sonuclar.items():
        yuzde = (v / total) * 100
        print(f"{k}: {v} makale (%{yuzde:.1f})")

if __name__ == "__main__":
    main()
