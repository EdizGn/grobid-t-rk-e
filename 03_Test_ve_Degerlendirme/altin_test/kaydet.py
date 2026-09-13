# -*- coding: utf-8 -*-
"""Elle dogrulanan kararlari altin DB'ye yazar."""
import sys, json, sqlite3, datetime, adim3_sunucu as S

db = S.init_altin("altin_test_metadatalar.db")
kayit = {x["id"]: x for x in S.veri_yukle()}
kararlar = json.load(open(sys.argv[1], encoding="utf-8"))
n = 0
for k in kararlar:
    v = kayit[k["id"]]
    satir = {"id": k["id"]}
    for alan in ("baslik", "yazarlar", "ozet", "kelimeler"):
        d = k.get(alan, "dogru")
        if d == "atla":            # dogrulanamadi -- altin kumeye girmesin
            satir[alan + "_durum"], satir[alan] = "", v[alan]
            continue
        if isinstance(d, list):           # ["duzeltildi", "yeni deger"]
            satir[alan + "_durum"], satir[alan] = d[0], d[1]
        else:
            satir[alan + "_durum"], satir[alan] = d, v[alan]
    db.execute("""INSERT OR REPLACE INTO altin
        (id,baslik,baslik_durum,yazarlar,yazarlar_durum,ozet,ozet_durum,
         kelimeler,kelimeler_durum,guncelleme) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (satir["id"], satir["baslik"], satir["baslik_durum"],
         satir["yazarlar"], satir["yazarlar_durum"], satir["ozet"], satir["ozet_durum"],
         satir["kelimeler"], satir["kelimeler_durum"],
         datetime.datetime.now().isoformat(timespec="seconds")))
    n += 1
db.commit()
print("kaydedilen: %d   toplam: %d" % (n, db.execute("select count(*) from altin").fetchone()[0]))
