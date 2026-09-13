# -*- coding: utf-8 -*-
"""
50 makalelik ELLE dogrulamanin serbest metin gerekcelerini metrik basina
kategorilere ayirir. Dashboard'daki "hata nedenleri" bolumunun kaynagi budur
-- tahmin degil, tek tek PDF kapagina bakilarak yazilmis notlar.

Siniflandirma anahtar kelimeye dayanir; kural listesi asagida aciktir ki
sayilar yeniden uretilebilsin.
"""
import os
import re
import sqlite3
import collections

# (metrik, etiket, gerekce metninde aranan desen)
KURAL = [
    ("yazarlar", "Sira farki (ayni kisiler, farkli sira)", r"SIRA"),
    ("yazarlar", "DB'de isim yanlis/eksik (gercek icerik hatasi)",
     r"YANLIS SOYAD|EKSIK SOYAD|soyadsiz|fazladan soyad|EKSIK ve sira|DB'de YOK"),
    ("yazarlar", "Yazar kapak metninde hic gecmiyor", r"HIC gecmiyor"),
    ("yazarlar", "Sadece diakritik farki", r"yazar sadece diakritik|diakritik farki"),
    ("yazarlar", "Sadece buyuk/kucuk harf farki", r"yazar sadece buyuk"),
    ("yazarlar", "Yazar kisi degil (kurul/kurum)", r"kisi degil"),

    ("kelimeler", "DB bos, makalede VAR (referans eksik)", r"kelime: DB bos, makalede (var|hem)"),
    ("kelimeler", "Indeksleyici kendi terimlerini yazmis",
     r"indeksleyici|TAMAMEN FARKLI|FARKLI terimler|FAZLADAN terim"),
    ("kelimeler", "Sira farki", r"kelime: ayni.*(sira|SIRA)"),
    ("kelimeler", "Makale anahtar kelime basmiyor", r"anahtar kelime basmiyor|makalede de yok"),
    ("kelimeler", "Sadece buyuk/kucuk harf veya ayrac farki", r"kelime sadece buyuk|ayrac farkli"),

    ("baslik", "DB kaydinda bicim hatasi (bosluk eksik/fazla)", r"BOSLUK EKSIK|BOSLUK"),
    ("baslik", "DB Turkce, kapakta sadece Ingilizce", r"baslik: DB'de Turkce"),

    ("ozet", "Zorlu PDF / bozuk font", r"ZORLU PDF|BOZUK FONT"),
]


def main():
    c = sqlite3.connect(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "altin_test_metadatalar.db"))
    kayit = list(c.execute(
        "select id, gerekce, baslik_durum, yazarlar_durum, ozet_durum, kelimeler_durum "
        "from altin"))

    print("=== 50 MAKALELIK ELLE DOGRULAMA ===")
    print()
    # "yok" arayuzde "Makalede yok" demek: alan PDF'te yok. DB eksigi DEGIL,
    # o yuzden "duzeltildi" ile toplanmamali -- sucu farkli tarafta.
    print("--- 50 makalede alan basina karar ---")
    for ad, idx in (("baslik", 2), ("yazarlar", 3), ("ozet", 4), ("kelimeler", 5)):
        d = collections.Counter((r[idx] or "bos").strip() or "bos" for r in kayit)
        top = sum(d.values())
        print("  %-10s dogru %2d | DB duzeltildi %2d | makalede yok %2d   "
              "(DB hatasi %.0f%%)"
              % (ad, d.get("dogru", 0), d.get("duzeltildi", 0), d.get("yok", 0),
                 100.0 * d.get("duzeltildi", 0) / top))

    print()
    print("--- gerekce yazilmis %d makalede hata nedenleri ---"
          % sum(1 for r in kayit if (r[1] or "").strip()))
    say = collections.defaultdict(collections.Counter)
    for _, g, _, _, _, _ in kayit:
        g = g or ""
        for metrik, etiket, desen in KURAL:
            if re.search(desen, g, re.I):
                say[metrik][etiket] += 1

    for metrik in ("baslik", "yazarlar", "ozet", "kelimeler"):
        print()
        print("  [%s]" % metrik.upper())
        for k, v in say[metrik].most_common():
            print("     %-52s %2d" % (k, v))

    print()
    print("--- ozet ortusme dagilimi (gerekcede olculmus) ---")
    kova = collections.Counter()
    for _, g, _, _, _, _ in kayit:
        m = re.search(r"ozet ortusme ([01]\.\d+)", g or "")
        if m:
            v = float(m.group(1))
            kova["1.00 (tam)" if v >= 0.995 else
                 "0.80-0.99" if v >= 0.80 else
                 "0.30-0.79" if v >= 0.30 else "0.00-0.29 (basarisiz)"] += 1
    for k in ("1.00 (tam)", "0.80-0.99", "0.30-0.79", "0.00-0.29 (basarisiz)"):
        if kova.get(k):
            print("     %-24s %2d" % (k, kova[k]))


if __name__ == "__main__":
    main()
