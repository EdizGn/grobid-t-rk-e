import os
import glob
from collections import Counter
from bs4 import BeautifulSoup

XML_DIR = r"C:\Users\EG\Desktop\Tubitak___is\1500_random_test\grobid_xml"

# İzin verilen standart karakterler
IZIN_VERILENLER = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "çğıöşüÇĞIİÖŞÜ"
    " \t\n\r"
    ".,;:'\"!?()-[]{}/\\&@#$%^*_+=~`|<>"
    "“”‘’–—"
)

def analyze():
    xml_dosyalari = glob.glob(os.path.join(XML_DIR, "*.xml"))
    anomali_sayaci = Counter()
    
    for dosya_yolu in xml_dosyalari:
        try:
            with open(dosya_yolu, 'r', encoding='utf-8') as f:
                icerik = f.read()
                
            soup = BeautifulSoup(icerik, "lxml-xml")
            metin = soup.get_text()
            
            for char in metin:
                if char not in IZIN_VERILENLER:
                    anomali_sayaci[char] += 1
                    
        except Exception as e:
            pass
            
    with open("anomali_raporu.txt", "w", encoding="utf-8") as out_f:
        out_f.write("=== ANOMALİ KARAKTER FREKANS RAPORU ===\n")
        for char, frekans in anomali_sayaci.most_common():
            out_f.write(f"Karakter: '{char}' | Unicode: U+{ord(char):04X} | Frekans: {frekans}\n")
            
    print("Rapor anomali_raporu.txt dosyasina yazildi.")

if __name__ == "__main__":
    analyze()
