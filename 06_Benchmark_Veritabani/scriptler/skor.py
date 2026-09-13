#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark-300 icin TEK kanonik skorlama modulu.

Neden var: eski akista stok skorlari tek-baslikli `gold`, TRUBA skorlari
cok-baslikli `gold2` ile hesaplanmisti; ayrica cift dilli (TR+EN) baslik
bloklarini bitisik donduren dogru cikarimlar 0.60-0.70 bandina dusup
"cozemedi" sayiliyordu. Bu modul her iki tarafi ayni gold ve ayni metrikle
olcer.

Baslik icin uc sayi uretilir:
  sim      : eski davranis (difflib, gold varyantlarinin en iyisi)  -> sureklilik
  kapsama  : tahmin, bir gold basligin TUM token'larini iceriyor mu (0-1)
  fazlalik : gold basligina gore fazladan token orani (0 = tipatip)
Karar (`ok`): sim >= 0.70  VEYA  (kapsama >= 0.90 ve fazlalik <= 1.30)
Ikinci kol cift dilli birlesmeyi kurtarir; fazlalik tavani "tum sayfayi
basliga yapistir" tipi cikarimlarin puan kazanmasini engeller.
"""
import re, json, difflib, unicodedata

_TRMAP = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosuCGOSU")
TITLE_SIM_ESIK = 0.70      # eski, katı kol
TITLE_KAPSAMA_ESIK = 0.90  # gevsek kolun kapsama tabani
TITLE_FAZLALIK_TAVAN = 1.30  # gold basligin ~1 kati kadar fazla metne izin
AUTHOR_ESIK = 0.50


def norm(s):
    if not s:
        return ""
    s = s.translate(_TRMAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def toks(s, minlen=1):
    return [t for t in norm(s).split() if len(t) >= minlen]


def sim(a, b):
    a, b = norm(a), norm(b)
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 3) if a and b else 0.0


def baslik_skor(pred, gold_titles):
    """-> dict(sim, kapsama, fazlalik, ok, birlesik, eslesen)"""
    out = {"sim": 0.0, "kapsama": 0.0, "fazlalik": None, "ok": False,
           "birlesik": False, "eslesen": ""}
    golds = [g for g in (gold_titles or []) if (g or "").strip()]
    if not pred or not golds:
        return out
    pt = toks(pred)
    ps = set(pt)
    out["sim"] = max(sim(pred, g) for g in golds)

    kaps = []
    for g in golds:
        gt = toks(g)
        if not gt:
            kaps.append((0.0, g, 0))
            continue
        kaps.append((len(set(gt) & ps) / len(set(gt)), g, len(gt)))
    kaps.sort(key=lambda x: (-x[0], -x[2]))
    k, g_best, n_gold = kaps[0]
    out["kapsama"] = round(k, 3)
    out["eslesen"] = g_best[:120]
    out["fazlalik"] = round(max(0, len(pt) - n_gold) / max(1, n_gold), 3)
    gevsek = k >= TITLE_KAPSAMA_ESIK and out["fazlalik"] <= TITLE_FAZLALIK_TAVAN
    out["ok"] = bool(out["sim"] >= TITLE_SIM_ESIK or gevsek)
    # iki ayri gold baslik da kapsaniyorsa: cift dilli blok bitisik donmus
    out["birlesik"] = bool(gevsek and out["sim"] < TITLE_SIM_ESIK
                           and sum(1 for kk, _, _ in kaps if kk >= TITLE_KAPSAMA_ESIK) >= 2)
    return out


def _ad_tok(n):
    return {t for t in toks(n) if len(t) >= 3}


def yazar_skor(pred_names, gold_names):
    """gevsek (eski, >=3 harfli tek token ortakligi) + siki (soyad esitligi)
    recall/precision/F1. gold yoksa None doner."""
    gold = [g for g in (gold_names or []) if (g or "").strip()]
    if not gold:
        return {"recall": None, "precision": None, "f1": None,
                "siki_recall": None, "siki_precision": None, "siki_f1": None,
                "n_gold": 0, "n_pred": len(pred_names or [])}
    pred = [p for p in (pred_names or []) if (p or "").strip()]
    G = [_ad_tok(g) for g in gold]
    P = [_ad_tok(p) for p in pred]

    def gevsek(a, b):
        return bool(a and b and (a & b))

    def siki(a, b):
        # soyad ~ en uzun token; ikisi de esitse ve en az 1 token daha ortaksa esles
        if not a or not b:
            return False
        sa, sb = max(a, key=len), max(b, key=len)
        return sa == sb and len(a & b) >= 1

    def rp(fn):
        r = sum(1 for g in G if any(fn(g, p) for p in P)) / len(G)
        pr = (sum(1 for p in P if any(fn(g, p) for g in G)) / len(P)) if P else 0.0
        f = (2 * r * pr / (r + pr)) if (r + pr) else 0.0
        return round(r, 3), round(pr, 3), round(f, 3)

    r1, p1, f1 = rp(gevsek)
    r2, p2, f2 = rp(siki)
    return {"recall": r1, "precision": p1, "f1": f1,
            "siki_recall": r2, "siki_precision": p2, "siki_f1": f2,
            "n_gold": len(G), "n_pred": len(P)}


def ozet_skor(pred, gold_abstracts):
    golds = [a for a in (gold_abstracts or []) if (a or "").strip()]
    if not golds:
        return None
    if not pred:
        return 0.0
    return max(sim(pred, a) for a in golds)


# ---------- TEI ayristirma ----------
def tei_parse(x):
    """GROBID TEI header -> (title, abstract, [names])"""
    if not x:
        return "", "", []
    h = x.split("</teiHeader>")[0] if "</teiHeader>" in x else x
    t = (re.search(r'<title[^>]*type="main"[^>]*>(.*?)</title>', h, re.S)
         or re.search(r"<title[^>]*>(.*?)</title>", h, re.S))
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.group(1))).strip() if t else ""
    ab = re.search(r"<abstract[^>]*>(.*?)</abstract>", h, re.S)
    abst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ab.group(1))).strip() if ab else ""
    names = []
    for blok in re.findall(r"<author\b[^>]*>(.*?)</author>", h, re.S):
        for pn in re.findall(r"<persName[^>]*>(.*?)</persName>", blok, re.S):
            nm = " ".join(w.strip() for w in re.findall(r">([^<]+)<", ">" + pn) if w.strip())
            if nm:
                names.append(nm)
    if not names:  # author disinda persName varsa yine de topla
        for pn in re.findall(r"<persName[^>]*>(.*?)</persName>", h, re.S):
            nm = " ".join(w.strip() for w in re.findall(r">([^<]+)<", ">" + pn) if w.strip())
            if nm:
                names.append(nm)
    title = title.replace("&apos;", "'").replace("&amp;", "&").replace("&quot;", '"')
    return title, abst, names


def gold_yukle(p):
    """gold / gold2 / kolay_gold semalarini tek sekle indirger."""
    g = json.load(open(p, encoding="utf-8"))
    return {
        "titles": [t for t in (g.get("titles") or ([g["title"]] if g.get("title") else [])) if (t or "").strip()],
        "abstracts": [a for a in (g.get("abstracts") or ([g["abstract"]] if g.get("abstract") else [])) if (a or "").strip()],
        "authors": [a for a in (g.get("authors") or []) if (a or "").strip()],
        "year": g.get("year", ""), "journal": g.get("journal", ""),
        "doi": g.get("doi", ""), "found": g.get("found", None),
    }
