import os
import glob

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hedef Başlıklar
titles = {
    '1302465': "Neuraxial anesthesia",
    '14635': "Monosemptomatik hipokondriak",
    '301108': "AMELİYATHANEDE HİZMET ALAN",
    '59465': "Familial mediterranean fever",
    '63585': "Türkiye Ekonomisinde"
}

out_dir = PROJE_KOK + r"\test_failed_pdfs_out"

xml_files = glob.glob(os.path.join(out_dir, "*.training.header.tei.xml"))

print("=== MANUEL KONTROL SONUÇLARI ===")
if not xml_files:
    print("Henüz XML dosyası üretilmemiş!")
else:
    for fpath in xml_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            
        found = False
        for id_str, target_title in titles.items():
            if id_str in fpath:
                if target_title.lower() in content:
                    print(f"[{id_str}] BAŞARI: Başlık yazısı (.tei.xml) dosyasının İÇİNDE BULUNDU! (Header Modeli Hatası)")
                else:
                    print(f"[{id_str}] HATA: Başlık yazısı (.tei.xml) dosyasının İÇİNDE YOK! (Segmentasyon Modeli Hatası)")
                found = True
                
        if not found:
            print(f"Bilinmeyen dosya: {fpath}")
