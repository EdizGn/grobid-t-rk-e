#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_300'u tek gold + tek metrikle yeniden skorlar.

Duzelttikleri:
  1) stok skorlari tek-baslikli `gold`, truba skorlari cok-baslikli `gold2`
     ile hesaplanmisti -> ikisi de artik ayni birlesik gold ile olculur.
  2) cift dilli baslik bloklarini bitisik donduren DOGRU cikarimlar
     "cozemedi" sayiliyordu -> skor.baslik_skor kapsama kolu ile kurtarilir.
  3) yazar icin yalnizca gevsek recall vardi -> precision/F1 + siki eslesme.
  4) taranmis / bozuk-font etiketleri olcumle yeniden dogrulanir
     (metin_katmani kolonu).

Cikti: secim/benchmark_300_v2.csv , secim/ozet_v2.txt , secim/gold300/
Girdiyi (benchmark_300.csv) DEGISTIRMEZ.
"""
import os, re, csv, json, sys, glob, collections, warnings, logging
import statistics as st
warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.CRITICAL)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skor

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
OUT = os.path.join(BASE, "06_Benchmark_Veritabani")
SEC = os.path.join(OUT, "secim")
TESHIS_D = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis")
GOLD_HAVUZ = os.path.join(TESHIS_D, "gold2")      # cok baslikli surum
GOLD_KOLAY = os.path.join(OUT, "kolay_gold")
TEI_STOK_HAVUZ = os.path.join(TESHIS_D, "tei_stock")
TEI_STOK_KOLAY = os.path.join(OUT, "kolay_tei")
TEI_TRUBA = os.path.join(OUT, "truba_tei")
GOLD300 = os.path.join(SEC, "gold300")

_HARF = re.compile(r"[a-zA-Z\u00e7\u011f\u0131\u00f6\u015f\u00fc\u00c7\u011e\u0130\u00d6\u015e\u00dc]")
# ToUnicode'u eksik fontlarda cikan glif adlari: /g28 , /MT65 , /uni0130 ...
_GLIF = re.compile(r"/[A-Za-z]{1,4}\d+")


def metin_tani(path, sayfa=3):
    """PDF metin katmani teshisi -> (sinif, harf_orani, glif_orani, n_char)

    metinsiz      : secilebilir metin yok, OCR sart (GROBID bos doner)
    bozuk_kodlama : metin var ama glif kodu/anlamsiz -> icerik cop
    kismen_bozuk  : govdenin bir kismi glif kodu (genelde sekil/tablo fontlari)
    saglam        : metin katmani kullanilabilir
    """
    try:
        from pypdf import PdfReader
        rd = PdfReader(path)
        t = ""
        for pg in rd.pages[:sayfa]:
            try:
                t += pg.extract_text() or ""
            except Exception:
                pass
    except Exception:
        return "acilmadi", 0.0, 0.0, 0
    n = len(t.strip())
    if n < 100:
        return "metinsiz", 0.0, 0.0, n
    harf = len(_HARF.findall(t)) / max(1, len(t))
    glif = sum(len(x) for x in _GLIF.findall(t)) / max(1, len(t))
    if glif >= 0.30 or harf < 0.45:
        sinif = "bozuk_kodlama"
    elif glif >= 0.03:
        sinif = "kismen_bozuk"
    else:
        sinif = "saglam"
    return sinif, round(harf, 3), round(glif, 3), n


def etiket_onerisi(primary, metin_katmani):
    """Olculen metin katmani ile PRIMARY etiketinin celistigi yerleri isaretler."""
    if metin_katmani == "metinsiz":
        return "" if primary in ("grobid-crash", "taranmis") else "gercekten metinsiz -> taranmis/OCR sinifi"
    if metin_katmani == "bozuk_kodlama":
        if primary == "taranmis":
            return "taranmis DEGIL: metin katmani var ama kodlamasi bozuk -> bozuk-font"
        if primary in ("temiz-tr-taze",):
            return "temiz DEGIL: kodlamasi bozuk -> bozuk-font (kolay katmandan cikarilmali)"
        if primary != "bozuk-font":
            return "kodlama bozuk -> FLAGS'e bozuk-font eklenmeli"
    if metin_katmani == "kismen_bozuk" and primary == "temiz-tr-taze":
        return "kismi glif bozulmasi (govdede); baslik etkilenmiyorsa kolay kalabilir"
    return ""


def oku(p):
    return open(p, encoding="utf-8", errors="ignore").read() if os.path.exists(p) else ""


def main():
    rows = list(csv.DictReader(open(os.path.join(SEC, "benchmark_300.csv"), encoding="utf-8-sig")))
    os.makedirs(GOLD300, exist_ok=True)
    pdf = {os.path.basename(p).replace("makale_", "")[:-4]: p
           for p in glob.glob(os.path.join(SEC, "pdf300", "*", "*", "*.pdf"))}

    for i, r in enumerate(rows, 1):
        mid = r["makale_id"]
        kolay = r["kaynak"] == "kolay"
        gp = os.path.join(GOLD_KOLAY if kolay else GOLD_HAVUZ, mid + ".json")
        g = skor.gold_yukle(gp)
        json.dump(g, open(os.path.join(GOLD300, mid + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        stok_x = oku(os.path.join(TEI_STOK_KOLAY if kolay else TEI_STOK_HAVUZ, mid + ".header.xml"))
        trb_x = oku(os.path.join(TEI_TRUBA, mid + ".xml"))

        for etiket, x in (("stok", stok_x), ("truba", trb_x)):
            t, a, nm = skor.tei_parse(x)
            b = skor.baslik_skor(t, g["titles"])
            y = skor.yazar_skor(nm, g["authors"])
            o = skor.ozet_skor(a, g["abstracts"])
            r[etiket + "_uretti"] = int(bool(x.strip()))
            r[etiket + "_t_sim"] = b["sim"]
            r[etiket + "_t_kapsama"] = b["kapsama"]
            r[etiket + "_t_fazlalik"] = "" if b["fazlalik"] is None else b["fazlalik"]
            r[etiket + "_t_ok"] = int(b["ok"])
            r[etiket + "_t_birlesik"] = int(b["birlesik"])
            r[etiket + "_y_recall"] = "" if y["recall"] is None else y["recall"]
            r[etiket + "_y_f1"] = "" if y["f1"] is None else y["f1"]
            r[etiket + "_y_siki_f1"] = "" if y["siki_f1"] is None else y["siki_f1"]
            r[etiket + "_y_ok"] = "" if y["recall"] is None else int(y["recall"] >= skor.AUTHOR_ESIK)
            r[etiket + "_o_sim"] = "" if o is None else o
            r[etiket + "_baslik"] = t[:150]

        sinif, harf, glif, nch = metin_tani(pdf[mid])
        r["metin_katmani"] = sinif
        r["harf_orani"] = harf
        r["glif_orani"] = glif
        r["etiket_onerisi"] = etiket_onerisi(r["PRIMARY"], sinif)
        r["gold_n_baslik"] = len(g["titles"])
        r["gold_n_yazar"] = len(g["authors"])
        r["gold_ozet_var"] = int(bool(g["abstracts"]))
        if i % 50 == 0:
            print("  %d/%d" % (i, len(rows)))

    def cmp3(s, t):
        return ("iki_de_cozdu" if s and t else "truba_duzeltti" if (not s and t)
                else "truba_bozdu" if (s and not t) else "iki_de_cozemedi")

    for r in rows:
        r["v2_baslik_kars"] = cmp3(r["stok_t_ok"] == 1, r["truba_t_ok"] == 1)
        r["v2_yazar_kars"] = cmp3(str(r["stok_y_ok"]) == "1", str(r["truba_y_ok"]) == "1")

    cols = list(rows[0].keys())
    with open(os.path.join(SEC, "benchmark_300_v2.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # ---- ozet ----
    def f(v, d=0.0):
        try:
            return float(v)
        except Exception:
            return d

    L = ["BENCHMARK 300 - v2 skorlama (tek gold: gold2/kolay_gold, tek metrik: skor.py)",
         "baslik ok = sim>=0.70 VEYA (kapsama>=0.90 ve fazlalik<=1.30) ; yazar ok = gevsek recall>=0.50", ""]
    L.append("### BASLIK - cozulen belge sayisi (300 uzerinden) ###")
    L.append("  %-7s %4s | %-12s %-12s | %-12s %-12s" % ("TIER", "n", "stok v1", "stok v2", "truba v1", "truba v2"))
    for t in ("kolay", "orta", "zor", "TOPLAM"):
        g = rows if t == "TOPLAM" else [r for r in rows if r["TIER"] == t]
        s1 = sum(1 for r in g if f(r["stok_title_sim"]) >= 0.70)
        s2 = sum(1 for r in g if r["stok_t_ok"] == 1)
        t1 = sum(1 for r in g if f(r["truba_title_sim"]) >= 0.70)
        t2 = sum(1 for r in g if r["truba_t_ok"] == 1)
        L.append("  %-7s %4d | %-12s %-12s | %-12s %-12s" % (
            t, len(g), "%d (%.0f%%)" % (s1, 100 * s1 / len(g)), "%d (%.0f%%)" % (s2, 100 * s2 / len(g)),
            "%d (%.0f%%)" % (t1, 100 * t1 / len(g)), "%d (%.0f%%)" % (t2, 100 * t2 / len(g))))
    L.append("")
    L.append("  cift dilli birlesik baslik (v1'de haksiz yere cozemedi sayilan): stok %d , truba %d"
             % (sum(1 for r in rows if r["stok_t_birlesik"] == 1),
                sum(1 for r in rows if r["truba_t_birlesik"] == 1)))
    L.append("")
    L.append("### YAZAR ###")
    for e in ("stok", "truba"):
        rr = [f(r[e + "_y_recall"]) for r in rows if r[e + "_y_recall"] != ""]
        ff = [f(r[e + "_y_f1"]) for r in rows if r[e + "_y_f1"] != ""]
        sf = [f(r[e + "_y_siki_f1"]) for r in rows if r[e + "_y_siki_f1"] != ""]
        ok = sum(1 for r in rows if str(r[e + "_y_ok"]) == "1")
        L.append("  %-6s recall=%.3f  F1=%.3f  siki_F1=%.3f  cozulen=%d/%d  hic yazar dondurmedi=%d"
                 % (e, st.mean(rr), st.mean(ff), st.mean(sf), ok, len(rows),
                    sum(1 for r in rows if r[e + "_y_recall"] != "" and f(r[e + "_y_recall"]) == 0)))
    L.append("")
    L.append("### STOK vs TRUBA (v2 metrik) ###")
    for ad, k in (("BASLIK", "v2_baslik_kars"), ("YAZAR", "v2_yazar_kars")):
        c = collections.Counter(r[k] for r in rows)
        L.append("  %-7s %s" % (ad, {x: c[x] for x in ("iki_de_cozdu", "truba_duzeltti", "truba_bozdu", "iki_de_cozemedi")}))
    L.append("")
    L.append("### METIN KATMANI (olculen) vs PRIMARY etiketi ###")
    m = collections.Counter(r["metin_katmani"] for r in rows)
    L.append("  " + str(dict(m)))
    carpraz = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["metin_katmani"] != "saglam":
            carpraz[r["metin_katmani"]][r["PRIMARY"]] += 1
    for k, v in carpraz.items():
        L.append("    %-14s %s" % (k, dict(v)))
    oner = [r for r in rows if r["etiket_onerisi"]]
    L.append("")
    L.append("### ETIKET DUZELTME ONERISI (%d belge) ###" % len(oner))
    for r in oner:
        L.append("  %-9s %-16s %-14s %s" % (r["makale_id"], r["PRIMARY"], r["metin_katmani"], r["etiket_onerisi"]))
    txt = "\n".join(L)
    open(os.path.join(SEC, "ozet_v2.txt"), "w", encoding="utf-8").write(txt)
    print("\n" + txt)
    print("\n-> secim/benchmark_300_v2.csv , secim/ozet_v2.txt , secim/gold300/ (%d dosya)" % len(rows))


if __name__ == "__main__":
    main()
