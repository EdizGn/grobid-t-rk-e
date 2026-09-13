# -*- coding: utf-8 -*-
"""
Karantinayi ALT KUMELERE ayirip GROBID'in her birinde ne yaptigini olcer.

Sorunun tam hali: etiketleyicimiz 289 belgede basligi "bulamadi", ama ayni
esiklerle tum header bolgesinde arayinca baslik ORADA cikti -- yani sorun
aramanin konum penceresiydi. Peki GROBID bu belgelerde basligi buluyor mu?

  buluyorsa  -> belge saglam, suc tamamen etiketleyicide, KURTARILABILIR
  bulamiyorsa-> belge gercekten zor, karantina hakli

Ayni soru yazar icin de sorulur.
"""
import os
import io
import re
import csv
import sys
import glob
import sqlite3
import difflib
import collections
import unicodedata
import xml.etree.ElementTree as ET

import grobid_standart_eval as GSE
GSE.YOKSAY_DIAKRITIK = True        # olcum --diakritik-yoksay ile kosuldu

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(KOK, "04_Genisletilmis_Egitim")
sys.path.insert(0, os.path.join(KOK, "01_Header_Modeli"))
from db_span import canvas_tokens, hedef_tokens, find_span

KAR = os.path.join(GEN, "etiketli_v5", "karantina")
RAPOR = os.path.join(GEN, "etiketli_v5", "rapor.csv")
DB = os.path.join(GEN, "egitim_metadatalar.db")
EGT = os.path.join(GEN, "corpus_v4", "tei")
XML = os.path.join(KOK, "03_Test_ve_Degerlendirme", "karantina_benchmark", "grobid_xml")
NS = "{http://www.tei-c.org/ns/1.0}"
TAG = re.compile(r'<(?!lb\b)[^>]*>')
DIA = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def norm(s):
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("I", "ı").replace("İ", "i").lower().translate(DIA)
    return re.sub(r'[^\w]', '', s, flags=re.UNICODE)


def lev(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def grobid_oku(yol):
    try:
        k = ET.parse(yol).getroot()
    except Exception:
        return "", ""
    t = k.find(".//%stitleStmt/%stitle" % (NS, NS))
    baslik = "".join(t.itertext()).strip() if t is not None else ""
    isim = []
    for a in k.findall(".//%ssourceDesc//%sauthor//%spersName" % (NS, NS, NS)):
        isim.append(" ".join(x.strip() for x in a.itertext() if x.strip()))
    return baslik, " ".join(isim)


def main():
    egitilmis = set(os.listdir(EGT))
    con = sqlite3.connect(DB)
    meta = {}
    for i, bt, yz, bt_en in con.execute(
            "select id, gercek_baslik, gercek_yazarlar, gercek_baslik_en "
            "from orijinal_metadatalar"):
        # baslik icin TR ve EN'in ikisi de gecerli referans -- olcum betigi de
        # boyle yapiyor. Bu belgelerde Turkce baslik cogu zaten PDF'te yok.
        meta[str(i)] = ([x for x in (bt, bt_en) if str(x or "").strip()],
                        [yz] if str(yz or "").strip() else [])

    # --- her belgeyi "ilk takildigi kapi" + "kurtarilabilir mi" ile etiketle
    etiket = {}
    for r in csv.DictReader(io.open(RAPOR, encoding="utf-8-sig")):
        if r["durum"] != "karantina" or r["dosya"] in egitilmis:
            continue
        f = set(x for x in r["alanlar"].split("|") if x)
        mid = re.search(r"makale_(\d+)", r["dosya"]).group(1)
        if "title" not in f:
            kapi, alan = "baslik", 0
        elif not ({"abstract_tr", "abstract_en"} & f or {"keyword_tr", "keyword_en"} & f):
            etiket[mid] = ("ozet/kelime yok", None)
            continue
        elif "author" not in f:
            kapi, alan = "yazar", 1
        else:
            etiket[mid] = ("diger", None)
            continue

        ham = io.open(os.path.join(KAR, r["dosya"]), encoding="utf-8").read()
        m = re.search(r"<front>(.*?)</front>", ham, re.S)
        canvas = TAG.sub("", m.group(1)) if m else ""
        ctoks = canvas_tokens(canvas)
        hedefler = meta.get(mid, ([], []))[alan]
        hed = hedef_tokens(hedefler[0]) if hedefler else []
        # etiketleyicinin TAM esikleri, ama tum front'ta ara
        varmi = bool(hed) and bool(find_span(ctoks, hed, min_kapsama=0.45,
                                             min_yogunluk=0.34))
        etiket[mid] = (kapi, "pencere" if varmi else "yok")

    # --- GROBID her alt kumede ne yapti
    say = collections.defaultdict(lambda: {"n": 0, "uretti": 0, "dogru": 0})
    for yol in glob.glob(os.path.join(XML, "*.xml")):
        mid = os.path.basename(yol)[7:-4]
        if mid not in etiket:
            continue
        kapi, tur = etiket[mid]
        if tur is None:
            continue
        p = GSE.oku(yol)
        if not p:
            continue
        dogrular = meta.get(mid, ([], []))[0 if kapi == "baslik" else 1]
        alan_ad = "title" if kapi == "baslik" else "authors"
        tahmin = p[alan_ad]
        anahtar = "%s / %s" % (kapi, tur)
        d = say[anahtar]
        d["n"] += 1
        if str(tahmin).strip():
            d["uretti"] += 1
            if alan_ad == "authors":
                ok = any(GSE.esles("levenshtein", GSE.yazar_normalize(tahmin),
                                   GSE.yazar_normalize(x)) for x in dogrular)
            else:
                ok = any(GSE.esles("levenshtein", tahmin, x) for x in dogrular)
            if ok:
                d["dogru"] += 1

    print("=== GROBID, karantinanin ALT KUMELERINDE ne yapti ===")
    print()
    print("  'pencere' = etiketleyici bulamadi ama metinde AYNI esiklerle var")
    print("  'yok'     = metinde gercekten yok")
    print()
    print("  %-22s %6s %10s %10s" % ("alt kume", "belge", "uretti", "dogru(lev>=.8)"))
    for k in sorted(say):
        d = say[k]
        print("  %-22s %6d %6d(%3.0f%%) %6d(%3.0f%%)"
              % (k, d["n"], d["uretti"], 100.0*d["uretti"]/max(d["n"], 1),
                 d["dogru"], 100.0*d["dogru"]/max(d["n"], 1)))


if __name__ == "__main__":
    main()
