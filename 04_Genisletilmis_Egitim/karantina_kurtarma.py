# -*- coding: utf-8 -*-
"""
Karantinadaki belgelerde DB'nin basligi/yazari metinde GERCEKTEN yok mu,
yoksa bizim bulanik esleyicimiz mi bulamadi?

Etiketleyici find_span'i min_kapsama=0.45 ile cagiriyor. Burada ayni hedefi
giderek gevseyen esiklerle ariyoruz. Eger dusuk esikte bulunuyorsa belge
KURTARILABILIR -- suc esikte. Hicbir esikte bulunmuyorsa metinde gercekten
yok -- karantina hakli.
"""
import os
import io
import re
import sys
import csv
import sqlite3
import collections

KOK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(KOK), "01_Header_Modeli"))
from db_span import canvas_tokens, hedef_tokens, find_span

KAR = os.path.join(KOK, "etiketli_v5", "karantina")
RAPOR = os.path.join(KOK, "etiketli_v5", "rapor.csv")
DB = os.path.join(KOK, "egitim_metadatalar.db")
EGT = os.path.join(KOK, "corpus_v4", "tei")
TAG = re.compile(r'<(?!lb\b)[^>]*>')

ESIKLER = [0.45, 0.35, 0.25, 0.15]      # 0.45 = etiketleyicinin kullandigi


def main():
    egitilmis = set(os.listdir(EGT))
    con = sqlite3.connect(DB)
    meta = {}
    for i, bt, yz in con.execute(
            "select id, gercek_baslik, gercek_yazarlar from orijinal_metadatalar"):
        meta[str(i)] = (bt or "", yz or "")

    # hangi belge hangi kapiya takildi
    kapi = {}
    for r in csv.DictReader(io.open(RAPOR, encoding="utf-8-sig")):
        if r["durum"] != "karantina" or r["dosya"] in egitilmis:
            continue
        f = set(x for x in r["alanlar"].split("|") if x)
        if "title" not in f:
            kapi[r["dosya"]] = "baslik"
        elif not ({"abstract_tr", "abstract_en"} & f or
                  {"keyword_tr", "keyword_en"} & f):
            kapi[r["dosya"]] = "ozet"
        elif "author" not in f:
            kapi[r["dosya"]] = "yazar"

    sonuc = {"baslik": collections.Counter(), "yazar": collections.Counter()}
    for ad, hangi in sorted(kapi.items()):
        if hangi == "ozet":
            continue
        mid = re.search(r"makale_(\d+)", ad).group(1)
        bt, yz = meta.get(mid, ("", ""))
        hedef_metin = bt if hangi == "baslik" else yz
        if not str(hedef_metin).strip():
            sonuc[hangi]["DB'de bu alan zaten BOS"] += 1
            continue
        ham = io.open(os.path.join(KAR, ad), encoding="utf-8").read()
        m = re.search(r"<front>(.*?)</front>", ham, re.S)
        if not m:
            sonuc[hangi]["metin okunamadi"] += 1
            continue
        canvas = TAG.sub("", m.group(1))
        ctoks = canvas_tokens(canvas)
        hed = hedef_tokens(hedef_metin)
        # a) etiketleyicinin TAM parametreleri, ama tum front'ta ara.
        #    Burada bulunuyorsa sorun esik degil, aramanin KONUM PENCERESI.
        if find_span(ctoks, hed, min_kapsama=0.45, min_yogunluk=0.34):
            sonuc[hangi]["ayni esikte bulunuyor -> sorun KONUM PENCERESI"] += 1
            continue
        # b) esikleri gevset
        bulundu = None
        for e in ESIKLER:
            if find_span(ctoks, hed, min_kapsama=e, min_yogunluk=0.20):
                bulundu = e
                break
        if bulundu is None:
            sonuc[hangi]["metinde HIC yok (karantina hakli)"] += 1
        else:
            sonuc[hangi]["ancak esik gevseyince bulunuyor (kapsama %.2f)" % bulundu] += 1

    for hangi, etiket in (("baslik", "TURKCE BASLIK bulunamayan 495 belge"),
                          ("yazar", "YAZAR bulunamayan 392 belge")):
        c = sonuc[hangi]
        t = sum(c.values())
        print("=== %s ===" % etiket)
        for k, v in c.most_common():
            print("   %-52s %4d  (%4.1f%%)" % (k, v, 100.0 * v / max(t, 1)))
        print()


if __name__ == "__main__":
    main()
