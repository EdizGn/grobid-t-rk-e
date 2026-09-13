# -*- coding: utf-8 -*-
"""
GROBID'in KAYNAKCA zincirini olcer. Bu zincir projede hic egitilmedi ve
hic olculmedi -- tum olcumlerimiz processHeaderDocument ile yapildi, o da
yalnizca header bolgesini isliyor.

Zincir:
    segmentation        -> PDF'te kaynakca bolgesini bulur
    reference-segmenter -> o blogu tek tek kunyelere boler
    citation            -> bir kunyeyi alanlara ayirir
    name/citation       -> kunyedeki isimleri parcalar

ALTIN VERI: TR Dizin API'si makalenin kaynakcasini da donuyor
(`references[].context` = kunyenin ham metni). Toplayici betiklerimiz bu
alani atiyordu; burada dogrudan API'den cekiyoruz.

    python kaynakca_olc.py --n 100

Adimlar:
  1. Test kumesinden N makale sec (PDF'i yerelde olanlardan)
  2. TR Dizin API'sinden kaynakcalarini cek
  3. GROBID processFulltextDocument ile PDF'leri isle
  4. Bulunan kunyeleri altin kunyelerle karsilastir
"""
import os
import re
import sys
import json
import time
import glob
import random
import difflib
import argparse
import sqlite3
import requests
import concurrent.futures
import xml.etree.ElementTree as ET

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST = os.path.join(KOK, "03_Test_ve_Degerlendirme", "1500_random_test")
PDF_D = os.path.join(TEST, "makaleler")
ONBELLEK = os.path.join(KOK, "03_Test_ve_Degerlendirme", "kaynakca_altin")
XML_D = os.path.join(KOK, "03_Test_ve_Degerlendirme", "kaynakca_xml")

API = "https://search.trdizin.gov.tr/api/publicationById/{}?archiveSearch=ADD_ARCHIVE"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
GROBID = "http://127.0.0.1:8070/api/processFulltextDocument"
NS = "{http://www.tei-c.org/ns/1.0}"


# ---------------------------------------------------------------- altin veri
def altin_cek(mid):
    """TR Dizin'den kaynakca listesini ceker. Onbellege yazar."""
    p = os.path.join(ONBELLEK, "%s.json" % mid)
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    try:
        r = requests.get(API.format(mid), headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        d = r.json()
    except Exception:
        return None
    kayit = d.get("hits", {}).get("hits", [{}])
    kaynak = kayit[0].get("_source", {}) if kayit else {}
    if not kaynak:
        kaynak = d if isinstance(d, dict) else {}
    refs = kaynak.get("references") or []
    out = [str(x.get("context") or "").strip()
           for x in refs if isinstance(x, dict) and x.get("context")]
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return out


# ---------------------------------------------------------------- GROBID
def grobid_isle(pdf, mid):
    o = os.path.join(XML_D, "makale_%s.xml" % mid)
    if os.path.exists(o):
        return "atlandi"
    try:
        with open(pdf, "rb") as f:
            r = requests.post(GROBID,
                              files={"input": (os.path.basename(pdf), f, "application/pdf")},
                              data={"consolidateCitations": "0"},
                              headers={"Accept": "application/xml"}, timeout=300)
        if r.status_code == 200:
            open(o, "w", encoding="utf-8").write(r.text)
            return "ok"
        return "http%s" % r.status_code
    except Exception:
        return "hata"


def kunyeleri_cikar(xml_yolu):
    """listBibl icindeki her biblStruct'i (duz metin, alanlar) olarak dondurur."""
    try:
        kok = ET.parse(xml_yolu).getroot()
    except Exception:
        return []
    out = []
    for lb in kok.iter("%slistBibl" % NS):
        for bs in lb.findall("%sbiblStruct" % NS):
            metin = " ".join(t.strip() for t in bs.itertext() if t and t.strip())
            alan = {}
            t = bs.find(".//%stitle[@level='a']" % NS)
            if t is not None and t.text:
                alan["baslik"] = t.text.strip()
            j = bs.find(".//%stitle[@level='j']" % NS)
            if j is not None and j.text:
                alan["dergi"] = j.text.strip()
            d = bs.find(".//%sdate" % NS)
            if d is not None:
                alan["yil"] = (d.get("when") or d.text or "").strip()[:4]
            yazarlar = []
            for a in bs.findall(".//%sauthor//%ssurname" % (NS, NS)):
                if a.text:
                    yazarlar.append(a.text.strip())
            if yazarlar:
                alan["yazarlar"] = yazarlar
            out.append((re.sub(r"\s+", " ", metin), alan))
    return out


# ---------------------------------------------------------------- eslestirme
def norm(s):
    return re.sub(r"[^0-9a-zà-ÿ]+", " ",
                  (s or "").lower().replace("ı", "i").replace("ş", "s")
                  .replace("ğ", "g").replace("ü", "u").replace("ö", "o")
                  .replace("ç", "c")).strip()


def benzerlik(a, b):
    return difflib.SequenceMatcher(None, norm(a)[:300], norm(b)[:300]).ratio()


def esle(bulunan, altin, esik=0.55):
    """Her altin kunyeyi en iyi bulunan kunyeyle eslestirir (birebir)."""
    kalan = list(range(len(bulunan)))
    eslesme = []
    for i, alt in enumerate(altin):
        en_iyi, en_iyi_j = 0.0, None
        for j in kalan:
            s = benzerlik(alt, bulunan[j][0])
            if s > en_iyi:
                en_iyi, en_iyi_j = s, j
        if en_iyi_j is not None and en_iyi >= esik:
            kalan.remove(en_iyi_j)
            eslesme.append((i, en_iyi_j, en_iyi))
    return eslesme


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="kac makale")
    ap.add_argument("--tohum", type=int, default=42)
    a = ap.parse_args()

    os.makedirs(ONBELLEK, exist_ok=True)
    os.makedirs(XML_D, exist_ok=True)

    pdfler = sorted(glob.glob(os.path.join(PDF_D, "*.pdf")))
    random.seed(a.tohum)
    random.shuffle(pdfler)

    print("=== 1/4  Altin kaynakca cekiliyor (TR Dizin API) ===")
    secilen = []
    for p in pdfler:
        if len(secilen) >= a.n:
            break
        mid = re.search(r"makale_(\d+)", os.path.basename(p)).group(1)
        refs = altin_cek(mid)
        if refs and len(refs) >= 3:
            secilen.append((mid, p, refs))
            if len(secilen) % 20 == 0:
                print("   %d makale (kaynakcali)" % len(secilen), flush=True)
        time.sleep(0.15)
    print("   secilen: %d makale, toplam %d altin kunye"
          % (len(secilen), sum(len(r) for _, _, r in secilen)))
    if not secilen:
        print("HATA: API'den kaynakca alinamadi.")
        return 1

    print("\n=== 2/4  GROBID processFulltextDocument ===")
    say = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        isler = {ex.submit(grobid_isle, p, m): m for m, p, _ in secilen}
        for i, fut in enumerate(concurrent.futures.as_completed(isler), 1):
            s = fut.result()
            say[s] = say.get(s, 0) + 1
            if i % 25 == 0:
                print("   %d/%d %s" % (i, len(secilen), say), flush=True)
    print("   bitti: %s" % say)

    print("\n=== 3/4  Karsilastiriliyor ===")
    top_altin = top_bulunan = top_eslesen = 0
    alan_var = {"baslik": 0, "dergi": 0, "yil": 0, "yazarlar": 0}
    alan_dogru = {"baslik": 0, "dergi": 0, "yil": 0}
    belge_sayilari = []
    for mid, _, altin in secilen:
        x = os.path.join(XML_D, "makale_%s.xml" % mid)
        if not os.path.exists(x):
            continue
        bulunan = kunyeleri_cikar(x)
        eslesme = esle(bulunan, altin)
        top_altin += len(altin)
        top_bulunan += len(bulunan)
        top_eslesen += len(eslesme)
        belge_sayilari.append((len(altin), len(bulunan), len(eslesme)))
        for i, j, _ in eslesme:
            _, alanlar = bulunan[j]
            alt = altin[i]
            for k in alan_var:
                if alanlar.get(k):
                    alan_var[k] += 1
            for k in ("baslik", "dergi"):
                if alanlar.get(k) and norm(alanlar[k])[:40] and norm(alanlar[k])[:40] in norm(alt):
                    alan_dogru[k] += 1
            y = alanlar.get("yil")
            if y and re.fullmatch(r"(19|20)\d{2}", y) and y in alt:
                alan_dogru["yil"] += 1

    print("\n=== 4/4  SONUC ===")
    print("Belge                     : %d" % len(belge_sayilari))
    print("Altin kunye (TR Dizin)    : %d" % top_altin)
    print("GROBID'in buldugu kunye   : %d" % top_bulunan)
    print("Eslesen                   : %d" % top_eslesen)
    if top_altin:
        print("\nKUNYE BOLME (reference-segmenter + segmentation)")
        print("  duyarlilik : %.2f%%   (altin kunyelerin kaci bulundu)"
              % (100.0 * top_eslesen / top_altin))
    if top_bulunan:
        print("  kesinlik   : %.2f%%   (bulunanlarin kaci gercek)"
              % (100.0 * top_eslesen / top_bulunan))
    if top_eslesen:
        print("\nALAN AYRISTIRMA (citation modeli) -- eslesen %d kunye uzerinde"
              % top_eslesen)
        for k in ("baslik", "dergi", "yil"):
            print("  %-10s uretildi %5d (%5.1f%%)   dogru %5d (%5.1f%%)"
                  % (k, alan_var[k], 100.0*alan_var[k]/top_eslesen,
                     alan_dogru[k], 100.0*alan_dogru[k]/top_eslesen))
        print("  %-10s uretildi %5d (%5.1f%%)"
              % ("yazarlar", alan_var["yazarlar"],
                 100.0*alan_var["yazarlar"]/top_eslesen))
    print("\nXML: %s" % XML_D)
    print("Altin: %s" % ONBELLEK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
