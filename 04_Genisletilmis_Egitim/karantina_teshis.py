# -*- coding: utf-8 -*-
"""
v5 karantinasindaki belgeler NEDEN elendi?

Etiketleyicinin kapilarini AYNI SIRAYLA yeniden uygular (header_auto_annotate
satir 675-719). Boylece her belge tek bir "ilk takildigi kapi"ya atanir --
yoksa ayni belge birden cok nedene sayilir.

    ok = ("title" in found) and (abstract_* veya keyword_*)
    + yazar etiketi bulunmali
    + yazar etiketi DOGRU olmali (DB ile ortusme >= 0.3)
    + etiketler soyulunca metin degismemeli (hizalama)

Sadece kurulu modelin egitiminde GORULMEYEN belgeleri sayar; gorulenler
olcume sokulamaz.
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
from db_span import norm_kelime

KAR = os.path.join(KOK, "etiketli_v5", "karantina")
RAPOR = os.path.join(KOK, "etiketli_v5", "rapor.csv")
DB = os.path.join(KOK, "egitim_metadatalar.db")
EGT = os.path.join(KOK, "corpus_v4", "tei")

AUTHOR = re.compile(r"<docAuthor>(.*?)</docAuthor>", re.S)
TAG = re.compile(r"<[^>]+>")


def main():
    egitilmis = set(os.listdir(EGT))

    con = sqlite3.connect(DB)
    meta = {}
    for ad, yz in con.execute(
            "select dosya_adi, gercek_yazarlar from orijinal_metadatalar"):
        k = re.search(r"(\d+)", str(ad or ""))
        if k:
            meta[k.group(1)] = yz or ""

    sayac = collections.Counter()
    kurtarilabilir = []
    ortusme = collections.Counter()

    for r in csv.DictReader(io.open(RAPOR, encoding="utf-8-sig")):
        if r["durum"] != "karantina" or r["dosya"] in egitilmis:
            continue
        ad = r["dosya"]
        found = set(x for x in r["alanlar"].split("|") if x)

        # --- kapi 1: Turkce baslik
        if "title" not in found:
            sayac["1. Turkce baslik bulunamadi" +
                  (" (ama Ingilizcesi var)" if "title_en" in found else "")] += 1
            continue
        # --- kapi 2: ozet veya anahtar kelime
        if not ({"abstract_tr", "abstract_en"} & found or
                {"keyword_tr", "keyword_en"} & found):
            sayac["2. ozet ve anahtar kelime ikisi de yok"] += 1
            continue
        # --- kapi 3: yazar etiketi var mi
        if "author" not in found:
            sayac["3. yazar etiketi hic bulunamadi"] += 1
            continue
        # --- kapi 4: yazar etiketi dogru mu
        mid = re.search(r"makale_(\d+)", ad).group(1)
        hedef = set(n for n in (norm_kelime(t) for t in meta.get(mid, "").split())
                    if len(n) > 2)
        s = io.open(os.path.join(KAR, ad), encoding="utf-8").read()
        m = AUTHOR.search(s)
        etiket = set(n for n in (norm_kelime(t) for t in TAG.sub(" ", m.group(1)).split())
                     if len(n) > 2) if m else set()
        if hedef:
            o = len(hedef & etiket) / float(len(hedef))
            ortusme[min(int(o * 10), 9)] += 1
            if o < 0.3:
                sayac["4. yazar etiketi YANLIS (ortusme < 0.3)"] += 1
                continue
        else:
            sayac["4b. DB'de yazar yok, dogrulanamadi"] += 1
            continue
        # --- kapi 5: geriye sadece hizalama kaliyor
        sayac["5. HIZALAMA bozuk (etiket soyulunca metin degisiyor)"] += 1
        kurtarilabilir.append((ad, o))

    top = sum(sayac.values())
    print("=== v5 KARANTINA: ilk takilan kapi (egitimde gorulmeyen %d belge) ===" % top)
    print()
    for k, v in sorted(sayac.items()):
        print("  %-56s %5d  (%4.1f%%)" % (k, v, 100.0 * v / max(top, 1)))

    if ortusme:
        print()
        print("--- kapi 3'u gecenlerde yazar ortusme dagilimi ---")
        for i in range(10):
            n = ortusme.get(i, 0)
            if n:
                print("  %.1f-%.1f  %4d  %s" % (i/10.0, (i+1)/10.0, n, "#" * (n // 8)))

    if kurtarilabilir:
        print()
        print("--- HIZALAMA yuzunden kaybedilenler: %d belge ---" % len(kurtarilabilir))
        print("    bunlarin etiketleri dogru; tek sorun teknik. Ornek:")
        for ad, o in kurtarilabilir[:5]:
            print("      %s  (yazar ortusmesi %.2f)" % (ad, o))


if __name__ == "__main__":
    main()
