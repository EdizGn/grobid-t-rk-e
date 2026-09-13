#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAZE TURKCE KOLAY ADAY CEKME
  TR Dizin'den rastgele ID tarar -> Turkce ozetli + PDF'li yayin indirir
  -> metin katmani/dogum kontrolu -> stock GROBID (:8071) + gold diff
  -> yalnizca TEMIZ + Turkce-agirlikli olanlari kolay_adaylar.csv'ye yazar
Ciktilar: kolay_ham/makale_<id>.pdf , kolay_gold/<id>.json , kolay_adaylar.csv , kolay_ham_hepsi.csv
Yeniden calistirilabilir (indirilmis + teshis edilmis atlanir).
"""
import os, re, csv, json, time, random, argparse, difflib, unicodedata, threading
import concurrent.futures as cf
import requests
import pypdfium2 as pdfium

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = PROJE_KOK + r""
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani")
HAM = os.path.join(OUT, "kolay_ham")
GOLD = os.path.join(OUT, "kolay_gold")
TEI = os.path.join(OUT, "kolay_tei")
for d in (HAM, GOLD, TEI):
    os.makedirs(d, exist_ok=True)
TESHIS_CSV = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
G_STOCK = "http://localhost:8071/api"
BYID = "https://search.trdizin.gov.tr/api/publicationById/{}?archiveSearch=ADD_ARCHIVE"
GETF = "https://search.trdizin.gov.tr/api/getFile/{}?showViewer=false"
HDRS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MAX_ID = 2_000_000
TR_CHARS = set("ıİşŞğĞçÇöÖüÜ")
_TRMAP = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiiosuCGOSU")
_pdfium_lock = threading.Lock()
_wl = threading.Lock()


def norm(s):
    if not s:
        return ""
    s = s.translate(_TRMAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s)).strip()


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 3)


def best_sim(t, cands):
    return max([sim(t, c) for c in cands] + [0.0])


def name_tokens(n):
    return {x for x in re.split(r"[\s,.]+", norm(n)) if len(x) >= 3}


def author_recall(stock, gold):
    if not gold:
        return None
    gs = [name_tokens(a) for a in gold]
    ss = [name_tokens(a) for a in stock]
    return round(sum(1 for g in gs if g and any(g & s for s in ss)) / len(gs), 2)


# ---------- TR Dizin ----------
def fetch_meta(mid):
    try:
        r = requests.get(BYID.format(mid), headers=HDRS, timeout=12)
        hits = r.json().get("hits", {}).get("hits", [])
        return hits[0].get("_source", {}) if hits else None
    except Exception:
        return None


def gold_from_source(src):
    ab = src.get("abstracts", []) or []
    titles = [a.get("title", "") for a in ab if a.get("title")]
    if src.get("orderTitle"):
        titles.append(src["orderTitle"])
    return {
        "titles": titles,
        "abstracts": [a.get("abstract", "") for a in ab if a.get("abstract")],
        "authors": [a.get("name", "") for a in src.get("authors", []) if isinstance(a, dict)],
        "year": str(src.get("publicationYear") or ""),
        "journal": (src.get("journal") or {}).get("name", "") if isinstance(src.get("journal"), dict) else "",
        "doi": src.get("doi") or "",
        "has_tr_abstract": any(a.get("language") == "TUR" and a.get("abstract") for a in ab),
        "found": True,
    }


def download(mid, src):
    pdf_path = os.path.join(HAM, f"makale_{mid}.pdf")
    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 2000:
        return pdf_path
    key = src.get("pdf")
    if not key:
        return None
    try:
        u = requests.get(GETF.format(key), headers=HDRS, timeout=12).text.strip().strip('"').strip("'")
        if not u.startswith("http"):
            return None
        pr = requests.get(u, headers=HDRS, timeout=25, stream=True)
        if pr.status_code != 200:
            return None
        with open(pdf_path, "wb") as f:
            for ch in pr.iter_content(8192):
                f.write(ch)
        return pdf_path if os.path.getsize(pdf_path) > 2000 else None
    except Exception:
        return None


# ---------- indirici (rastgele tarama) ----------
def try_one(mid, skip):
    if mid in skip:
        return None
    src = fetch_meta(mid)
    if not src or not src.get("pdf"):
        return None
    g = gold_from_source(src)
    if not g["has_tr_abstract"] or not g["titles"] or not g["authors"]:
        return None
    p = download(mid, src)
    if not p:
        return None
    json.dump(g, open(os.path.join(GOLD, f"{mid}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return mid


def sweep(target, skip, min_id=1):
    have = [f[7:-4] for f in os.listdir(HAM) if f.endswith(".pdf")]
    got = set(have)
    print(f"kolay_ham'da {len(got)} PDF var, hedef {target}  (id araligi {min_id}-{MAX_ID})")
    seen = set(int(x) for x in got if x.isdigit())
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        while len(got) < target:
            batch = []
            while len(batch) < 120:
                rid = random.randint(min_id, MAX_ID)
                if rid not in seen:
                    seen.add(rid); batch.append(rid)
            for fut in cf.as_completed([ex.submit(try_one, r, skip) for r in batch]):
                m = fut.result()
                if m:
                    got.add(str(m))
                    if len(got) % 20 == 0:
                        print(f"  indirilen {len(got)}/{target}")
                    if len(got) >= target:
                        break
    return sorted(got, key=int)


# ---------- teshis (stock GROBID + gold) ----------
def grobid(mid, path, ep, sub):
    cache = os.path.join(TEI, f"{mid}.{sub}.xml")
    if os.path.exists(cache) and os.path.getsize(cache) > 40:
        return open(cache, encoding="utf-8").read()
    for k in range(3):
        try:
            with open(path, "rb") as fh:
                r = requests.post(f"{G_STOCK}/{ep}",
                                  files={"input": (os.path.basename(path), fh, "application/pdf")}, timeout=150)
            if r.status_code == 200:
                open(cache, "w", encoding="utf-8").write(r.text)
                return r.text
        except Exception:
            time.sleep(2 * (k + 1))
    return ""


def tt(x, rx):
    m = re.search(rx, x, re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""


def diagnose(mid, path):
    d = {"makale_id": mid, "path": path}
    try:
        with _pdfium_lock:
            pdf = pdfium.PdfDocument(path)
            n = len(pdf)
            txt = "\n".join(pdf[i].get_textpage().get_text_range() for i in range(min(n, 5)))
            pdf.close()
    except Exception as e:
        d["red"] = f"pdf_err {type(e).__name__}"
        return d
    nsp = sum(1 for c in txt if not c.isspace()) or 1
    d["pages"] = n
    d["chars_per_page"] = round(len(txt) / max(1, min(n, 5)))
    d["harf_orani"] = round(sum(c.isalpha() for c in txt) / nsp * 100, 1)
    d["tr_chars"] = sum(1 for c in txt if c in TR_CHARS)
    d["replacement"] = txt.count("\ufffd")
    tr_hit = len(re.findall(r"\b(ve|bir|bu|ile|için|olarak|çalışma|araştırma|sonuç|amaç|yöntem)\b", txt, re.I))
    en_hit = len(re.findall(r"\b(the|and|of|to|in|is|for|this|study|results|method)\b", txt, re.I))
    d["dil"] = "tr" if tr_hit > en_hit * 1.3 else ("en" if en_hit > tr_hit * 1.3 else "mix")

    g = json.load(open(os.path.join(GOLD, f"{mid}.json"), encoding="utf-8"))
    d["gold_journal"] = g["journal"]; d["year"] = g["year"]
    hx = grobid(mid, path, "processHeaderDocument", "header")
    fx = grobid(mid, path, "processFulltextDocument", "fulltext")
    title = tt(hx, r'<title[^>]*type="main"[^>]*>(.*?)</title>') or tt(hx, r'<title[^>]*>(.*?)</title>')
    abst = tt(hx, r"<abstract[^>]*>(.*?)</abstract>") or tt(fx, r"<abstract[^>]*>(.*?)</abstract>")
    names = []
    for pn in re.findall(r"<persName[^>]*>(.*?)</persName>", hx, re.S):
        nm = " ".join(t.strip() for t in re.findall(r">([^<]+)<", ">" + pn) if t.strip())
        if nm:
            names.append(nm)
    body_len = len(tt(fx, r"<body[^>]*>(.*?)</body>"))
    d["title_sim"] = best_sim(title, g["titles"])
    d["abstract_sim"] = best_sim(abst, g["abstracts"]) if g["abstracts"] else None
    d["author_recall"] = author_recall(names, g["authors"])
    d["stock_body_len"] = body_len
    d["grobid_ok"] = int(bool(hx))

    # KOLAY-TEMIZ kriteri
    scanned = d["chars_per_page"] < 400 or d["harf_orani"] < 55
    reasons = []
    if scanned: reasons.append("taranmis/dusuk-metin")
    if not (4 <= n <= 30): reasons.append(f"sayfa={n}")
    if d["tr_chars"] < 30 or d["dil"] == "en": reasons.append("turkce-degil")
    if d["replacement"] > 4: reasons.append("karakter-bozuk")
    if not hx: reasons.append("grobid-crash")
    if d["title_sim"] < 0.75: reasons.append(f"baslik_sim={d['title_sim']}")
    if not abst or len(abst) < 120: reasons.append("ozet-yok")
    elif d["abstract_sim"] is not None and d["abstract_sim"] < 0.45: reasons.append(f"ozet_sim={d['abstract_sim']}")
    if d["author_recall"] is not None and d["author_recall"] < 0.5: reasons.append(f"yazar_rec={d['author_recall']}")
    if body_len < 1500: reasons.append("govde-kisa")
    d["temiz_tr"] = int(not reasons)
    d["red"] = ";".join(reasons)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ham", type=int, default=350, help="indirilecek ham Turkce PDF sayisi")
    ap.add_argument("--min-id", type=int, default=1, help="rastgele ID alt siniri (yeni=born-digital icin yukselt)")
    a = ap.parse_args()
    skip = set()
    if os.path.exists(TESHIS_CSV):
        skip = {r["makale_id"] for r in csv.DictReader(open(TESHIS_CSV, encoding="utf-8-sig"))}
    skip = {int(x) for x in skip if str(x).isdigit()}
    print(f"havuzdaki {len(skip)} ID atlanacak")

    ids = sweep(a.ham, skip, a.min_id)
    print(f"\n{len(ids)} ham PDF hazir, teshis basliyor (stock GROBID :8071)...")

    rows = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(diagnose, m, os.path.join(HAM, f"makale_{m}.pdf")): m for m in ids}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            try:
                rows.append(fut.result())
            except Exception as e:
                rows.append({"makale_id": futs[fut], "red": f"ISLEM {e}"[:80]})
            if i % 20 == 0:
                print(f"  teshis {i}/{len(ids)}")

    cols = ["makale_id", "temiz_tr", "dil", "pages", "year", "gold_journal", "harf_orani",
            "chars_per_page", "tr_chars", "replacement", "title_sim", "abstract_sim",
            "author_recall", "stock_body_len", "grobid_ok", "red", "path"]
    allp = os.path.join(OUT, "kolay_ham_hepsi.csv")
    with open(allp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    temiz = [r for r in rows if r.get("temiz_tr") == 1]
    okp = os.path.join(OUT, "kolay_adaylar.csv")
    with open(okp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(temiz)
    import collections
    red = collections.Counter()
    for r in rows:
        for x in (r.get("red") or "").split(";"):
            if x:
                red[x.split("=")[0]] += 1
    print(f"\n== SONUC ==\nham teshis: {len(rows)}   TEMIZ-TR: {len(temiz)}")
    print("dil(temiz):", collections.Counter(r["dil"] for r in temiz))
    print("eleme sebepleri:", dict(red.most_common()))
    print(f"-> {okp}\n-> {allp}")


if __name__ == "__main__":
    main()
