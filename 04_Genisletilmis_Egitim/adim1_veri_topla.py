# -*- coding: utf-8 -*-
"""
ADIM 1/4 -- Genisletilmis header egitim korpusu icin veri toplama.

TR Dizin'den rastgele makale secer, metadata + PDF indirir.

ONEMLI: 1500'luk test kumesindeki ve mevcut korpuslardaki ID'ler DISLANIR.
Egitim/test sizintisi olmamasi icin bu sart.

Sadece TAM metadata'si olan makaleler alinir (baslik + ozet + yazar), cunku
otomatik etiketleme bu degerleri metinde arayarak span buluyor.

Yarim kalirsa tekrar calistirilabilir.
"""
import os
import re
import glob
import random
import sqlite3
import argparse
import requests
import threading
import concurrent.futures

API = "https://search.trdizin.gov.tr/api/publicationById/{}?archiveSearch=ADD_ARCHIVE"
DOSYA = "https://search.trdizin.gov.tr/api/getFile/{}?showViewer=false"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
}
KOK = r"C:\Users\EG\Desktop\Tubitak___is"


def init_db(path):
    # check_same_thread=False: yazmalar zaten tek bir kilit altinda yapiliyor
    c = sqlite3.connect(path, check_same_thread=False)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orijinal_metadatalar (
            id TEXT PRIMARY KEY, dosya_adi TEXT,
            gercek_baslik TEXT, gercek_ozet TEXT, gercek_yazarlar TEXT,
            gercek_anahtar_kelimeler TEXT, gercek_yil TEXT, gercek_dergi TEXT,
            gercek_doi TEXT, gercek_baslik_en TEXT, gercek_ozet_en TEXT,
            gercek_anahtar_kelimeler_en TEXT, durum TEXT)
    """)
    c.commit()
    return c


def yasakli_idler():
    """Toplamada DOKUNULMAYACAK kimlikler.

    Egitim korpusu ile herhangi bir test/degerlendirme kumesinin kesismesi
    sonuclari gecersiz kilar. Bu yuzden butun kumeler ACIKCA dislaniyor;
    hicbiri "zaten cakismaz" varsayimina birakilmiyor.

    Kapsam:
      1. 1500'luk Turkce test kumesi (test_metadatalar.db + PDF klasoru)
      2. Altin test kumesi (300 makale) -- 1'in alt kumesi, yine de acik
      3. Zorluk katmanli benchmark (300 makale)
      4. Eski 546'lik header kumesi
      5. Halihazirda toplanmis egitim havuzu (2989)
      6. Butun korpus klasorleri ve YEDEKLERI
      7. Diskteki butun makale PDF'leri
    """
    yasak = set()
    eksik = []

    def dbden(yol, etiket):
        try:
            for r in sqlite3.connect(yol).execute(
                    "select id from orijinal_metadatalar"):
                yasak.add(str(r[0]))
        except Exception as e:
            eksik.append("%s (%s)" % (etiket, e))

    def dosyadan(desen, etiket):
        bulundu = 0
        for f in glob.glob(desen, recursive=True):
            m = re.search(r'makale_(\d+)', os.path.basename(f))
            if m:
                yasak.add(m.group(1))
                bulundu += 1
        if not bulundu:
            eksik.append("%s (dosya bulunamadi: %s)" % (etiket, desen))

    J = os.path.join
    dbden(J(KOK, "03_Test_ve_Degerlendirme", "1500_random_test",
            "test_metadatalar.db"), "1500'luk test kumesi")
    # altin test DB'sinde tablo adi "altin" (digerlerinde orijinal_metadatalar)
    try:
        for r in sqlite3.connect(J(KOK, "03_Test_ve_Degerlendirme", "altin_test",
                                   "altin_test_metadatalar.db")
                                 ).execute("select id from altin"):
            yasak.add(str(r[0]))
    except Exception as e:
        eksik.append("altin test kumesi (%s)" % e)
    dosyadan(J(KOK, "03_Test_ve_Degerlendirme", "altin_test", "**", "*.pdf"),
             "altin test PDF'leri")
    dbden(J(KOK, "01_Header_Modeli", "header_metadatalar.db"),
          "eski 546'lik header kumesi")
    dbden(J(KOK, "04_Genisletilmis_Egitim", "egitim_metadatalar.db"),
          "mevcut egitim havuzu")

    dosyadan(J(KOK, "03_Test_ve_Degerlendirme", "1500_random_test",
               "makaleler", "*.pdf"), "test PDF'leri")
    dosyadan(J(KOK, "06_Benchmark_Veritabani", "**", "*.pdf"), "benchmark 300")
    dosyadan(J(KOK, "04_Genisletilmis_Egitim", "makaleler", "*.pdf"),
             "toplanmis PDF'ler")
    dosyadan(J(KOK, "grobid", "grobid-trainer", "resources", "dataset",
               "**", "*.xml"), "korpus TEI (yedekler dahil)")
    dosyadan(J(KOK, "04_Genisletilmis_Egitim", "etiketli*", "**", "*.xml"),
             "etiketleme ciktilari")

    print("DISLANAN KIMLIK: %d" % len(yasak))
    if eksik:
        print("!!! UYARI -- su kaynaklar okunamadi, SIZINTI RISKI:")
        for e in eksik:
            print("      %s" % e)
    return yasak


def dil_sec(absl, kod):
    return next((a for a in absl if isinstance(a, dict) and a.get("language") == kod), None)


def dene(pub_id, pdf_dir):
    """(durum, satir) -- durum: 'ok' | 'eksik' | 'yok' | 'hata'"""
    try:
        r = requests.get(API.format(pub_id), headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return "hata", None
        hits = r.json().get("hits", {}).get("hits", [])
        if not hits:
            return "yok", None
        k = hits[0].get("_source", {}) or {}

        absl = k.get("abstracts", []) or []
        tr, en = dil_sec(absl, "TUR"), dil_sec(absl, "ENG")
        al = lambda d, a: (d.get(a) or "") if isinstance(d, dict) else ""

        baslik = al(tr, "title") or k.get("orderTitle", "")
        ozet = al(tr, "abstract")
        yazarlar = ", ".join(y.get("name", "") for y in (k.get("authors") or [])
                             if isinstance(y, dict) and y.get("name"))
        # Otomatik etiketleme icin bu ucu sart
        if not (baslik and ozet and yazarlar):
            return "eksik", None

        pdf_key = k.get("pdf")
        if not pdf_key:
            return "eksik", None

        lr = requests.get(DOSYA.format(pdf_key), headers=HEADERS, timeout=15)
        if lr.status_code != 200:
            return "hata", None
        link = lr.text.strip().strip('"').strip("'")
        if not link.startswith("http"):
            return "hata", None
        pr = requests.get(link, headers=HEADERS, stream=True, timeout=45)
        if pr.status_code != 200:
            return "hata", None
        yol = os.path.join(pdf_dir, "makale_%s.pdf" % pub_id)
        boyut = 0
        with open(yol, "wb") as f:
            for ch in pr.iter_content(chunk_size=8192):
                f.write(ch)
                boyut += len(ch)
        if boyut < 10000:            # bozuk / bos PDF
            os.remove(yol)
            return "hata", None

        j = k.get("journal", {})
        return "ok", (
            str(pub_id), "makale_%s.pdf" % pub_id, baslik, ozet, yazarlar,
            ", ".join(al(tr, "keywords") or []), str(k.get("publicationYear", "") or ""),
            j.get("name", "") if isinstance(j, dict) else "", k.get("doi", "") or "",
            al(en, "title"), al(en, "abstract"), ", ".join(al(en, "keywords") or []),
            "Tam")
    except Exception:
        return "hata", None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedef", type=int, default=3000)
    ap.add_argument("--out", default=os.path.join(KOK, r"04_Genisletilmis_Egitim"))
    ap.add_argument("--max-id", type=int, default=2000000)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    pdf_dir = os.path.join(a.out, "makaleler")
    os.makedirs(pdf_dir, exist_ok=True)
    conn = init_db(os.path.join(a.out, "egitim_metadatalar.db"))

    yasak = yasakli_idler()
    var = {r[0] for r in conn.execute("select id from orijinal_metadatalar")}

    # Yetim PDF temizligi: DB kaydi olmayan PDF'ler (yarida kesilen kosulardan
    # kalir) egitimde kullanilamaz, cunku otomatik etiketleme metadata istiyor.
    yetim = 0
    for f in glob.glob(os.path.join(pdf_dir, "makale_*.pdf")):
        mid = os.path.basename(f)[7:-4]
        if mid not in var:
            os.remove(f)
            yetim += 1
    if yetim:
        print("yetim PDF silindi (DB kaydi yok): %d" % yetim)
    print("dislanan ID (test + mevcut korpus): %d" % len(yasak))
    print("zaten toplanmis                   : %d" % len(var))
    kalan = a.hedef - len(var)
    if kalan <= 0:
        print("Hedefe ulasilmis.")
        return
    print("toplanacak                        : %d\n" % kalan)

    kilit = threading.Lock()
    sayac = {"ok": 0, "eksik": 0, "yok": 0, "hata": 0, "denenen": 0}
    bulunan = []

    def calis(_):
        while True:
            with kilit:
                if sayac["ok"] >= kalan:
                    return
            mid = random.randint(1, a.max_id)
            if str(mid) in yasak or str(mid) in var:
                continue
            durum, satir = dene(mid, pdf_dir)
            with kilit:
                sayac["denenen"] += 1
                sayac[durum] += 1
                if durum == "ok":
                    bulunan.append(satir)
                    if len(bulunan) >= 25:
                        conn.executemany(
                            "INSERT OR REPLACE INTO orijinal_metadatalar "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", bulunan)
                        conn.commit()
                        bulunan.clear()
                    if sayac["ok"] % 100 == 0:
                        print("  %d/%d toplandi  (denenen %d, tam-olmayan %d, "
                              "kayit-yok %d, hata %d)"
                              % (sayac["ok"], kalan, sayac["denenen"],
                                 sayac["eksik"], sayac["yok"], sayac["hata"]))
                if sayac["ok"] >= kalan:
                    return

    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(calis, range(a.workers)))

    if bulunan:
        conn.executemany("INSERT OR REPLACE INTO orijinal_metadatalar "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", bulunan)
        conn.commit()

    n = conn.execute("select count(*) from orijinal_metadatalar").fetchone()[0]
    print("\nTOPLAM: %d makale   |   PDF: %s" % (n, pdf_dir))
    print("denenen ID: %d  (basari orani %.1f%%)"
          % (sayac["denenen"], sayac["ok"] * 100 / max(sayac["denenen"], 1)))
    conn.close()


if __name__ == "__main__":
    main()
