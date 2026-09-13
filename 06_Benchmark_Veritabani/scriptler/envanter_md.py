#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""teshis_refined + sablon_parmakizi -> SIKINTI_ENVANTERI.md
   Basliga gore ID listeleri + kisa aciklamalar. 'temiz' listelenmez."""
import os, csv, collections, datetime

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = PROJE_KOK + r""
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
PI = os.path.join(BASE, r"06_Benchmark_Veritabani\parmak_izi\sablon_parmakizi.csv")
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani\SIKINTI_ENVANTERI.md")

T = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
F = {r["makale_id"]: r for r in csv.DictReader(open(PI, encoding="utf-8-sig"))}
ids = sorted(T, key=int)


def idline(id_list):
    id_list = sorted(set(id_list), key=int)
    if not id_list:
        return "_(yok)_"
    return f"**({len(id_list)})** " + " ".join(id_list)


def by_flag(flag):
    return [i for i in ids if flag in (T[i]["FLAGS"] or "").split(";")]


def by(pred):
    return [i for i in ids if pred(T[i], F.get(i, {}))]


ntemiz = len(by_flag("temiz"))

L = []
L += [
    "# Sıkıntılı PDF Envanteri", "",
    f"- Üretim: {datetime.date.today()}  ",
    f"- Kaynak: `03_Test_ve_Degerlendirme/sıkıntılı_pdfler` → `teshis_refined.csv` ({len(ids)} PDF) + `sablon_parmakizi.csv`",
    "- Referans ayrıştırıcı: **stock GROBID 0.9.1-crf** (mount edilen eğitim modeli değil)",
    f"- Bu {len(ids)} PDF'in **{ntemiz}'i** stock GROBID'e karşı sıkıntısız çıktı (başlık+özet+yazar doğru). "
    "Sıkıntısız oldukları için bu envantere **alınmadılar**; ID'leri en alttaki ters indekste "
    "`PRIMARY = temiz` satırlarında görülebilir. (Not: bu grup çoğunlukla eğitimdeki mount modelini "
    "zorluyor ama referans ayrıştırıcı için kolay.)",
    "- **Çakışma var:** bir PDF birden çok başlıkta görünebilir "
    f"({sum(1 for i in ids if len([x for x in T[i]['FLAGS'].split(';') if x])>=2)} PDF ≥2 sıkıntı taşıyor). "
    "Her PDF'in tüm etiketleri için ters indekse bakın.",
    "", "---", "",
]

SECTIONS = [
 ("A. Metin katmanı sıkıntıları",
  "PDF'in kendi içeriğinden kaynaklanan, ayrıştırıcıdan bağımsız sorunlar. Metin daha okunmadan bozuk.",
  [
   ("A1 · Taranmış / resim PDF",
    "Sayfa bir görüntü olarak gömülü; seçilebilir metin katmanı yok (harf oranı ≈ %0). "
    "OCR olmadan hiçbir alan okunamaz, GROBID boş döner.",
    by_flag("taranmis")),
   ("A2 · Bozuk font / ToUnicode yok",
    "Yazı görünüyor ama fontun karakter eşleme tablosu eksik/yanlış. Kopyalanan metin anlamsız "
    "glif dizisi olur; harf oranı %1–45. GROBID metni alır ama içerik çöptür.",
    by_flag("bozuk-font")),
   ("A3 · Karakter anomalisi / mojibake",
    "Metin katmanı var ama içinde beklenmeyen karakterler yoğun: U+FFFD (kayıp glif), PUA kodları, "
    "yön kontrol işaretleri, Latin-1'den bozuk dönmüş harfler (Ã, Å), Türkçe harflerin yanlış kodlanması. "
    "Kısmen okunur ama alan sınırları kayar.",
    by_flag("karakter-anomali")),
  ]),
 ("B. GROBID pipeline sıkıntıları",
  "Metin katmanı yeterli ama dış model (stock GROBID) belgeyi bölütleyemiyor — segmentation/header "
  "adımı yapıyı yanlış çıkarıyor.",
  [
   ("B1 · GROBID header çöküyor",
    "`processHeaderDocument` boş gövde ya da hata döndürüyor — genelde metin katmanı yok (taranmış) "
    "ya da PDF yapısı bozuk. Hiç header çıktısı üretilemiyor.",
    by_flag("grobid-crash")),
   ("B2 · Başlık çıkmıyor",
    "GROBID çalışıyor, özet/anahtar kelimeyi buluyor ama `<title type=main>` boş. Segmentation başlık "
    "satırını 'header' bölgesine sokamamış; başlık gövde ya da not sanılmış.",
    by_flag("header-title-yok")),
   ("B3 · Başlık yerine dergi adı",
    "GROBID sayfa üstündeki dergi künyesini / running-header'ı başlık olarak etiketliyor. Çıktıda "
    "başlık yerine 'Journal of…', '… Arşivi', 'Faculty of…' gibi ifadeler görünüyor.",
    by_flag("baslik-dergi-adi")),
   ("B4 · Gövde çıkmıyor",
    "Fulltext TEI'de `<body>` neredeyse boş (<500 karakter). Segmentation gövde bloğunu bulamamış; "
    "makale metni dağılmış.",
    by_flag("govde-yok")),
  ]),
 ("C. Metadata-diff sıkıntıları",
  "GROBID bir çıktı üretiyor ama TR Dizin altın verisiyle (gold) karşılaştırınca tutmuyor. "
  "Sıkıntı çıktının doğruluğunda.",
  [
   ("C1 · Başlık yanlış",
    "GROBID bir başlık üretiyor ama gold başlıkla benzerlik < 0.72 — yanlış satır alınmış, "
    "ortadan kesilmiş ya da başka metinle karışmış.",
    by_flag("baslik-yanlis")),
   ("C2 · Çift dilli başlık birleşik",
    "Makalenin hem Türkçe hem İngilizce başlığı ard arda basılı; GROBID ikisini tek başlık olarak "
    "birleştirmiş (benzerlik 0.6–0.9).",
    by_flag("baslik-cift-dilli")),
   ("C3 · Düşük benzerlik",
    "Başlık büyük ölçüde doğru ama tam değil (0.72–0.85): fazladan kelime, eksik ek, noktalama/tire farkı.",
    by_flag("dusuk-benzerlik")),
   ("C4 · Özet eksik / kısmi",
    "Özet çıkarılmış ama gold ile benzerlik < 0.45 — ortadan kesilmiş, girişe taşmış ya da "
    "yanlış dildeki özet alınmış.",
    by_flag("ozet-eksik")),
   ("C5 · Özet yok",
    "En az 6 sayfalık (yani özeti olması beklenen) bir makalede GROBID özet bloğunu hiç bulamıyor.",
    by_flag("ozet-yok")),
   ("C6 · Yazarlar eksik / karışık",
    "Gold yazar listesinin yarıdan fazlası çıktıda yok, ya da yazar alanına künye/afiliasyon metni "
    "('Ekim 2018', dergi adı) yerleşmiş.",
    by_flag("yazar-eksik")),
  ]),
 ("D. Mizanpaj / şablon sıkıntıları",
  "Belgenin görsel tasarımı / üretim biçimi kaynaklı. Doğrudan 'hata' olmayabilir ama ayrıştırmayı zorlar "
  "ve benchmark'ta tasarım çeşitliliğini belirler.",
  [
   ("D1 · Şablon taklidi",
    "Sayfa geometrisi ticari yayıncı şablonuna benziyor (dar üst boşluk, ortalı küçük başlık, iki kolon) "
    "ama üretici MS Word ve fontlar jenerik (Times/Arial) — yani lisanslı şablonun taklidi.",
    [i for i in ids if F.get(i, {}).get("sablon_taklit") == "1"]),
   ("D2 · Döndürülmüş sayfa (rotation ≠ 0)",
    "Sayfada `/Rotate ≠ 0` — 90/180/270° döndürülmüş kaydedilmiş; metin çıkarma yönü ve sırası bozulur.",
    by(lambda t, f: t.get("rotation") not in ("0", "", None))),
   ("D3 · Landscape ilk sayfa",
    "İlk sayfa yatay (genişlik > yükseklik) — genelde geniş tablo/şekil sayfası makalenin önüne düşmüş.",
    by(lambda t, f: t.get("landscape") == "1")),
   ("D4 · Çok kolonlu düzen (2 kolon)",
    "İlk sayfa iki kolonlu. Başlık/yazar bloğu tek kolon, gövde çift kolon olduğunda segmentation "
    "zorlanır; kolon kırılması reading-order'ı bozabilir.",
    by(lambda t, f: t.get("kolon") == "2")),
   ("D5 · Üretici: LaTeX",
    "PDF `pdfTeX/XeTeX/LuaTeX` ile üretilmiş. Genelde temiz metin akışı ama matematik/ligatür ve "
    "özel karakter gömme sorunları buradan çıkar.",
    [i for i in ids if F.get(i, {}).get("meta_class") == "latex"]),
   ("D6 · Üretici: InDesign / FrameMaker / Arbortext",
    "Profesyonel dizgi yazılımı. Karmaşık kutu yapısı; metin görsel sırayla içerik akışı sırası "
    "uyuşmayabilir.",
    [i for i in ids if F.get(i, {}).get("meta_class") == "indesign"]),
   ("D7 · Üretici: MS Word / WPS",
    "Ofis yazılımı çıktısı. DergiPark varsayılan şablonları çoğunlukla buradan; farklı dergiler "
    "aynı Word şablonunu paylaşabilir.",
    [i for i in ids if F.get(i, {}).get("meta_class") == "word"]),
   ("D8 · Üretici metası boş",
    "Producer/Creator alanı hiç yazılmamış — çoğu taranmış ya da elde birleştirilmiş/yeniden basılmış PDF.",
    [i for i in ids if F.get(i, {}).get("meta_class") == "bos"]),
   ("D9 · Metinsiz ilk sayfa",
    "İlk sayfada 5'ten az metin satırı — kapak, iç kapak, künye ya da tam sayfa görsel. GROBID ilk "
    "2 sayfaya baktığı için başlık/yazarı hiç göremeyebilir.",
    [i for i in ids if F.get(i, {}).get("metinsiz") == "1"]),
  ]),
 ("E. İçerik-tipi kaynaklı",
  "Dosya teknik olarak sağlam ama belge türü / dili 'standart makale' varsayan modelleri zorlar.",
  [
   ("E1 · Çok kısa belge (≤4 sayfa)",
    "Olgu sunumu, editöre mektup, kitap tanıtımı, kısa bildiri. Çoğunda IMRaD yapısı ve bazen özet yok.",
    by(lambda t, f: t["pages"].isdigit() and int(t["pages"]) <= 4)),
   ("E2 · Çok uzun derleme (≥30 sayfa)",
    "Geniş derleme / çok bölümlü çalışma. Uzun referans listesi ve çok sayıda iç başlık segmentation'ı zorlar.",
    by(lambda t, f: t["pages"].isdigit() and int(t["pages"]) >= 30)),
   ("E3 · Saf İngilizce metin",
    "Türk dergisinde İngilizce yayımlanmış makale. Bu havuzda oran yüksek çünkü sıkıntılı örnekler "
    "çoğunlukla İngilizce dergilerden toplanmış.",
    by(lambda t, f: t["dil"] == "en")),
   ("E4 · Karışık dil (TR+EN gövde)",
    "Türkçe ve İngilizce bölümler paralel/iç içe (çift özet, çift başlık, iki dilli tam metin).",
    by(lambda t, f: t["dil"] == "mix")),
   ("E5 · Saf Türkçe metin",
    "Gövde ağırlıklı Türkçe — hedef dil profili.",
    by(lambda t, f: t["dil"] == "tr")),
  ]),
]

for stitle, sdesc, subs in SECTIONS:
    L.append(f"## {stitle}")
    L.append("")
    L.append(f"_{sdesc}_")
    L.append("")
    for sub, desc, lst in subs:
        L.append(f"### {sub}")
        L.append("")
        L.append(desc)
        L.append("")
        L.append(idline(lst))
        L.append("")
    L.append("---")
    L.append("")

# ---- ters indeks ----
L.append("## Ters indeks — her PDF'in tüm etiketleri")
L.append("")
L.append("`PRIMARY` = baskın sıkıntı · `FLAGS` = tüm sıkıntılar · `temiz` satırları envantere alınmadı.")
L.append("")
L.append("| makale_id | PRIMARY | TIER | FLAGS | sf | dil | yıl | meta | küme | dergi |")
L.append("|---|---|---|---|---|---|---|---|---|---|")
for i in ids:
    t = T[i]; f = F.get(i, {})
    L.append(f"| {i} | {t['PRIMARY']} | {t['TIER']} | {t['FLAGS']} | {t['pages']} | {t['dil']} | "
             f"{t['year']} | {f.get('meta_class','')} | {f.get('cluster','')} | "
             f"{(t.get('gold_journal') or t.get('journal_dir') or '')[:40]} |")
L.append("")

fc = collections.Counter()
for i in ids:
    for x in (T[i]["FLAGS"] or "").split(";"):
        if x:
            fc[x] += 1
L.append("## Sayısal özet (FLAG frekansı)")
L.append("")
for k, v in fc.most_common():
    L.append(f"- `{k}` — {v}")
nfl = collections.Counter(len([x for x in (T[i]["FLAGS"] or "").split(";") if x]) for i in ids)
L.append("")
L.append("Flag sayısı dağılımı: " + " · ".join(f"{k} flag: {v}" for k, v in sorted(nfl.items())))
L.append("")

open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("->", OUT, f"({len(ids)} PDF)")
