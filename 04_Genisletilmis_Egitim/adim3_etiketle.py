# -*- coding: utf-8 -*-
"""
ADIM 3/4 -- createTraining ciktisini korpus yapisina cevirir ve
mevcut otomatik etiketleyiciyi (01_Header_Modeli/header_auto_annotate.py)
genisletilmis veri uzerinde calistirir.

createTraining duz bir klasore yaziyor:
    makale_X.training.header            (raw feature)
    makale_X.training.header.tei.xml    (TEI)
Etiketleyici ise corpus/{tei,raw} yapisi bekliyor. Burada kopyalayarak
o yapiyi kuruyoruz (tasima degil kopyalama: adim 2 tekrar calistirilabilsin).
"""
import os
import re
import sys
import glob
import shutil
import sqlite3
import argparse
import subprocess

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KOK = PROJE_KOK + r""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--girdi", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\egitim_verisi"))
    ap.add_argument("--corpus", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\corpus"))
    ap.add_argument("--out", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\etiketli"))
    ap.add_argument("--db", default=os.path.join(KOK, r"04_Genisletilmis_Egitim\egitim_metadatalar.db"))
    a = ap.parse_args()

    tei_d = os.path.join(a.corpus, "tei")
    raw_d = os.path.join(a.corpus, "raw")
    os.makedirs(tei_d, exist_ok=True)
    os.makedirs(raw_d, exist_ok=True)

    # Metadata'si olmayan belgeyi almiyoruz: etiketleme DB span'ina dayaniyor
    try:
        meta = {str(r[0]) for r in sqlite3.connect(a.db).execute(
            "select id from orijinal_metadatalar")}
    except Exception as e:
        print("HATA: metadata DB okunamadi: %s" % e)
        return 1
    print("metadata'da kayitli makale: %d" % len(meta))

    kopya = atlanan = 0
    for tei in glob.glob(os.path.join(a.girdi, "*.training.header.tei.xml")):
        ad = os.path.basename(tei)
        m = re.search(r'makale_(\d+)', ad)
        if not m:
            continue
        mid = m.group(1)
        raw = os.path.join(a.girdi, ad.replace(".tei.xml", ""))
        if mid not in meta or not os.path.exists(raw):
            atlanan += 1
            continue
        shutil.copy2(tei, os.path.join(tei_d, ad))
        shutil.copy2(raw, os.path.join(raw_d, os.path.basename(raw)))
        kopya += 1

    print("korpusa kopyalanan: %d   (atlanan: %d)" % (kopya, atlanan))
    if kopya == 0:
        print("Etiketlenecek dosya yok.")
        return 1

    betik = os.path.join(KOK, r"01_Header_Modeli\header_auto_annotate.py")
    print("\notomatik etiketleme calistiriliyor...\n" + "-" * 55)
    r = subprocess.run(
        [sys.executable, betik, "--corpus", a.corpus, "--out", a.out, "--altin-db", a.db],
        cwd=os.path.dirname(betik),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
