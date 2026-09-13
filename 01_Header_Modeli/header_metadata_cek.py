# -*- coding: utf-8 -*-
"""
Header egitim korpusundaki (546 dosya) makalelerin metadata'sini
TR Dizin API'sinden ceker ve header_metadatalar.db'ye yazar.

PDF INDIRMEZ -- egitim metni zaten korpusta var, sadece "altin standart"
metadata gerekiyor (baslik / ozet / yazar / anahtar kelime / dergi / yil / DOI).

Yarim kalirsa tekrar calistirilabilir: DB'de zaten olan ID'ler atlanir.
"""
import os
import re
import glob
import time
import sqlite3
import argparse
import requests
import concurrent.futures

API = "https://search.trdizin.gov.tr/api/publicationById/{}?archiveSearch=ADD_ARCHIVE"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}


def init_db(path):
    conn = sqlite3.connect(path)
    conn.execute("""
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
            gercek_baslik_en TEXT,
            gercek_ozet_en TEXT,
            gercek_anahtar_kelimeler_en TEXT,
            durum TEXT
        )
    """)
    conn.commit()
    return conn


def dil_sec(abstracts, kod):
    return next((a for a in abstracts
                 if isinstance(a, dict) and a.get("language") == kod), None)


def cek(pub_id):
    """(mesaj, satir) dondurur. Eksik alanlar bos string olarak gecer --
    kurasyon scriptlerinin aksine BURADA eleme yapilmaz, kismi veri de isimize yarar."""
    try:
        r = requests.get(API.format(pub_id), headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return "[X] HTTP %s - %s" % (r.status_code, pub_id), None
        hits = r.json().get("hits", {}).get("hits", [])
        if not hits:
            return "[WARN] kayit yok - %s" % pub_id, None
        k = hits[0].get("_source", {}) or {}

        absl = k.get("abstracts", []) or []
        tr = dil_sec(absl, "TUR")
        en = dil_sec(absl, "ENG")

        def al(d, alan):
            return (d.get(alan) or "") if isinstance(d, dict) else ""

        baslik = al(tr, "title") or k.get("orderTitle", "") or al(en, "title")
        ozet = al(tr, "abstract")
        kelime = ", ".join(al(tr, "keywords") or [])
        baslik_en = al(en, "title")
        ozet_en = al(en, "abstract")
        kelime_en = ", ".join(al(en, "keywords") or [])

        yazarlar = ", ".join(y.get("name", "") for y in (k.get("authors") or [])
                             if isinstance(y, dict) and y.get("name"))
        j = k.get("journal", {})
        dergi = j.get("name", "") if isinstance(j, dict) else ""
        yil = str(k.get("publicationYear", "") or "")
        doi = k.get("doi", "") or ""

        eksik = [ad for ad, v in (("baslik", baslik), ("ozet", ozet),
                                  ("yazar", yazarlar)) if not v]
        durum = "Tam" if not eksik else "Eksik:" + "+".join(eksik)

        return "[OK] %s (%s)" % (pub_id, durum), (
            str(pub_id), "makale_%s.pdf" % pub_id, baslik, ozet, yazarlar,
            kelime, yil, dergi, doi, baslik_en, ozet_en, kelime_en, durum)
    except Exception as e:
        return "[WARN] %s - %s" % (e, pub_id), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=r"C:\Users\EG\Desktop\Tubitak___is\grobid\grobid-trainer\resources\dataset\header\corpus\tei")
    ap.add_argument("--db", default=r"C:\Users\EG\Desktop\Tubitak___is\01_Header_Modeli\header_metadatalar.db")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    ids = []
    for f in sorted(glob.glob(os.path.join(a.corpus, "*.xml"))):
        m = re.search(r'makale_(\d+)', os.path.basename(f))
        if m:
            ids.append(m.group(1))
    ids = sorted(set(ids))

    conn = init_db(a.db)
    var = {r[0] for r in conn.execute("select id from orijinal_metadatalar")}
    kalan = [i for i in ids if i not in var]
    print("korpus ID: %d   DB'de mevcut: %d   cekilecek: %d"
          % (len(ids), len(var), len(kalan)))
    if not kalan:
        print("Hepsi zaten cekilmis.")
        return

    ok = 0
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for msg, row in ex.map(cek, kalan):
            if row:
                conn.execute(
                    "INSERT OR REPLACE INTO orijinal_metadatalar VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
                ok += 1
                if ok % 50 == 0:
                    conn.commit()
                    print("  %d/%d ... (%.0f sn)" % (ok, len(kalan), time.time() - t0))
            else:
                print(" ", msg)
    conn.commit()

    print("\ncekilen: %d / %d" % (ok, len(kalan)))
    for durum, n in conn.execute(
            "select durum, count(*) from orijinal_metadatalar group by durum "
            "order by count(*) desc"):
        print("   %-22s %d" % (durum, n))
    conn.close()
    print("\nDB: %s" % a.db)


if __name__ == "__main__":
    main()
