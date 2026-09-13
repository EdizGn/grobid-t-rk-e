# -*- coding: utf-8 -*-
"""
ADIM 4/4 -- Etiketlenmis yeni veriyi GROBID egitim korpusuna kurar.

Mevcut 494 dosyayi SILMEZ, uzerine ekler. Karantinadakiler alinmaz.
Hem TEI hem de eslesen raw feature dosyasi kopyalanir (ikisi de sart).

Kurulumdan once mevcut korpus yedeklenir.
"""
import os
import re
import glob
import shutil
import argparse
import datetime

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KOK = PROJE_KOK + r""
HEDEF = os.path.join(KOK, r"grobid\grobid-trainer\resources\dataset\header\corpus")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--altin", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\etiketli\altin"))
    ap.add_argument("--raw", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\corpus\raw"))
    ap.add_argument("--hedef", default=HEDEF)
    ap.add_argument("--yedek", action="store_true", default=True)
    ap.add_argument("--kuru", action="store_true", help="sadece rapor, kopyalama yok")
    a = ap.parse_args()

    t_tei = os.path.join(a.hedef, "tei")
    t_raw = os.path.join(a.hedef, "raw")
    onceki = len(glob.glob(os.path.join(t_tei, "*.xml")))
    print("mevcut korpus TEI: %d" % onceki)

    altin = glob.glob(os.path.join(a.altin, "*.xml"))
    print("yeni altin dosya : %d" % len(altin))

    # raw esi olmayan TEI kurulamaz -- trainer hizalama icin ikisini de ister
    kurulacak = []
    raw_yok = 0
    for f in altin:
        ad = os.path.basename(f)
        raw_ad = ad.replace(".tei.xml", "")
        if os.path.exists(os.path.join(a.raw, raw_ad)):
            kurulacak.append((f, os.path.join(a.raw, raw_ad), ad, raw_ad))
        else:
            raw_yok += 1
    print("raw esi olan     : %d   (raw'i olmayan atlandi: %d)" % (len(kurulacak), raw_yok))

    if a.kuru:
        print("\n[kuru calisma] kopyalama yapilmadi.")
        print("kurulsaydi toplam korpus: %d" % (onceki + len(kurulacak)))
        return

    if not kurulacak:
        print("Kurulacak dosya yok.")
        return

    if a.yedek:
        damga = datetime.datetime.now().strftime("%m%d_%H%M")
        yed = os.path.join(a.hedef, "tei_YEDEK_%s" % damga)
        shutil.copytree(t_tei, yed)
        print("\nmevcut korpus yedeklendi -> %s" % os.path.basename(yed))

    for tei_k, raw_k, tei_ad, raw_ad in kurulacak:
        shutil.copy2(tei_k, os.path.join(t_tei, tei_ad))
        shutil.copy2(raw_k, os.path.join(t_raw, raw_ad))

    sonra = len(glob.glob(os.path.join(t_tei, "*.xml")))
    print("\nKORPUS: %d -> %d  (+%d)" % (onceki, sonra, sonra - onceki))

    print("\netiket dagilimi:")
    etiketler = ["docTitle", "docAuthor", "affiliation", 'div type="abstract"',
                 "keyword", "reference", "idno", "date"]
    icerik = {}
    for f in glob.glob(os.path.join(t_tei, "*.xml")):
        s = open(f, encoding="utf-8", errors="replace").read()
        for e in etiketler:
            if e in s:
                icerik[e] = icerik.get(e, 0) + 1
    for e in etiketler:
        v = icerik.get(e, 0)
        print("   %-22s %5d  (%5.1f%%)" % (e, v, v * 100 / max(sonra, 1)))

    print("\nSonraki adim:")
    print("  cd grobid && ./gradlew train_header")
    print("  python 01_Header_Modeli\model_kur.py")


if __name__ == "__main__":
    main()
