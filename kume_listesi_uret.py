# -*- coding: utf-8 -*-
"""
KUME LISTELERINI URETIR -- deponun kendi kendine yetmesi icin sart.

Sorun: hangi makalenin test, hangisinin egitim kumesinde oldugu bilgisi
yalnizca .db dosyalarinin ve PDF klasorlerinin icinde duruyordu. Ikisi de
depoya giremiyor (telif + boyut). O hâlde depoyu klonlayan biri egitim/test
ayrimini bilemez, olcumleri tekrarlayamaz -- projenin uzerine kuruldugu
"egitim ve test ayri" garantisi dogrulanamaz hale gelir.

Bu betik her kumeyi duz bir id listesine dokuyor. Listeler kucuk (birkac bin
satir sayi) ve depoya girer. adim1_veri_topla.py bu listelerden PDF'leri ve
metadata'yi TR Dizin API'sinden yeniden indirebilir.

    python kume_listesi_uret.py
"""
import os
import re
import glob
import sqlite3

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "kume_listeleri")


def idler_klasorden(desen, uzanti=None):
    out = set()
    for p in glob.glob(desen):
        m = re.search(r"makale_(\d+)", os.path.basename(p))
        if m:
            out.add(m.group(1))
    return out


def idler_dbden(yol, tablo="orijinal_metadatalar", sutun="id"):
    if not os.path.exists(yol):
        return set()
    try:
        c = sqlite3.connect(yol)
        return set(str(r[0]) for r in c.execute(
            'select "%s" from "%s"' % (sutun, tablo)))
    except Exception:
        return set()


KUMELER = [
    # (dosya adi, aciklama, uretici)
    ("test_1500.txt",
     "OLCUM REFERANSI. Tum TR olcumleri bu kume uzerinde yapildi. "
     "Egitime ASLA girmedi.",
     lambda: idler_dbden(os.path.join(
         KOK, "03_Test_ve_Degerlendirme", "1500_random_test",
         "test_metadatalar.db"))),

    ("egitim_v4_2153.txt",
     "Kurulu header modelinin (v4_80603) egitildigi belgeler.",
     lambda: idler_klasorden(os.path.join(
         KOK, "04_Genisletilmis_Egitim", "corpus_v4", "tei", "*"))),

    ("havuz_3992.txt",
     "Genisletilmis egitim havuzu: indirilen tum makaleler. "
     "Test kumeleriyle kesismemesi adim1_veri_topla.py'de garanti altinda.",
     lambda: idler_klasorden(os.path.join(
         KOK, "04_Genisletilmis_Egitim", "makaleler", "*.pdf"))),

    ("altin_test_300.txt",
     "Elle dogrulama icin secilen havuz; 50'si dogrulandi.",
     lambda: set(open(os.path.join(
         KOK, "03_Test_ve_Degerlendirme", "altin_test",
         "secilen_idler.txt")).read().split())),

    ("ingilizce_519.txt",
     "Ingilizce kiyas kumesi (PMC Open Access).",
     lambda: idler_dbden(os.path.join(
         KOK, "03_Test_ve_Degerlendirme", "ingilizce_kiyas",
         "ingilizce_metadatalar.db"))),

    ("karantina_1051.txt",
     "v5 etiketleyicisinin eledigi, kurulu modelin egitiminde GORULMEYEN "
     "belgeler. TR_v4_karantina1051 olcumunun kumesi.",
     lambda: idler_klasorden(os.path.join(
         KOK, "03_Test_ve_Degerlendirme", "karantina_benchmark",
         "grobid_xml", "*.xml"))),
]


def main():
    os.makedirs(CIKTI, exist_ok=True)
    ozet = []
    for ad, aciklama, uret in KUMELER:
        try:
            idler = uret()
        except Exception as e:
            print("  ATLANDI %-24s (%s)" % (ad, e))
            continue
        if not idler:
            print("  BOS     %-24s -- kaynak yok, atlandi" % ad)
            continue
        yol = os.path.join(CIKTI, ad)
        with open(yol, "w", newline="\n") as f:
            f.write("# %s\n" % aciklama)
            f.write("# %d makale\n" % len(idler))
            # Ingilizce kume PMC kimligi kullaniyor (PMC10021181), sayisal degil
            for i in sorted(idler, key=lambda x: (0, int(x)) if x.isdigit()
                            else (1, x)):
                f.write("%s\n" % i)
        print("  yazildi %-24s %5d makale" % (ad, len(idler)))
        ozet.append((ad, len(idler), aciklama, idler))

    # kesisim kontrolu -- projenin en onemli garantisi
    print("\n--- KESISIM KONTROLU (test kumeleri egitime sizmis mi) ---")
    d = {a: s for a, _, _, s in ozet}
    test = d.get("test_1500.txt", set())
    for ad in ("egitim_v4_2153.txt", "havuz_3992.txt"):
        if ad in d and test:
            k = len(test & d[ad])
            print("  test_1500 ile %-22s kesisim: %d %s"
                  % (ad, k, "(TEMIZ)" if k == 0 else "*** SIZINTI ***"))
    if "egitim_v4_2153.txt" in d and "karantina_1051.txt" in d:
        k = len(d["egitim_v4_2153.txt"] & d["karantina_1051.txt"])
        print("  egitim_v4 ile karantina_1051     kesisim: %d %s"
              % (k, "(TEMIZ)" if k == 0 else "*** SIZINTI ***"))


if __name__ == "__main__":
    main()
