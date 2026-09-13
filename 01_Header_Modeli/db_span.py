# -*- coding: utf-8 -*-
"""
TR Dizin'den gelen "altin" metadata degerlerinin, header egitim metni
icindeki karakter araligini (span) bulur.

Segmentasyon asamasinda kullanilan yontemin ayni: DB'deki gercek degeri
normalize edip metinde bulanik (fuzzy) olarak arar. Boylece etiket sinirlari
tahminle degil gercek veriyle belirlenir.
"""
import re
import difflib

FIX = {"›": "ı", "ﬂ": "ş", "ﬁ": "Ş", "¤": "ğ",
       "‹": "İ", "Ý": "İ", "ý": "ı", "Þ": "Ş",
       "þ": "ş", "Ð": "Ğ", "ð": "ğ", "Ġ": "İ",
       "ġ": "ş",
       # U+2044 (kesir cizgisi) bazi PDF fontlarinda "g yumusak g" yerine
       # gecmis: "KARINCAO⁄LU" -> "KARINCAOĞLU". Olculdu, eslesmeyi bozuyordu.
       "⁄": "ğ"}
TR = str.maketrans("çğıöşü", "cgiosu")


def norm_kelime(t):
    for a, b in FIX.items():
        t = t.replace(a, b)
    t = t.replace("I", "ı").replace("İ", "i").lower().translate(TR)
    return re.sub(r'[^\w]', '', t)


TOK = re.compile(r'<lb/>|[^\s<]+')


def canvas_tokens(canvas):
    """[(normalize_token, char_start, char_end)] -- satir sonu tiresi birlestirilir."""
    ham = []
    for m in TOK.finditer(canvas):
        if m.group(0) == "<lb/>":
            continue
        ham.append([m.group(0), m.start(), m.end()])
    out, i = [], 0
    while i < len(ham):
        met, s, e = ham[i]
        # "bütünlü-" + "ğünün"  ->  tek kelime
        while met.endswith("-") and i + 1 < len(ham):
            i += 1
            met = met[:-1] + ham[i][0]
            e = ham[i][2]
        n = norm_kelime(met)
        if n:
            out.append((n, s, e))
        i += 1
    return out


def hedef_tokens(s):
    return [n for n in (norm_kelime(t) for t in str(s or "").split()) if n]


def find_span(ctoks, hedef, lo=0, hi=None, min_kapsama=0.45, min_yogunluk=0.34):
    """hedef metnin ctoks icindeki (char_start, char_end) araligi.

    min_kapsama : hedef kelimelerinin en az bu orani bulunmali
    min_yogunluk: bulunan aralikta eslesen kelime orani (dagilmis eslesmeyi eler)
    """
    if hi is None:
        hi = len(ctoks)
    hedef = [t for t in hedef if len(t) > 2]
    if len(hedef) < 2 or hi - lo < 2:
        return None
    pencere = [t[0] for t in ctoks[lo:hi]]
    sm = difflib.SequenceMatcher(a=hedef, b=pencere, autojunk=False)
    bloklar = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not bloklar:
        return None
    eslesen = sum(b.size for b in bloklar)
    if eslesen / len(hedef) < min_kapsama:
        return None
    ilk = min(b.b for b in bloklar)
    son = max(b.b + b.size for b in bloklar)
    if son - ilk <= 0 or eslesen / (son - ilk) < min_yogunluk:
        return None
    return (ctoks[lo + ilk][1], ctoks[lo + son - 1][2])


def find_span_detay(ctoks, hedef, lo=0, hi=None, min_kapsama=0.45, min_yogunluk=0.34):
    """find_span ile ayni, ama ayrica ESLESEN token indekslerini de dondurur.
    Yazar span'ini satir bazinda kirpabilmek icin gerekli."""
    if hi is None:
        hi = len(ctoks)
    hedef = [t for t in hedef if len(t) > 2]
    if len(hedef) < 2 or hi - lo < 2:
        return None, set()
    pencere = [t[0] for t in ctoks[lo:hi]]
    sm = difflib.SequenceMatcher(a=hedef, b=pencere, autojunk=False)
    bloklar = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not bloklar:
        return None, set()
    eslesen = sum(b.size for b in bloklar)
    if eslesen / len(hedef) < min_kapsama:
        return None, set()
    ilk = min(b.b for b in bloklar)
    son = max(b.b + b.size for b in bloklar)
    if son - ilk <= 0 or eslesen / (son - ilk) < min_yogunluk:
        return None, set()
    idx = set()
    for b in bloklar:
        for k in range(b.size):
            idx.add(lo + b.b + k)
    return (ctoks[lo + ilk][1], ctoks[lo + son - 1][2]), idx


def tok_index(ctoks, char_pos):
    """char konumundan sonraki ilk token indeksi."""
    for i, (_, s, _) in enumerate(ctoks):
        if s >= char_pos:
            return i
    return len(ctoks)
