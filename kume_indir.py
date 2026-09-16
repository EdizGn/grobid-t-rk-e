# -*- coding: utf-8 -*-
"""
BELIRLI BIR KUMEYI INDIRIR -- kume_listeleri/ altindaki kimlik listesinden.

NEDEN AYRI BIR BETIK: adim1_veri_topla.py rastgele kimlik deniyor
(`random.randint`), cunku isi yeni egitim verisi toplamak. Belirli bir kumeyi
--- ornegin tum olcumlerin referansi olan 1500'luk test kumesini --- geri
getiremez. Bu yuzden depoyu klonlayan biri kume_listeleri/test_1500.txt'yi
gorse bile olcumleri tekrarlayamiyordu. Bu betik o kopuklugu kapatir.

INDIRME MANTIGI YENIDEN YAZILMADI: adim1_veri_topla.dene() dogrudan
kullaniliyor. Bir kere yazilmis ve 3992 makalede calismis kodu kopyalamak
yerine cagirmak, iki surumun zamanla birbirinden ayrilmasini da onler.
(TR Dizin alan yapisi tahmin edilecek gibi degil: baslik/ozet abstracts[]
icinde dile gore, PDF ise iki adimli -- once 'pdf' anahtari, sonra link.)

    python kume_indir.py --listele
    python kume_indir.py test_1500
    python kume_indir.py test_1500 --out bir/baska/klasor

Yarida kesilirse tekrar calistirilabilir: zaten inmis olanlari atlar.
"""
import io
import os
import sys
import time
import sqlite3
import argparse
import threading
import concurrent.futures

PROJE_KOK = os.path.dirname(os.path.abspath(__file__))
LISTE_D = os.path.join(PROJE_KOK, "kume_listeleri")
sys.path.insert(0, os.path.join(PROJE_KOK, "04_Genisletilmis_Egitim"))

from adim1_veri_topla import init_db, dil_sec, API, DOSYA, HEADERS  # noqa: E402

import requests                                     # noqa: E402


def cek(pub_id, pdf_dir):
    """(durum, satir). durum: ok | eksik | yok | hata

    NEDEN adim1.dene() KULLANILMIYOR: o fonksiyon TURKCE OZET sart kosuyor
    (`if not (baslik and ozet and yazarlar): return "eksik"`). Egitim korpusu
    toplarken dogru -- otomatik etiketleme Turkce ozeti metinde ariyor. Ama
    burada kume uyeligi ZATEN belli; ayni filtreyi uygulamak kumeden makale
    dusurur. Ornek: test kumesindeki 901 numarali makalenin yalnizca
    Ingilizce ozeti var, dene() onu "eksik" diye atiyor -- oysa tum TR
    olcumleri o makaleyi de kapsiyordu.

    Buradaki politika: metadata'nin ne kadari varsa alinir, PDF inerse 'ok'.
    """
    try:
        r = requests.get(API.format(pub_id), headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return "hata", None
        hits = r.json().get("hits", {}).get("hits", [])
        if not hits:
            return "yok", None
        k = hits[0].get("_source", {}) or {}

        absl = k.get("abstracts", []) or []
        tr, en = dil_sec(absl, "TUR"), dil_sec(absl, "ENG")
        al = lambda d, a: (d.get(a) or "") if isinstance(d, dict) else ""

        baslik = al(tr, "title") or k.get("orderTitle", "") or al(en, "title")
        yazarlar = ", ".join(y.get("name", "") for y in (k.get("authors") or [])
                             if isinstance(y, dict) and y.get("name"))

        pdf_key = k.get("pdf")
        if not pdf_key:
            return "eksik", None
        # Iki adimli: once dosya anahtari -> link, sonra linkten PDF
        lr = requests.get(DOSYA.format(pdf_key), headers=HEADERS, timeout=20)
        if lr.status_code != 200:
            return "hata", None
        link = lr.text.strip().strip('"').strip("'")
        if not link.startswith("http"):
            return "hata", None
        pr = requests.get(link, headers=HEADERS, stream=True, timeout=60)
        if pr.status_code != 200:
            return "hata", None
        yol = os.path.join(pdf_dir, "makale_%s.pdf" % pub_id)
        boyut = 0
        with open(yol, "wb") as f:
            for ch in pr.iter_content(chunk_size=8192):
                f.write(ch)
                boyut += len(ch)
        if boyut < 10000:                      # bozuk / bos PDF
            os.remove(yol)
            return "hata", None

        j = k.get("journal", {})
        return "ok", (
            str(pub_id), "makale_%s.pdf" % pub_id, baslik, al(tr, "abstract"),
            yazarlar, ", ".join(al(tr, "keywords") or []),
            str(k.get("publicationYear", "") or ""),
            j.get("name", "") if isinstance(j, dict) else "",
            k.get("doi", "") or "",
            al(en, "title"), al(en, "abstract"), ", ".join(al(en, "keywords") or []),
            "Tam")
    except Exception:
        return "hata", None

# Kume adi -> varsayilan hedef klasor (betiklerin aradigi yerler)
VARSAYILAN_HEDEF = {
    "test_1500":      os.path.join("03_Test_ve_Degerlendirme", "1500_random_test"),
    "altin_test_300": os.path.join("03_Test_ve_Degerlendirme", "altin_test"),
    "havuz_3992":     "04_Genisletilmis_Egitim",
    "egitim_v4_2153": "04_Genisletilmis_Egitim",
    "karantina_1051": "04_Genisletilmis_Egitim",
}
VARSAYILAN_DB = {
    "test_1500":      "test_metadatalar.db",
    "altin_test_300": "altin_test_metadatalar.db",
    "havuz_3992":     "egitim_metadatalar.db",
    "egitim_v4_2153": "egitim_metadatalar.db",
    "karantina_1051": "egitim_metadatalar.db",
}


def kumeyi_oku(ad):
    yol = os.path.join(LISTE_D, ad if ad.endswith(".txt") else ad + ".txt")
    if not os.path.exists(yol):
        return None, None
    idler, baslik = [], ""
    for satir in io.open(yol, encoding="utf-8"):
        s = satir.strip()
        if not s:
            continue
        if s.startswith("#"):
            if not baslik:
                baslik = s.lstrip("# ").strip()
            continue
        idler.append(s)
    return idler, baslik


def listele():
    print("Kullanilabilir kumeler (%s):\n" % LISTE_D)
    if not os.path.isdir(LISTE_D):
        print("  kume_listeleri/ yok -- once: python kume_listesi_uret.py")
        return 1
    for f in sorted(os.listdir(LISTE_D)):
        if f.endswith(".txt"):
            idler, baslik = kumeyi_oku(f)
            print("  %-22s %5d makale   %s" % (f[:-4], len(idler), baslik))
    print("\n  python kume_indir.py <kume-adi>")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kume", nargs="?", help="kume adi, orn. test_1500")
    ap.add_argument("--listele", action="store_true")
    ap.add_argument("--out", help="hedef klasor (varsayilan: kumeye gore)")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    if a.listele or not a.kume:
        return listele()

    idler, baslik = kumeyi_oku(a.kume)
    if idler is None:
        print("HATA: '%s' kumesi yok. --listele ile bakin." % a.kume)
        return 1

    kok_ad = a.kume.replace(".txt", "")
    hedef = a.out or VARSAYILAN_HEDEF.get(kok_ad, kok_ad)
    hedef = hedef if os.path.isabs(hedef) else os.path.join(PROJE_KOK, hedef)
    pdf_dir = os.path.join(hedef, "makaleler")
    os.makedirs(pdf_dir, exist_ok=True)
    db_yolu = os.path.join(hedef, VARSAYILAN_DB.get(kok_ad, "metadatalar.db"))
    conn = init_db(db_yolu)

    print("kume  : %s (%d makale)" % (kok_ad, len(idler)))
    print("        %s" % baslik)
    print("hedef : %s" % hedef)
    print("db    : %s\n" % db_yolu)

    var = {r[0] for r in conn.execute("select id from orijinal_metadatalar")}
    kalan = [i for i in idler
             if i not in var
             or not os.path.exists(os.path.join(pdf_dir, "makale_%s.pdf" % i))]
    print("zaten tam : %d\nindirilecek: %d\n" % (len(idler) - len(kalan), len(kalan)))
    if not kalan:
        print("Kume tam.")
        return 0

    kilit = threading.Lock()
    sayac = {"ok": 0, "eksik": 0, "yok": 0, "hata": 0}
    tampon = []
    t0 = time.time()

    def yaz(zorla=False):
        if len(tampon) >= 25 or (zorla and tampon):
            conn.executemany(
                "INSERT OR REPLACE INTO orijinal_metadatalar VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?)", tampon)
            conn.commit()
            del tampon[:]

    def calis(mid):
        durum, satir = cek(mid, pdf_dir)
        with kilit:
            sayac[durum] = sayac.get(durum, 0) + 1
            if satir:
                tampon.append(satir)
                yaz()
            n = sum(sayac.values())
            if n % 25 == 0:
                print("  %d/%d  %s  (%.0f sn)"
                      % (n, len(kalan), sayac, time.time() - t0), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(calis, kalan))
    with kilit:
        yaz(zorla=True)

    print("\nbitti: %s" % sayac)
    toplam = conn.execute("select count(*) from orijinal_metadatalar").fetchone()[0]
    print("db'deki kayit: %d / %d" % (toplam, len(idler)))
    if sayac.get("yok") or sayac.get("eksik"):
        print("\nNot: TR Dizin kayitlari zamanla degisiyor -- makale erisime "
              "kapanmis veya metadata'si eksilmis olabilir. Liste ile birebir "
              "ayni sayiyi tutturamamak normaldir; olculen belge sayisi "
              "(support) o yuzden raporlarda ayrica yaziliyor.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
