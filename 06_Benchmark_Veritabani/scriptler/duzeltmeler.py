#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark-300 veri duzeltmeleri (yeniden_skorla.py'den SONRA calistirilir).

1) Etiket duzeltmesi: olculen metin katmani ile celisen PRIMARY etiketleri.
   - 5 belge `taranmis` -> `bozuk-font` (metin katmani VAR, kodlamasi bozuk;
     gercek taranmislar `grobid-crash` grubunda, orada metin hic yok)
   - 618882: FLAGS'e bozuk-font eklenir (PRIMARY degismez)
   - 95366 : kolay katmanda ama kodlamasi bozuk -> `kolay_supheli` isaretlenir
     (PDF yerinde birakilir; degistirme karari kullaniciya ait, 120 sayisi bozulmasin)
   PDF klasorleri de yeni PRIMARY'ye tasinir (hepsi ayni TIER icinde kalir).

2) makale_29094.pdf: dosyanin basinda 128 baytlik cop on-ek, sonunda NUL dolgu
   var (%PDF- 128. bayttan basliyor). Katı ayristiricilar dosyayi reddediyor.
   Onarilir, orijinali .bozuk uzantisiyla saklanir.

3) secim/segmentation_gold.csv yenilenir: eski dosya onceki secim turundan
   kalma (26 satir, 24'u 300'de). Yenisi 300 icindeki onarilmis TEI'leri
   (onarilmis_var=1, 31 belge) XML yoluyla birlikte listeler.

Idempotent: tekrar calistirilabilir.
"""
import os, csv, re, glob, shutil, json

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = PROJE_KOK + r""
OUT = os.path.join(BASE, "06_Benchmark_Veritabani")
SEC = os.path.join(OUT, "secim")
PDF300 = os.path.join(SEC, "pdf300")
V2 = os.path.join(SEC, "benchmark_300_v2.csv")
ONARILMIS = os.path.join(BASE, "03_Test_ve_Degerlendirme", "sıkıntılı_pdfler", "Onarilmis_XMLler")

TARANMIS_DUZELT = ["83611", "88823", "88826", "98469", "98492"]
FLAG_EKLE = {"618882": "bozuk-font"}
KOLAY_SUPHELI = ["95366"]
BOZUK_PDF = "29094"

log = []


def pdf_yolu(mid):
    g = glob.glob(os.path.join(PDF300, "*", "*", "makale_%s.pdf" % mid))
    return g[0] if g else None


def main():
    rows = list(csv.DictReader(open(V2, encoding="utf-8-sig")))
    idx = {r["makale_id"]: r for r in rows}

    # --- 1) etiket duzeltmeleri ---
    for mid in TARANMIS_DUZELT:
        r = idx[mid]
        if r["PRIMARY"] == "taranmis":
            r["PRIMARY"] = "bozuk-font"
            fl = [x for x in r["FLAGS"].split(";") if x and x != "taranmis"]
            if "bozuk-font" not in fl:
                fl.insert(0, "bozuk-font")
            r["FLAGS"] = ";".join(fl)
            log.append("%s: PRIMARY taranmis -> bozuk-font" % mid)
        src = pdf_yolu(mid)
        hedef = os.path.join(PDF300, r["TIER"], r["PRIMARY"], "makale_%s.pdf" % mid)
        if src and os.path.abspath(src) != os.path.abspath(hedef):
            os.makedirs(os.path.dirname(hedef), exist_ok=True)
            shutil.move(src, hedef)
            log.append("%s: PDF -> %s/%s/" % (mid, r["TIER"], r["PRIMARY"]))

    for mid, fl in FLAG_EKLE.items():
        r = idx[mid]
        cur = [x for x in r["FLAGS"].split(";") if x]
        if fl not in cur:
            cur.append(fl)
            r["FLAGS"] = ";".join(cur)
            log.append("%s: FLAGS += %s" % (mid, fl))

    for r in rows:
        r["kolay_supheli"] = 1 if r["makale_id"] in KOLAY_SUPHELI else 0
    log.append("kolay_supheli isaretlenen: %s (PDF yerinde birakildi)" % ",".join(KOLAY_SUPHELI))

    # bosalan klasorleri temizle
    for d in glob.glob(os.path.join(PDF300, "*", "*")):
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            log.append("bos klasor silindi: %s" % os.path.relpath(d, PDF300))

    # --- 2) bozuk PDF on-eki ---
    p = pdf_yolu(BOZUK_PDF)
    if p:
        d = open(p, "rb").read()
        if not d.startswith(b"%PDF-"):
            i = d.find(b"%PDF-")
            j = d.rfind(b"%%EOF")
            if i > 0 and j > i:
                shutil.copy2(p, p + ".bozuk")
                open(p, "wb").write(d[i:j + 5])
                log.append("%s: %d baytlik cop on-ek ve sondaki NUL dolgu temizlendi "
                           "(orijinal: makale_%s.pdf.bozuk)" % (BOZUK_PDF, i, BOZUK_PDF))
        else:
            log.append("%s: zaten onarilmis" % BOZUK_PDF)

    # --- 3) segmentation gold yenile ---
    xml = {}
    for q in glob.glob(os.path.join(ONARILMIS, "*.xml")):
        m = re.search(r"(\d{3,})", os.path.basename(q))
        if m:
            xml[m.group(1)] = q
    seg = [r for r in rows if r["onarilmis_var"] == "1"]
    kol = ["makale_id", "PRIMARY", "TIER", "FLAGS", "dil", "year", "pages", "gold_journal",
           "meta_class", "siddet", "sikinti_skoru", "metin_katmani", "path"]
    with open(os.path.join(SEC, "segmentation_gold.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=kol + ["onarilmis_xml"], extrasaction="ignore")
        w.writeheader()
        for r in seg:
            r2 = dict(r)
            r2["onarilmis_xml"] = xml.get(r["makale_id"], "")
            w.writerow(r2)
    eksik = [r["makale_id"] for r in seg if r["makale_id"] not in xml]
    log.append("segmentation_gold.csv yenilendi: %d satir (XML eksik: %s)"
               % (len(seg), eksik or "yok"))

    # --- yaz ---
    with open(V2, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    open(os.path.join(SEC, "duzeltme_log.txt"), "w", encoding="utf-8").write("\n".join(log))
    print("\n".join(log))
    print("\n-> benchmark_300_v2.csv , segmentation_gold.csv , duzeltme_log.txt guncellendi")


if __name__ == "__main__":
    main()
