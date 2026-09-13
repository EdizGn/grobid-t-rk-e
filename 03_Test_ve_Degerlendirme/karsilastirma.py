import os
import glob
import json
from bs4 import BeautifulSoup
import re
import math
from collections import Counter
import sqlite3

def normalize_text(s):
    if not s: return ""
    s = str(s)
    # PDF Font Bozulmalarını (Encoding Hataları) Düzelt
    bozuk_karakterler = {
        "Ġ": "İ", "ġ": "ş", "Ý": "İ", "ý": "ı", 
        "Þ": "Ş", "þ": "ş", "Ð": "Ğ", "ð": "ğ"
    }
    for bozuk, duzgun in bozuk_karakterler.items():
        s = s.replace(bozuk, duzgun)
        
    s = s.replace("I", "ı").replace("İ", "i").lower()
    trans = str.maketrans("çğıöşü", "cgiosu")
    s = s.translate(trans)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def advanced_token_similarity(str1, str2):
    str1 = normalize_text(str1)
    str2 = normalize_text(str2)
    
    # Kısaltmaları (tek harfleri) ve noktalama işaretlerini yok say, kelimeleri set yap
    words1 = set(w for w in str1.split() if len(w) > 1)
    words2 = set(w for w in str2.split() if len(w) > 1)
    
    if not words2:
        return None, None
    if not words1:
        return 0.0, 0.0
        
    intersection = words1.intersection(words2)
    
    # Recall: Orijinal kelimelerin yüzde kaçını buldu? (Doğru yazarları bulma oranı)
    recall = (len(intersection) / len(words2)) if words2 else 0.0
    
    # Precision: Bulduğu kelimelerin yüzde kaçı orijinal? (Fazladan çöp kelime bulmama, kesinlik oranı)
    precision = (len(intersection) / len(words1)) if words1 else 0.0
    
    return recall * 100, precision * 100

def karsilastir_grobid_ve_trdizin(grobid_klasoru, json_dosyasi, cikti_klasoru, db_adi="tubitak_makaleler.db"):
    db_yolu = os.path.join(cikti_klasoru, db_adi)
    if not os.path.exists(db_yolu):
        print(f"HATA: {db_yolu} bulunamadı!")
        return
        
    conn = sqlite3.connect(db_yolu)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orijinal_metadatalar")
    rows = cursor.fetchall()
    column_names = [desc[0] for desc in cursor.description]
    
    # ID ile kolay erişim için sözlük oluştur
    orijinal_dict = {}
    for row in rows:
        row_dict = dict(zip(column_names, row))
        mapped_dict = {
            "id": row_dict["id"],
            "Dosya Adı": row_dict["dosya_adi"],
            "Gerçek Başlık": row_dict["gercek_baslik"],
            "Gerçek Özet": row_dict["gercek_ozet"],
            "Gerçek Yazarlar": row_dict["gercek_yazarlar"],
            "Gerçek Anahtar Kelimeler": row_dict["gercek_anahtar_kelimeler"],
            "Gerçek Yıl": row_dict["gercek_yil"],
            "Gerçek Dergi": row_dict["gercek_dergi"],
            "Gerçek DOI": row_dict["gercek_doi"],
            "Durum": row_dict["durum"]
        }
        orijinal_dict[str(mapped_dict['id'])] = mapped_dict
    conn.close()
    
    xml_dosyalari = glob.glob(os.path.join(grobid_klasoru, "*.xml"))
    print(f"Toplam {len(xml_dosyalari)} Grobid XML dosyası bulundu.")
    kiyaslama_sonuclari = []
    
    for i, xml_yolu in enumerate(xml_dosyalari):
        dosya_adi = os.path.basename(xml_yolu)
        # Dosya adı formatı: makale_12345.xml (veya eskisi gibiyse .grobid.tei.xml)
        makale_id = dosya_adi.replace("makale_", "").replace(".grobid.tei.xml", "").replace(".xml", "")
        
        # Grobid verilerini parse et
        with open(xml_yolu, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "xml")
            
            # Başlık
            title_tag = soup.find('title', type='main')
            if not title_tag:
                title_tag = soup.find('title')
            grobid_baslik = title_tag.text.strip() if title_tag else ""
            
            # Özet
            abstract_tag = soup.find('abstract')
            grobid_ozet = abstract_tag.text.strip() if abstract_tag else ""
            
            # Yazarlar ve Kelimeleri Sadece teiHeader içinden al (referanslardaki yazarları almamak için)
            tei_header = soup.find('teiHeader')
            authors = []
            keywords = []
            
            if tei_header:
                for author_tag in tei_header.find_all('author'):
                    isimler = author_tag.find_all("persName")
                    if isimler:
                        for isim in isimler:
                            text = " ".join([t.get_text(strip=True) for t in isim.find_all(True) if t.name in ["forename", "surname"]])
                            if text:
                                # Yalnızca akademik unvanları filtrele (TR Dizin'de unvan olmadığı için haksızlık olmasın)
                                # Grobid'in yazar sandığı "üniversite, bölüm, özet" gibi kelimeleri bilerek silmiyoruz ki 
                                # yapay zekanın yaptığı bu ayıplar Yazar Temizlik (Precision) skorunu dürüstçe düşürsün!
                                yasakli_kelimeler = ["prof", "dr", "doç", "uzman", "uzm", "araş", "gör"]
                                if not any(yasak in text.lower() for yasak in yasakli_kelimeler):
                                    authors.append(text)
                            
                for term in tei_header.find_all('term'):
                    keywords.append(term.text.strip())
                    
            grobid_yazarlar = ", ".join(authors)
            grobid_keywords = ", ".join(keywords)
            
            # DOI
            doi_tag = soup.find('idno', type='DOI')
            grobid_doi = doi_tag.text.strip() if doi_tag else ""
            
            # Yıl
            date_tag = soup.find('date')
            grobid_yil = date_tag.text.strip() if date_tag else ""
            
            # Dergi Adı
            journal_tag = soup.find('title', level='j')
            grobid_dergi = journal_tag.text.strip() if journal_tag else ""
            
        # Orijinal verileri al
        orijinal = orijinal_dict.get(makale_id)
        if orijinal:
            orijinal_baslik = str(orijinal.get('Gerçek Başlık') or '')
            orijinal_ozet = str(orijinal.get('Gerçek Özet') or '')
            orijinal_yazarlar = str(orijinal.get('Gerçek Yazarlar') or '')
            orijinal_kelimeler = str(orijinal.get('Gerçek Anahtar Kelimeler') or '')
            orijinal_yil = str(orijinal.get('Gerçek Yıl') or '')
            orijinal_dergi = str(orijinal.get('Gerçek Dergi') or '')
            orijinal_doi = str(orijinal.get('Gerçek DOI') or '')
            
            # Basit temizlik
            if orijinal_baslik == "BAŞLIK BULUNAMADI": orijinal_baslik = ""
            if orijinal_ozet == "ÖZET BULUNAMADI": orijinal_ozet = ""
            
            # Dergi skorlaması için Jaccard formülü:
            def jaccard_similarity(s1, s2):
                w1 = set(re.findall(r'\b\w+\b', normalize_text(s1)))
                w2 = set(re.findall(r'\b\w+\b', normalize_text(s2)))
                if not w2: return None
                if not w1: return 0.0
                return (len(w1 & w2) / len(w1 | w2)) * 100

            # Başlık ve Özet için de Kelime (Token) tabanlı örtüşme (Recall/Precision)
            baslik_recall, baslik_precision = advanced_token_similarity(grobid_baslik, orijinal_baslik)
            ozet_recall, ozet_precision = advanced_token_similarity(grobid_ozet, orijinal_ozet)
            
            # Yazar ve Anahtar Kelimelerde düz string kıyaslaması yerine kelime (token) tabanlı örtüşme (Dice katsayısı)
            yazar_recall, yazar_precision = advanced_token_similarity(grobid_yazarlar, orijinal_yazarlar)
            kelime_recall, kelime_precision = advanced_token_similarity(grobid_keywords, orijinal_kelimeler)
            
            # Yıl: Birebir 4 haneli eşleşme
            def extract_year(y):
                m = re.search(r'\b(19|20)\d{2}\b', str(y))
                return m.group(0) if m else ""
            
            o_yil = extract_year(orijinal_yil)
            g_yil = extract_year(grobid_yil)
            
            if not o_yil:
                yil_skor = None
            elif not g_yil:
                yil_skor = 0.0
            elif o_yil == g_yil:
                yil_skor = 100.0
            else:
                yil_skor = 0.0
                
            # Dergi: Jaccard (Tıpkı başlıklar gibi kelime bazlı kesişim)
            dergi_skor = jaccard_similarity(grobid_dergi, orijinal_dergi)
            
            # DOI: URL kalıntılarını temizledikten sonra birebir eşleşme
            def clean_doi(d):
                d = str(d).lower().strip()
                d = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', d)
                d = re.sub(r'^doi:\s*', '', d)
                return d
                
            o_doi = clean_doi(orijinal_doi)
            g_doi = clean_doi(grobid_doi)
            
            if not o_doi:
                doi_skor = None
            elif not g_doi:
                doi_skor = 0.0
            elif o_doi == g_doi:
                doi_skor = 100.0
            else:
                doi_skor = 0.0
            
            def safe_round(val):
                return round(val, 2) if val is not None else None

            kiyaslama_sonuclari.append({
                "Makale ID": makale_id,
                "Durum": "Eşleşti",
                "Orijinal Başlık": orijinal_baslik,
                "Grobid Başlık": grobid_baslik,
                "Başlık Bulma Oranı (%)": safe_round(baslik_recall),
                "Başlık Kesinlik Oranı (%)": safe_round(baslik_precision),
                "Orijinal Özet": orijinal_ozet,
                "Grobid Özet": grobid_ozet,
                "Özet Bulma Oranı (%)": safe_round(ozet_recall),
                "Özet Kesinlik Oranı (%)": safe_round(ozet_precision),
                "Orijinal Yazarlar": orijinal_yazarlar,
                "Grobid Yazarlar": grobid_yazarlar,
                "Yazar Bulma Oranı (%)": safe_round(yazar_recall),
                "Yazar Kesinlik Oranı (%)": safe_round(yazar_precision),
                "Orijinal Anahtar Kelimeler": orijinal_kelimeler,
                "Grobid Anahtar Kelimeler": grobid_keywords,
                "Kelime Bulma Oranı (%)": safe_round(kelime_recall),
                "Kelime Kesinlik Oranı (%)": safe_round(kelime_precision),
                "Orijinal Yıl": orijinal_yil,
                "Grobid Yıl": grobid_yil,
                "Yıl Başarı Oranı (%)": safe_round(yil_skor),
                "Orijinal Dergi": orijinal_dergi,
                "Grobid Dergi": grobid_dergi,
                "Dergi Başarı Oranı (%)": safe_round(dergi_skor),
                "Orijinal DOI": orijinal_doi,
                "Grobid DOI": grobid_doi,
                "DOI Başarı Oranı (%)": safe_round(doi_skor)
            })
        else:
            # JSON'da bulunamadı
            kiyaslama_sonuclari.append({
                "Makale ID": makale_id,
                "Durum": "Orijinal Metadata Yok",
                "Orijinal Başlık": "",
                "Grobid Başlık": grobid_baslik,
                "Başlık Bulma Oranı (%)": None,
                "Başlık Kesinlik Oranı (%)": None,
                "Orijinal Özet": "",
                "Grobid Özet": grobid_ozet,
                "Özet Bulma Oranı (%)": None,
                "Özet Kesinlik Oranı (%)": None,
                "Orijinal Yazarlar": "",
                "Grobid Yazarlar": grobid_yazarlar,
                "Yazar Bulma Oranı (%)": 0,
                "Yazar Temizlik Oranı (%)": 0,
                "Orijinal Anahtar Kelimeler": "",
                "Grobid Anahtar Kelimeler": grobid_keywords,
                "Kelime Bulma Oranı (%)": 0,
                "Kelime Temizlik Oranı (%)": 0,
                "Orijinal Yıl": "",
                "Grobid Yıl": grobid_yil,
                "Yıl Başarı Oranı (%)": 0,
                "Orijinal Dergi": "",
                "Grobid Dergi": grobid_dergi,
                "Dergi Başarı Oranı (%)": 0,
                "Orijinal DOI": "",
                "Grobid DOI": grobid_doi,
                "DOI Başarı Oranı (%)": 0
            })
            
        if (i + 1) % 500 == 0:
            print(f"{i + 1} XML dosyası işlendi...")
            
    print("Sonuçlar hesaplandı. Dashboard verisi oluşturuluyor...")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    dashboard_klasoru = os.path.join(BASE_DIR, "dashboard")
    if not os.path.exists(dashboard_klasoru):
        os.makedirs(dashboard_klasoru)
        
    js_yolu = os.path.join(dashboard_klasoru, "data.js")
    
    json_verisi = json.dumps(kiyaslama_sonuclari, ensure_ascii=False)
    js_icerigi = f"const kiyaslamaVerileri = {json_verisi};\n"
    
    with open(js_yolu, "w", encoding="utf-8") as f:
        f.write(js_icerigi)
        
    print(f"Kıyaslama tamamlandı! Dashboard verisi güncellendi: {js_yolu}")

if __name__ == "__main__":
    import argparse
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Grobid XML çıktılarını orijinal DB ile kıyaslar.")
    parser.add_argument("--grobid_klasoru", default=os.path.join(BASE_DIR, "makaleler_test", "grobid_xml"))
    parser.add_argument("--json_dosyasi", default=os.path.join(BASE_DIR, "dashboard", "sonuclar.json"))
    parser.add_argument("--cikti_klasoru", default=os.path.join(BASE_DIR, "makaleler_test"))
    parser.add_argument("--db_adi", default="test_metadatalar.db")
    
    args = parser.parse_args()
    karsilastir_grobid_ve_trdizin(args.grobid_klasoru, args.json_dosyasi, args.cikti_klasoru, args.db_adi)