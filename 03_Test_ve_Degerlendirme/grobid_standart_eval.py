# -*- coding: utf-8 -*-
"""
GROBID'in KENDI degerlendirme protokolu ile olcum.

Neden: projedeki `karsilastirma_yeni.py` ortalama token ortusmesi hesapliyor.
Bu kismi puan veren, GROBID'in yayinladigi benchmark sayilariyla KIYASLANAMAZ
bir olcu. Burada GROBID'in dort eslesme modu birebir uygulanir; boylece
Turkce sonuc, doc/benchmarks/Benchmarking-pmc.md icindeki Ingilizce sonuclarla
dogrudan karsilastirilabilir olur.

Modlar (GROBID EvaluationUtilities ile ayni):
  strict      : birebir string esitligi
  soft        : noktalama / buyuk-kucuk harf / bosluk farklari yok sayilir
  levenshtein : Levenshtein benzerligi >= 0.80
  ratcliff    : Ratcliff/Obershelp benzerligi >= 0.95

Alan bazli ikili karar verilir (esledi / eslemedi), sonra P / R / F1.
"""
import os
import re
import glob
import difflib
import sqlite3
import argparse
import unicodedata
from lxml import etree

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NS = {'t': 'http://www.tei-c.org/ns/1.0'}


# ---------------------------------------------------------------- normalize
# Turkce diakritik katlamasi.
# GEREKCE: TR Dizin kayitlarinda diakritikler sistematik olarak soyulmus
# ("Sule Pekuz" <-> "Şule PEKUZ", "Omer Yilmaz" <-> "Ömer Yılmaz").
# Elle dogrulanan 20 makalede yazar uyusmazliklarinin 7/10'u SADECE bundan
# kaynaklaniyordu -- yani icerik ayni, yazim farkli.
# GROBID'in kendi "soft matching" modu da ayni gerekceyle buyuk-kucuk harfi
# ve noktalamayi yok sayiyor; diakritigi yok saymak o mantigin devami.
# PDF'e BAKMADIGIMIZ icin dongusellik yaratmaz: bu bir olcum tanimi,
# veri duzeltmesi degil.
DIAKRITIK = str.maketrans("çğıöşüâîû", "cgiosuaiu")

YOKSAY_DIAKRITIK = False


def soft_norm(s):
    """GROBID 'soft matching': noktalama, buyuk-kucuk harf ve bosluk yok sayilir."""
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("I", "ı").replace("İ", "i").lower()
    if YOKSAY_DIAKRITIK:
        s = s.translate(DIAKRITIK)
    s = re.sub(r'[^\w]', '', s, flags=re.UNICODE)
    return s


def strict_norm(s):
    return " ".join(str(s or "").split())


def levenshtein_ratio(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    onceki = list(range(lb + 1))
    for i in range(1, la + 1):
        simdi = [i] + [0] * lb
        for j in range(1, lb + 1):
            simdi[j] = min(onceki[j] + 1, simdi[j - 1] + 1,
                           onceki[j - 1] + (a[i - 1] != b[j - 1]))
        onceki = simdi
    return 1.0 - onceki[lb] / max(la, lb)


def ratcliff(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


MODLAR = ("strict", "soft", "levenshtein", "ratcliff")


def esles(mod, tahmin, dogru):
    if mod == "strict":
        return strict_norm(tahmin) == strict_norm(dogru)
    a, b = soft_norm(tahmin), soft_norm(dogru)
    if mod == "soft":
        return a == b
    if mod == "levenshtein":
        return levenshtein_ratio(a, b) >= 0.80
    return ratcliff(a, b) >= 0.95


# ---------------------------------------------------------------- cikarim
def oku(path):
    try:
        r = etree.parse(path).getroot()
    except Exception:
        return None
    h = r.xpath(".//t:teiHeader", namespaces=NS)
    if not h:
        return None
    h = h[0]

    def g(xp):
        e = h.xpath(xp, namespaces=NS)
        return " ".join("".join(e[0].itertext()).split()) if e else ""

    ts = h.xpath(".//t:titleStmt", namespaces=NS)
    title = ""
    if ts:
        el = ts[0].xpath("./t:title[@type='main']", namespaces=NS) or ts[0].xpath("./t:title", namespaces=NS)
        if el:
            title = " ".join("".join(el[0].itertext()).split())

    UNVAN = {"prof", "dr", "doç", "doc", "uzman", "uzm", "araş", "aras",
             "gör", "gor", "yrd", "öğr", "ogr"}
    isimler = []
    for a in h.xpath(".//t:sourceDesc//t:author/t:persName", namespaces=NS):
        ad = " ".join(" ".join("".join(c.itertext()).split()) for c in a).strip()
        parca = {p.strip(".,;:").lower() for p in ad.split() if p.strip(".,;:")}
        if ad and not (parca and parca <= UNVAN):
            isimler.append(ad)

    return {
        "title": title,
        "abstract": g(".//t:profileDesc/t:abstract"),
        "authors": "; ".join(isimler),
        "first_author": isimler[0] if isimler else "",
        "keywords": "; ".join(" ".join("".join(t.itertext()).split())
                              for t in h.xpath(".//t:term", namespaces=NS)),
    }


def yazar_normalize(s):
    """Yazar / anahtar kelime listelerini SIRASIZ karsilastirilabilir hale getirir.
    (GROBID ile DB'de siralamalar farkli olabiliyor; sira farki hata sayilmamali.)"""
    p = [soft_norm(x) for x in re.split(r'[;,]', str(s or "")) if soft_norm(x)]
    return " ".join(sorted(p))


ALANLAR = ["title", "authors", "first_author", "abstract", "keywords"]


def main():
    ap = argparse.ArgumentParser()
    b = PROJE_KOK + r"\03_Test_ve_Degerlendirme\1500_random_test"
    ap.add_argument("--xml", default=os.path.join(b, "grobid_xml_birlesik"))
    ap.add_argument("--db", default=os.path.join(b, "test_metadatalar.db"))
    ap.add_argument("--dil", choices=["tr", "iki"], default="iki",
                    help="tr = sadece Turkce referans (kati); iki = TR veya EN kabul")
    ap.add_argument("--diakritik-yoksay", action="store_true",
                    help="Turkce diakritikleri katla (TR Dizin kayitlarinda "
                         "sistematik olarak soyulmus durumda)")
    a = ap.parse_args()
    global YOKSAY_DIAKRITIK
    YOKSAY_DIAKRITIK = a.diakritik_yoksay

    gold = {}
    for r in sqlite3.connect(a.db).execute(
            "select id,gercek_baslik,gercek_ozet,gercek_yazarlar,gercek_anahtar_kelimeler,"
            "gercek_baslik_en,gercek_ozet_en,gercek_anahtar_kelimeler_en from orijinal_metadatalar"):
        gold[str(r[0])] = {
            "title": [r[1]] + ([r[5]] if a.dil == "iki" and r[5] else []),
            "abstract": [r[2]] + ([r[6]] if a.dil == "iki" and r[6] else []),
            "authors": [r[3]], "first_author": [r[3]],
            "keywords": [r[4]] + ([r[7]] if a.dil == "iki" and r[7] else []),
        }

    say = {m: {f: {"tp": 0, "pred": 0, "sup": 0} for f in ALANLAR} for m in MODLAR}
    n = 0
    for f in sorted(glob.glob(os.path.join(a.xml, "*.xml"))):
        mid = os.path.basename(f)[7:-4]
        g = gold.get(mid)
        p = oku(f)
        if not g or not p:
            continue
        n += 1
        for alan in ALANLAR:
            dogrular = [d for d in g[alan] if str(d or "").strip()]
            if alan == "first_author":
                dogrular = [str(d).split(",")[0].strip() for d in dogrular]
            if not dogrular:
                continue
            tahmin = p[alan]
            for m in MODLAR:
                say[m][alan]["sup"] += 1
                if str(tahmin).strip():
                    say[m][alan]["pred"] += 1
                if alan in ("authors", "keywords"):
                    ok = any(esles(m, yazar_normalize(tahmin), yazar_normalize(d)) for d in dogrular)
                else:
                    ok = any(esles(m, tahmin, d) for d in dogrular)
                if ok and str(tahmin).strip():
                    say[m][alan]["tp"] += 1

    baslik = {"strict": "Strict Matching (exact matches)",
              "soft": "Soft Matching (punctuation/case/space ignored)",
              "levenshtein": "Levenshtein Matching (>= 0.8)",
              "ratcliff": "Ratcliff/Obershelp Matching (>= 0.95)"}
    print("Degerlendirilen: %d dosya   |   referans dili: %s\n"
          % (n, "TR+EN" if a.dil == "iki" else "sadece TR"))
    for m in MODLAR:
        print("#### %s" % baslik[m])
        print("| %-14s | %9s | %9s | %9s | %7s |" % ("label", "precision", "recall", "f1", "support"))
        print("|" + "-" * 16 + "|" + ("-" * 11 + "|") * 3 + "-" * 9 + "|")
        for alan in ALANLAR:
            d = say[m][alan]
            pr = d["tp"] / d["pred"] * 100 if d["pred"] else 0.0
            rc = d["tp"] / d["sup"] * 100 if d["sup"] else 0.0
            f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
            print("| %-14s | %9.2f | %9.2f | %9.2f | %7d |" % (alan, pr, rc, f1, d["sup"]))
        print()


if __name__ == "__main__":
    main()
