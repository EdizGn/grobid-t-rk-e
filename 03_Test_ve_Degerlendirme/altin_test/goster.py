# -*- coding: utf-8 -*-
import sys, re, adim3_sunucu as S
k = {x["id"]: x for x in S.veri_yukle()}
ids = [l.strip() for l in open("secilen_idler.txt", encoding="utf-8") if l.strip()]
a, b = int(sys.argv[1]), int(sys.argv[2])
sat = int(sys.argv[3]) if len(sys.argv) > 3 else 22
for n, mid in enumerate(ids[a:b], start=a + 1):
    v = k.get(mid)
    if not v:
        continue
    print("=" * 76)
    print("#%d  ID %s  |  %s" % (n, mid, (v["dergi"] or "")[:46]))
    print("  DB BASLIK   : %s" % (v["baslik"] or "(BOS)")[:150])
    print("  DB YAZARLAR : %s" % (v["yazarlar"] or "(BOS)")[:150])
    print("  DB KELIMELER: %s" % (v["kelimeler"] or "(BOS)")[:150])
    print("  DB OZET     : %s" % (v["ozet"] or "(BOS)")[:120].replace("\n", " "))
    print("  " + "-" * 72)
    satirlar = (v["kapak"] or "(cikarilamadi)").split("\n")
    for l in satirlar[:sat]:
        print("   | " + l[:104])
    # anahtar kelime satirlarini ayrica goster (kapakta asagida olabilir)
    ek = [l for i, l in enumerate(satirlar) if i >= sat
          and re.search(r'anahtar|keyword|key words', l, re.I)]
    for l in ek[:3]:
        print("   >>> " + l[:104])
    print()
