import os
import glob

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Düzenlenecek XML klasörü
XML_DIR = PROJE_KOK + r"\1500_random_test\grobid_xml"

# Bozuk OCR / Font Encoding Karakterlerinin Doğru Türkçe Karşılıkları
TEMIZLIK_SOZLUGU = {
    "Ġ": "İ", "ġ": "ş", 
    "Ý": "İ", "ý": "ı", 
    "Þ": "Ş", "þ": "ş", 
    "Ð": "Ğ", "ð": "ğ",
    "Ÿ": "Y",
    "›": "ı",  # Sık rastlanan MacTurkish 'ı' hatası
    "¤": "ğ",  # Sık rastlanan MacTurkish 'ğ' hatası
    "Ģ": "ş",  # Sık rastlanan 'ş' hatası (örn: kiĢinin)
    "": "ı",  # Özel fontlardan gelen 'ı' hatası
    "ß": "ş"   # 'ş' yerine geçen Beta sembolü
}

def temizle():
    xml_dosyalari = glob.glob(os.path.join(XML_DIR, "*.xml"))
    duzeltilen_dosya_sayisi = 0
    toplam_degisiklik = 0
    
    for dosya_yolu in xml_dosyalari:
        try:
            with open(dosya_yolu, 'r', encoding='utf-8') as f:
                icerik = f.read()
                
            yeni_icerik = icerik
            degisiklik_var = False
            
            for bozuk, duzgun in TEMIZLIK_SOZLUGU.items():
                if bozuk in yeni_icerik:
                    yeni_icerik = yeni_icerik.replace(bozuk, duzgun)
                    degisiklik_var = True
                    toplam_degisiklik += icerik.count(bozuk)
                    
            if degisiklik_var:
                with open(dosya_yolu, 'w', encoding='utf-8') as f:
                    f.write(yeni_icerik)
                duzeltilen_dosya_sayisi += 1
                
        except Exception as e:
            print(f"Hata ({dosya_yolu}): {e}")
            
    print(f"İşlem tamamlandı!")
    print(f"Toplam incelenen XML: {len(xml_dosyalari)}")
    print(f"İçinde bozuk karakter bulunup düzeltilen XML sayısı: {duzeltilen_dosya_sayisi}")
    print(f"Toplam değiştirilen karakter sayısı: {toplam_degisiklik}")

if __name__ == "__main__":
    temizle()
