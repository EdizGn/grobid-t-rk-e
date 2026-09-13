import os
import requests
import random
import concurrent.futures
import sqlite3

HEDEF_KLASOR = r"C:\Users\EG\Desktop\Tubitak___is\1500_random_test\makaleler"
DB_YOLU = r"C:\Users\EG\Desktop\Tubitak___is\1500_random_test\test_metadatalar.db"
HEDEF_SAYI = 1500
MAX_ID = 2000000

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def init_db():
    conn = sqlite3.connect(DB_YOLU)
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
    conn.close()

def save_metadata(meta):
    conn = sqlite3.connect(DB_YOLU)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO orijinal_metadatalar 
    (id, dosya_adi, gercek_baslik, gercek_ozet, gercek_yazarlar, gercek_anahtar_kelimeler, gercek_yil, gercek_dergi, gercek_doi, durum) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        meta.get("id"), meta.get("Dosya AdÄ±"), meta.get("GerÃ§ek BaÅŸlÄ±k"), 
        meta.get("GerÃ§ek Ã–zet"), meta.get("GerÃ§ek Yazarlar"), 
        meta.get("GerÃ§ek Anahtar Kelimeler"), meta.get("GerÃ§ek YÄ±l"), 
        meta.get("GerÃ§ek Dergi"), meta.get("GerÃ§ek DOI"), meta.get("Durum")
    ))
    conn.commit()
    conn.close()

def process_random_id(makale_id):
    meta_url = f"https://search.trdizin.gov.tr/api/publicationById/{makale_id}?archiveSearch=ADD_ARCHIVE"
    try:
        meta_res = requests.get(meta_url, headers=headers, timeout=10)
        if meta_res.status_code == 200:
            data = meta_res.json()
            hits = data.get("hits", {}).get("hits", [])
            if not hits: return None
            source = hits[0].get("_source", {})
            pdf_key = source.get("pdf")
            if not pdf_key: return None
            
            abstracts_list = source.get("abstracts", [])
            ozet, baslik = "Ã–ZET BULUNAMADI", "BAÅLIK BULUNAMADI"
            anahtar_kelimeler = []
            
            if abstracts_list:
                tr_abstract = next((a for a in abstracts_list if a.get("language") == "TUR"), None)
                if tr_abstract:
                    ozet = tr_abstract.get("abstract") or ozet
                    baslik = tr_abstract.get("title") or baslik
                    anahtar_kelimeler = tr_abstract.get("keywords") or []
                else:
                    first_abs = abstracts_list[0]
                    ozet = first_abs.get("abstract") or ozet
                    baslik = first_abs.get("title") or baslik
                    anahtar_kelimeler = first_abs.get("keywords") or []
                    
            yazarlar_list = source.get("authors") or []
            yazarlar = ", ".join([y.get("name", "") for y in yazarlar_list if isinstance(y, dict) and y.get("name")])
            keywords_str = ", ".join(anahtar_kelimeler)
            yil = source.get("publicationYear", "")
            dergi = source.get("journal", {}).get("name", "") if isinstance(source.get("journal"), dict) else ""
            doi = source.get("doi", "")
            
            link_url = f"https://search.trdizin.gov.tr/api/getFile/{pdf_key}?showViewer=false"
            link_res = requests.get(link_url, headers=headers, timeout=10)
            if link_res.status_code == 200:
                pdf_url = link_res.text.strip().strip('"').strip("'")
                if pdf_url.startswith("http"):
                    pdf_res = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
                    if pdf_res.status_code == 200:
                        pdf_path = os.path.join(HEDEF_KLASOR, f"makale_{makale_id}.pdf")
                        with open(pdf_path, "wb") as f:
                            for chunk in pdf_res.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        meta_obj = {
                            "id": str(makale_id), "Dosya AdÄ±": f"makale_{makale_id}.pdf",
                            "GerÃ§ek BaÅŸlÄ±k": baslik, "GerÃ§ek Ã–zet": ozet, "GerÃ§ek Yazarlar": yazarlar,
                            "GerÃ§ek Anahtar Kelimeler": keywords_str, "GerÃ§ek YÄ±l": yil,
                            "GerÃ§ek Dergi": dergi, "GerÃ§ek DOI": doi, "Durum": "BaÅŸarÄ±lÄ±"
                        }
                        save_metadata(meta_obj)
                        return f"âœ… Ä°ndirildi: {makale_id}"
        return None
    except Exception as e:
        return None

def main():
    os.makedirs(HEDEF_KLASOR, exist_ok=True)
    init_db()
    
    # Calculate how many we already have
    existing = len([f for f in os.listdir(HEDEF_KLASOR) if f.endswith('.pdf')])
    print(f"Mevcut PDF sayÄ±sÄ±: {existing}. Toplam 1500'e tamamlanacak (Eksik: {HEDEF_SAYI - existing}).")
    
    downloaded = existing
    visited = set()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        while downloaded < HEDEF_SAYI:
            # Generate a batch of random IDs
            batch = []
            while len(batch) < 100:
                rid = random.randint(1, MAX_ID)
                if rid not in visited:
                    visited.add(rid)
                    batch.append(rid)
            
            futures = [executor.submit(process_random_id, rid) for rid in batch]
            for future in concurrent.futures.as_completed(futures):
                res_text = future.result()
                if res_text and "âœ…" in res_text:
                    downloaded += 1
                    print(f"[{downloaded}/{HEDEF_SAYI}] {res_text}")
                    if downloaded >= HEDEF_SAYI:
                        break

if __name__ == '__main__':
    main()
