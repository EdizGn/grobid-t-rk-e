import os
import sqlite3
import glob
import re

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def etiketleri_duzelt(xml_klasoru, db_yolu, etiket_tipi="title"):
    """
    Grobid tarafından üretilen TEI XML dosyalarındaki dergi ve yıl etiketlerini,
    veritabanındaki %100 doğru API verileriyle (gerçek_dergi, gerçek_yil) günceller.
    
    etiket_tipi: 
       "title" -> <title level="j">Dergi Adı</title>
       "note"  -> <note type="submission">Dergi Adı</note>
    """
    if not os.path.exists(db_yolu):
        print(f"❌ Veritabanı bulunamadı: {db_yolu}")
        return

    # Veritabanına bağlan
    conn = sqlite3.connect(db_yolu)
    cursor = conn.cursor()
    
    xml_dosyalari = glob.glob(os.path.join(xml_klasoru, "*.xml"))
    # .tei.xml gibi uzantılar da olabilir, o yüzden bu şekilde de arayalım
    if not xml_dosyalari:
        xml_dosyalari = glob.glob(os.path.join(xml_klasoru, "*.tei.xml"))
        
    print(f"Klasörde {len(xml_dosyalari)} adet XML/TEI dosyası bulundu.")
    
    basarili_sayisi = 0
    hata_sayisi = 0
    
    for xml_dosya in xml_dosyalari:
        dosya_adi = os.path.basename(xml_dosya)
        
        # Dosya adından ID'yi çıkar (ör: makale_12345.tei.xml veya makale_12345.xml)
        match = re.search(r"makale_(\d+)", dosya_adi)
        if not match:
            print(f"⚠️ ID bulunamadı: {dosya_adi}")
            hata_sayisi += 1
            continue
            
        makale_id = match.group(1)
        
        # Veritabanından doğru verileri çek
        cursor.execute("SELECT gercek_dergi, gercek_yil FROM orijinal_metadatalar WHERE id=?", (makale_id,))
        sonuc = cursor.fetchone()
        
        if not sonuc:
            print(f"⚠️ Veritabanında ID {makale_id} için kayıt bulunamadı.")
            hata_sayisi += 1
            continue
            
        gercek_dergi, gercek_yil = sonuc
        
        # Eğer dergi veya yıl boşsa es geç veya uyarı ver
        if not gercek_dergi or not gercek_yil:
            print(f"⚠️ ID {makale_id} için DB'de Dergi veya Yıl boş.")
            hata_sayisi += 1
            continue
            
        # XML dosyasını oku
        with open(xml_dosya, "r", encoding="utf-8") as f:
            xml_icerik = f.read()
            
        degisti_mi = False
        
        # 1. YIL (Date) DÜZELTMESİ
        # Grobid genelde <date type="published" when="2023"/> veya benzeri şekilde çıkarır
        # En kaba haliyle <date>YIL</date> içine veriyi yazıyoruz. Eğer detaylı XML parse istiyorsanız BeautifulSoup (lxml) kullanılabilir.
        # Basit string replace / regex ile TEI Header içindeki date etiketini hedef alalım.
        
        # Önce mevcut bir <date> var mı bakalım (TEI Header içindeki publicationStmt alanında olur genelde)
        # Regex ile mevcut publication date'i bulup değiştirelim
        date_pattern = r'(<date[^>]*>)(.*?)(</date>)'
        
        def date_replacer(match):
            # Grobid when="2023" attribute'unu da kullanıyor olabilir
            return f'<date>{gercek_yil}</date>'
            
        # Sadece sourceDesc altındaki ilk date'i değiştirmek daha güvenli olabilir ama genelde Grobid başlık altına koyuyor.
        yeni_icerik, num_subs = re.subn(date_pattern, date_replacer, xml_icerik, count=1)
        if num_subs > 0:
            degisti_mi = True
            xml_icerik = yeni_icerik
        else:
            # Eğer hiç date etiketi yoksa, <publicationStmt> içine ekleyebiliriz ama Grobid formatını bozmamak için dikkatli olmak lazım.
            pass
            
        # 2. DERGİ ADI DÜZELTMESİ
        if etiket_tipi == "title":
            # <title level="j">... </title>
            title_pattern = r'(<title level="j"[^>]*>)(.*?)(</title>)'
            def title_replacer(match):
                return f'{match.group(1)}{gercek_dergi}{match.group(3)}'
                
            yeni_icerik, num_subs = re.subn(title_pattern, title_replacer, xml_icerik)
            if num_subs > 0:
                degisti_mi = True
                xml_icerik = yeni_icerik
        else:
            # <note type="submission">... </note>
            note_pattern = r'(<note type="submission"[^>]*>)(.*?)(</note>)'
            def note_replacer(match):
                return f'{match.group(1)}{gercek_dergi}{match.group(3)}'
                
            yeni_icerik, num_subs = re.subn(note_pattern, note_replacer, xml_icerik)
            if num_subs > 0:
                degisti_mi = True
                xml_icerik = yeni_icerik
                
        # Değişiklik olduysa kaydet
        if degisti_mi:
            with open(xml_dosya, "w", encoding="utf-8") as f:
                f.write(xml_icerik)
            basarili_sayisi += 1
            # print(f"✅ Güncellendi: {dosya_adi}")
        else:
            hata_sayisi += 1
            print(f"⚠️ Etiketler bulunamadı (Regex eşleşmedi): {dosya_adi}")

    conn.close()
    print("-" * 50)
    print(f"İşlem Tamamlandı! Başarıyla güncellenen dosya sayısı: {basarili_sayisi}, Uyarı/Hata: {hata_sayisi}")

if __name__ == "__main__":
    # Örnek kullanım (Kendi yollarınızı buraya göre ayarlayabilirsiniz)
    XML_KLASORU = PROJE_KOK + r"\xml_cikti"  # Grobid'in ürettiği XML'lerin olduğu klasör
    DB_YOLU = PROJE_KOK + r"\ciktilar\tubitak_makaleler.db"
    
    # EĞER klasör yoksa oluştur (test için)
    if not os.path.exists(XML_KLASORU):
        os.makedirs(XML_KLASORU)
        print(f"Lütfen oluşturulan {XML_KLASORU} klasörüne Grobid'den çıkan XML dosyalarını koyun ve tekrar çalıştırın.")
    else:
        # Etiket tipi: "title" (<title level="j">) veya "note" (<note type="submission">)
        # Grobid standartları gereği genelde title level="j" tavsiye edilir.
        etiketleri_duzelt(XML_KLASORU, DB_YOLU, etiket_tipi="title")
