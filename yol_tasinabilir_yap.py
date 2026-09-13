# -*- coding: utf-8 -*-
"""
SABIT KODLANMIS YOLLARI TASINABILIR HALE GETIRIR.

Sorun: 93 betikten 51'inde "C:\\Users\\EG\\Desktop\\Tubitak___is" yolu gomulu.
Depoyu klonlayan baska biri bu betiklerin hicbirini calistiramaz -- ne klasor
adi ne surucu harfi ayni olur. Deponun kendi kendine yetmesi icin sart.

Yontem: anlam koruyan, mekanik bir degisim. String'in ICERIGINE dokunmadan,
yalnizca basindaki kok kismini bir degiskene cikariyoruz:

    r"C:\\Users\\EG\\Desktop\\Tubitak___is\\grobid\\x"
        ->  PROJE_KOK + r"\\grobid\\x"

PROJE_KOK dosyanin KENDI konumundan hesaplanir, yani depo nereye klonlanirsa
klonlansin dogru yeri gosterir.

    python yol_tasinabilir_yap.py --dene     # neyin degisecegini goster
    python yol_tasinabilir_yap.py --uygula
"""
import io
import os
import re
import ast
import sys
import argparse
import subprocess

TERS = chr(92)                      # ters bolu; kaynakta literal yazmiyoruz
KOK_BICIMLERI = [
    "C:" + TERS + "Users" + TERS + "EG" + TERS + "Desktop" + TERS + "Tubitak___is",
    "C:/Users/EG/Desktop/Tubitak___is",
]
SABIT = "PROJE_KOK"


def kok_ifadesi(rel_yol):
    """Dosyanin depo icindeki derinligine gore kok hesaplayan ifade."""
    derinlik = rel_yol.replace(TERS, "/").count("/")
    ic = "os.path.abspath(__file__)"
    for _ in range(derinlik + 1):
        ic = "os.path.dirname(%s)" % ic
    return ic


def ekleme_noktasi(metin):
    """Son top-level import'un BITTIGI satir (0-tabanli indeks).

    Regex kullanmiyoruz: "from x import (a,\n b)" gibi cok satirli import'larda
    regex parantezin ortasina isaret ediyor ve dosyayi bozuyordu. ast gercek
    bitis satirini verir.
    """
    try:
        agac = ast.parse(metin)
    except SyntaxError:
        return 0
    son = 0
    for d in agac.body:
        if isinstance(d, (ast.Import, ast.ImportFrom)):
            son = max(son, getattr(d, "end_lineno", d.lineno))
    if son:
        return son
    # import yok: docstring varsa ondan sonra
    if agac.body and isinstance(agac.body[0], ast.Expr) and \
            isinstance(getattr(agac.body[0], "value", None), ast.Constant) and \
            isinstance(agac.body[0].value.value, str):
        return getattr(agac.body[0], "end_lineno", 1)
    return 0


def donustur(yol):
    rel = yol.replace(TERS, "/")
    ham = open(yol, "rb").read()
    # utf-8-sig: bazi dosyalarda BOM var, duz utf-8 ile okununca U+FEFF
    # kaynak koda karisip ast'i bozuyor. Eski arsiv betiklerinden birkaci
    # cp1254 kodlu; onlari da kurtariyoruz.
    metin = None
    for kod in ("utf-8-sig", "cp1254"):
        try:
            metin = ham.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    if metin is None:
        return None, "okunamadi (bilinen kodlama degil)"

    if not any(k in metin for k in KOK_BICIMLERI):
        return None, "sabit yol yok"

    yeni = metin
    sayac = 0
    for kok in KOK_BICIMLERI:
        # r"KOK... / "KOK... / 'KOK...  ->  PROJE_KOK + r"...
        desen = re.compile(r'''(\br)?(["'])''' + re.escape(kok))
        yeni, n = desen.subn(
            lambda m: '%s + %s%s' % (SABIT, m.group(1) or "", m.group(2)), yeni)
        sayac += n

    if sayac == 0:
        return None, "string disinda geciyor -- ELLE bakilmali"

    if not re.search(r'^import os\b', yeni, re.M):
        s = yeni.splitlines(True)
        s.insert(ekleme_noktasi(yeni), "import os\n")
        yeni = "".join(s)
    s = yeni.splitlines(True)
    s.insert(ekleme_noktasi(yeni),
             "\n# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.\n"
             "%s = %s\n" % (SABIT, kok_ifadesi(rel)))
    yeni = "".join(s)

    try:
        ast.parse(yeni)
    except SyntaxError as e:
        return None, "DONUSUM SONRASI SOZDIZIMI BOZUK: %s" % e
    return yeni, "%d yer degisti" % sayac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uygula", action="store_true")
    a = ap.parse_args()

    dosyalar = [d for d in subprocess.check_output(
        ["git", "ls-files"], text=True).split() if d.endswith(".py")]

    degisen = atlanan = hatali = 0
    for d in dosyalar:
        yeni, not_ = donustur(d)
        if yeni is None:
            if not_ == "sabit yol yok":
                continue
            print("  !! %-58s %s" % (d, not_))
            hatali += 1
            continue
        print("  ok %-58s %s" % (d, not_))
        degisen += 1
        if a.uygula:
            io.open(d, "w", encoding="utf-8", newline="\n").write(yeni)

    print()
    print("degisen: %d   elle bakilacak: %d" % (degisen, hatali))
    if not a.uygula:
        print("(deneme modu -- yazmak icin --uygula)")


if __name__ == "__main__":
    sys.exit(main())
