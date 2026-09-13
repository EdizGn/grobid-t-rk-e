# -*- coding: utf-8 -*-
"""Tum model/mod kombinasyonlarini tek tabloda toplar."""
import re, os

O = "olcumler"
MODLAR = ["Strict Matching", "Soft Matching", "Levenshtein Matching", "Ratcliff/Obershelp"]
ALANLAR = ["title", "authors", "first_author", "abstract", "keywords"]

# GROBID'in yayinladigi Ingilizce sonuclar (doc/benchmarks/Benchmarking-pmc.md)
# PMC 1943 makale / 1943 farkli dergi
INGILIZCE = {
    ("Strict Matching", "title"): 84.25, ("Strict Matching", "authors"): 92.86,
    ("Strict Matching", "first_author"): 96.68, ("Strict Matching", "abstract"): 16.20,
    ("Strict Matching", "keywords"): 62.12,
    ("Soft Matching", "title"): 91.88, ("Soft Matching", "authors"): 94.82,
    ("Soft Matching", "first_author"): 97.14, ("Soft Matching", "abstract"): 62.43,
    ("Soft Matching", "keywords"): 69.93,
    ("Levenshtein Matching", "title"): 98.07, ("Levenshtein Matching", "authors"): 96.68,
    ("Levenshtein Matching", "first_author"): 97.35, ("Levenshtein Matching", "abstract"): 89.08,
    ("Levenshtein Matching", "keywords"): 83.27,
    ("Ratcliff/Obershelp", "title"): 96.06, ("Ratcliff/Obershelp", "authors"): 95.75,
    ("Ratcliff/Obershelp", "first_author"): 96.68, ("Ratcliff/Obershelp", "abstract"): 85.01,
    ("Ratcliff/Obershelp", "keywords"): 76.93,
}


def oku(dosya):
    p = os.path.join(O, dosya)
    if not os.path.exists(p):
        return {}
    d, mod = {}, None
    for l in open(p, encoding="utf-8"):
        if l.startswith("####"):
            for m in MODLAR:
                if l.replace("####", "").strip().startswith(m.split("/")[0]):
                    mod = m
        m = re.match(r'\|\s*(\w+)\s*\|\s*[\d.]+\s*\|\s*[\d.]+\s*\|\s*([\d.]+)\s*\|', l)
        if m and mod:
            d[(mod, m.group(1))] = float(m.group(2))
    return d


K = [("Stok GROBID (CRF)  ", "stokcrf"),
     ("Stok GROBID (DeLFT)", "delft"),
     ("Egitilmis  494 belge", "w494"),
     ("Egitilmis 2999 belge", "w2999")]

for mod in MODLAR:
    print("\n" + "=" * 92)
    print("### %s" % mod)
    print("=" * 92)
    print("%-22s %-14s %-14s %-14s | %s" %
          ("MODEL", "diakritik ON", "diakritik OFF", "kazanc", "Ingilizce (PMC)"))
    print("-" * 92)
    for alan in ALANLAR:
        print("  [%s]" % alan)
        for ad, kod in K:
            a = oku(kod + "_diak.txt").get((mod, alan))
            b = oku(kod + "_nodiak.txt").get((mod, alan))
            if a is None:
                continue
            ing = INGILIZCE.get((mod, alan))
            print("   %-20s %13.2f %14.2f %13s | %s" %
                  (ad, a, b if b is not None else 0,
                   ("%+.2f" % (b - a)) if b is not None else "-",
                   ("%.2f" % ing) if ing else "-"))
        print()
