#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""benchmark_300.csv -> her belgeye sikinti_skoru (0-100) + siddet (hafif/orta/agir)
   Kaynak metrikler: teshis_refined.csv (havuz) + kolay_ham_hepsi.csv (kolay)"""
import os, csv, collections

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = PROJE_KOK + r""
B300 = os.path.join(BASE, r"06_Benchmark_Veritabani\secim\benchmark_300.csv")
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
KOLAY = os.path.join(BASE, r"06_Benchmark_Veritabani\kolay_ham_hepsi.csv")


def fnum(d, k, dv=0.0):
    v = d.get(k, "")
    try:
        return float(v) if v not in ("", "None", None) else dv
    except Exception:
        return dv


T = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
K = {r["makale_id"]: r for r in csv.DictReader(open(KOLAY, encoding="utf-8-sig"))}
rows = list(csv.DictReader(open(B300, encoding="utf-8-sig")))


def score(r):
    mid = r["makale_id"]
    src = T.get(mid) or K.get(mid) or {}
    kolay = r["kaynak"] == "kolay"
    cpp = fnum(src, "chars_per_page")
    harf = fnum(src, "harf_orani", 100)
    repl = fnum(src, "replacement")
    anom = fnum(src, "anomali_promil")
    body = fnum(src, "stock_body_len")
    tsim = src.get("title_sim", r.get("title_sim", ""))
    asim = src.get("abstract_sim", r.get("abstract_sim", ""))
    arec = src.get("author_recall", r.get("author_recall", ""))
    crash = (src.get("stock_hdr", "200") != "200") if not kolay else (src.get("grobid_ok", "1") != "1")
    flags = [x for x in (r.get("FLAGS") or "").split(";") if x and x != "temiz"]

    scanned = cpp and cpp < 120 or harf < 8
    s = 0.0
    if scanned:
        s += 45
    elif harf < 45:
        s += 32
    elif harf < 60:
        s += 10
    if crash and not scanned:
        s += 28
    if not scanned and not crash:
        if str(tsim) not in ("", "None"):
            s += (1 - float(tsim)) * 22
        if str(asim) in ("", "None"):
            s += 10
        elif float(asim) < 0.45:
            s += (1 - float(asim)) * 12
        if str(arec) not in ("", "None"):
            s += (1 - float(arec)) * 10
        if body and body < 500:
            s += 14
        s += min(anom, 15)
        s += min(repl * 1.5, 10)
    s += max(0, len(set(flags)) - 1) * 4
    s = min(100, round(s))
    sd = "hafif" if s < 20 else ("orta" if s <= 50 else "agir")
    return s, sd


for r in rows:
    r["sikinti_skoru"], r["siddet"] = score(r)

cols = list(rows[0].keys())
with open(B300, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print("siddet dagilimi (300):", dict(collections.Counter(r["siddet"] for r in rows)))
print("  kolay(100):", dict(collections.Counter(r["siddet"] for r in rows if r["kaynak"] == "kolay")))
print("  havuz(200):", dict(collections.Counter(r["siddet"] for r in rows if r["kaynak"] == "havuz")))
print()
print("PRIMARY -> ort skor / aralik:")
byp = collections.defaultdict(list)
for r in rows:
    byp[r["PRIMARY"]].append(r["sikinti_skoru"])
for p, sc in sorted(byp.items(), key=lambda x: -sum(x[1]) / len(x[1])):
    print(f"  {p:18} n={len(sc):3}  ort={sum(sc)/len(sc):5.1f}  min={min(sc):3}  max={max(sc):3}")
print("\n->", B300)
