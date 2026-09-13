import os
import json
import PyPDF2
from bs4 import BeautifulSoup
import concurrent.futures

PDF_DIR = r"C:\Users\EG\Desktop\Tubitak___is\1500_random_test\makaleler"
XML_DIR = r"C:\Users\EG\Desktop\Tubitak___is\1500_random_test\grobid_xml"

def analyze_offline(makale_id):
    pdf_path = os.path.join(PDF_DIR, f"makale_{makale_id}.pdf")
    xml_path = os.path.join(XML_DIR, f"makale_{makale_id}.xml")
    
    # 1. Metin var mı? (Taranmış PDF Kontrolü)
    has_text = False
    try:
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) > 0:
                    text = reader.pages[0].extract_text()
                    if text and len(text.strip()) > 50:
                        has_text = True
    except Exception:
        return "PDF_BOZUK_VEYA_OKUNAMIYOR"
        
    if not has_text:
        return "TARANMIŞ_VEYA_METİN_YOK_PDF"
        
    # 2. XML Var mı ve Dolu mu? (Grobid Çökme Kontrolü)
    if not os.path.exists(xml_path):
        return "GROBID_ÇÖKMESİ_XML_YOK"
        
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
            
        if len(xml_content.strip()) < 100:
            return "GROBID_ÇÖKMESİ_XML_BOŞ"
            
        soup = BeautifulSoup(xml_content, "xml")
        
        # 3. Model Hatası Tespiti
        # XML var, metin de var, ama başlık bulunamamış.
        # Acaba <front> tagi var mı?
        front = soup.find('front')
        title = soup.find('title', type='main')
        
        if not front:
            return "SEGMENTASYON_HATASI (Header bloğunu hiç bulamamış)"
            
        if title and not title.text.strip():
            return "HEADER_MODEL_HATASI (Header'ı bulmuş ama başlığı ayırt edememiş)"
            
        return "BİLİNMEYEN_MODEL_HATASI"
        
    except Exception as e:
        return "XML_OKUMA_HATASI"

def main():
    print("Tüm hatalı makaleler taranıyor...")
    with open(r'C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\dashboard\data.js', 'r', encoding='utf-8') as f:
        js_icerik = f.read().replace('const kiyaslamaVerileri = ', '').strip().rstrip(';')
        data = json.loads(js_icerik)
        
    failed_ids = [str(d['Makale ID']) for d in data if d.get('Başlık Bulma Oranı (%)') == 0.0 or d.get('Başlık Bulma Oranı (%)') is None]
    print(f"Toplam tespit edilecek başarısız makale sayısı: {len(failed_ids)}")
    
    sonuclar = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_id = {executor.submit(analyze_offline, mid): mid for mid in failed_ids}
        for future in concurrent.futures.as_completed(future_to_id):
            res = future.result()
            sonuclar[res] = sonuclar.get(res, 0) + 1
            
    print("\n=== TÜM BAŞARISIZ MAKALELER İÇİN KESİN KÖK NEDEN RAPORU ===")
    for k, v in sorted(sonuclar.items(), key=lambda item: item[1], reverse=True):
        yuzde = (v / len(failed_ids)) * 100
        print(f"{k}: {v} makale (%{yuzde:.1f})")

if __name__ == "__main__":
    main()
