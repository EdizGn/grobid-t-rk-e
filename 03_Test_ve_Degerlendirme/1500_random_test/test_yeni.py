import os
import requests
import glob
import time
import concurrent.futures

PDF_DIR = r"C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\1500_random_test\makaleler"
XML_DIR = r"C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\1500_random_test\grobid_xml_yeni_model"
GROBID_URL = "http://127.0.0.1:8070/api/processHeaderDocument"

os.makedirs(XML_DIR, exist_ok=True)

def wait_for_grobid(timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        try:
            res = requests.get("http://127.0.0.1:8070/api/isalive", timeout=5)
            if res.status_code == 200:
                return True
        except:
            time.sleep(5)
    return False

def process_pdf(pdf_path):
    basename = os.path.basename(pdf_path)
    makale_id = basename.replace("makale_", "").replace(".pdf", "")
    out_path = os.path.join(XML_DIR, f"makale_{makale_id}.xml")
    
    if os.path.exists(out_path):
        return f"[ATLANDI] {basename}"
        
    try:
        with open(pdf_path, 'rb') as f:
            files = {'input': (basename, f, 'application/pdf')}
            headers = {'Accept': 'application/xml'}
            res = requests.post(GROBID_URL, files=files, headers=headers, timeout=60)
            
        if res.status_code == 200:
            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(res.text)
            return f"[OK] {basename}"
        else:
            return f"[HATA] {basename} HTTP {res.status_code}"
    except Exception as e:
        return f"[HATA] {basename} çöktü: {str(e)}"

def main():
    print("Grobid bekleniyor...")
    if not wait_for_grobid():
        print("Grobid başlamadı!")
        return
        
    pdfs = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    print(f"Toplam {len(pdfs)} PDF Grobid'e gönderiliyor...")
    
    basarili = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for res in executor.map(process_pdf, pdfs):
            if "[OK]" in res:
                basarili += 1
                if basarili % 100 == 0:
                    print(f"İlerleme: {basarili} dosya çıkarıldı.")
                    
    print(f"Bitti! Toplam başarı: {basarili}/{len(pdfs)}")

if __name__ == '__main__':
    main()
