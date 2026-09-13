# -*- coding: utf-8 -*-
"""
ADIM 1/3 -- Dogrulanacak altin test kumesini secer.

Neden gerekli: olculen tavanlar (yazar %47.5, anahtar kelime %43.4) modelin
degil, REFERANS VERININ siniri. TR Dizin kaydi ayri elle girilmis bir indeks
kaydi; PDF'in kendi metadata'si degil. Bu yuzden "GROBID yazari %25 buluyor"
demek yaniltici olabilir.

Cozum: bir alt kumede metadata'yi PDF'e bakarak elle dogrulamak.

Ornekleme dergiye gore katmanli: 1500'luk kumede 663 farkli dergi var,
az dergiden cok makale yerine cok dergiden az makale seciyoruz ki
sablon cesitliligi korunsun.
"""
import os
import random
import sqlite3
import argparse
import collections

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = PROJE_KOK + r""
TEST = os.path.join(KOK, r"03_Test_ve_Degerlendirme\1500_random_test")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--tohum", type=int, default=42, help="tekrarlanabilirlik icin")
    ap.add_argument("--out", default=os.path.join(KOK, r"03_Test_ve_Degerlendirme/altin_test"))
    a = ap.parse_args()

    conn = sqlite3.connect(os.path.join(TEST, "test_metadatalar.db"))
    rows = list(conn.execute(
        "select id, gercek_dergi from orijinal_metadatalar "
        "where gercek_baslik is not null and gercek_baslik != ''"))

    # sadece GROBID ciktisi ve PDF'i olanlar (dogrulama icin ikisi de lazim)
    xml_d = os.path.join(TEST, "grobid_xml_birlesik")
    pdf_d = os.path.join(TEST, "makaleler")
    uygun = [(str(i), d or "(dergisiz)") for i, d in rows
             if os.path.exists(os.path.join(pdf_d, "makale_%s.pdf" % i))
             and os.path.exists(os.path.join(xml_d, "makale_%s.xml" % i))]
    print("uygun makale: %d" % len(uygun))

    # dergiye gore grupla, her dergiden sirayla bir tane al (katmanli ornekleme)
    gruplar = collections.defaultdict(list)
    for mid, dergi in uygun:
        gruplar[dergi.strip()].append(mid)
    rnd = random.Random(a.tohum)
    for g in gruplar.values():
        rnd.shuffle(g)

    dergiler = sorted(gruplar)
    rnd.shuffle(dergiler)
    secilen, tur = [], 0
    while len(secilen) < a.n:
        eklendi = False
        for d in dergiler:
            if tur < len(gruplar[d]):
                secilen.append(gruplar[d][tur])
                eklendi = True
                if len(secilen) >= a.n:
                    break
        if not eklendi:
            break
        tur += 1

    kapsanan = len({d for d in dergiler if any(m in secilen for m in gruplar[d])})
    print("secilen: %d makale, %d farkli dergi" % (len(secilen), kapsanan))
    print("dergi basina ortalama: %.2f" % (len(secilen) / max(kapsanan, 1)))

    os.makedirs(a.out, exist_ok=True)
    lst = os.path.join(a.out, "secilen_idler.txt")
    with open(lst, "w", encoding="utf-8") as f:
        f.write("\n".join(secilen) + "\n")

    # PDF'leri ayri klasore kopyala (createTraining'e girdi olacak)
    import shutil
    hedef = os.path.join(a.out, "pdf")
    os.makedirs(hedef, exist_ok=True)
    n = 0
    for mid in secilen:
        src = os.path.join(pdf_d, "makale_%s.pdf" % mid)
        dst = os.path.join(hedef, "makale_%s.pdf" % mid)
        if not os.path.exists(dst):
            shutil.copy2(src, dst)
        n += 1
    print("\nID listesi : %s" % lst)
    print("PDF klasoru: %s  (%d dosya)" % (hedef, n))
    print("\nSonraki adim: adim2_kapak_metni.sh")


if __name__ == "__main__":
    main()
