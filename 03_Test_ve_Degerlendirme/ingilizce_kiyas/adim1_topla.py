# -*- coding: utf-8 -*-
"""
ADIM 1/3 -- Ingilizce kiyas kumesi toplar (PMC Open Access).

NEDEN: GROBID'in yayinladigi PMC benchmark'i (baslik 98.07) DeLFT header
modeli VE biblio-glutton konsolidasyonu ile uretilmis. Bizim Turkce
olcumlerimiz konsolidasyonsuz saf CRF. Bu yuzden dogrudan kiyaslanamaz.

Cozum: Ingilizce makaleleri KENDI hattimizdan gecirmek -- ayni container,
ayni model, ayni degerlendirme scripti, konsolidasyon yok.

Kaynak: s3://pmc-oa-opendata  (her makale klasorunde hem PDF hem JATS XML)
Altin standart: JATS XML = yayincinin kendi yapilandirilmis metadata'si.
"""
import os
import re
import json
import random
import sqlite3
import argparse
import requests
import threading
import concurrent.futures
from lxml import etree

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

S3 = "https://pmc-oa-opendata.s3.amazonaws.com/"
H = {"User-Agent": "GROBID-TR-benchmark/1.0 (academic research)"}


def init_db(path):
    c = sqlite3.connect(path, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS orijinal_metadatalar (
        id TEXT PRIMARY KEY, dosya_adi TEXT,
        gercek_baslik TEXT, gercek_ozet TEXT, gercek_yazarlar TEXT,
        gercek_anahtar_kelimeler TEXT, gercek_yil TEXT, gercek_dergi TEXT,
        gercek_doi TEXT, gercek_baslik_en TEXT, gercek_ozet_en TEXT,
        gercek_anahtar_kelimeler_en TEXT, durum TEXT)""")
    c.commit()
    return c


def metin(el):
    if el is None:
        return ""
    return " ".join("".join(el.itertext()).split())


def jats_coz(xml_bayt):
    """JATS XML'den altin standart metadata cikarir."""
    try:
        r = etree.fromstring(xml_bayt)
    except Exception:
        return None
    f = r.find(".//front")
    if f is None:
        return None
    am = f.find(".//article-meta")
    jm = f.find(".//journal-meta")
    if am is None:
        return None

    baslik = metin(am.find(".//title-group/article-title"))

    yazarlar = []
    for c in am.findall(".//contrib-group/contrib"):
        if c.get("contrib-type") not in (None, "author"):
            continue
        sn, gn = c.find(".//surname"), c.find(".//given-names")
        ad = " ".join(x for x in [metin(gn), metin(sn)] if x)
        if ad:
            yazarlar.append(ad)

    ozet = ""
    for a in am.findall(".//abstract"):
        if a.get("abstract-type") in (None, "", "summary"):
            ozet = metin(a)
            break
    if not ozet:
        ozet = metin(am.find(".//abstract"))
    # JATS'ta abstract basliklari metne karisiyor, ilk "Abstract" etiketini at
    ozet = re.sub(r'^\s*Abstract\s*', '', ozet)

    kelimeler = [metin(k) for k in am.findall(".//kwd-group/kwd")]
    yil = metin(am.find(".//pub-date/year"))
    dergi = metin(jm.find(".//journal-title")) if jm is not None else ""
    doi = ""
    for i in am.findall(".//article-id"):
        if i.get("pub-id-type") == "doi":
            doi = metin(i)
    return dict(baslik=baslik, yazarlar=", ".join(yazarlar), ozet=ozet,
                kelimeler=", ".join(kelimeler), yil=yil, dergi=dergi, doi=doi)


def indir(pmc, pdf_dir):
    """(durum, satir)"""
    kok = "%s%s/%s" % (S3, pmc, pmc)
    try:
        xr = requests.get(kok + ".xml", headers=H, timeout=40)
        if xr.status_code != 200:
            return "xml_yok", None
        m = jats_coz(xr.content)
        if not m or not (m["baslik"] and m["ozet"] and m["yazarlar"]):
            return "eksik", None

        pr = requests.get(kok + ".pdf", headers=H, timeout=90, stream=True)
        if pr.status_code != 200:
            return "pdf_yok", None
        mid = pmc.split(".")[0]
        yol = os.path.join(pdf_dir, "makale_%s.pdf" % mid)
        boyut = 0
        with open(yol, "wb") as fh:
            for ch in pr.iter_content(8192):
                fh.write(ch)
                boyut += len(ch)
        if boyut < 20000:
            os.remove(yol)
            return "bozuk", None
        return "ok", (mid, "makale_%s.pdf" % mid, m["baslik"], m["ozet"],
                      m["yazarlar"], m["kelimeler"], m["yil"], m["dergi"],
                      m["doi"], "", "", "", "Tam")
    except Exception:
        return "hata", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedef", type=int, default=500)
    ap.add_argument("--out", default=PROJE_KOK + r"\08_Ingilizce_Kiyas")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--tohum", type=int, default=42)
    a = ap.parse_args()

    pdf_dir = os.path.join(a.out, "makaleler")
    os.makedirs(pdf_dir, exist_ok=True)
    conn = init_db(os.path.join(a.out, "ingilizce_metadatalar.db"))
    var = {r[0] for r in conn.execute("select id from orijinal_metadatalar")}

    # S3 anahtar listesinden rastgele makale klasoru sec
    print("S3 makale listesi cekiliyor...")
    klasorler, token = [], None
    while len(klasorler) < 20000:
        u = S3 + "?list-type=2&delimiter=/&max-keys=1000"
        if token:
            u += "&continuation-token=" + requests.utils.quote(token, safe="")
        r = requests.get(u, headers=H, timeout=60)
        s = r.text
        yeni = re.findall(r'<Prefix>(PMC[\d.]+)/</Prefix>', s)
        if not yeni:
            break
        klasorler += yeni
        m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', s)
        if not m:
            break
        token = m.group(1)
    print("aday makale klasoru: %d" % len(klasorler))

    rnd = random.Random(a.tohum)
    rnd.shuffle(klasorler)

    kilit = threading.Lock()
    say = {"ok": 0, "eksik": 0, "xml_yok": 0, "pdf_yok": 0, "bozuk": 0, "hata": 0}
    tampon = []

    def calis(pmc):
        with kilit:
            if say["ok"] >= a.hedef:
                return
        if pmc.split(".")[0] in var:
            return
        d, satir = indir(pmc, pdf_dir)
        with kilit:
            say[d] = say.get(d, 0) + 1
            if satir:
                tampon.append(satir)
                if len(tampon) >= 20:
                    conn.executemany("INSERT OR REPLACE INTO orijinal_metadatalar "
                                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", tampon)
                    conn.commit()
                    tampon.clear()
                if say["ok"] % 50 == 0:
                    print("  %d/%d  (eksik %d, pdf yok %d, hata %d)"
                          % (say["ok"], a.hedef, say["eksik"], say["pdf_yok"], say["hata"]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(calis, klasorler))

    if tampon:
        conn.executemany("INSERT OR REPLACE INTO orijinal_metadatalar "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", tampon)
        conn.commit()
    n = conn.execute("select count(*) from orijinal_metadatalar").fetchone()[0]
    print("\nTOPLAM: %d makale   PDF: %s" % (n, pdf_dir))
    print("durumlar:", say)
    conn.close()


if __name__ == "__main__":
    main()
