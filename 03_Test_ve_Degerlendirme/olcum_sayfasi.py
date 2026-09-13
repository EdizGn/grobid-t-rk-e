# -*- coding: utf-8 -*-
"""
05_TRUBA/olcumler/*.txt ciktilarini tek bir karsilastirma sayfasina cevirir.

    python olcum_sayfasi.py

Cikti: dashboard/olcumler.html  (kendi kendine yeten, veri gomulu)

NEDEN KAYIT DEFTERI (KAYIT sozlugu) VAR:
Bu projede bir kez su oldu -- "Stok GROBID (CRF)" diye raporlanan tum
rakamlar aslinda YANLIS bir model dosyasiyla (YANLIS-STOK_10792_0828.wapiti,
10.792 oznitelik; gercek 0.9.1 stok modeli 15.545) olculmustu. Hata ancak
Ingilizce testte %79 bos ciktI verince fark edildi. Ayrica DeLFT olcumleri
GROBID 0.8.0 ile uretilmisti, digerleri 0.9.1 ile -- yani ayni tabloda yan
yana konulamazlar.

Bu yuzden her dosyanin hangi model / hangi GROBID surumu ile uretildigi
ELLE kaydediliyor ve gecersiz olanlar sayfada ayri bolumde, sebebiyle
birlikte gosteriliyor. Kayitta olmayan bir dosya sessizce tabloya girmez;
uyari basilir. Yeni olcum ekleyince buraya bir satir yazmak SART.
"""
import os
import re
import io
import json
import html
import datetime

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLCUM = os.path.join(KOK, "05_TRUBA", "olcumler")
CIKTI = os.path.join(KOK, "03_Test_ve_Degerlendirme", "dashboard", "olcumler.html")

# dosya -> (etiket, korpus, model, grobid surumu, diakritik, durum, not)
#   durum: "gecerli" | "gecersiz" | "kiyaslanamaz"
KAYIT = {
    "TR_stok091.txt": (
        "Stok CRF", "TR", "stok_15545_imaj091.wapiti", "0.9.1",
        "katlanmis", "gecerli", ""),
    "w2999_nodiak.txt": (
        "2. egitim - 2999 belge", "TR", "v1_113397_2999belge_barbun.wapiti", "0.9.1",
        "katlanmis", "gecerli", ""),
    "w2999_diak.txt": (
        "2. egitim - 2999 belge", "TR", "v1_113397_2999belge_barbun.wapiti", "0.9.1",
        "ham", "gecerli", ""),
    "w494_nodiak.txt": (
        "1. egitim - 494 belge", "TR", "v0_26793_494belge.wapiti", "0.9.1",
        "katlanmis", "gecerli", ""),
    "w494_diak.txt": (
        "1. egitim - 494 belge", "TR", "v0_26793_494belge.wapiti", "0.9.1",
        "ham", "gecerli", ""),
    # --- 3. egitim, v4 etiketlemesi (2153 belge): Ingilizce baslik da
    # etiketli, yazarsiz belge karantinada. TRUBA'da 600 iterasyon, onceki
    # kosuyla birebir ayni hiperparametre (epsilon 1e-6, window 30).
    #
    # ETIKETLEME SURUMLERI (04_Genisletilmis_Egitim/etiketli*/altin):
    #   v1  2505 altin  -> 2505 + 494 eski = 2999 belge, 2. EGITIMDE KULLANILDI
    #   v2  2411 altin  -> hic egitilmedi
    #   v3  2208 altin  -> 2208 + 419 eski = 2627 belge, HIC EGITILMEDI
    #   v4  1827 altin  -> 1827 + 326 eski = 2153 belge, 3. EGITIMDE KULLANILDI
    # Yani v1'den dogrudan v4'e gecildi; aradaki iki surum paketlendi ama
    # egitilmedi. "2999 belge" satiri uzun sure yanlislikla "v3" diye
    # etiketliydi; 2505+494=2999 aritmetigi v1 oldugunu gosteriyor.
    "TR_v4_600.txt": (
        "3. egitim - 2153 belge (orfoz)", "TR", "v4_80603_2153belge_orfoz.wapiti",
        "0.9.1", "katlanmis", "gecerli", ""),
    "TR_v4_600b.txt": (
        "3. egitim - 2153 belge (barbun)", "TR", "v4_85537_2153belge_barbun.wapiti",
        "0.9.1", "katlanmis", "gecerli", ""),
    "ING_v4_600.txt": (
        "3. egitim - 2153 belge (orfoz)", "ING", "v4_80603_2153belge_orfoz.wapiti",
        "0.9.1", "-", "gecerli", ""),
    "ING_v4_600b.txt": (
        "3. egitim - 2153 belge (barbun)", "ING", "v4_85537_2153belge_barbun.wapiti",
        "0.9.1", "-", "gecerli", ""),

    # --- v4 header + BIZIM Turkce segmentasyon modeli (20.803 oznitelik).
    # Diger tum olcumler stok segmentasyonla (14.232) yapildi; burada
    # segmentasyon degistigi icin karsilastirma "ayni hat" degil, kasitli
    # olarak farkli. Turkcede keywords +4.56 / abstract +2.05 kazandiriyor,
    # Ingilizcede keywords -11.15 kaybettiriyor -- Turkce'ye ozellesme.
    "TR_v4_trseg.txt": (
        "3. egitim - 2153 belge (orfoz) + TR segmentasyon", "TR",
        "v4_80603_2153belge_orfoz.wapiti + segmentation tr_20803_0908", "0.9.1",
        "katlanmis", "gecerli", ""),
    # AYRI KORPUS. 1435'lik testle ayni tabloya konmamali: bunlar
    # etiketleyicinin "guvenilmez" diye eledigi, bilerek zor secilmis belgeler.
    "TR_v4_karantina1051.txt": (
        "3. egitim - 2153 belge (orfoz) + TR segmentasyon", "KAR",
        "v4_80603_2153belge_orfoz.wapiti + segmentation tr_20803_0908", "0.9.1",
        "katlanmis", "gecerli", ""),
    "ING_v4_trseg.txt": (
        "3. egitim - 2153 belge (orfoz) + TR segmentasyon", "ING",
        "v4_80603_2153belge_orfoz.wapiti + segmentation tr_20803_0908", "0.9.1",
        "-", "gecerli", ""),

    # --- "Ayirt et" (diakritik duyarli) karsiliklar. Ayni XML ciktilarindan,
    # sadece --diakritik-yoksay bayragi OLMADAN yeniden degerlendirildi;
    # PDF'ler tekrar islenmedi. Boylece o modda da stok referans satiri ve
    # v4 kosulari gorunur oluyor.
    "TR_stok091_diak.txt": (
        "Stok CRF", "TR", "stok_15545_imaj091.wapiti", "0.9.1",
        "ham", "gecerli", ""),
    "TR_v4_600_diak.txt": (
        "3. egitim - 2153 belge (orfoz)", "TR", "v4_80603_2153belge_orfoz.wapiti",
        "0.9.1", "ham", "gecerli", ""),
    "TR_v4_600b_diak.txt": (
        "3. egitim - 2153 belge (barbun)", "TR", "v4_85537_2153belge_barbun.wapiti",
        "0.9.1", "ham", "gecerli", ""),
    "TR_v4_trseg_diak.txt": (
        "3. egitim - 2153 belge (orfoz) + TR segmentasyon", "TR",
        "v4_80603_2153belge_orfoz.wapiti + segmentation tr_20803_0908", "0.9.1",
        "ham", "gecerli", ""),

    "ING_stok091.txt": (
        "Stok CRF", "ING", "stok_15545_imaj091.wapiti", "0.9.1",
        "-", "gecerli", ""),
    "ING_w2999.txt": (
        "2. egitim - 2999 belge", "ING", "v1_113397_2999belge_barbun.wapiti", "0.9.1",
        "-", "gecerli", ""),

    "stokcrf_nodiak.txt": (
        "Stok CRF -- YANLIS MODEL", "TR", "YANLIS-STOK_10792_0828.wapiti",
        "0.9.1", "katlanmis", "gecersiz",
        "Stok saniIan dosya aslinda eski bir surumden kalmaydi. Bu olcumden "
        "cikan 'egitilmis modelimiz baslikta stoktan 14 puan geride' iddiasi "
        "yanlisti; dogru stok modelle fark 3.8 puan."),
    "stokcrf_diak.txt": (
        "Stok CRF -- YANLIS MODEL", "TR", "YANLIS-STOK_10792_0828.wapiti",
        "0.9.1", "ham", "gecersiz", "Yukaridakiyle ayni sebep."),
    "ING_stokcrf.txt": (
        "Stok CRF -- YANLIS MODEL", "ING", "YANLIS-STOK_10792_0828.wapiti",
        "0.9.1", "-", "gecersiz",
        "Hatayi ifsa eden olcum: baslik F1 = 1.15, makalelerin %79'unda bos "
        "header uretti. Bu sayede yanlis model dosyasi fark edildi."),

    "delft_nodiak.txt": (
        "DeLFT", "TR", "header-BidLSTM_CRF_FEATURES", "0.8.0",
        "katlanmis", "kiyaslanamaz",
        "GROBID 0.8.0 ile uretildi, digerleri 0.9.1. Farkli surum = farkli stok "
        "segmentasyon modeli ve farkli oznitelik uretimi. Ayni tabloda yan yana "
        "konulamaz. 0.9.1-full imajiyla yeniden olculecek (delft_olc.sh)."),
    "delft_diak.txt": (
        "DeLFT", "TR", "header-BidLSTM_CRF_FEATURES", "0.8.0",
        "ham", "kiyaslanamaz", "Yukaridakiyle ayni sebep."),
}

# Tablodaki satir sirasi: stok referans basta, sonra ESKIDEN YENIYE egitimler,
# en sonda segmentasyon da degistirilen varyant (tek degisken kurali orada
# bozuluyor, o yuzden ayri durmasi daha dogru).
SIRA = [
    "Stok CRF",
    "1. egitim - 494 belge",
    "2. egitim - 2999 belge",
    "3. egitim - 2153 belge (barbun)",
    # orfoz ve "orfoz + TR segmentasyon" ALT ALTA duruyor: aralarindaki tek
    # fark segmentasyon modeli, yani o iki satir karsilastirilinca
    # segmentasyonun etkisi dogrudan okunuyor.
    "3. egitim - 2153 belge (orfoz)",
    "3. egitim - 2153 belge (orfoz) + TR segmentasyon",
]

MODLAR = [
    ("strict", "Strict", "Birebir ayni"),
    ("soft", "Soft", "Noktalama / buyuk-kucuk / bosluk yoksayilir"),
    ("lev", "Levenshtein", "Duzenleme benzerligi >= 0.80"),
    ("ratcliff", "Ratcliff/Obershelp", "Ortak alt dizi benzerligi >= 0.95"),
]
MOD_DESEN = {
    "strict": "Strict Matching",
    "soft": "Soft Matching",
    "lev": "Levenshtein Matching",
    "ratcliff": "Ratcliff/Obershelp",
}
ALANLAR = ["title", "authors", "first_author", "abstract", "keywords"]
ALAN_TR = {
    "title": "Başlık", "authors": "Yazarlar", "first_author": "İlk yazar ⚠",
    "abstract": "Özet", "keywords": "Anahtar kelime",
}
# UYARI -- "Ilk yazar" metrigi guvenilmez:
# 50 makalelik elle dogrulamada TR Dizin'in ILK yazari, makalenin gercek ilk
# yazari olma orani yalnizca %62 cikti. Referansin siralamasi keyfi oldugu icin
# bu metrigin tavani %62'dir ve olcum yontemi degistirilerek duzeltilemez.
# "Yazarlar" ve "Anahtar kelime" metrikleri SIRASIZDIR (yazar_normalize
# listeleri siralayarak karsilastirir), orada sira farki ceza degildir.

# ---------------------------------------------------------------- hata nedenleri
# Sayfanin altindaki "Hatalar nereden geliyor" bolumunun verisi.
#
# KAYNAK: 03_Test_ve_Degerlendirme/altin_test -- 50 makalenin PDF kapagi tek
# tek acilip TR Dizin kaydiyla karsilastirildi; 30'una serbest metin gerekce
# yazildi. Sayilar o gerekcelerden uretiliyor:
#     python altin_test/gerekce_ozet.py
# Tahmin veya genel gecer aciklama DEGIL -- her sayi elle dogrulanmis.
#
# "kim" alani sucun kimde oldugunu soyler:
#     referans = TR Dizin kaydi hatali/eksik  -> model dogru olsa bile ceza yer
#     belge    = PDF'in kendisi sorunlu       -> cikarilacak veri ortada yok
#     model    = GROBID yanlis cikariyor      -> egitimle duzelebilecek kisim
#     yazim    = ayni icerik, farkli yazim    -> olcum tanimiyla ilgili
NEDENLER = [
    {
        "alan": "title", "ad": "Başlık",
        "ozet": "En saglam metrik. Kalan hatanin cogu referans kaydinin "
                "bicim hatasi, modelin okuma hatasi degil.",
        "dogrulama": "50 makalenin 4'unde (%8) TR Dizin basligi duzeltme gerektirdi; hicbirinde baslik makaleden eksik degildi.",
        "nedenler": [
            {"ad": "DB kaydinda bosluk eksik ('LanguageAnxiety', 'UzerineNitel')",
             "n": 3, "kim": "referans"},
            {"ad": "DB'de Turkce baslik var, kapakta yalnizca Ingilizcesi basili",
             "n": 1, "kim": "belge"},
        ],
        "not": "Karantina cozumlemesinde basligi bulunamayan 495 belgenin "
               "%35,6'sinda baslik kapak metninde gercekten yok: dikey dergi "
               "logosunun parcalanmis harfleri, yalnizca 'Cite this article as' "
               "satirinda gecen baslik, taranmis goruntu.",
    },
    {
        "alan": "authors", "ad": "Yazarlar",
        "ozet": "En cok puan kaybettigimiz metrik. Kaybin yarisindan fazlasi "
                "referansin kendisinden geliyor.",
        "dogrulama": "50 makalenin 26'sinda TR Dizin yazar alani duzeltildi, 2'sinde yazar makalede hic yok — toplam 28/50 (%56).",
        "nedenler": [
            {"ad": "Ayni kisiler, farkli sira", "n": 14, "kim": "referans"},
            {"ad": "DB'de isim yanlis veya eksik (YENTURK/YENTUR, eksik soyad)",
             "n": 7, "kim": "referans"},
            {"ad": "Sadece diakritik farki (Sule / Şule)", "n": 3, "kim": "yazim"},
            {"ad": "Yazar kapak metninde hic gecmiyor", "n": 2, "kim": "belge"},
            {"ad": "Sadece buyuk/kucuk harf farki", "n": 2, "kim": "yazim"},
            {"ad": "Yazar kisi degil (duzenleme kurulu)", "n": 1, "kim": "belge"},
        ],
        "not": "Model tarafindaki acigin %91'i header modelinden, %9'u "
               "segmentasyondan geliyor: isimler GROBID'in okudugu bolgenin "
               "icinde duruyor ama etiketlenmiyor. Egitimle duzelebilecek kisim bu.",
    },
    {
        "alan": "first_author", "ad": "İlk yazar",
        "ozet": "Bu referansla olculemez. Tablodaki deger model kalitesini "
                "degil, TR Dizin'in yazar siralamasini olcuyor.",
        "dogrulama": "TR Dizin'in ilk yazari, makalenin gercek ilk yazari olma "
                     "orani 50 makalede %62.",
        "nedenler": [
            {"ad": "DB'nin yazar sirasi keyfi (19 yazarli makalede ilk yazar eksikti)",
             "n": 14, "kim": "referans"},
        ],
        "not": "Yazarlar ve Anahtar kelime metrikleri listeyi siralayip "
               "karsilastirir, sira farki orada ceza degildir. Ilk yazar ise "
               "dogrudan siraya bagli. Tavani %62 ve olcum yontemi "
               "degistirilerek duzeltilemez -- referansin duzelmesi gerekir.",
    },
    {
        "alan": "abstract", "ad": "Özet",
        "ozet": "Ya tam tutuyor ya hic tutmuyor; ara deger neredeyse yok. "
                "Basarisizlik segmentasyonun ozet blogunu kacirmasi demek.",
        "dogrulama": "50 makalenin 1'inde ozet duzeltildi, 5'inde ozet makalede yok. "
                     "Olculen 30 makalede ortusme: 16 tam (1.00), 8 yuksek "
                     "(0.80-0.99), 1 orta, 5 basarisiz (<0.30).",
        "nedenler": [
            {"ad": "Zorlu PDF / bozuk font (Turkce harfler dusmus)", "n": 2, "kim": "belge"},
            {"ad": "Makalede ozet hic yok (elle dogrulandi)", "n": 5, "kim": "belge"},
        ],
        "not": "Basarisiz 5 belgenin ortak yani kapak duzeni: dikey dergi "
               "logosu, parcalanmis harfler, cok sutunlu kapak. Bunlarda "
               "segmentasyon ozet blogunu yanlis yere koyuyor, header modeli "
               "de bozuk girdiyle calisiyor.",
    },
    {
        "alan": "keywords", "ad": "Anahtar kelime",
        "ozet": "Olculen hatanin buyuk cogunlugu modelin degil, referansin "
                "eksikligi. Model makaledeki kelimeleri dogru buluyor, "
                "karsilastiracak kayit yok.",
        "dogrulama": "50 makalenin 29'unda TR Dizin anahtar kelime alani duzeltildi, "
                     "4'unde makalede anahtar kelime yok — toplam 33/50 (%66).",
        "nedenler": [
            {"ad": "DB alani bos ama makalede anahtar kelime var", "n": 14, "kim": "referans"},
            {"ad": "Indeksleyici kendi terimlerini yazmis (makalede gecmiyor)",
             "n": 5, "kim": "referans"},
            {"ad": "Ayni terimler, farkli sira", "n": 5, "kim": "referans"},
            {"ad": "Makale anahtar kelime basmiyor (eski dergi sayilari)", "n": 3, "kim": "belge"},
            {"ad": "Sadece buyuk/kucuk harf veya ayrac farki", "n": 2, "kim": "yazim"},
        ],
        "not": "DB alani bos oldugunda olcum o makaleyi atliyor, yani skor "
               "yalnizca kayit bulunan makaleler uzerinden. Tablodaki kapsama "
               "sayisi (orn. 460/519) tam da bu yuzden onemli -- skor dusuk "
               "gorunmese bile daha az makaleye dayaniyor olabilir.",
    },
]

KIM_TR = {
    "referans": "TR Dizin kaydı",
    "belge": "PDF'in kendisi",
    "model": "GROBID",
    "yazim": "Yazım farkı",
}

BASLIK_RE = re.compile(r'Degerlendirilen:\s*(\d+)\s*dosya.*?referans dili:\s*(.+)$')
SATIR_RE = re.compile(
    r'^\|\s*(\w+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|')


def coz(yol):
    """Bir olcum dosyasini {mod: {alan: {p, r, f1, support}}} yapisina cevirir."""
    metin = io.open(yol, encoding="utf-8", errors="replace").read()
    satirlar = metin.split("\n")

    belge, dil = 0, "?"
    m = BASLIK_RE.search(satirlar[0]) if satirlar else None
    if m:
        belge, dil = int(m.group(1)), m.group(2).strip()

    sonuc, aktif = {}, None
    for s in satirlar:
        for anahtar, desen in MOD_DESEN.items():
            if desen in s:
                aktif = anahtar
                sonuc[aktif] = {}
                break
        else:
            if aktif:
                sm = SATIR_RE.match(s)
                if sm and sm.group(1) in ALANLAR:
                    sonuc[aktif][sm.group(1)] = {
                        "p": float(sm.group(2)), "r": float(sm.group(3)),
                        "f1": float(sm.group(4)), "n": int(sm.group(5)),
                    }
    return belge, dil, sonuc


def topla():
    kosular, uyari = [], []
    if not os.path.isdir(OLCUM):
        raise SystemExit("HATA: %s yok" % OLCUM)
    for ad in sorted(os.listdir(OLCUM)):
        if not ad.endswith(".txt"):
            continue
        if ad not in KAYIT:
            uyari.append(ad)
            continue
        etiket, korpus, model, surum, diak, durum, aciklama = KAYIT[ad]
        belge, dil, veri = coz(os.path.join(OLCUM, ad))
        if not veri:
            uyari.append("%s (ayristirilamadi)" % ad)
            continue
        kosular.append({
            "dosya": ad, "etiket": etiket, "korpus": korpus, "model": model,
            "surum": surum, "diakritik": diak, "durum": durum, "aciklama": aciklama,
            "belge": belge, "dil": dil, "veri": veri,
            "tarih": datetime.datetime.fromtimestamp(
                os.path.getmtime(os.path.join(OLCUM, ad))).strftime("%d.%m.%Y %H:%M"),
        })
    return kosular, uyari


SAYFA = u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Model Olcumleri &mdash; GROBID Header</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
<style>
.olcum-wrap{max-width:1400px;margin:0 auto;padding:0 20px}
.kontrol{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-end;
         padding:18px 22px;margin-bottom:26px}
.kontrol .grup{display:flex;flex-direction:column;gap:7px}
.kontrol label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;
               color:var(--text-muted);font-weight:600}
.segment{display:flex;background:rgba(2,6,23,.5);border:1px solid var(--glass-border);
         border-radius:10px;overflow:hidden}
.segment button{background:none;border:none;color:var(--text-muted);
                font:600 13px Inter,sans-serif;padding:9px 15px;cursor:pointer;
                transition:all .18s;white-space:nowrap}
.segment button:hover{color:var(--text-main);background:rgba(255,255,255,.05)}
.segment button[aria-pressed="true"]{background:var(--accent-blue);color:#fff}
.mod-aciklama{font-size:12.5px;color:var(--text-muted);margin:-12px 0 24px;
              padding-left:4px}
h2.bolum{font-size:17px;font-weight:800;margin:34px 0 6px;
         display:flex;align-items:center;gap:11px}
h2.bolum .rozet{font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;
                background:rgba(59,130,246,.18);color:#93c5fd;letter-spacing:.03em}
.bolum-alt{font-size:12.5px;color:var(--text-muted);margin-bottom:14px}
table.olcum{width:100%;border-collapse:separate;border-spacing:0;font-size:13.5px;
            background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:14px;overflow:hidden}
table.olcum th{background:rgba(2,6,23,.55);padding:13px 14px;text-align:right;
               font-weight:600;font-size:11px;letter-spacing:.07em;
               text-transform:uppercase;color:var(--text-muted);white-space:nowrap}
table.olcum th:first-child{text-align:left;min-width:230px}
table.olcum td{padding:12px 14px;text-align:right;
               border-top:1px solid rgba(255,255,255,.055);
               font-variant-numeric:tabular-nums}
table.olcum td:first-child{text-align:left}
table.olcum tr:hover td{background:rgba(255,255,255,.035)}
.kosu-ad{font-weight:600}
.kosu-alt{font-size:11px;color:var(--text-muted);margin-top:3px;font-weight:400}
.deger{display:inline-block;min-width:52px;padding:3px 8px;border-radius:7px;
       font-weight:600}
.iyi{background:rgba(16,185,129,.16);color:#6ee7b7}
.orta{background:rgba(245,158,11,.16);color:#fcd34d}
.zayif{background:rgba(239,68,68,.15);color:#fca5a5}
.yok{color:var(--text-muted)}
tr.satir{cursor:pointer}
tr.satir:hover td{background:rgba(59,130,246,.07)}
tr.satir.taban td{background:rgba(59,130,246,.11)}
tr.satir.taban td:first-child{box-shadow:inset 3px 0 0 var(--accent-blue)}
.taban-rozet{margin-left:9px;font-size:10px;font-weight:700;letter-spacing:.06em;
             text-transform:uppercase;color:#93c5fd;background:rgba(59,130,246,.18);
             padding:2px 7px;border-radius:20px;vertical-align:middle}
.fark{font-size:11px;margin-left:6px;font-weight:600}
.fark.arti{color:#6ee7b7}
.fark.eksi{color:#fca5a5}
.uyari{border-left:3px solid var(--danger);background:rgba(239,68,68,.07);
       padding:15px 19px;border-radius:0 12px 12px 0;margin:14px 0;font-size:13.5px;
       line-height:1.65}
.uyari.sari{border-left-color:var(--warning);background:rgba(245,158,11,.07)}
.uyari b{color:var(--text-main)}
.uyari-baslik{font-weight:700;margin-bottom:5px;font-size:13px;
              letter-spacing:.03em;text-transform:uppercase}
.uyari-baslik.kirmizi{color:#fca5a5}
.uyari-baslik.sari{color:#fcd34d}
h2.neden-baslik{font-size:17px;font-weight:800;margin:40px 0 6px;
                display:flex;align-items:center;gap:10px}
.neden-alt{font-size:12.5px;color:var(--text-muted);margin-bottom:18px;max-width:900px}
.neden-izgara{display:grid;gap:14px;
              grid-template-columns:repeat(auto-fit,minmax(330px,1fr))}
.neden-kart{background:var(--glass-bg);border:1px solid var(--glass-border);
            border-radius:14px;padding:16px 18px}
.neden-kart h3{margin:0 0 4px;font-size:14px;font-weight:800;
               display:flex;align-items:center;gap:8px}
.neden-ozet{font-size:12.5px;color:var(--text-muted);line-height:1.55;margin-bottom:11px}
.neden-dog{font-size:11.5px;font-weight:600;color:#93c5fd;
           background:rgba(59,130,246,.12);border-radius:8px;
           padding:7px 10px;margin-bottom:11px;line-height:1.45}
.neden-liste{list-style:none;padding:0;margin:0 0 11px}
.neden-liste li{display:flex;align-items:flex-start;gap:9px;
                font-size:12px;line-height:1.5;padding:5px 0;
                border-top:1px solid rgba(255,255,255,.05)}
.neden-liste li:first-child{border-top:none}
.neden-n{flex:0 0 26px;text-align:right;font-weight:800;font-variant-numeric:tabular-nums}
.neden-ad{flex:1;color:var(--text-muted)}
.kim{flex:0 0 auto;font-size:9.5px;font-weight:700;letter-spacing:.04em;
     text-transform:uppercase;padding:2px 7px;border-radius:20px;white-space:nowrap}
.kim.referans{background:rgba(245,158,11,.16);color:#fcd34d}
.kim.belge{background:rgba(168,85,247,.16);color:#d8b4fe}
.kim.model{background:rgba(239,68,68,.15);color:#fca5a5}
.kim.yazim{background:rgba(148,163,184,.16);color:#cbd5e1}
.neden-not{font-size:11.5px;color:var(--text-muted);line-height:1.55;
           border-left:2px solid var(--glass-border);padding-left:10px}
.kim-anahtar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:center}
.kim-anahtar span.et{font-size:11.5px;color:var(--text-muted)}
details.gizli{margin-top:30px}
details.gizli summary{cursor:pointer;font-weight:600;font-size:14px;
                      padding:13px 18px;background:var(--glass-bg);
                      border:1px solid var(--glass-border);border-radius:12px;
                      list-style:none;user-select:none}
details.gizli summary::-webkit-details-marker{display:none}
details.gizli summary:before{content:"\\25B8 ";color:var(--text-muted)}
details.gizli[open] summary:before{content:"\\25BE "}
details.gizli > div{padding-top:16px}
.geri{display:inline-flex;align-items:center;gap:8px;margin-bottom:22px;
      color:var(--text-muted);text-decoration:none;font-size:13px;font-weight:600;
      padding:8px 14px 8px 11px;border:1px solid var(--glass-border);
      border-radius:9px;background:var(--glass-bg);transition:all .16s}
.geri:hover{color:var(--text-main);border-color:rgba(59,130,246,.45);
            background:rgba(59,130,246,.10)}
.geri:focus-visible{outline:2px solid var(--accent-blue);outline-offset:2px}
.geri span.ok{font-size:15px;line-height:1;opacity:.75}
.damga{font-size:11.5px;color:var(--text-muted);margin-top:38px;
       padding-top:16px;border-top:1px solid rgba(255,255,255,.07)}
@media(max-width:820px){
  table.olcum{font-size:12px} table.olcum th,table.olcum td{padding:9px 8px}
  table.olcum th:first-child{min-width:150px}
}
.kaydir{overflow-x:auto;-webkit-overflow-scrolling:touch}
</style>
</head>
<body>
<div class="background-gradients">
  <div class="glow-orb orb-1"></div><div class="glow-orb orb-2"></div>
  <div class="glow-orb orb-3"></div>
</div>
<div class="container olcum-wrap">
  <a class="geri" href="index.html"><span class="ok">&larr;</span> Makale bazl&#305; rapor</a>
  <header>
    <h1>Model <span>Olcumleri</span></h1>
    <p>GROBID header modellerinin ayni test kumesindeki karsilastirmasi</p>
  </header>

  <div class="card glass kontrol">
    <div class="grup">
      <label>Eslesme modu</label>
      <div class="segment" id="mod-secim"></div>
    </div>
    <div class="grup">
      <label>Metrik</label>
      <div class="segment" id="metrik-secim">
        <button data-v="f1" aria-pressed="true">F1</button>
        <button data-v="p" aria-pressed="false">Kesinlik</button>
        <button data-v="r" aria-pressed="false">Duyarlilik</button>
      </div>
    </div>
    <div class="grup">
      <label>Turkce diakritik</label>
      <div class="segment" id="diak-secim">
        <button data-v="katlanmis" aria-pressed="true">Yoksay (&#351; = s)</button>
        <button data-v="ham" aria-pressed="false">Ay&#305;rt et (&#351; &ne; s)</button>
      </div>
    </div>
  </div>
  <div class="mod-aciklama" id="mod-aciklama"></div>

  <div id="tablolar"></div>

  <details class="gizli" id="supheli-kutu">
    <summary>Gecersiz ve kiyaslanamaz olcumler &mdash; <span id="supheli-sayi"></span></summary>
    <div id="supheli"></div>
  </details>

  <h2 class="neden-baslik">Hatalar nereden geliyor</h2>
  <div class="neden-alt">
    Yukaridaki skorlarin her biri bir <b>anlasmazlik</b> olcuyor: modelin
    cikardigi deger ile TR Dizin kaydinin uyusmamasi. Anlasmazligin her zaman
    modelden kaynaklanmadigini gormek icin 50 makalenin PDF kapagi tek tek
    acildi ve kayitla karsilastirildi. Asagidaki sayilar o incelemeden geliyor.
  </div>
  <div class="kim-anahtar" id="kim-anahtar"></div>
  <div class="neden-izgara" id="nedenler"></div>

  <div class="damga" id="damga"></div>
</div>

<script>
const KOSULAR = __VERI__;
const MODLAR  = __MODLAR__;
const SIRA    = __SIRA__;
const ALAN_TR = __ALAN_TR__;
const ALANLAR = __ALANLAR__;
const URETIM  = "__URETIM__";

let mod = "lev", metrik = "f1", diak = "katlanmis";
// Fark sutunlarinin karsilastirildigi kosu. Korpus basina ayri
// tutuluyor; null ise stok CRF kullanilir.
let taban = {TR: null, ING: null};

function kacis(s){return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function sinif(v){ return v >= 70 ? "iyi" : v >= 40 ? "orta" : "zayif"; }

function hucre(kosu, alan, taban){
  const g = (kosu.veri[mod]||{})[alan];
  if(!g) return '<td class="yok">&mdash;</td>';
  const v = g[metrik];
  let fark = "";
  if(taban && taban !== kosu){
    const t = (taban.veri[mod]||{})[alan];
    if(t){
      const d = v - t[metrik];
      if(Math.abs(d) >= 0.05)
        fark = '<span class="fark '+(d>0?"arti":"eksi")+'">'+
               (d>0?"+":"")+d.toFixed(1)+'</span>';
    }
  }
  return '<td><span class="deger '+sinif(v)+'">'+v.toFixed(2)+'</span>'+fark+'</td>';
}

function tablo(kosular, taban, kod){
  let h = '<div class="kaydir"><table class="olcum"><thead><tr><th>Kosu</th>';
  ALANLAR.forEach(a => h += '<th'+(a === "first_author"
      ? ' title="TR Dizin siralamasi keyfi: ilk yazar %62 dogru. Bu metrigin tavani %62."'
      : '')+'>'+ALAN_TR[a]+'</th>');
  h += '</tr></thead><tbody>';
  kosular.forEach(k => {
    const secili = (k === taban);
    h += '<tr class="satir'+(secili?' taban':'')+'" data-kod="'+kod+
         '" data-etiket="'+kacis(k.etiket)+'" title="Fark sutunlarini bu kosuya gore hesapla">'+
         '<td><div class="kosu-ad">'+kacis(k.etiket)+
         (secili?'<span class="taban-rozet">taban</span>':'')+'</div>'+
         '<div class="kosu-alt">'+kacis(k.model)+' &middot; GROBID '+k.surum+
         ' &middot; '+k.belge+' belge</div></td>';
    ALANLAR.forEach(a => h += hucre(k, a, taban));
    h += '</tr>';
  });
  return h + '</tbody></table></div>';
}

function ciz(){
  document.querySelectorAll('#mod-secim button').forEach(
    b => b.setAttribute('aria-pressed', b.dataset.v === mod));
  document.querySelectorAll('#metrik-secim button').forEach(
    b => b.setAttribute('aria-pressed', b.dataset.v === metrik));
  document.querySelectorAll('#diak-secim button').forEach(
    b => b.setAttribute('aria-pressed', b.dataset.v === diak));

  const m = MODLAR.find(x => x[0] === mod);
  // Ilk yazar sutunu icin kalici uyari
  const diakNot = diak === "katlanmis"
    ? "Turkce isaretler karsilastirmadan once silinir (çğıöşü → cgiosu), "
      + "boylece bozuk PDF fontlari modele hata olarak yazilmaz."
    : "Turkce isaretler oldugu gibi karsilastirilir; bozuk font kodlamasi da hata sayilir.";
  document.getElementById('mod-aciklama').innerHTML =
    (m ? m[2] : "") + ' <span style="opacity:.6">&middot;</span> ' + diakNot;

  const gecerli = KOSULAR.filter(k => k.durum === "gecerli");
  let out = "";

  [["TR","Turkce &mdash; TR Dizin","1435 makale &middot; referans TR+EN, ilk eslesen kabul edilir"],
   ["ING","Ingilizce &mdash; PMC Open Access","519 makale &middot; referans JATS XML"],
   ["KAR","Karantina &mdash; etiketleyicinin eledigi belgeler",
    "1051 makale &middot; diakritik katlanmis &middot; <b>1435&apos;lik testle ayni tabloda "+
    "kiyaslanamaz</b>: bunlar bilerek zor secilmis belgeler. Onemli olan kesinligin "+
    "neredeyse ayni kalmasi (&minus;3 puan), kapsamanin ise dusmesi (&minus;9 ila &minus;17 puan) "+
    "&mdash; model bu belgelerde YANLIS cevap vermiyor, HIC cevap vermiyor."]].forEach(
    ([kod, ad, alt]) => {
      let liste = gecerli.filter(k => k.korpus === kod);
      if(kod === "TR") liste = liste.filter(k => k.diakritik === diak);
      if(!liste.length) return;
      const secili = taban[kod]
        ? liste.find(k => k.etiket === taban[kod]) : null;
      const stok = secili || liste.find(k => k.etiket === "Stok CRF");
      // SIRA listesindeki duzen: stok, sonra eskiden yeniye, en sonda
      // segmentasyonu da degistirilen varyant. Listede olmayan bir kosu
      // sona gider (yeni olcum eklenince gorunur kalsin diye).
      const yer = e => { const i = SIRA.indexOf(e); return i < 0 ? 999 : i; };
      const sira = liste.slice().sort((a,b) => yer(a.etiket) - yer(b.etiket));
      out += '<h2 class="bolum">'+ad+'<span class="rozet">'+liste.length+' kosu</span></h2>'+
             '<div class="bolum-alt">'+alt+
             (stok ? ' &middot; fark sutunlari <b>'+kacis(stok.etiket)+
               '</b> satirina gore &mdash; degistirmek icin bir satira tikla'
               : '')+'</div>'+
             tablo(sira, stok, kod);
    });

  document.getElementById('tablolar').innerHTML = out;

  document.querySelectorAll('tr.satir').forEach(tr => {
    tr.onclick = () => {
      const kod = tr.dataset.kod, et = tr.dataset.etiket;
      taban[kod] = (taban[kod] === et) ? null : et;   // tekrar tiklayinca stok'a don
      ciz();
    };
  });

  const supheli = KOSULAR.filter(k => k.durum !== "gecerli");
  document.getElementById('supheli-sayi').textContent = supheli.length + " olcum";
  let s = "";
  const gorulen = new Set();
  supheli.forEach(k => {
    const anahtar = k.etiket + "|" + k.korpus;
    if(gorulen.has(anahtar)) return;
    gorulen.add(anahtar);
    const gecersiz = k.durum === "gecersiz";
    s += '<div class="uyari'+(gecersiz ? "" : " sari")+'">'+
         '<div class="uyari-baslik '+(gecersiz ? "kirmizi" : "sari")+'">'+
         (gecersiz ? "GECERSIZ" : "KIYASLANAMAZ")+' &mdash; '+kacis(k.etiket)+
         ' ('+({TR:"Turkce", ING:"Ingilizce", KAR:"Karantina"}[k.korpus] || k.korpus)+')</div>'+
         '<b>'+kacis(k.model)+'</b> &middot; GROBID '+k.surum+'<br>'+
         kacis(k.aciklama)+'</div>';
  });
  document.getElementById('supheli').innerHTML = s;
  document.getElementById('damga').textContent =
    "Uretim: " + URETIM + "  |  Kaynak: 05_TRUBA/olcumler/*.txt  |  " +
    "Yeniden uretmek icin: python 03_Test_ve_Degerlendirme/olcum_sayfasi.py";
}

// --- hata nedenleri bolumu (secimden bagimsiz, bir kez cizilir)
const NEDENLER = __NEDENLER__;
const KIM_TR = __KIM_TR__;

document.getElementById('kim-anahtar').innerHTML =
  '<span class="et">Sucun kaynagi:</span>' +
  Object.keys(KIM_TR).map(k =>
    '<span class="kim '+k+'">'+kacis(KIM_TR[k])+'</span>').join('');

document.getElementById('nedenler').innerHTML = NEDENLER.map(x => {
  const toplam = x.nedenler.reduce((a, b) => a + b.n, 0);
  return '<div class="neden-kart">' +
    '<h3>'+kacis(x.ad)+
      (x.alan === "first_author" ? ' <span class="kim model">ölçülemez</span>' : '')+
    '</h3>' +
    '<div class="neden-ozet">'+kacis(x.ozet)+'</div>' +
    '<div class="neden-dog">'+kacis(x.dogrulama)+'</div>' +
    '<ul class="neden-liste">' +
      x.nedenler.map(n =>
        '<li><span class="neden-n">'+n.n+'</span>'+
        '<span class="neden-ad">'+kacis(n.ad)+'</span>'+
        '<span class="kim '+n.kim+'">'+kacis(KIM_TR[n.kim])+'</span></li>').join('') +
    '</ul>' +
    '<div class="neden-not">'+kacis(x.not_)+'</div>' +
  '</div>';
}).join('');

const mv = document.getElementById('mod-secim');
MODLAR.forEach(([k, ad]) => {
  const b = document.createElement('button');
  b.dataset.v = k; b.textContent = ad;
  b.onclick = () => { mod = k; ciz(); };
  mv.appendChild(b);
});
document.querySelectorAll('#metrik-secim button').forEach(
  b => b.onclick = () => { metrik = b.dataset.v; ciz(); });
document.querySelectorAll('#diak-secim button').forEach(
  b => b.onclick = () => { diak = b.dataset.v; ciz(); });

ciz();
</script>
</body>
</html>
"""


def main():
    kosular, uyari = topla()
    print("okunan olcum: %d" % len(kosular))
    for u in uyari:
        print("  UYARI: kayitta yok, atlandi -> %s" % u)

    gecerli = [k for k in kosular if k["durum"] == "gecerli"]
    print("  gecerli: %d   gecersiz/kiyaslanamaz: %d"
          % (len(gecerli), len(kosular) - len(gecerli)))

    sayfa = SAYFA
    sayfa = sayfa.replace("__VERI__", json.dumps(kosular, ensure_ascii=False))
    sayfa = sayfa.replace("__MODLAR__", json.dumps(MODLAR, ensure_ascii=False))
    sayfa = sayfa.replace("__SIRA__", json.dumps(SIRA, ensure_ascii=False))
    sayfa = sayfa.replace("__ALAN_TR__", json.dumps(ALAN_TR, ensure_ascii=False))
    sayfa = sayfa.replace("__ALANLAR__", json.dumps(ALANLAR, ensure_ascii=False))
    # "not" Python'da anahtar kelime degil ama JS'te okunakli olsun diye
    # not_ olarak gonderiyoruz.
    nedenler_js = [dict(x, not_=x["not"]) for x in NEDENLER]
    for x in nedenler_js:
        x.pop("not", None)
    sayfa = sayfa.replace("__NEDENLER__",
                          json.dumps(nedenler_js, ensure_ascii=False))
    sayfa = sayfa.replace("__KIM_TR__", json.dumps(KIM_TR, ensure_ascii=False))
    sayfa = sayfa.replace("__URETIM__",
                          datetime.datetime.now().strftime("%d.%m.%Y %H:%M"))

    os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
    io.open(CIKTI, "w", encoding="utf-8").write(sayfa)
    print("\nyazildi: %s" % CIKTI)


if __name__ == "__main__":
    main()
