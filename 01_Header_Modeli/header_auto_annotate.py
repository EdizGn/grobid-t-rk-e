# -*- coding: utf-8 -*-
"""
Header egitim korpusunu otomatik etiketler.

Girdi : grobid-trainer/resources/dataset/header/corpus/{tei,raw}
Cikti : --out klasoru altinda  altin/  (egitime hazir)  +  karantina/  (guvenilmez)
        + rapor.csv

Onemli: TEI metnine DOKUNULMAZ. Sadece etiket eklenir; boylece raw feature
dosyasindaki token dizisiyle hizalama bozulmaz.
"""
import os, re, csv, glob, html, argparse, difflib, sqlite3
from db_span import (canvas_tokens, hedef_tokens, find_span, find_span_detay,
                     tok_index, norm_kelime)

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- eski PDF font bozulmalari -------------------------------------------
FIX = {"\u203a": "\u0131", "\ufb02": "\u015f", "\ufb01": "\u015e", "\u00a4": "\u011f",
       "\u2039": "\u0130", "\u00dd": "\u0130", "\u00fd": "\u0131", "\u00de": "\u015e",
       "\u00fe": "\u015f", "\u00d0": "\u011e", "\u00f0": "\u011f", "\u0120": "\u0130",
       "\u0121": "\u015f",
       # U+2044 kesir cizgisi, bazi fontlarda "g" yerine: KARINCAO\u2044LU
       "\u2044": "\u011f"}


def defix(s):
    for a, b in FIX.items():
        s = s.replace(a, b)
    return s


def low(s):
    return defix(s).replace("I", "\u0131").replace("\u0130", "i").lower()


KURUM = re.compile(r'[u\u00fc]niversite|fak[u\u00fc]lte|anabilim|b[o\u00f6]l[u\u00fc]m|'
                   r'y[u\u00fc]ksekokul|hastane|enstit[u\u00fc]|dekanl', re.I)
# Kunye / yayin bilgisi satirlari -- basliga karismamali.
# OLCUM: eski desen "published by", "(c)", "original article", "vol." gibi
# kaliplari yakalamiyordu; 2999 dosyanin 81'inde (%2.7) kunye satiri
# <docTitle> olarak etiketlenmis, model de ciktida bunu uretmisti
# (or. "CILT VOL. 15 -SAYI NO. 3", "Published by Galenos Publishing House").
KUNYE = re.compile(r'dergi|journal|b[u\u00fc]lten|cilt|say[\u0131i]\s*[:.]?\s*\d|'
                   r'volume|number|issn|vol\.|no\.\s*\d|'
                   r'published\s+by|publishing|press|\u00a9|copyright|'
                   r'original\s+article|research\s+article|review\s+article|'
                   r'letter\s+to\s+editor|case\s+report|'
                   r'[o\u00f6]zg[u\u00fc]n\s+ara[s\u015f]t[i\u0131]rma|'
                   r'ara[s\u015f]t[i\u0131]rma\s+makalesi|olgu\s+sunumu|'
                   r'edit[o\u00f6]re\s+mektup|mecmuas[i\u0131]', re.I)
# "OZET:" / "OZ" / "Ozet" -- iki nokta zorunlu degil, ama kelime sinirinda olmali
OZ_BAS = re.compile(r'(?:^|<lb/>|\s)(?:\u00d6ZET|\u00d6Z|\u00d6zet|\u00d6z)'
                    r'\s*[:\uff1a]?\s*(?![a-z\u00e7\u011f\u0131\u00f6\u015f\u00fc])')
ABS_BAS = re.compile(r'\b(?:ABSTRACT|Abstract)\b\s*[:\uff1a]?')
KW_TR = re.compile(r'Anahtar\s*(?:Kelimeler|kelimeler|S[o\u00f6]zc[u\u00fc]kler|'
                   r's[o\u00f6]zc[u\u00fc]kler)\s*[:\uff1a]?', re.I)
KW_EN = re.compile(r'\bKey\s*[Ww]ords?\b\s*[:\uff1a]?', re.I)
DOI_RE = re.compile(r'10\.\d{4,9}/[^\s<]+')
TARIH = re.compile(r'(Geli[\u015fs]\s*[Tt]arihi|Kabul\s*[Tt]arihi|Received|Accepted)'
                   r'\s*[:\uff1a]?\s*([0-9]{1,2}[./ ][A-Za-z\u00c7\u011e\u0130\u00d6\u015e\u00dc'
                   r'\u00e7\u011f\u0131\u00f6\u015f\u00fc0-9]+[./ ][0-9]{2,4})')
UNVAN = re.compile(r'\b(Dr|Prof|Do[\u00e7c]|Ar[\u015fs]|G[o\u00f6]r|Uzm|Yrd)\b\.?', re.I)

# Yazar etiketine ASLA girmemesi gereken satirlar.
#
# OLCUM (v4 korpusu, 2153 belge): yazar etiketlerinin %20.3'u hatali ve
# hatalarin buyuk kismi asagidaki dort desenden geliyordu --
#   yazisma adresi 31, e-posta/ORCID 31, "Key words/Abstract" 32,
#   dergi kunyesi / atif sekli 30, kurum 22 belge.
# Bunlar modele "yazar budur" diye ogretiliyordu; ayni belgelerde gercek
# yazar satiri etiketsiz kaldigi icin "yazar degildir" diye ogretiliyordu.
# Basliktaki celiskinin aynisi: etiketsiz token = acik olumsuz ornek.
YAZAR_YASAK = re.compile(
    r'yaz[\u0131i][\u015fs]ma|sorumlu\s+yazar|correspond|address\s+for|'
    r'@|orcid|'
    r'key\s*words?|anahtar\s*(kelime|s[o\u00f6]zc)|abstract|\u00f6zet\b|'
    r'at[\u0131i]f\s*[\u015fs]ekli|how\s+to\s+cite|cite\s+this|'
    r'bulletin|dergisi|journal|\bvol\.|\bcilt\b|'
    r'creative\s+commons|attribution|licen[cs]e',
    re.I)

# Sezgisel yolda kullanilan DAR liste: bir yazar satirinda asla bulunmayacak
# desenler. Genis YAZAR_YASAK listesi yalnizca DB eslesmesi olan yerlerde
# (yazar_kirp) kullanilir; orada "isim varsa satiri koru" kurali isliyor.
YAZAR_KESIN_YASAK = re.compile(
    r'yaz[ıi][şs]ma|sorumlu\s+yazar|correspond|address\s+for|'
    r'@|orcid|at[ıi]f\s*[şs]ekli|how\s+to\s+cite|cite\s+this|'
    r'creative\s+commons|licen[cs]e', re.I)

FRONT_RE = re.compile(r'(<front>)(.*?)(</front>)', re.S)
TAG_RE = re.compile(r'<(?!lb\b)[^>]*>')


def read_front(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    m = FRONT_RE.search(s)
    if not m:
        return None, None
    return s, m


def strip_tags(front):
    """Var olan etiketleri sok, <lb/> kalsin. Metin birebir korunur."""
    return TAG_RE.sub("", front)


TOK_RE = re.compile(r'<lb/>|[^\s<]+')


def tokenize(canvas):
    """(token, start, end) listesi; <lb/> atlanir."""
    out = []
    for m in TOK_RE.finditer(canvas):
        t = m.group(0)
        if t == "<lb/>":
            continue
        out.append((html.unescape(t), m.start(), m.end()))
    return out


def line_spans(canvas):
    """<lb/> ile ayrilan satirlarin (start, end) araliklari."""
    marks = [m.start() for m in re.finditer(r'<lb/>', canvas)]
    bounds, prev = [], 0
    for p in marks:
        bounds.append((prev, p))
        prev = p + 5
    bounds.append((prev, len(canvas)))
    return [(a, b) for a, b in bounds if canvas[a:b].strip()]


def read_raw(path):
    toks, feats = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) < 12:
            continue
        toks.append(p[0])
        feats.append(p)
    return toks, feats


FONT_DELTA = {"HIGHERFONT": 1, "LOWERFONT": -1, "SAMEFONTSIZE": 0}


def font_series(feats):
    """Her token icin kumulatif (goreli) font buyuklugu."""
    cur, out = 0, []
    for f in feats:
        for c in f:
            if c in FONT_DELTA:
                cur += FONT_DELTA[c]
                break
        out.append(cur)
    return out


def align(canvas_toks, raw_toks):
    """canvas token index -> raw token index."""
    a = [low(t) for t, _, _ in canvas_toks]
    b = [low(t) for t in raw_toks]
    mp = {}
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for x, y, n in sm.get_matching_blocks():
        for i in range(n):
            mp[x + i] = y + i
    return mp


def is_author_line(seg):
    """Yazar satiri mi? Ayirt edici sinyal: unvan, ya da ayni satirda
    BUYUK harfli soyad + Ilk harfi buyuk ad birlikte gecmesi.
    (Tamami buyuk harfli basliklarda Titlecase token bulunmaz.)"""
    d = defix(seg)
    # Sezgisel yolda DB erisimi yok; burada yalnizca yazar ISMI icermesi
    # mumkun olmayan kesin desenleri eliyoruz. "Ozet/Abstract/Key words"
    # gibi basliklar YAZAR_YASAK'ta var ama burada KULLANILMIYOR, cunku
    # Turkce makalelerde yazar satiri sik sik "... SONMEZ* Ozet" seklinde
    # ozet basligiyla ayni satirda bitiyor.
    if (KURUM.search(d) or KUNYE.search(low(d))
            or YAZAR_KESIN_YASAK.search(d)):
        return False
    w = [t.strip(",.;:*()[]") for t in d.split()]
    w = [t for t in w if t]
    if not (2 <= len(w) <= 18):
        return False
    if UNVAN.search(d):
        return True
    buyuk = [t for t in w if len(t) >= 3 and t.isupper()]
    titlec = [t for t in w if len(t) >= 3 and t[0].isupper() and not t.isupper()]
    return bool(buyuk and titlec)


def find_title(canvas, stop):
    """Baslik = kunye satirlarindan sonra, yazar/ozet blogundan once kalan satirlar.
    Font ozelligi kullanilmaz: GROBID'in HIGHERFONT/LOWERFONT bayraklari
    goreli oldugu icin kumulatif toplam surukleniyor ve mutlak punto vermiyor."""
    bas, son = None, None
    for a, b in line_spans(canvas):
        if a >= stop:
            break
        seg = canvas[a:b]
        # kunye, sayfa no, tarih, DOI satirlarini basliga dahil etme
        if (KUNYE.search(low(seg)) or DOI_RE.search(seg) or TARIH.search(seg)
                or not re.search(r'[A-Za-zÇĞİÖŞÜ'
                                 r'çğıöşü]{3}', seg)):
            bas, son = None, None      # kunyeden sonra bastan basla
            continue
        if bas is None:
            bas = a
        son = b
    if bas is None or son is None:
        return None
    if len(canvas[bas:son].split()) < 3:
        return None
    return (bas, son)


def span_between(canvas, start_re, end_res, search_from=0):
    m = start_re.search(canvas, search_from)
    if not m:
        return None
    s = m.end()
    ends = [r.search(canvas, s) for r in end_res]
    ends = [e.start() for e in ends if e]
    e = min(ends) if ends else len(canvas)
    if e - s < 40:
        return None
    return (s, e)


def line_span_after(canvas, marker_re, search_from=0):
    """Marker'dan satir sonuna kadar; satir cok kisaysa bir sonrakini de al."""
    m = marker_re.search(canvas, search_from)
    if not m:
        return None
    s = m.end()
    nxt = canvas.find("<lb/>", s)
    e = nxt if nxt != -1 else len(canvas)
    tail = canvas.find("<lb/>", e + 5)
    if e - s < 15 and tail != -1:
        e = tail
    return (s, e) if e > s + 3 else None



def yazar_kirp(canvas, ct, span, idx):
    """Yazar span'ini SADECE gercekten isim gecen satirlara daralt.

    find_span ilk eslesmeden son eslesmeye kadar her seyi kapsiyor; arada
    kurum/adres satiri varsa o da yazar etiketine giriyordu. Burada:
      - hic eslesme icermeyen bas/son satirlar atilir,
      - ortada eslesmesi olmayan bir KURUM satiri varsa span orada kesilir.
    """
    s, e = span
    eslesen_karakter = [(ct[i][1], ct[i][2]) for i in idx]
    if not eslesen_karakter:
        return None
    satirlar = [(a, b) for a, b in line_spans(canvas) if b > s and a < e]
    if not satirlar:
        return span

    def isimli(a, b):
        return any(a <= ks < b for ks, _ in eslesen_karakter)

    # YASAKLI satirlar bastan elenir: yazisma adresi, e-posta/ORCID,
    # "Key words/Abstract", dergi kunyesi, lisans metni. Bunlar isim
    # icerse bile (ornegin "Yazismalarin yapilacagi yazar: Nilay GULMEZ")
    # yazar blogu degildir; etikete girerse model kunye satirini yazar
    # sanmayi ogreniyor.
    #
    # DIKKAT: satiri yalnizca yasakli desen varsa DEGIL, ayrica o satirda
    # hicbir DB ismi eslesmiyorsa atiyoruz. Cunku Turkce makalelerde yazar
    # satiri cok sik ozet basligiyla ayni satirda bitiyor:
    #     "Cahide SINMAZ SONMEZ* Ozet"
    #     "Ugur AKPUR 2  Seval FER 3 Oz"
    # Kosulsuz elemek bu satirlari da yok ediyordu (olculdu: altin 1827 -> 1310).
    satirlar = [(a, b) for a, b in satirlar
                if isimli(a, b) or not YAZAR_YASAK.search(canvas[a:b])]
    if not satirlar:
        return None

    # eslesme iceren ilk ve son satir
    dolu = [i for i, (a, b) in enumerate(satirlar) if isimli(a, b)]
    if not dolu:
        return None
    ilk, son = dolu[0], dolu[-1]
    # aradaki eslesmesiz KURUM satirinda kes
    for i in range(ilk, son + 1):
        a, b = satirlar[i]
        if not isimli(a, b) and KURUM.search(canvas[a:b]):
            son = i - 1
            break
    if son < ilk:
        return None
    yeni_s = max(s, satirlar[ilk][0])
    yeni_e = min(e, satirlar[son][1])
    return (yeni_s, yeni_e) if yeni_e > yeni_s else None


def collect_db(canvas, meta):
    """Altin metadata ile span bulur. Bulunamayan alan icin None birakir;
    cagiran taraf o alani heuristic ile doldurur."""
    ct = canvas_tokens(canvas)
    if len(ct) < 5:
        return {}
    bul = {}

    def ara(alan, deger, lo=0, hi=None, kaps=0.45):
        sp = find_span(ct, hedef_tokens(deger), lo, hi, kaps)
        if sp:
            bul[alan] = sp
        return sp

    # 1) Ozetler: en guvenilir capa (uzun ve ayirt edici metin)
    ab_tr = ara("abstract_tr", meta.get("ozet"), kaps=0.40)
    ab_en = ara("abstract_en", meta.get("ozet_en"), kaps=0.40)

    ust = min([x[0] for x in (ab_tr, ab_en) if x] or [len(canvas)])
    ust_i = tok_index(ct, ust)

    # 2) Baslik: ozet blogundan once ara (ozet icinde tekrar edebilir)
    # Basligi SADECE Turkce DB degeriyle ara.
    # OLCUM: Ingilizce basliga dusme yedegi, iki dilli makalelerde 2999
    # dosyanin 392'sinde (%13.1) Ingilizce blogu <docTitle> olarak
    # etiketletmisti; model de ciktida Turkce yerine Ingilizce basligi
    # veriyordu. Yari yanlis etiket, etiketsizden kotudur -- bulunamazsa
    # bos birakiyoruz, heuristic devrede kalir.
    ara("title", meta.get("baslik"), 0, ust_i, 0.55)

    # 2b) Ingilizce baslik da <docTitle>.
    # OLCUM (v3 korpusu): Ingilizce basligi kapakta bulunan 1847 belgenin
    # 1825'inde (%98.8) bu blok ETIKETSIZ birakilmisti. CRF'te etiketsiz
    # token = acik olumsuz ornek; yani modele 1825 kez "bu Ingilizce satir
    # baslik DEGILDIR" diye ogretmisiz. Sonuc: egitilmis model 519 Ingilizce
    # makalenin %53.8'inde hic baslik uretmiyor (stok modelde %1.9).
    # Ozet alaninda TR+EN'i birlikte etiketliyorduk ve tek stoktan iyi alan
    # o oldu -- ayni seyi basliga da uyguluyoruz.
    #
    # Arama TUM canvas'ta yapilir: Ingilizce baslik cogu makalede Turkce
    # ozetten SONRA gelir, bu yuzden ust_i siniri kullanilamaz. Ozet veya
    # Turkce baslik span'iyla cakisirsa etiket dusurulur (kirpilmis yarim
    # baslik, etiketsizden kotudur).
    b_en = (meta.get("baslik_en") or "").strip()
    if b_en and len(b_en.split()) >= 4:
        sp_en = find_span(ct, hedef_tokens(b_en), 0, None, 0.60)
        if sp_en:
            def cakisir(o):
                return bool(o) and not (sp_en[1] <= o[0] or sp_en[0] >= o[1])
            if not (cakisir(ab_tr) or cakisir(ab_en) or cakisir(bul.get("title"))):
                bul["title_en"] = sp_en

    # 3) Yazarlar: baslik ile ozet arasi.
    # Esik 0.35 -> 0.60 ve yogunluk 0.34 -> 0.50: gevsek eslesmede span, ilk
    # isimden uzaktaki rastlantisal bir eslesmeye kadar uzayip aradaki kurum
    # satirlarini yutuyordu. CRF tutarsiz sinirdan ogrenemiyor.
    t_i = tok_index(ct, bul["title"][1]) if "title" in bul else 0
    ysp, yidx = find_span_detay(ct, hedef_tokens(meta.get("yazarlar")),
                                t_i, ust_i, 0.60, 0.50)
    if ysp:
        ysp = yazar_kirp(canvas, ct, ysp, yidx)
    if ysp:
        bul["author"] = ysp

    # 4) Anahtar kelimeler: ozetten sonra
    if ab_tr:
        ara("keyword_tr", meta.get("kelime"), tok_index(ct, ab_tr[1]), None, 0.45)
    if ab_en:
        ara("keyword_en", meta.get("kelime_en"), tok_index(ct, ab_en[1]), None, 0.45)

    # 5) Dergi kunyesi -> <reference>
    ara("reference", meta.get("dergi"), 0, ust_i, 0.55)

    # 6) DOI ve yil: regex, ama DB degeriyle dogrulanarak
    doi = (meta.get("doi") or "").strip()
    if doi:
        m = re.search(re.escape(doi.split("/")[-1]), canvas)
        if m:
            b = canvas.rfind("10.", 0, m.start())
            bul["doi"] = (b if b != -1 else m.start(), m.end())
    yil = str(meta.get("yil") or "").strip()
    if re.fullmatch(r'(19|20)\d{2}', yil):
        m = re.search(r'' + yil + r'', canvas)
        if m:
            bul["date"] = (m.start(), m.end())
    return bul


def collect(canvas, toks, mp, fonts, dergi_hint):
    """[(start, end, open_tag, close_tag, alan_adi)]"""
    sp = []

    def add(span, o, c, name):
        if span and span[1] > span[0]:
            sp.append((span[0], span[1], o, c, name))

    lines = line_spans(canvas)

    # 1) Once ozet/anahtar kelime capalarini bul: baslik bolgesinin ust siniri
    def ilk(rx):
        m = rx.search(canvas)
        return m.start() if m else len(canvas)
    sinir = min(ilk(OZ_BAS), ilk(ABS_BAS), ilk(KW_TR), ilk(KW_EN))

    def run(test, devam, basla=0, bitis=None):
        """Ardisik eslesen satirlari tek blok halinde dondur (cok satirli
        yazar listeleri ve kurum adresleri icin)."""
        bas = son = None
        ust = sinir if bitis is None else bitis
        for a, b in lines:
            if a >= ust:
                break
            if a < basla:
                continue
            seg = canvas[a:b]
            if test(seg):
                if bas is None:
                    bas = a
                son = b
            elif bas is not None:
                if devam(seg):
                    son = b
                    continue
                break
        return (bas, son) if bas is not None else None

    # 2) Yazar blogu: capadan once, kurum olmayan, isim gorunumlu ardisik satirlar
    yazar = run(is_author_line,
                lambda s: bool(UNVAN.search(s)) or
                (s.strip().startswith(",") and not KURUM.search(s)))

    # 3) Kurum blogu
    kurum = run(lambda s: bool(KURUM.search(s)),
                lambda s: len(s.split()) <= 8 and not OZ_BAS.search(s)
                and not is_author_line(s),
                basla=yazar[1] if yazar else 0, bitis=len(canvas))

    # 4) Baslik: kunyeden sonra, yazar/kurum/ozet capasindan once kalan blok
    ust = min([sinir] + [x[0] for x in (yazar, kurum) if x])
    title = find_title(canvas, ust)
    add(title, "<docTitle><titlePart>", "</titlePart></docTitle>", "title")
    tend = title[1] if title else 0

    add(yazar, "<byline><docAuthor>", "</docAuthor></byline>", "author")
    add(kurum, "<byline><affiliation>", "</affiliation></byline>", "affiliation")

    # 5) Kunye satiri -> <reference> (dergi adi + cilt/sayi + yil buradan cikar)
    for a, b in lines:
        if title and a >= title[0]:
            break
        seg = canvas[a:b]
        if KUNYE.search(low(seg)) or (dergi_hint and dergi_hint[:20] in low(seg)):
            add((a, b), "<reference>", "</reference>", "reference")
            break

    # ozet TR : OZ/OZET -> Anahtar Kelimeler | Abstract   (TAM span, kesilmez)
    body_start = max([tend] + [s[1] for s in sp if s[4] in ("author", "affiliation")])
    tr = span_between(canvas, OZ_BAS, [KW_TR, ABS_BAS], tend)
    if not tr:
        # Capa yok: kunye/yazar bloguyla "Anahtar Kelimeler" arasini ozet say.
        kw = KW_TR.search(canvas, body_start)
        if kw:
            s, e = body_start, kw.start()
            ab = ABS_BAS.search(canvas, s)
            if ab and ab.start() < e:
                e = ab.start()          # Ingilizce ozeti yutma
            # Bastaki kurum / DOI / tarih / kunye satirlarini ozete dahil etme
            for la, lb in line_spans(canvas):
                if lb <= s or la >= e:
                    continue
                seg = canvas[la:lb]
                if (KURUM.search(seg) or DOI_RE.search(seg)
                        or TARIH.search(seg) or KUNYE.search(low(seg))):
                    s = min(lb + 5, e)
                else:
                    break
            if e - s >= 120:
                tr = (s, e)
    add(tr, '<div type="abstract">', "</div>", "abstract_tr")

    # ozet EN
    en = span_between(canvas, ABS_BAS, [KW_EN, KW_TR], tr[1] if tr else tend)
    add(en, '<div type="abstract">', "</div>", "abstract_en")

    # anahtar kelimeler
    add(line_span_after(canvas, KW_TR, tend), "<keyword>", "</keyword>", "keyword_tr")
    add(line_span_after(canvas, KW_EN, tend), "<keyword>", "</keyword>", "keyword_en")

    m = DOI_RE.search(canvas)
    if m:
        add((m.start(), m.end()), "<idno>", "</idno>", "doi")

    for m in TARIH.finditer(canvas):
        add((m.start(2), m.end(2)), "<date>", "</date>", "date")
        break
    return sp


# Cakisma halinde once gelen kazanir; sonraki DUSMEZ, kirpilir.
TAGS = {
    "title":       ("<docTitle><titlePart>", "</titlePart></docTitle>"),
    "title_en":    ("<docTitle><titlePart>", "</titlePart></docTitle>"),
    "author":      ("<byline><docAuthor>", "</docAuthor></byline>"),
    "affiliation": ("<byline><affiliation>", "</affiliation></byline>"),
    "abstract_tr": ('<div type="abstract">', "</div>"),
    "abstract_en": ('<div type="abstract">', "</div>"),
    "keyword_tr":  ("<keyword>", "</keyword>"),
    "keyword_en":  ("<keyword>", "</keyword>"),
    "reference":   ("<reference>", "</reference>"),
    "doi":         ("<idno>", "</idno>"),
    "date":        ("<date>", "</date>"),
}

ONCELIK = ["doi", "date", "title", "title_en", "abstract_tr", "abstract_en",
           "keyword_tr", "keyword_en", "author", "affiliation", "reference"]
MIN_UZUNLUK = {"title": 12, "title_en": 12, "abstract_tr": 100, "abstract_en": 100,
               "keyword_tr": 6, "keyword_en": 6, "author": 6,
               "affiliation": 8, "reference": 8, "doi": 6, "date": 4}


def resolve(spans):
    """Yuksek oncelikli span'i koru, dusuk oncelikliyi uzerine binen kisimdan kirp."""
    spans.sort(key=lambda x: ONCELIK.index(x[4]) if x[4] in ONCELIK else 99)
    dolu, out = [], []
    for s, e, o, c, name in spans:
        parcalar = [(s, e)]
        for ds, de in dolu:
            yeni = []
            for ps, pe in parcalar:
                if pe <= ds or ps >= de:
                    yeni.append((ps, pe))
                    continue
                if ps < ds:
                    yeni.append((ps, ds))
                if pe > de:
                    yeni.append((de, pe))
            parcalar = yeni
        if not parcalar:
            continue
        ps, pe = max(parcalar, key=lambda p: p[1] - p[0])
        if pe - ps < MIN_UZUNLUK.get(name, 4):
            continue
        dolu.append((ps, pe))
        out.append((ps, pe, o, c, name))
    out.sort(key=lambda x: x[0])
    return out


def snap(canvas, i):
    """i konumu bir <lb/> etiketinin ortasina denk geliyorsa disina tasi."""
    for m in re.finditer(r'<lb/>', canvas):
        if m.start() < i < m.end():
            return m.end()
    return i


def apply_spans(canvas, spans):
    out, prev = [], 0
    for s, e, o, c, _ in spans:
        out.append(canvas[prev:s])
        out.append(o)
        out.append(canvas[s:e])
        out.append(c)
        prev = e
    out.append(canvas[prev:])
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    base = PROJE_KOK + r"\grobid\grobid-trainer\resources\dataset\header\corpus"
    ap.add_argument("--corpus", default=base)
    ap.add_argument("--out", default=PROJE_KOK + r"\01_Header_Modeli\otomatik_etiketli")
    ap.add_argument("--db", default=PROJE_KOK + r"\02_Segmentation_Modeli\makaleler_segmentation\segmentation_metadatalar.db")
    ap.add_argument("--yazar-zorunlu-degil", dest="yazar_serbest",
                    action="store_true",
                    help="Yazar etiketi bulunamayan belgeyi de altina al "
                         "(v3 davranisi). Varsayilan: karantinaya at.")
    ap.add_argument("--altin-db", dest="altin_db",
                    default=PROJE_KOK + r"\01_Header_Modeli\header_metadatalar.db")
    a = ap.parse_args()

    dergi = {}
    try:
        for i, d in sqlite3.connect(a.db).execute("select id, dergi from segmentation_metadatalar"):
            if d:
                dergi[str(i)] = low(d)
    except Exception:
        pass

    meta = {}
    try:
        alanlar = ("baslik", "ozet", "yazarlar", "kelime", "yil", "dergi", "doi",
                   "baslik_en", "ozet_en", "kelime_en")
        for r in sqlite3.connect(a.altin_db).execute(
                "select id, gercek_baslik, gercek_ozet, gercek_yazarlar, "
                "gercek_anahtar_kelimeler, gercek_yil, gercek_dergi, gercek_doi, "
                "gercek_baslik_en, gercek_ozet_en, gercek_anahtar_kelimeler_en "
                "from orijinal_metadatalar"):
            meta[str(r[0])] = dict(zip(alanlar, r[1:]))
        print("altin metadata yuklendi: %d makale" % len(meta))
    except Exception as e:
        print("UYARI: altin metadata okunamadi (%s) -- sadece heuristic" % e)

    altin = os.path.join(a.out, "altin")
    kar = os.path.join(a.out, "karantina")
    os.makedirs(altin, exist_ok=True)
    os.makedirs(kar, exist_ok=True)

    yazar_zorunlu = not a.yazar_serbest
    yazarsiz = 0
    yazar_yanlis = 0
    rows, stat, bozuk, dusen, kaynak = [], {}, [], {}, {}
    for tei in sorted(glob.glob(os.path.join(a.corpus, "tei", "*.xml"))):
        name = os.path.basename(tei)
        mid = name.split(".")[0].replace("makale_", "")
        rawp = os.path.join(a.corpus, "raw", name.replace(".tei.xml", ""))
        full, m = read_front(tei)
        if not full:
            continue
        canvas = strip_tags(m.group(2))
        toks = tokenize(canvas)
        rtoks, feats = read_raw(rawp) if os.path.exists(rawp) else ([], [])
        mp = align(toks, rtoks) if rtoks else {}
        fonts = font_series(feats) if feats else []

        # Once altin metadata ile span ara; bulunamayan alanlari heuristic doldurur.
        ham_h = collect(canvas, toks, mp, fonts, dergi.get(mid))
        db_sp = collect_db(canvas, meta[mid]) if mid in meta else {}
        birlesik = {}
        for x, y, o, c, nm in ham_h:
            birlesik.setdefault(nm, (x, y, o, c, "H"))
        for nm, (x, y) in db_sp.items():
            birlesik[nm] = (x, y, TAGS[nm][0], TAGS[nm][1], "DB")

        # Heuristic'in buldugu baslik DIL KONTROLU.
        # find_title dil bilmez; iki dilli makalelerde Ingilizce blogu
        # secebiliyor. DB'de her iki baslik da varsa span'in hangisine daha
        # cok benzedigine bakariz.
        # v3'te Ingilizce cikinca etiket DUSURULUYORDU; v4'te dusurmuyoruz,
        # title_en'e tasiyoruz -- blok gercekten bir basliktir, sadece obur
        # dildedir. Dusurmek modele "bu baslik degil" diye ogretiyordu.
        if birlesik.get("title", (0, 0, 0, 0, ""))[4] == "H" and mid in meta:
            mtr = meta[mid].get("baslik") or ""
            men = meta[mid].get("baslik_en") or ""
            if mtr and men:
                x, y = birlesik["title"][0], birlesik["title"][1]
                sp_kel = set(low(TAG_RE.sub(" ", canvas[x:y])).split())
                if sp_kel:
                    tr_ort = len(sp_kel & set(low(mtr).split()))
                    en_ort = len(sp_kel & set(low(men).split()))
                    if en_ort > tr_ort:
                        tasinan = birlesik.pop("title")
                        if "title_en" not in birlesik:
                            birlesik["title_en"] = (
                                tasinan[0], tasinan[1],
                                TAGS["title_en"][0], TAGS["title_en"][1], "H")
        for v in birlesik.values():
            kaynak[v[4]] = kaynak.get(v[4], 0) + 1
        ham = [(v[0], v[1], v[2], v[3], nm) for nm, v in birlesik.items()]
        spans = resolve(ham)
        spans = [(snap(canvas, x), snap(canvas, y), o, c, nm) for x, y, o, c, nm in spans]
        found = {s[4] for s in spans}
        for nm in {x[4] for x in ham} - found:
            dusen[nm] = dusen.get(nm, 0) + 1
        for f in found:
            stat[f] = stat.get(f, 0) + 1

        # Karantina olcutu.
        # v3: baslik + (ozet veya anahtar kelime). Yazar araniyordu ama
        # bulunamazsa belge yine de altina giriyordu -- 2627 belgenin
        # 471'inde (%17.9) hic <docAuthor> yok. CRF icin bu "bu makalede
        # yazar yoktur" demek; egitilmis model Ingilizce makalelerin
        # %79.4'unde hic yazar uretmiyor.
        # v4: yazar da zorunlu (--yazar-zorunlu-degil ile kapatilabilir).
        ok = ("title" in found) and bool(
            {"abstract_tr", "abstract_en"} & found or {"keyword_tr", "keyword_en"} & found)
        if ok and yazar_zorunlu and "author" not in found:
            ok = False
            yazarsiz += 1

        # v5: yazar etiketi VAR olmasi yetmiyor, DOGRU da olmali.
        #
        # OLCUM (v4 korpusu): yazar etiketi olan 2153 belgenin yalnizca
        # %79.7'sinde etiket DB'deki isimlerle ortusuyordu. Kalan %20.3
        # modele yanlis sey ogretiyordu (yazisma adresi, dergi kunyesi,
        # "Key words" basligi...). Ayni belgede gercek yazar satiri
        # etiketsiz kaldigi icin ikinci bir yanlis daha ogretiliyordu.
        #
        # Testte bu, yazar kaybinin %91'inin header modelinden gelmesiyle
        # sonuclandi: 170 makalede isimler GROBID'in okudugu metinde
        # duruyor ama model etiketlemiyor.
        if ok and yazar_zorunlu and mid in meta:
            asp = birlesik.get("author")
            hedef = set(n for n in (norm_kelime(w)
                                    for w in str(meta[mid].get("yazarlar") or "").split())
                        if len(n) > 2)
            if hedef and asp:
                etiket = set(n for n in (norm_kelime(w)
                                         for w in TAG_RE.sub(" ", canvas[asp[0]:asp[1]]).split())
                             if len(n) > 2)
                # ESIK 0.3 -- olcumle secildi. Ortusme dagilimi (2882 belge):
                #   herhangi bir etiket 2001 | >=0.2  1738 | >=0.3  1715
                #   >=0.4  1688 | >=0.6  1576 | >=0.8  1335
                # Asil ucurum 0.0-0.2 arasinda: 263 belge neredeyse sifir
                # ortusmeli, yani gercekten yanlis etiketli. Daha yukari
                # esikler iyi belgeleri de atiyor, cunku DB'nin kendisi
                # yazarlarda hatali (50 makalelik elle dogrulamada 26'sinda
                # duzeltme gerekti). Yanlis etiketi elemek ile saglam belgeyi
                # korumak arasindaki denge burada.
                if len(hedef & etiket) / len(hedef) < 0.3:
                    ok = False
                    yazar_yanlis += 1
        body = apply_spans(canvas, spans)

        # HIZALAMA GUVENLIGI: etiketler soyulunca metin birebir ayni kalmali,
        # yoksa trainer raw feature dosyasiyla hizalayamaz.
        if strip_tags(body) != canvas:
            bozuk.append(name)
            ok = False

        outp = os.path.join(altin if ok else kar, name)
        with open(outp, "w", encoding="utf-8", newline="\n") as f:
            f.write(full[:m.start(2)] + body + full[m.end(2):])
        rows.append({"dosya": name, "durum": "altin" if ok else "karantina",
                     "alanlar": "|".join(sorted(found))})

    with open(os.path.join(a.out, "rapor.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dosya", "durum", "alanlar"])
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    g = sum(1 for r in rows if r["durum"] == "altin")
    print("islenen: %d   ALTIN: %d (%.1f%%)   KARANTINA: %d" % (n, g, g * 100 / max(n, 1), n - g))
    print("etiket kaynagi: DB=%d  heuristic=%d"
          % (kaynak.get("DB", 0), kaynak.get("H", 0)))
    if yazar_zorunlu:
        print("yazar etiketi bulunamadigi icin karantinaya giden : %d" % yazarsiz)
        print("yazar etiketi YANLIS oldugu icin karantinaya giden: %d" % yazar_yanlis)
    print("alan bazinda bulunma:")
    for k in sorted(stat, key=lambda x: -stat[x]):
        print("   %-14s %4d  (%5.1f%%)" % (k, stat[k], stat[k] * 100 / max(n, 1)))
    if bozuk:
        print("\nHIZALAMA BOZUK (karantinaya alindi): %d dosya" % len(bozuk))
        for b in bozuk[:5]:
            print("   ", b)
    else:
        print("\nHizalama dogrulamasi: %d/%d dosyada metin birebir korundu." % (n, n))
    if dusen:
        print("Cakisma yuzunden dusen alan (toplam %d):" % sum(dusen.values()))
        for k in sorted(dusen, key=lambda x: -dusen[x]):
            print("   %-14s %4d" % (k, dusen[k]))
    print("\ncikti: %s" % a.out)


if __name__ == "__main__":
    main()
