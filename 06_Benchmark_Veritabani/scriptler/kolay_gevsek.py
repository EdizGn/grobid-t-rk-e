#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kolay_ham_hepsi.csv -> gevsetilmis 'taninan format = kolay' suzgeci -> kolay_adaylar.csv
   Kriter: GROBID gercekten calisti + Turkce/karisik + taranmamis + 5-28 sayfa
           + govde var + baslik makul (title_sim>=0.4).  Siki ozet/yazar esikleri YOK."""
import os, csv

OUT = os.path.join(r"C:\Users\EG\Desktop\Tubitak___is", "06_Benchmark_Veritabani")
SRC = os.path.join(OUT, "kolay_ham_hepsi.csv")
DST = os.path.join(OUT, "kolay_adaylar.csv")


def fnum(r, k, d=0.0):
    v = r.get(k, "")
    try:
        return float(v) if v not in ("", "None") else d
    except Exception:
        return d


rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
out = []
red = {}
for r in rows:
    why = None
    if r.get("grobid_ok") != "1":
        why = "grobid-calismadi"
    elif r["dil"] == "en":
        why = "ingilizce"
    elif fnum(r, "chars_per_page") < 400 or fnum(r, "harf_orani") < 55:
        why = "taranmis"
    elif not (r["pages"].isdigit() and 5 <= int(r["pages"]) <= 28):
        why = "sayfa-araligi"
    elif fnum(r, "replacement") > 4:
        why = "karakter-bozuk"
    elif fnum(r, "stock_body_len") < 1500:
        why = "govde-kisa"
    elif fnum(r, "title_sim") < 0.4:
        why = "baslik-cok-yanlis"
    if why:
        red[why] = red.get(why, 0) + 1
        continue
    out.append(r)

cols = list(rows[0].keys())
with open(DST, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(out)
print(f"{len(rows)} ham -> {len(out)} kolay aday")
print("eleme:", red)
import collections
print("dil:", dict(collections.Counter(r["dil"] for r in out)))
print("farkli dergi:", len(set(r["gold_journal"] for r in out)))
print("->", DST)
