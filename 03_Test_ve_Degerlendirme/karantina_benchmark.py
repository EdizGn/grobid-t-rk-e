# -*- coding: utf-8 -*-
"""
KARANTINA BENCHMARK -- etiketleyicinin eledigi belgelerde model ne yapiyor?

Soru: v5 etiketleyicisi 1314 belgeyi "guvenilmez" diye eledi. Bu belgeler
gercekten bozuk mu, yoksa etiketleyicimiz mi beceremedi? Modelin kendisi
ayni belgelerde dogru cikarim yapiyorsa, sucun bizde oldugunu gosterir.

SIZINTI KONTROLU: karantinadaki 1314 belgenin 263'u kurulu modelin egitim
kumesinde (corpus_v4/tei) var -- onlar olculemez, model onlari ezberlemis
olabilir. Sadece kalan 1051 belge kullanilir. Bu filtre burada tekrar
uygulanir, disaridan verilen listeye guvenilmez.

    python karantina_benchmark.py --isle      # GROBID'den XML uret
    python karantina_benchmark.py --olc       # skorla

Karsilastirma referansi: ayni model, 1500'luk rastgele test kumesi.
"""
import os
import re
import sys
import glob
import time
import argparse
import requests
import concurrent.futures

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(KOK, "04_Genisletilmis_Egitim")
KAR = os.path.join(GEN, "etiketli_v5", "karantina")
EGT = os.path.join(GEN, "corpus_v4", "tei")
PDF = os.path.join(GEN, "makaleler")
CIK = os.path.join(KOK, "03_Test_ve_Degerlendirme", "karantina_benchmark")
XML = os.path.join(CIK, "grobid_xml")
GROBID = "http://127.0.0.1:8070/api/processHeaderDocument"


def hedef_idler():
    """Karantinada olan ama egitimde GORULMEYEN belgelerin id'leri."""
    egitilmis = set(os.listdir(EGT))
    out = []
    for ad in sorted(os.listdir(KAR)):
        if ad in egitilmis:
            continue
        m = re.search(r"makale_(\d+)", ad)
        if m:
            out.append(m.group(1))
    return out


def isle(mid):
    o = os.path.join(XML, "makale_%s.xml" % mid)
    if os.path.exists(o) and os.path.getsize(o) > 200:
        return "atlandi"
    p = os.path.join(PDF, "makale_%s.pdf" % mid)
    if not os.path.exists(p):
        return "pdf_yok"
    try:
        with open(p, "rb") as f:
            r = requests.post(GROBID,
                              files={"input": (os.path.basename(p), f,
                                               "application/pdf")},
                              headers={"Accept": "application/xml"}, timeout=300)
        if r.status_code == 200:
            with open(o, "w", encoding="utf-8") as g:
                g.write(r.text)
            return "ok"
        return "http%s" % r.status_code
    except Exception:
        return "hata"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--isle", action="store_true")
    ap.add_argument("--olc", action="store_true")
    ap.add_argument("--is-sayisi", type=int, default=4)
    a = ap.parse_args()

    os.makedirs(XML, exist_ok=True)
    idler = hedef_idler()
    print("karantinada + egitimde gorulmemis: %d belge" % len(idler))

    if a.isle:
        try:
            requests.get("http://127.0.0.1:8070/api/isalive", timeout=5)
        except Exception:
            print("HATA: GROBID servisi (8070) ayakta degil.")
            return 1
        say = {}
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.is_sayisi) as ex:
            for i, s in enumerate(ex.map(isle, idler), 1):
                say[s] = say.get(s, 0) + 1
                if i % 100 == 0:
                    print("   %d/%d  %s  (%.0f sn)"
                          % (i, len(idler), say, time.time() - t0), flush=True)
        print("bitti: %s" % say)

    if a.olc:
        n = len(glob.glob(os.path.join(XML, "*.xml")))
        print("uretilen XML: %d" % n)
        print("\nSkorlamak icin:")
        print("  python grobid_standart_eval.py --xml %s \\" % XML)
        print("      --db %s \\" % os.path.join(GEN, "egitim_metadatalar.db"))
        print("      --diakritik-yoksay")
    return 0


if __name__ == "__main__":
    sys.exit(main())
