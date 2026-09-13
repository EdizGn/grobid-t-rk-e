# -*- coding: utf-8 -*-
"""
EGITILMIS MODELLERI GITHUB RELEASES'TEN INDIRIR.

Modeller depoda degil, cunku en buyugu 109 MiB ve GitHub 100 MiB ustu
dosyalari reddediyor. Ayrica 830 MB modeli depoda tutmak her `git clone`
islemine o yuku bindirirdi. Release ekleri dosya basina 2 GB'a izin verir
ve depo boyutuna sayilmaz.

    python 08_Modeller/model_indir.py              # hepsini indir
    python 08_Modeller/model_indir.py --kur        # indir + GROBID'e kur

Depo adresi `git remote get-url origin` ile bulunur; elle vermek icin
--depo kullanici/depo.

Indirilen her dosya PARMAK IZIYLE dogrulanir: Wapiti modelinin ilk
baytlarindaki `#mdl#2#<oznitelik>` sayisi beklenene esit degilse dosya
silinir. Bu projede bir kez yanlis model dosyasiyla bir gunluk olcum
cope gitti; kontrol o yuzden var.
"""
import io
import os
import re
import sys
import json
import argparse
import subprocess
import urllib.request

PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BURASI = os.path.dirname(os.path.abspath(__file__))

# (release'teki dosya adi, hedef alt klasor, beklenen oznitelik sayisi, aciklama)
MODELLER = [
    ("v4_80603_2153belge_orfoz.wapiti", "header", 80603,
     "Kurulu header modeli -- 2153 belgeyle egitildi"),
    ("tr_20803_0908.wapiti", "segmentation", 20803,
     "Turkce segmentasyon modeli"),
    ("stok_15545_imaj091.wapiti", "header", 15545,
     "GROBID 0.9.1 stok header modeli -- karsilastirma referansi"),
]


def depo_adresi(verilen=None):
    if verilen:
        return verilen.strip("/")
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=PROJE_KOK, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None
    m = re.search(r"github\.com[:/]+([^/]+/[^/.]+)", url)
    return m.group(1) if m else None


def parmak_izi(yol):
    """Wapiti model dosyasinin ilk baytlarindaki oznitelik sayisi."""
    try:
        with open(yol, "rb") as f:
            bas = f.read(64).decode("latin-1", "ignore")
    except OSError:
        return None
    m = re.search(r"#mdl#\d+#(\d+)", bas)
    return int(m.group(1)) if m else None


def release_varliklari(depo):
    url = "https://api.github.com/repos/%s/releases/latest" % depo
    istek = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "model_indir",
    })
    with urllib.request.urlopen(istek, timeout=30) as r:
        d = json.load(r)
    return {a["name"]: a["browser_download_url"] for a in d.get("assets", [])}


def indir(url, hedef):
    gecici = hedef + ".indiriliyor"
    istek = urllib.request.Request(url, headers={"User-Agent": "model_indir"})
    with urllib.request.urlopen(istek, timeout=120) as r, open(gecici, "wb") as f:
        toplam = int(r.headers.get("Content-Length") or 0)
        inen = 0
        while True:
            parca = r.read(1 << 20)
            if not parca:
                break
            f.write(parca)
            inen += len(parca)
            if toplam:
                sys.stdout.write("\r    %5.1f MB / %5.1f MB"
                                 % (inen / 1e6, toplam / 1e6))
                sys.stdout.flush()
    sys.stdout.write("\r" + " " * 40 + "\r")
    os.replace(gecici, hedef)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depo", help="kullanici/depo (varsayilan: git remote origin)")
    ap.add_argument("--kur", action="store_true",
                    help="indirdikten sonra model_kur.py ile GROBID'e kur")
    a = ap.parse_args()

    depo = depo_adresi(a.depo)
    if not depo:
        print("HATA: depo adresi bulunamadi. --depo kullanici/depo verin.")
        return 1
    print("depo: %s" % depo)

    try:
        varliklar = release_varliklari(depo)
    except Exception as e:
        print("HATA: release bilgisi alinamadi (%s)" % e)
        print("Modeller henuz yayinlanmamis olabilir.")
        return 1
    if not varliklar:
        print("HATA: son release'te dosya yok.")
        return 1

    inen = []
    for ad, klasor, beklenen, aciklama in MODELLER:
        hedef_d = os.path.join(BURASI, klasor)
        os.makedirs(hedef_d, exist_ok=True)
        hedef = os.path.join(hedef_d, ad)

        if parmak_izi(hedef) == beklenen:
            print("  atlandi  %-38s (zaten var, dogrulandi)" % ad)
            inen.append((hedef, klasor))
            continue
        if ad not in varliklar:
            print("  YOK      %-38s release'te bulunamadi" % ad)
            continue

        print("  indiriliyor %-35s %s" % (ad, aciklama))
        try:
            indir(varliklar[ad], hedef)
        except Exception as e:
            print("  HATA     %-38s %s" % (ad, e))
            continue

        bulunan = parmak_izi(hedef)
        if bulunan != beklenen:
            os.remove(hedef)
            print("  BOZUK    %-38s oznitelik %s, beklenen %d -- silindi"
                  % (ad, bulunan, beklenen))
            continue
        print("  ok       %-38s oznitelik %d dogrulandi" % (ad, beklenen))
        inen.append((hedef, klasor))

    if a.kur and inen:
        kur = os.path.join(PROJE_KOK, "01_Header_Modeli", "model_kur.py")
        for hedef, klasor in inen:
            if "stok" in os.path.basename(hedef):
                continue          # stok model referans, kurulmaz
            print("\nkuruluyor: %s" % os.path.basename(hedef))
            subprocess.call([sys.executable, kur, "--model", klasor,
                             "--kaynak", hedef])
    return 0


if __name__ == "__main__":
    sys.exit(main())
