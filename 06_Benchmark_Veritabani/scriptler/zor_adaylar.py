#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kolay_ham_hepsi.csv (787 teshisli) -> 300'e girmemis TAZE ZOR adaylari
   Stok GROBID'in takildigi Turkce/karisik belgeler, ayni PRIMARY taksonomisine gore siniflandirilir.
   Cikti: zor_adaylar.csv"""
import os, csv, collections

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

B = PROJE_KOK + r"\06_Benchmark_Veritabani"
SRC = os.path.join(B, "kolay_ham_hepsi.csv")
USED = os.path.join(B, "secim", "benchmark_300_v2.csv")
KOLAY = os.path.join(B, "kolay_adaylar.csv")
DST = os.path.join(B, "zor_adaylar.csv")


def f(r, k, d=None):
    v = r.get(k, "")
    try:
        return float(v) if v not in ("", "None", None) else d
    except Exception:
        return d


rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
used = {r["makale_id"] for r in csv.DictReader(open(USED, encoding="utf-8-sig"))}
kolay_aday = {r["makale_id"] for r in csv.DictReader(open(KOLAY, encoding="utf-8-sig"))}

out = []
for r in rows:
    mid = r["makale_id"]
    if mid in used or mid in kolay_aday:      # 300'de olan ya da kolay adayi olanlari alma
        continue
    if r["dil"] == "en":                      # Turkce agirligi koru
        continue
    # --- TARANMIS / METINSIZ: GROBID'in cokmesi zaten olayin kendisi, grobid_ok sarti yok ---
    _pg = int(r["pages"]) if r["pages"].isdigit() else 0
    if (f(r, "chars_per_page", 0.0) < 200 or f(r, "harf_orani", 100.0) < 20) and 3 <= _pg <= 60:
        d = dict(r)
        d["PRIMARY"] = "taranmis" if f(r, "harf_orani", 100.0) < 8 else "bozuk-font"
        d["TIER"] = "zor"; d["FLAGS"] = d["PRIMARY"]; d["kaynak"] = "taze_zor"
        out.append(d)
        continue
    if r.get("grobid_ok") != "1":              # metin var ama GROBID calismamis -> guvenilmez
        continue
    ts = f(r, "title_sim", 0.0)
    as_ = f(r, "abstract_sim")
    ar = f(r, "author_recall")
    harf = f(r, "harf_orani", 100.0)
    cpp = f(r, "chars_per_page", 0.0)
    body = f(r, "stock_body_len", 0.0)
    repl = f(r, "replacement", 0.0)
    pages = int(r["pages"]) if r["pages"].isdigit() else 0
    if pages < 3 or pages > 40:
        continue

    if cpp < 120 or harf < 8:
        p, tier = "taranmis", "zor"
    elif harf < 45:
        p, tier = "bozuk-font", "zor"
    elif repl > 4:
        p, tier = "karakter-anomali", "zor"
    elif ts < 0.30:
        p, tier = "header-title-yok", "zor"
    elif ts < 0.72:
        p, tier = "baslik-yanlis", "orta"
    elif body < 500:
        p, tier = "govde-yok", "zor"
    elif as_ is None or as_ < 0.45:
        p, tier = "ozet-eksik", "orta"
    elif ar is not None and ar < 0.5:
        p, tier = "yazar-eksik", "orta"
    else:
        continue
    d = dict(r)
    d["PRIMARY"] = p
    d["TIER"] = tier
    d["FLAGS"] = p
    d["kaynak"] = "taze_zor"
    out.append(d)

cols = list(rows[0].keys()) + ["PRIMARY", "TIER", "FLAGS", "kaynak"]
with open(DST, "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader(); w.writerows(out)

print(f"{len(out)} taze zor aday -> {DST}")
print("PRIMARY:", dict(collections.Counter(r["PRIMARY"] for r in out).most_common()))
print("TIER   :", dict(collections.Counter(r["TIER"] for r in out)))
print("dil    :", dict(collections.Counter(r["dil"] for r in out)))
print("farkli dergi:", len(set(r["gold_journal"] for r in out)))
