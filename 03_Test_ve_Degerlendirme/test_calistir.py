import os
import glob
import requests
import time
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PDF_DIR = os.path.join(BASE_DIR, "makaleler_test")
GROBID_XML_DIR = os.path.join(TEST_PDF_DIR, "grobid_xml")

os.makedirs(GROBID_XML_DIR, exist_ok=True)

GROBID_URL = "http://localhost:8070/api/processHeaderDocument"

def wait_for_grobid():
    print("Grobid sunucusunun başlaması bekleniyor (Derleme işlemi uzun sürebilir)...")
    for i in range(120): # 120 * 5 = 600 saniye (10 dakika) bekler
        try:
            res = requests.get("http://localhost:8070/api/isalive", timeout=3)
            if res.status_code == 200 and res.text == "true":
                print("Grobid sunucusu aktif!")
                return True
        except:
            pass
        time.sleep(5)
    return False

def process_pdf(pdf_path):
    basename = os.path.basename(pdf_path)
    makale_id = basename.replace("makale_", "").replace(".pdf", "")
    xml_name = f"makale_{makale_id}.xml"
    out_path = os.path.join(GROBID_XML_DIR, xml_name)
    
    if os.path.exists(out_path):
        return f"[ATLANDI] {xml_name} zaten var."
        
    try:
        with open(pdf_path, 'rb') as f:
            files = {'input': (basename, f, 'application/pdf')}
            response = requests.post(GROBID_URL, files=files, timeout=60)
            
        if response.status_code == 200:
            with open(out_path, 'w', encoding='utf-8') as out_f:
                out_f.write(response.text)
            return f"[OK] {xml_name} oluşturuldu."
        elif response.status_code == 204:
            return f"[BOS] {xml_name} boş döndü (204)."
        else:
            return f"[HATA] {basename} HTTP {response.status_code}"
    except Exception as e:
        return f"[HATA] {basename} işlenirken çöktü: {str(e)}"

def ana_islem():
    if not wait_for_grobid():
        print("HATA: Grobid sunucusu (localhost:8070) 10 dakika boyunca yanıt vermedi!")
        print("Lütfen Docker container'ını './gradlew run' komutu ile başlatın.")
        return
        
    pdf_files = glob.glob(os.path.join(TEST_PDF_DIR, "*.pdf"))
    if not pdf_files:
        print(f"Uyarı: {TEST_PDF_DIR} klasöründe test PDF'i bulunamadı.")
        return
        
    print(f"Toplam {len(pdf_files)} test PDF'i Grobid'den (Yeni Eğitilmiş Model) geçiriliyor...")
    
    basarili = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_pdf, p): p for p in pdf_files}
        
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            print(res)
            if "[OK]" in res:
                basarili += 1
                
    print(f"\nİşlem bitti! {basarili}/{len(pdf_files)} PDF başarıyla Grobid'den çıkarıldı.")
    print(f"XML'ler şu klasörde: {GROBID_XML_DIR}")

if __name__ == "__main__":
    ana_islem()
