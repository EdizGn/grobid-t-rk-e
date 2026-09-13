# -*- coding: utf-8 -*-
"""
DeLFT ve Wapiti header modellerinin ciktilarini alan bazinda birlestirir ve
standart GROBID TEI formatinda yeni XML'ler uretir.

Neden: iki model farkli alanlarda iyi.
  Wapiti (egitilmis) : ozet +33, kelime +11, yil +6, yazar precision +36
  DeLFT  (stok)      : yazar recall +67

Birlestirme kurali SABITTIR (oracle degil) -- her alan icin hangi modelin
daha iyi oldugu 1435 dosyada olculmus, kural ona gore yazilmistir.

Cikti mevcut karsilastirma_yeni.py ve dashboard ile dogrudan uyumludur.
"""
import os
import re
import glob
import argparse
from lxml import etree

NS = {'t': 'http://www.tei-c.org/ns/1.0'}
TEI = "http://www.tei-c.org/ns/1.0"


def nrm(s):
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    s = s.translate(str.maketrans("çğıöşü", "cgiosu"))
    return set(w for w in re.sub(r'[^\w\s]', ' ', s).split() if len(w) > 2)


# Turkce baslik ekleri: yazar alanina dusmus baslik parcalarini yakalar
SUF = ("nin", "nın", "nun", "nün", "leri", "ları", "lerin", "ların", "masi",
       "mesi", "sinin", "ının", "incelenmesi", "degerlendirilmesi", "etkisi",
       "etkileri", "analizi", "uzerine", "acisindan", "iliskisi", "ornegi",
       "karsilastirilmasi", "belirlenmesi", "arastirilmasi", "uygulamasi")
STOP = {"ve", "ile", "bir", "icin", "uzerine", "ozet", "abstract", "giris",
        "anahtar", "kelimeler", "key", "words", "the", "of", "and",
        "universitesi", "dergisi", "fakultesi", "bolumu"}


def baslik_parcasi(ad):
    """Bu 'yazar' aslinda basligin devami mi?"""
    n = nrm(ad)
    if not n:
        return True
    if n & STOP:
        return True
    if any(t.endswith(SUF) for t in n):
        return True
    return len(ad.split()) >= 4


def oku(path):
    try:
        r = etree.parse(path).getroot()
    except Exception:
        return None
    h = r.xpath(".//t:teiHeader", namespaces=NS)
    if not h:
        return None
    h = h[0]

    def g(xp):
        e = h.xpath(xp, namespaces=NS)
        return " ".join("".join(e[0].itertext()).split()) if e else ""

    return {
        "root": r,
        "title": g(".//t:titleStmt/t:title"),
        "abs_el": (h.xpath(".//t:profileDesc/t:abstract", namespaces=NS) or [None])[0],
        "abs": g(".//t:profileDesc/t:abstract"),
        "kw_els": h.xpath(".//t:profileDesc//t:keywords", namespaces=NS),
        "kw": [" ".join("".join(t.itertext()).split())
               for t in h.xpath(".//t:term", namespaces=NS)],
        "au_els": h.xpath(".//t:sourceDesc//t:analytic/t:author", namespaces=NS),
        "au": [" ".join(" ".join("".join(c.itertext()).split()) for c in a)
               for a in h.xpath(".//t:sourceDesc//t:author/t:persName", namespaces=NS)],
        "date": g(".//t:monogr//t:date") or g(".//t:publicationStmt/t:date"),
        "doi": g(".//t:idno[@type='DOI']"),
    }


def q(tag):
    return "{%s}%s" % (TEI, tag)


def birlestir(D, W):
    """Wapiti ciktisini temel al, DeLFT'ten eksikleri tamamla.
    Donen: degistirilmis W['root'] agaci."""
    r = W["root"]
    h = r.xpath(".//t:teiHeader", namespaces=NS)[0]

    # --- YAZAR: Wapiti varsa kalsin (precision 89); yoksa DeLFT'ten al ---
    bas_ek = []
    if not W["au"] and D["au"]:
        temiz = [a for a in D["au_els"]
                 if not baslik_parcasi(" ".join(" ".join("".join(c.itertext()).split())
                                                for c in (a.xpath("./t:persName", namespaces=NS) or [a])))]
        bas_ek = [" ".join("".join(p.itertext()).split())
                  for a in D["au_els"]
                  for p in a.xpath("./t:persName", namespaces=NS)
                  if baslik_parcasi(" ".join("".join(p.itertext()).split()))]
        an = h.xpath(".//t:sourceDesc//t:analytic", namespaces=NS)
        if an and temiz:
            for a in temiz:
                an[0].append(etree.fromstring(etree.tostring(a)))

    # --- BASLIK: iki modelin bilgi olarak zengin olani + kurtarilan parcalar ---
    t_el = h.xpath(".//t:titleStmt/t:title", namespaces=NS)
    en_iyi = max([D["title"], W["title"]], key=lambda t: len(nrm(t)))
    if bas_ek:
        en_iyi = (en_iyi + " " + " ".join(bas_ek)).strip()
    if t_el and en_iyi and en_iyi != W["title"]:
        t_el[0].text = en_iyi
        for c in list(t_el[0]):
            t_el[0].remove(c)

    # --- OZET: Wapiti bos ise DeLFT'ten al ---
    if not W["abs"] and D["abs_el"] is not None:
        pd = h.xpath(".//t:profileDesc", namespaces=NS)
        if pd:
            eski = h.xpath(".//t:profileDesc/t:abstract", namespaces=NS)
            for e in eski:
                e.getparent().remove(e)
            pd[0].append(etree.fromstring(etree.tostring(D["abs_el"])))

    # --- ANAHTAR KELIME: Wapiti bos ise DeLFT'ten al ---
    if not W["kw"] and D["kw_els"]:
        pd = h.xpath(".//t:profileDesc", namespaces=NS)
        if pd:
            pd[0].append(etree.fromstring(etree.tostring(D["kw_els"][0])))

    # --- DOI: Wapiti bos ise DeLFT'ten al ---
    if not W["doi"] and D["doi"]:
        sd = h.xpath(".//t:sourceDesc//t:analytic", namespaces=NS)
        if sd:
            idno = etree.SubElement(sd[0], q("idno"))
            idno.set("type", "DOI")
            idno.text = D["doi"]
    return r


def main():
    ap = argparse.ArgumentParser()
    b = r"C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\1500_random_test"
    ap.add_argument("--delft", default=os.path.join(b, "grobid_xml_delft_header"))
    ap.add_argument("--wapiti", default=os.path.join(b, "grobid_xml_yeni_model"))
    ap.add_argument("--out", default=os.path.join(b, "grobid_xml_birlesik"))
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    n = sadece_w = sadece_d = 0
    for f in sorted(glob.glob(os.path.join(a.wapiti, "*.xml"))):
        ad = os.path.basename(f)
        W = oku(f)
        if W is None:
            continue
        dp = os.path.join(a.delft, ad)
        D = oku(dp) if os.path.exists(dp) else None
        if D is None:
            sadece_w += 1
            r = W["root"]
        else:
            r = birlestir(D, W)
        r.getroottree().write(os.path.join(a.out, ad), encoding="utf-8",
                              xml_declaration=True)
        n += 1

    # Wapiti'de hic olmayan ama DeLFT'te olan dosyalar
    for f in sorted(glob.glob(os.path.join(a.delft, "*.xml"))):
        ad = os.path.basename(f)
        if not os.path.exists(os.path.join(a.wapiti, ad)):
            D = oku(f)
            if D:
                D["root"].getroottree().write(os.path.join(a.out, ad),
                                              encoding="utf-8", xml_declaration=True)
                sadece_d += 1
                n += 1

    print("uretilen: %d" % n)
    print("  sadece Wapiti'de olan: %d" % sadece_w)
    print("  sadece DeLFT'te olan : %d" % sadece_d)
    print("\ncikti: %s" % a.out)
    print("\nSonraki adim:")
    print("  python ..\\karsilastirma_yeni.py --grobid_klasoru \"%s\" \\" % a.out)
    print("      --cikti_klasoru \"%s\" --db_adi test_metadatalar.db" % b)


if __name__ == "__main__":
    main()
