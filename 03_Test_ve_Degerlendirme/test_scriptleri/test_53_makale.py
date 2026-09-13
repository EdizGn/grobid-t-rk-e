import os
import glob
import time
import requests
import sys
import subprocess
import shutil

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except:
    pass

ONARILMIS_KLASOR = "c:/Users/EG/Desktop/Tubitak___is/03_Test_ve_Degerlendirme/Onarilmis_Veriler"
XML_Cikti_Klasoru = "c:/Users/EG/Desktop/Tubitak___is/03_Test_ve_Degerlendirme/Onarilmis_XMLler"
DB_YOLU = "c:/Users/EG/Desktop/Tubitak___is/03_Test_ve_Degerlendirme/makaleler_test/test_metadatalar.db"
KARSILASTIRMA_SCRIPT = "c:/Users/EG/Desktop/Tubitak___is/grobid/karsilastirma_tmp.py"
JSON_SONUC = "c:/Users/EG/Desktop/Tubitak___is/03_Test_ve_Degerlendirme/Onarilmis_XMLler/onarim_sonuclari.json"

os.makedirs(XML_Cikti_Klasoru, exist_ok=True)

def wait_for_grobid():
    print("Docker uzerindeki GROBID servisinin baslamasi bekleniyor (http://localhost:8070)...")
    for _ in range(30):
        try:
            r = requests.get('http://localhost:8070/api/isalive', timeout=2)
            if r.status_code == 200:
                print("\n✅ GROBID servisi hazir!")
                return True
        except:
            pass
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(3)
    return False

def pdf_to_xml():
    pdfler = glob.glob(os.path.join(ONARILMIS_KLASOR, "**", "*.pdf"), recursive=True)
    if not pdfler:
        print(f"HATA: {ONARILMIS_KLASOR} klasorunde PDF bulunamadi!")
        return 0

    print(f"\nToplam {len(pdfler)} adet onarilmis PDF GROBID ile isleniyor...")
    
    basarili = 0
    for i, pdf_yolu in enumerate(pdfler):
        dosya_adi = os.path.basename(pdf_yolu)
        xml_dosya_adi = dosya_adi.replace(".pdf", ".xml")
        xml_yolu = os.path.join(XML_Cikti_Klasoru, xml_dosya_adi)
        
        print(f"[{i+1}/{len(pdfler)}] Isleniyor: {dosya_adi} ... ", end="")
        sys.stdout.flush()
        
        try:
            with open(pdf_yolu, 'rb') as f:
                files = {'input': (dosya_adi, f, 'application/pdf')}
                r = requests.post('http://localhost:8070/api/processHeaderDocument', files=files, timeout=120)
                
            if r.status_code == 200:
                with open(xml_yolu, "w", encoding="utf-8") as out_f:
                    out_f.write(r.text)
                print("✅ XML Olusturuldu")
                basarili += 1
            else:
                print(f"❌ GROBID Hatasi: HTTP {r.status_code}")
        except Exception as e:
            print(f"❌ BAGLANTI HATASI: {e}")
            
    return basarili

def run_comparison():
    print("\n=======================================================")
    print("📊 Karsilastirma (Test) Sonuclari Hesaplanir...")
    print("=======================================================")
    
    cmd = [
        "python", KARSILASTIRMA_SCRIPT,
        "--grobid_klasoru", XML_Cikti_Klasoru,
        "--json_dosyasi", JSON_SONUC,
        "--cikti_klasoru", XML_Cikti_Klasoru,
        "--db_adi", "test_metadatalar.db"
    ]
    
    shutil.copy2(DB_YOLU, os.path.join(XML_Cikti_Klasoru, "test_metadatalar.db"))
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Test tamamlandi. Sonuclar Onarilmis_XMLler klasorunde.")
    except Exception as e:
        print(f"Karsilastirma scripti calistirilirken hata olustu: {e}")

if __name__ == "__main__":
    if wait_for_grobid():
        xml_sayisi = pdf_to_xml()
        if xml_sayisi > 0:
            run_comparison()
