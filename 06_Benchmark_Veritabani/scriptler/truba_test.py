#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
benchmark_300'u TRUBA header modeliyle (:8072) test et, STOK sonucuyla karsilastir.
STOK sonuclari: havuz -> teshis_refined.csv , kolay -> kolay_ham_hepsi.csv
Cikti: secim/truba_karsilastirma.csv  + benchmark_300.csv'ye truba_* kolonlari + ozet
"""
import os, re, csv, json, time, difflib, unicodedata, collections
import concurrent.futures as cf
import requests

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani")
SEC = os.path.join(OUT, "secim")
B300 = os.path.join(SEC, "benchmark_300.csv")
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
KH = os.path.join(OUT, "kolay_ham_hepsi.csv")
GOLD_HAVUZ = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\gold2")
GOLD_KOLAY = os.path.join(OUT, "kolay_gold")
TRUBA = "http://localhost:8072/api/processHeaderDocument"
TEI = os.path.join(OUT, "truba_tei")
os.makedirs(TEI, exist_ok=True)
_TRMAP = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosuCGOSU")


def norm(s):
    if not s:
        return ""
    s = s.translate(_TRMAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def sim(a, b):
    a, b = norm(a), norm(b)
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 3) if a and b else 0.0


def bestsim(t, cands):
    return max([sim(t, c) for c in cands] + [0.0])


def ntok(n):
    return {x for x in re.split(r"[\s,.]+", norm(n)) if len(x) >= 3}


def arecall(got, gold):
    if not gold:
        return None
    gs = [ntok(x) for x in gold]
    ss = [ntok(x) for x in got]
    return round(sum(1 for g in gs if g and any(g & s for s in ss)) / len(gs), 2)


def gold_of(mid, kaynak):
    p = os.path.join(GOLD_HAVUZ if kaynak == "havuz" else GOLD_KOLAY, f"{mid}.json")
    if not os.path.exists(p):
        p2 = os.path.join(GOLD_KOLAY if kaynak == "havuz" else GOLD_HAVUZ, f"{mid}.json")
        p = p2 if os.path.exists(p2) else p
    try:
        g = json.load(open(p, encoding="utf-8"))
    except Exception:
        return {"titles": [], "abstracts": [], "authors": []}
    return {"titles": g.get("titles") or ([g["title"]] if g.get("title") else []),
            "abstracts": g.get("abstracts") or ([g["abstract"]] if g.get("abstract") else []),
            "authors": g.get("authors", [])}


def truba(mid, path):
    cache = os.path.join(TEI, f"{mid}.xml")
    if os.path.exists(cache) and os.path.getsize(cache) > 40:
        return open(cache, encoding="utf-8").read()
    for k in range(3):
        try:
            with open(path, "rb") as fh:
                r = requests.post(TRUBA, files={"input": (os.path.basename(path), fh, "application/pdf")}, timeout=150)
            if r.status_code == 200:
                open(cache, "w", encoding="utf-8").write(r.text)
                return r.text
        except Exception:
            time.sleep(2 * (k + 1))
    return ""


def parse(x):
    t = re.search(r'<title[^>]*type="main"[^>]*>(.*?)</title>', x, re.S) or re.search(r"<title[^>]*>(.*?)</title>", x, re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.group(1))).strip() if t else ""
    ab = re.search(r"<abstract[^>]*>(.*?)</abstract>", x, re.S)
    abst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ab.group(1))).strip() if ab else ""
    names = []
    for pn in re.findall(r"<persName[^>]*>(.*?)</persName>", x, re.S):
        nm = " ".join(w.strip() for w in re.findall(r">([^<]+)<", ">" + pn) if w.strip())
        if nm:
            names.append(nm)
    return title, abst, names


def okt(sim_):   # baslik cozuldu mu
    return sim_ is not None and sim_ >= 0.70


def oka(rec):    # yazar cozuldu mu (gold yoksa notr)
    return rec is None or rec >= 0.5


def cmp3(s_ok, t_ok):
    return ("iki_de_cozdu" if s_ok and t_ok else
            "truba_duzeltti" if (not s_ok and t_ok) else
            "truba_bozdu" if (s_ok and not t_ok) else "iki_de_cozemedi")


def main():
    rows = list(csv.DictReader(open(B300, encoding="utf-8-sig")))
    T = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
    K = {r["makale_id"]: r for r in csv.DictReader(open(KH, encoding="utf-8-sig"))}

    def stok_vals(r):
        s = T.get(r["makale_id"]) or K.get(r["makale_id"]) or {}
        def fv(k):
            v = s.get(k, "")
            try:
                return float(v) if v not in ("", "None", None) else None
            except Exception:
                return None
        return fv("title_sim"), fv("abstract_sim"), fv("author_recall")

    def work(r):
        mid = r["makale_id"]
        g = gold_of(mid, r["kaynak"])
        x = truba(mid, r["path"])
        if not x:
            return mid, dict(truba_hdr=0, truba_title_sim=0.0, truba_abstract_sim=0.0, truba_author_recall=0.0)
        title, abst, names = parse(x)
        return mid, dict(
            truba_hdr=1,
            truba_title_sim=bestsim(title, g["titles"]),
            truba_abstract_sim=bestsim(abst, g["abstracts"]) if g["abstracts"] else None,
            truba_author_recall=arecall(names, g["authors"]),
            truba_title=title[:120],
        )

    res = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(work, r): r["makale_id"] for r in rows}
        for i, f in enumerate(cf.as_completed(futs), 1):
            mid, d = f.result()
            res[mid] = d
            if i % 25 == 0:
                print(f"  {i}/{len(rows)}")

    labT = collections.Counter(); labA = collections.Counter()
    labT_dil = collections.defaultdict(collections.Counter)
    for r in rows:
        d = res[r["makale_id"]]
        stt, sta, str_ = stok_vals(r)
        tl = cmp3(okt(stt), okt(d["truba_title_sim"]))
        au = cmp3(oka(str_), oka(d.get("truba_author_recall")))
        r["stok_title_sim"] = "" if stt is None else stt
        r["stok_author_recall"] = "" if str_ is None else str_
        r["truba_title_sim"] = d["truba_title_sim"]
        r["truba_author_recall"] = "" if d.get("truba_author_recall") is None else d["truba_author_recall"]
        r["truba_abstract_sim"] = "" if d.get("truba_abstract_sim") is None else d["truba_abstract_sim"]
        r["truba_uretti"] = d["truba_hdr"]
        r["baslik_stok_vs_truba"] = tl
        r["yazar_stok_vs_truba"] = au
        labT[tl] += 1; labA[au] += 1
        labT_dil[r["dil"]][tl] += 1
    lab, lab_dil = labT, labT_dil

    cols = list(rows[0].keys())
    with open(B300, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    kc = ["makale_id", "kaynak", "dil", "PRIMARY", "siddet", "sikinti_skoru", "truba_uretti",
          "stok_title_sim", "truba_title_sim", "stok_author_recall", "truba_author_recall",
          "truba_abstract_sim", "baslik_stok_vs_truba", "yazar_stok_vs_truba", "gold_journal"]
    with open(os.path.join(SEC, "truba_karsilastirma.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=kc, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

    order = ("iki_de_cozdu", "truba_duzeltti", "truba_bozdu", "iki_de_cozemedi")
    nout = sum(1 for r in rows if r.get("truba_uretti") == 1)
    L = [f"STOK vs TRUBA header modeli — {len(rows)} belge  (truba header URETTI: {nout}, 500/bos: {len(rows)-nout})",
         "", "eslik esigi: baslik sim>=0.70 ; yazar recall>=0.5", "",
         "### BASLIK ###"]
    for k in order:
        L.append(f"  {k:18} {labT[k]}")
    L.append("\n  dile gore (baslik):")
    for d in ("tr", "en", "mix"):
        c = labT_dil[d]
        L.append(f"    {d:4} n={sum(c.values()):3}  iki_cozdu={c['iki_de_cozdu']:3}  truba_duzeltti={c['truba_duzeltti']:2}  "
                 f"truba_bozdu={c['truba_bozdu']:3}  iki_cozemedi={c['iki_de_cozemedi']:3}")
    L.append("\n### YAZAR ###")
    for k in order:
        L.append(f"  {k:18} {labA[k]}")
    txt = "\n".join(L)
    open(os.path.join(SEC, "truba_ozet.txt"), "w", encoding="utf-8").write(txt)
    print("\n" + txt)
    print("\n-> secim/truba_karsilastirma.csv , secim/truba_ozet.txt , benchmark_300.csv guncellendi")


if __name__ == "__main__":
    main()
