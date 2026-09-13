# -*- coding: utf-8 -*-
"""
ADIM 3/3 -- Dogrulama arayuzu.

Tarayicida acilan bir sayfa: solda TR Dizin'den gelen deger, sagda PDF'in
kapak metni. Kullanici her alan icin "dogru / duzeltildi / makalede yok" der.

Neden gerekli: olculen tavanlar (yazar %47.5, anahtar kelime %43.4) modelin
degil REFERANS VERININ siniri. TR Dizin kaydi ayri elle girilmis bir indeks
kaydi, PDF'in kendi metadata'si degil. Dogrulanmis bir alt kume olmadan
"GROBID yazari %25 buluyor" ifadesi yaniltici olur.

Veriler YERELDE kalir: altin_test_metadatalar.db dosyasina yazilir,
orijinal test_metadatalar.db'ye DOKUNULMAZ.

Calistirma:
    python adim3_sunucu.py
"""
import os
import re
import json
import sqlite3
import datetime
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

from arayuz import SAYFA

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = PROJE_KOK + r""
BURASI = os.path.join(KOK, "03_Test_ve_Degerlendirme/altin_test")
TEST = os.path.join(KOK, r"03_Test_ve_Degerlendirme\1500_random_test")

ALANLAR = [
    ("baslik",    "Başlık",            "gercek_baslik"),
    ("yazarlar",  "Yazarlar",          "gercek_yazarlar"),
    ("ozet",      "Özet",              "gercek_ozet"),
    ("kelimeler", "Anahtar Kelimeler", "gercek_anahtar_kelimeler"),
]

TAG = re.compile(r'<(?!lb\b)[^>]*>')
FRONT = re.compile(r'<front>(.*?)</front>', re.S)
KACIS = [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
         ("&apos;", "'"), ("&quot;", '"')]


def kapak_metni(mid):
    """createTraining ciktisindaki <front> blogu = makalenin kapak metni."""
    p = os.path.join(BURASI, "kapak_metni",
                     "makale_%s.training.header.tei.xml" % mid)
    if not os.path.exists(p):
        return ""
    s = open(p, encoding="utf-8", errors="replace").read()
    m = FRONT.search(s)
    if not m:
        return ""
    t = m.group(1).replace("<lb/>", "\n")
    t = TAG.sub("", t)
    for a, b in KACIS:
        t = t.replace(a, b)
    return "\n".join(l.strip() for l in t.split("\n") if l.strip())


def init_altin(path):
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE IF NOT EXISTS altin (
        id TEXT PRIMARY KEY,
        baslik TEXT, baslik_durum TEXT,
        yazarlar TEXT, yazarlar_durum TEXT,
        ozet TEXT, ozet_durum TEXT,
        kelimeler TEXT, kelimeler_durum TEXT,
        guncelleme TEXT)""")
    c.commit()
    return c


def veri_yukle():
    ids = [l.strip() for l in
           open(os.path.join(BURASI, "secilen_idler.txt"), encoding="utf-8")
           if l.strip()]
    conn = sqlite3.connect(os.path.join(TEST, "test_metadatalar.db"))
    kolonlar = ",".join(k for _, _, k in ALANLAR)
    kayit = {str(r[0]): r for r in conn.execute(
        "select id,%s,gercek_dergi,gercek_yil from orijinal_metadatalar" % kolonlar)}
    conn.close()
    out = []
    for mid in ids:
        r = kayit.get(mid)
        if not r:
            continue
        d = {"id": mid, "dergi": r[len(ALANLAR) + 1] or "",
             "yil": r[len(ALANLAR) + 2] or "", "kapak": kapak_metni(mid)}
        for i, (ad, _, _) in enumerate(ALANLAR):
            d[ad] = r[1 + i] or ""
        out.append(d)
    return out


class Sunucu(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _gonder(self, kod, tip, veri):
        self.send_response(kod)
        self.send_header("Content-Type", tip)
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = SAYFA.replace("__ALANLAR__", json.dumps(
                [[a, e] for a, e, _ in ALANLAR], ensure_ascii=False))
            self._gonder(200, "text/html; charset=utf-8", html.encode("utf-8"))
        elif self.path == "/veri":
            c = init_altin(self.server.db_yolu)
            cur = c.execute("select * from altin")
            adlar = [d[0] for d in cur.description]
            altin = {r[0]: dict(zip(adlar, r)) for r in cur.fetchall()}
            c.close()
            veri = {"kayitlar": self.server.kayitlar, "altin": altin}
            self._gonder(200, "application/json; charset=utf-8",
                         json.dumps(veri, ensure_ascii=False).encode("utf-8"))
        else:
            self._gonder(404, "text/plain", b"yok")

    def do_POST(self):
        if self.path != "/kaydet":
            return self._gonder(404, "text/plain", b"yok")
        n = int(self.headers.get("Content-Length", 0))
        k = json.loads(self.rfile.read(n).decode("utf-8"))
        c = init_altin(self.server.db_yolu)
        c.execute("""INSERT OR REPLACE INTO altin
            (id,baslik,baslik_durum,yazarlar,yazarlar_durum,ozet,ozet_durum,
             kelimeler,kelimeler_durum,guncelleme)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
                  (k["id"], k.get("baslik"), k.get("baslik_durum"),
                   k.get("yazarlar"), k.get("yazarlar_durum"),
                   k.get("ozet"), k.get("ozet_durum"),
                   k.get("kelimeler"), k.get("kelimeler_durum"),
                   datetime.datetime.now().isoformat(timespec="seconds")))
        c.commit()
        n_top = c.execute("select count(*) from altin").fetchone()[0]
        c.close()
        self._gonder(200, "application/json",
                     json.dumps({"ok": 1, "n": n_top}).encode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--db", default=os.path.join(BURASI, "altin_test_metadatalar.db"))
    ap.add_argument("--tarayici-acma", action="store_true")
    a = ap.parse_args()

    kayitlar = veri_yukle()
    kapaksiz = sum(1 for k in kayitlar if not k["kapak"])
    print("yuklenen makale : %d" % len(kayitlar))
    if kapaksiz:
        print("kapak metni YOK : %d  (adim2 tamamlandi mi?)" % kapaksiz)
    c = init_altin(a.db)
    print("zaten dogrulanan: %d" %
          c.execute("select count(*) from altin").fetchone()[0])
    c.close()

    srv = HTTPServer(("127.0.0.1", a.port), Sunucu)
    srv.kayitlar = kayitlar
    srv.db_yolu = a.db
    url = "http://127.0.0.1:%d" % a.port
    print("\n  %s\n\nDurdurmak icin Ctrl+C. Kayitlar: %s" % (url, a.db))
    if not a.tarayici_acma:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nkapatildi")


if __name__ == "__main__":
    main()
