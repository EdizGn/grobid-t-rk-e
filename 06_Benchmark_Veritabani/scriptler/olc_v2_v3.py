#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 ve v3 secimlerini AYNI metrikle (skor.py) stok GROBID'e karsi olcer.
   Amac: v3 gercekten zorlastı mi? TEI'ler cache'den okunur, GROBID'e gidilmez."""
import os, csv, collections, sys
import skor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(HERE)
TEI_HAVUZ = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\tei_stock")
GOLD_HAVUZ = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\gold2")
TEI_TAZE = os.path.join(HERE, "kolay_tei")
GOLD_TAZE = os.path.join(HERE, "kolay_gold")
SEC = os.path.join(HERE, "secim")


def tei_of(mid):
    for p in (os.path.join(TEI_HAVUZ, f"{mid}.header.xml"),
              os.path.join(TEI_TAZE, f"{mid}.header.xml")):
        if os.path.exists(p) and os.path.getsize(p) > 40:
            return open(p, encoding="utf-8").read()
    return ""


def gold_of(mid):
    for p in (os.path.join(GOLD_HAVUZ, f"{mid}.json"), os.path.join(GOLD_TAZE, f"{mid}.json")):
        if os.path.exists(p):
            return skor.gold_yukle(p)
    return None


def olc(csv_path, etiket):
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    res = []
    eksik = 0
    for r in rows:
        mid = r["makale_id"]
        g = gold_of(mid)
        if g is None:
            eksik += 1
            continue
        x = tei_of(mid)
        title, abst, names = skor.tei_parse(x)
        b = skor.baslik_skor(title, g["titles"])
        y = skor.yazar_skor(names, g["authors"])
        res.append({"tier": r.get("TIER", "?"), "dil": r.get("dil", "?"),
                    "primary": r.get("PRIMARY", "?"), "uretti": bool(x),
                    "b_ok": b["ok"], "b_sim": b["sim"],
                    "y_ok": bool(y and y.get("recall") is not None
                                 and y["recall"] >= skor.AUTHOR_ESIK),
                    "y_rec": (y or {}).get("recall") or 0.0})
    n = len(res)
    bok = sum(1 for r in res if r["b_ok"])
    yok_ = sum(1 for r in res if r["y_ok"])
    hic = sum(1 for r in res if not r["uretti"])
    print(f"\n===== {etiket}  (n={n}, gold eksik={eksik}) =====")
    print(f"  stok BASLIK cozulen : {bok}/{n}  ({100*bok/n:.0f}%)")
    print(f"  stok YAZAR cozulen  : {yok_}/{n}  ({100*yok_/n:.0f}%)")
    print(f"  GROBID hic cikti vermedi: {hic}")
    print("  TIER bazinda baslik:")
    for t in ("kolay", "orta", "zor"):
        sub = [r for r in res if r["tier"] == t]
        if sub:
            k = sum(1 for r in sub if r["b_ok"])
            print(f"    {t:6} {k:3}/{len(sub):3}  ({100*k/len(sub):.0f}%)")
    print("  dil bazinda baslik:")
    for d in ("tr", "mix", "en"):
        sub = [r for r in res if r["dil"] == d]
        if sub:
            k = sum(1 for r in sub if r["b_ok"])
            print(f"    {d:4} {k:3}/{len(sub):3}  ({100*k/len(sub):.0f}%)")
    return {"n": n, "b": bok, "y": yok_}


if __name__ == "__main__":
    a = olc(os.path.join(SEC, "benchmark_300_v2.csv"), "v2 (mevcut 300)")
    b = olc(os.path.join(SEC, "benchmark_300_v3.csv"), "v3 (zorlastirilmis 300)")
    print("\n===== KARSILASTIRMA =====")
    print(f"  stok basligi cozme: v2 %{100*a['b']/a['n']:.0f}  ->  v3 %{100*b['b']/b['n']:.0f}"
          f"   ({100*b['b']/b['n'] - 100*a['b']/a['n']:+.0f} puan)")
    print(f"  stok yazari cozme : v2 %{100*a['y']/a['n']:.0f}  ->  v3 %{100*b['y']/b['n']:.0f}"
          f"   ({100*b['y']/b['n'] - 100*a['y']/a['n']:+.0f} puan)")
    print("  (dusus = benchmark zorlasti)")
