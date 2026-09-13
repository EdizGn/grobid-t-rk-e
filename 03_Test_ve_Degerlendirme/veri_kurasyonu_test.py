import os
import requests
import time
import concurrent.futures
import sqlite3
import json

# --- VERİTABANI BAŞLATMA ---
def init_db(db_yolu):
    conn = sqlite3.connect(db_yolu)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orijinal_metadatalar (
            id TEXT PRIMARY KEY,
            dosya_adi TEXT,
            gercek_baslik TEXT,
            gercek_ozet TEXT,
            gercek_yazarlar TEXT,
            gercek_anahtar_kelimeler TEXT,
            gercek_yil TEXT,
            gercek_dergi TEXT,
            gercek_doi TEXT,
            durum TEXT
        )
    ''')
    conn.commit()
    return conn

# --- TEK BİR MAKALEYİ İNDİREN BAĞIMSIZ FONKSİYON ---
def tek_makale_indir_ve_kaydet(pub_id, hedef_klasor, headers):
    meta_url = f"https://search.trdizin.gov.tr/api/publicationById/{pub_id}?archiveSearch=ADD_ARCHIVE"
    try:
        meta_cevap = requests.get(meta_url, headers=headers, timeout=10)
        if meta_cevap.status_code == 200:
            veri = meta_cevap.json()
            hits_dizisi = veri.get('hits', {}).get('hits', [])
            
            if hits_dizisi:
                kaynak = hits_dizisi[0].get('_source', {})
                
                # --- KALİTE KONTROL (Metadata Eksiksiz mi?) ---
                baslik = kaynak.get("orderTitle", "")
                if baslik == "NOT_FOUND" or not baslik:
                    return f"[X] Başlık eksik - ID: {pub_id}", None
                
                abstracts_list = kaynak.get("abstracts", [])
                if not abstracts_list:
                    return f"[X] Özet eksik - ID: {pub_id}", None
                
                tr_abstract = next((a for a in abstracts_list if a.get("language") == "TUR"), None)
                if not tr_abstract:
                    return f"[X] Türkçe özet/başlık eksik - ID: {pub_id}", None
                
                ozet = tr_abstract.get("abstract", "")
                gercek_baslik = tr_abstract.get("title") or baslik
                kelimeler = tr_abstract.get("keywords", [])
                
                if not ozet or not kelimeler:
                    return f"[X] Özet veya Kelime eksik - ID: {pub_id}", None
                
                yazarlar_list = kaynak.get("authors", [])
                if not yazarlar_list:
                    return f"[X] Yazar eksik - ID: {pub_id}", None
                
                gercek_yazarlar = ", ".join([y.get("name", "") for y in yazarlar_list if isinstance(y, dict) and y.get("name")])
                gercek_kelimeler = ", ".join(kelimeler)
                gercek_yil = str(kaynak.get("publicationYear", ""))
                
                journal_dict = kaynak.get("journal", {})
                gercek_dergi = journal_dict.get("name", "") if isinstance(journal_dict, dict) else ""
                gercek_doi = kaynak.get("doi", "")
                
                # Her şey mükemmelse PDF indirme aşamasına geç
                pdf_key = kaynak.get('pdf')
                if pdf_key:
                    link_istek_url = f"https://search.trdizin.gov.tr/api/getFile/{pdf_key}?showViewer=false"
                    link_cevap = requests.get(link_istek_url, headers=headers, timeout=10)
                    
                    if link_cevap.status_code == 200:
                        asil_indirme_linki = link_cevap.text.strip().strip('"').strip("'")
                        
                        if asil_indirme_linki.startswith("http"):
                            pdf_cevap = requests.get(asil_indirme_linki, headers=headers, stream=True, timeout=20)
                            
                            if pdf_cevap.status_code == 200:
                                dosya_yolu = os.path.join(hedef_klasor, f"makale_{pub_id}.pdf")
                                with open(dosya_yolu, "wb") as f:
                                    for chunk in pdf_cevap.iter_content(chunk_size=8192):
                                        f.write(chunk)
                                        
                                # Başarılı indirme! Meta veriyi de döndür.
                                meta_satiri = (
                                    pub_id, f"makale_{pub_id}.pdf", gercek_baslik, ozet, 
                                    gercek_yazarlar, gercek_kelimeler, gercek_yil, gercek_dergi, gercek_doi, "Başarılı"
                                )
                                return f"[OK] Başarılı: makale_{pub_id}.pdf", meta_satiri
                            else:
                                return f"[X] PDF indirilemedi (HTTP {pdf_cevap.status_code}) - ID: {pub_id}", None
                        else:
                            return f"[X] Gelen metin link değil - ID: {pub_id}", None
                    else:
                        return f"[X] İndirme linki alınamadı (HTTP {link_cevap.status_code}) - ID: {pub_id}", None
                else:
                    return f"[WARN] PDF anahtarı yok - ID: {pub_id}", None
            else:
                return f"[WARN] Makale detayı boş - ID: {pub_id}", None
        else:
             return f"[X] Meta veri alınamadı (HTTP {meta_cevap.status_code}) - ID: {pub_id}", None
    except Exception as e:
        return f"[WARN] Hata ({e}) - ID: {pub_id}", None


# --- ANA ÇALIŞTIRMA FONKSİYONU ---
def makale_indir_altin_standart(hedef_klasor=r"C:\Users\EG\Desktop\Tubitak___is\makaleler_test", toplam_hedef=200, dergi_limiti=5):
    baslangic_zamani = time.time()
    
    if not os.path.exists(hedef_klasor):
        os.makedirs(hedef_klasor)
        
    db_yolu = os.path.join(hedef_klasor, "test_metadatalar.db")
    conn = init_db(db_yolu)
    cursor = conn.cursor()

    # Eğitim verilerinin ID'lerini al
    egitim_db = r"C:\Users\EG\Desktop\Tubitak___is\makaleler_altin\altin_metadatalar.db"
    egitim_idleri = set()
    if os.path.exists(egitim_db):
        egitim_conn = sqlite3.connect(egitim_db)
        egitim_cursor = egitim_conn.cursor()
        egitim_cursor.execute("SELECT id FROM orijinal_metadatalar")
        for row in egitim_cursor.fetchall():
            egitim_idleri.add(str(row[0]))
        egitim_conn.close()

    cursor.execute("SELECT COUNT(*) FROM orijinal_metadatalar WHERE durum='Başarılı'")
    mevcut_sayi = cursor.fetchone()[0]
    hedef_kalan = toplam_hedef - mevcut_sayi
    
    if hedef_kalan <= 0:
        print(f"Zaten {mevcut_sayi} adet makale inmiş. Hedefe ({toplam_hedef}) ulaşılmış.")
        return

    # Arama terimlerini biraz daha farklılaştıralım (eğitim setinden daha farklı veriler gelsin diye)
    sorgular = [
        "yapay zeka", "enerji", "çevre", "bilişim", "robotik",
        "finans", "yönetim", "mimari", "psikiyatri", "radyoloji",
        "makine", "inşaat", "orman", "maden", "malzeme",
        "tasarım", "uzay", "genetik", "nanoteknoloji", "biyoteknoloji"
    ]
    
    print(f"TR Dizin'den 'Test Seti' için eksik olan {hedef_kalan} makale toplanıyor... (Mevcut: {mevcut_sayi})")
    print(f"Aynı dergiden maksimum {dergi_limiti} makale alınacak.\n")
    print(f"Eğitim setindeki {len(egitim_idleri)} makale tamamen dışlanacak (Data Leakage Önlemi)!\n")

    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Mevcut ID'leri ve dergi sayılarını yükle ki aynılarını tekrar indirmeyelim
    cursor.execute("SELECT id, gercek_dergi FROM orijinal_metadatalar WHERE durum='Başarılı'")
    kayitli_veriler = cursor.fetchall()
    makale_id_listesi = [row[0] for row in kayitli_veriler]
    dergi_sayaclari = {}
    for row in kayitli_veriler:
        dergi = row[1]
        dergi_sayaclari[dergi] = dergi_sayaclari.get(dergi, 0) + 1
        
    yeni_id_listesi = []
    
    # Adım 1: Aday ID Toplama
    for sorgu in sorgular:
        if len(yeni_id_listesi) >= hedef_kalan * 3: # Daha fazla toplayalım ki metadata filtresinde elenenler olsun
            break
            
        print(f"'{sorgu}' sorgusu için aranıyor...")
        sayfa = 1
        
        while len(yeni_id_listesi) < hedef_kalan * 3:
            arama_url = f"https://search.trdizin.gov.tr/api/defaultSearch/publication/?q={sorgu}&order=relevance-DESC&page={sayfa}&limit=50&facet-accessType=OPEN"
            try:
                cevap = requests.get(arama_url, headers=headers, timeout=10)
                if cevap.status_code == 200:
                    data = cevap.json()
                    sonuclar = data.get('hits', {}).get('hits', [])
                    if not sonuclar:
                        break 
                    
                    for makale in sonuclar:
                        kaynak = makale.get('_source', {})
                        m_id = str(kaynak.get('id') or makale.get('_id'))
                        
                        journal_info = kaynak.get("journal", {})
                        dergi_adi = journal_info.get("name", "Bilinmeyen Dergi") if isinstance(journal_info, dict) else "Bilinmeyen Dergi"
                        
                        if m_id and m_id not in makale_id_listesi and m_id not in yeni_id_listesi and m_id not in egitim_idleri:
                            mevcut_sayi_dergi = dergi_sayaclari.get(dergi_adi, 0)
                            if mevcut_sayi_dergi < dergi_limiti:
                                yeni_id_listesi.append(m_id)
                                dergi_sayaclari[dergi_adi] = mevcut_sayi_dergi + 1
                                
                    print(f"  Sayfa {sayfa} tarandı... (Yeni Aday ID Havuzu: {len(yeni_id_listesi)})")
                    sayfa += 1
                else:
                    break 
            except Exception as e:
                break
                
    # Adım 2: PARALEL İNDİRME VE METADATA KONTROLÜ
    print(f"\nToplam {len(yeni_id_listesi)} YENİ aday ID bulundu.")
    print("PARALEL KALİTE KONTROL VE İNDİRME başlatılıyor...\n" + "-"*40)
    
    basarili_sayisi = mevcut_sayi
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        batch_size = 50
        for i in range(0, len(yeni_id_listesi), batch_size):
            if basarili_sayisi >= toplam_hedef:
                break
            
            batch_ids = yeni_id_listesi[i:i+batch_size]
            gelecek_gorevler = [executor.submit(tek_makale_indir_ve_kaydet, p_id, hedef_klasor, headers) for p_id in batch_ids]
            
            for tamamlanan in concurrent.futures.as_completed(gelecek_gorevler):
                if basarili_sayisi >= toplam_hedef:
                    continue # Hedefe ulaştıysak diğer sonuçları yoksay
                    
                mesaj, meta = tamamlanan.result()
                if meta:
                    basarili_sayisi += 1
                    print(f"[{basarili_sayisi}/{toplam_hedef}] {mesaj}")
                    # Veritabanına yaz
                    cursor.execute('''
                        INSERT OR REPLACE INTO orijinal_metadatalar 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', meta)
                    conn.commit()
                else:
                    print(mesaj)

    conn.close()
    
    bitis_zamani = time.time()
    gecen_sure = bitis_zamani - baslangic_zamani
    dakika = int(gecen_sure // 60)
    saniye = int(gecen_sure % 60)
    
    print("-" * 40)
    print(f"ALTIN STANDART İŞLEMİ BİTTİ! Toplam {basarili_sayisi} mükemmel makale indirildi.")
    print(f"Veritabanı: {db_yolu}")
    print(f"Toplam Süre: {dakika} dakika {saniye} saniye")

if __name__ == "__main__":
    makale_indir_altin_standart(toplam_hedef=200, dergi_limiti=5)
