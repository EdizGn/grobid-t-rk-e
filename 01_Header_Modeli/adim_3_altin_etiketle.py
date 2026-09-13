import os
import glob
import sqlite3
import json
import subprocess

# Yollar
ALTIN_KLASOR = r"C:\Users\EG\Desktop\Tubitak___is\makaleler_altin"
RAW_DIR = os.path.join(ALTIN_KLASOR, "out")
DB_PATH = os.path.join(ALTIN_KLASOR, "altin_metadatalar.db")
OUT_DIR = os.path.join(ALTIN_KLASOR, "xml_egitim_verisi")

os.makedirs(OUT_DIR, exist_ok=True)
temp_json = os.path.join(ALTIN_KLASOR, "temp_metadata.json")

def etiketleme_baslat():
    raw_files = glob.glob(os.path.join(RAW_DIR, "*.training.header.tei.xml"))
    if not raw_files:
        print(f"Hata: {RAW_DIR} klasöründe hiç ham XML bulunamadı!")
        print("Lütfen önce Docker createTrainingHeader komutunu çalıştırın.")
        return
        
    print(f"Toplam {len(raw_files)} adet ham XML dosyası bulundu.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    basarili_sayisi = 0
    hata_sayisi = 0
    toplam_metrikler = {}

    for raw_path in raw_files:
        basename = os.path.basename(raw_path)
        # makale_12345.training.header.tei.xml -> 12345
        try:
            m_id = basename.split('_')[1].split('.')[0]
        except:
            print(f"Uyarı: {basename} dosyasından ID çıkarılamadı.")
            continue
            
        # Veritabanından makaleyi bul
        cursor.execute("SELECT * FROM orijinal_metadatalar WHERE id=?", (m_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"Uyarı: ID {m_id} veritabanında bulunamadı!")
            continue
            
        # row: (id, pdf_ismi, baslik, ozet, yazarlar, kelimeler, yil, gercek_dergi, doi, durum)
        _, _, baslik, ozet, yazarlar_str, kelimeler_str, yil, dergi, doi, _ = row
        
        # auto_annotator.py'nin beklediği JSON formatını oluştur (Elasticsearch TR Dizin benzeri)
        yazarlar_list = [{"name": y.strip()} for y in yazarlar_str.split(", ") if y.strip()]
        kelimeler_list = [k.strip() for k in kelimeler_str.split(", ") if k.strip()]
        
        record = {
            "journal": {"name": dergi},
            "abstracts": [{
                "language": "TUR",
                "title": baslik,
                "abstract": ozet,
                "keywords": kelimeler_list
            }],
            "authors": yazarlar_list,
            "publicationYear": yil,
            "doi": doi
        }
        
        with open(temp_json, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
            
        out_path = os.path.join(OUT_DIR, basename)
        
        cmd = [
            "python", r"C:\Users\EG\Desktop\Tubitak___is\altin_etiketleyici.py", 
            "--raw", raw_path, 
            "--json", temp_json, 
            "--out", out_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            basarili_sayisi += 1
            print(f"[{basarili_sayisi}] Etiketlendi: {basename}")
            # Opsiyonel: stdout içindeki Alignment skorlarını pars edip toplam_metrikler'e ekleyebiliriz
        else:
            print(f"Hata ({basename}): {result.stderr}")
            hata_sayisi += 1

    conn.close()
    if os.path.exists(temp_json):
        os.remove(temp_json)
        
    print("\n" + "="*40)
    print(f"ETİKETLEME BİTTİ!")
    print(f"Başarılı: {basarili_sayisi}")
    print(f"Hatalı: {hata_sayisi}")
    print(f"Sonuçlar {OUT_DIR} klasörüne kaydedildi.")

if __name__ == "__main__":
    etiketleme_baslat()
