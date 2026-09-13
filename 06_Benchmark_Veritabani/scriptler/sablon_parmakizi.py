#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SABLON PARMAK IZI  -  belge mizanpaji benzerligi / sablon klonu tespiti
  Katman 1 (yapisal): pdfminer ile 1. sayfa kutu geometrisi + pypdf font/meta imzasi
  Katman 2 (gorsel)  : pypdfium2 render -> gri -> blur -> 16x16 murekkep haritasi
  Birlesik vektor -> pairwise mesafe -> agglomerative kumeleme
  Ciktilar: parmak_izi/sablon_parmakizi.csv , yakin_kopya_raporu.txt , kume_ozeti.txt
            render_p1/<id>.png  (kucuk onizleme)
Girdi: teshis_refined.csv (makale_id, path, PRIMARY, TIER, FLAGS, gold_journal, dil ...)
Yeniden calistirilabilir: parmak_izi/cache/<id>.json
"""
import os, re, csv, json, math, sys, statistics, collections
import numpy as np
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTTextLine, LTTextContainer, LTChar, LTTextLineHorizontal

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
TESHIS_CSV = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani")
PI_DIR = os.path.join(OUT, "parmak_izi")
CACHE = os.path.join(PI_DIR, "cache")
REND = os.path.join(OUT, "render_p1")
for d in (PI_DIR, CACHE, REND):
    os.makedirs(d, exist_ok=True)

VIS = 16          # gorsel harita VISxVIS
COMMERCIAL_FONTS = re.compile(r"(gulliver|nexus|minion|utopia|stone\s*serif|agaramond|garamond|"
                              r"charter|lexicon|swift|scala|frutiger|univers|dtl|fedra|celeste|"
                              r"legacy|caecilia|joanna|photina)", re.I)
GENERIC_FONTS = re.compile(r"(times new roman|timesnewroman|^times|arial|helvetica|calibri|cambria|"
                           r"liberation|nimbus|dejavu)", re.I)
META_LATEX = re.compile(r"(tex|dvips|ghostscript|pdftex|xetex|luatex)", re.I)
META_WORD = re.compile(r"(microsoft|word|office|wps)", re.I)
META_INDESIGN = re.compile(r"(indesign|adobe.*pdf library|framemaker|quarkxpress|arbortext|3b2)", re.I)
META_SCAN = re.compile(r"(scan|kofax|abbyy|finereader|canon|epson|xerox|imagerunner|scanjet)", re.I)


# ---------------- Katman 1: yapisal ----------------
def structural(path):
    d = {}
    try:
        pages = list(extract_pages(path, maxpages=1,
                     laparams=LAParams(line_margin=0.3, char_margin=2.0, word_margin=0.1)))
    except Exception as e:
        d["struct_err"] = f"{type(e).__name__}"[:60]
        return d
    if not pages:
        d["struct_err"] = "no_page"
        return d
    pg = pages[0]
    W, H = float(pg.width), float(pg.height)
    d["W"], d["H"], d["aspect"] = round(W, 1), round(H, 1), round(W / max(H, 1), 4)

    lines = []
    def walk(o):
        for el in o:
            if isinstance(el, (LTTextLine, LTTextLineHorizontal)):
                sizes = [c.size for c in el if isinstance(c, LTChar)]
                txt = el.get_text().strip()
                if txt and sizes:
                    x0, y0, x1, y1 = el.bbox
                    lines.append((x0, y0, x1, y1, statistics.median(sizes), txt))
            elif isinstance(el, LTTextContainer):
                walk(el)
    walk(pg)
    d["n_lines_p1"] = len(lines)
    if len(lines) < 5:
        d["metinsiz"] = 1
        return d
    d["metinsiz"] = 0

    xs0 = np.array([l[0] for l in lines]); xs1 = np.array([l[2] for l in lines])
    ys0 = np.array([l[1] for l in lines]); ys1 = np.array([l[3] for l in lines])
    hts = np.array([l[4] for l in lines])
    medh = float(np.median(hts))
    d["margin_l"] = round(float(xs0.min()) / W, 4)
    d["margin_r"] = round(1 - float(xs1.max()) / W, 4)
    d["margin_t"] = round(1 - float(ys1.max()) / H, 4)
    d["margin_b"] = round(float(ys0.min()) / H, 4)
    d["med_fontsize"] = round(medh, 2)
    d["font_spread"] = round(float(np.percentile(hts, 90) - np.percentile(hts, 10)) / max(medh, 1), 3)

    # sutun tespiti: sag yariya dusen populer bir satir-baslangic kumesi var mi -> 2 sutun
    left_starts = (xs0 < W * 0.45).sum()
    right_starts = ((xs0 > W * 0.5) & (xs0 < W * 0.9)).sum()
    two_col = right_starts > 6 and left_starts > 6 and right_starts / max(left_starts, 1) > 0.25
    d["n_cols"] = 2 if two_col else 1
    if two_col:
        rmode = float(np.median(xs0[(xs0 > W * 0.5) & (xs0 < W * 0.9)]))
        lmax = float(np.percentile(xs1[xs0 < W * 0.45], 90))
        d["gutter_center"] = round((lmax + rmode) / 2 / W, 4)
        d["gutter_w"] = round(max(0.0, rmode - lmax) / W, 4)
        d["col_w"] = round((rmode - float(xs0.min())) / W, 4)
    else:
        d["gutter_center"] = 0.0; d["gutter_w"] = 0.0
        d["col_w"] = round(float(xs1.max() - xs0.min()) / W, 4)

    # header / footer bandi
    d["hdr_band"] = round(float((ys1 > H * 0.92).mean()), 3)
    d["ftr_band"] = round(float((ys0 < H * 0.08).mean()), 3)

    # baslik: en ustteki buyuk-punto satir
    big = [l for l in lines if l[4] >= 1.35 * medh]
    if big:
        top_big = max(big, key=lambda l: l[3])
        d["title_y"] = round(1 - top_big[3] / H, 4)          # ustten uzaklik
        d["title_ratio"] = round(top_big[4] / medh, 3)
        d["title_cx"] = round(((top_big[0] + top_big[2]) / 2) / W, 3)  # yatay merkez -> ortali mi
    else:
        d["title_y"] = round(1 - float(ys1.max()) / H, 4)
        d["title_ratio"] = 1.0
        d["title_cx"] = round(((float(xs0.min()) + float(xs1.max())) / 2) / W, 3)

    # satir araligi
    order = sorted(lines, key=lambda l: -l[3])
    gaps = [order[i][3] - order[i + 1][3] for i in range(len(order) - 1)]
    gaps = [g for g in gaps if 0 < g < 5 * medh]
    d["leading"] = round(float(np.median(gaps)) / medh, 3) if gaps else 1.2

    d["txt_density"] = round(sum(len(l[5]) for l in lines) / (W * H) * 1000, 3)
    return d


def font_meta(path):
    d = {"n_fonts": 0, "commercial_font": 0, "generic_font": 0, "meta_class": "other", "producer": ""}
    try:
        rd = PdfReader(path)
        names = set()
        try:
            res = rd.pages[0].get("/Resources") or {}
            fd = res.get("/Font") or {}
            for f in list(fd.values()):
                fo = f.get_object()
                bn = str(fo.get("/BaseFont", ""))
                bn = re.sub(r"^/([A-Z]{6}\+)?", "", bn)
                if bn:
                    names.add(bn)
        except Exception:
            pass
        d["n_fonts"] = len(names)
        d["fonts"] = "|".join(sorted(names))[:200]
        joined = " ".join(names)
        d["commercial_font"] = int(bool(COMMERCIAL_FONTS.search(joined)))
        d["generic_font"] = int(bool(GENERIC_FONTS.search(joined)))
        md = rd.metadata or {}
        prod = f"{md.get('/Producer','')} {md.get('/Creator','')}".strip()
        d["producer"] = prod[:80]
        if META_LATEX.search(prod): d["meta_class"] = "latex"
        elif META_INDESIGN.search(prod): d["meta_class"] = "indesign"
        elif META_WORD.search(prod): d["meta_class"] = "word"
        elif META_SCAN.search(prod): d["meta_class"] = "scan"
        elif prod.strip(): d["meta_class"] = "other"
        else: d["meta_class"] = "bos"
    except Exception as e:
        d["meta_err"] = type(e).__name__
    return d


# ---------------- Katman 2: gorsel ----------------
def visual(path, mid):
    try:
        pdf = pdfium.PdfDocument(path)
        page = pdf[0]
        bmp = page.render(scale=110 / 72).to_pil().convert("L")
        pdf.close()
        thumb = bmp.resize((200, 260))
        thumb.save(os.path.join(REND, f"{mid}.png"))
        g = bmp.resize((64, 64)).filter(ImageFilter.GaussianBlur(1.6)).resize((VIS, VIS))
        a = np.asarray(g, dtype=np.float32)
        a = 255.0 - a                      # murekkep = yuksek
        if a.std() > 1e-6:
            a = (a - a.mean()) / a.std()
        return a.flatten()
    except Exception:
        return np.zeros(VIS * VIS, dtype=np.float32)


# ---------------- fingerprint tek PDF ----------------
STRUCT_KEYS = ["aspect", "margin_l", "margin_r", "margin_t", "margin_b", "med_fontsize",
               "font_spread", "n_cols", "gutter_center", "gutter_w", "col_w", "hdr_band",
               "ftr_band", "title_y", "title_ratio", "title_cx", "leading", "txt_density",
               "n_fonts", "commercial_font", "generic_font"]


def fingerprint(mid, path):
    cf = os.path.join(CACHE, f"{mid}.json")
    if os.path.exists(cf):
        try:
            d = json.load(open(cf, encoding="utf-8"))
            d["_vis"] = np.array(d["_vis"], dtype=np.float32)
            return d
        except Exception:
            pass
    d = {"makale_id": mid}
    d.update(structural(path))
    d.update(font_meta(path))
    vis = visual(path, mid)
    d["_vis"] = vis
    dj = dict(d); dj["_vis"] = vis.tolist()
    json.dump(dj, open(cf, "w", encoding="utf-8"), ensure_ascii=False)
    return d


# ---------------- ana ----------------
def main():
    rows = list(csv.DictReader(open(TESHIS_CSV, encoding="utf-8-sig")))
    print(f"{len(rows)} PDF parmak izi cikariliyor...")
    fps = []
    for i, r in enumerate(rows, 1):
        p = r["path"]
        if not os.path.exists(p):
            print("  YOK:", p); continue
        fp = fingerprint(r["makale_id"], p)
        fp["_row"] = r
        fps.append(fp)
        if i % 25 == 0:
            print(f"  {i}/{len(rows)}")

    ids = [f["makale_id"] for f in fps]
    # yapisal matris (eksikleri median ile doldur, z-skor)
    S = np.full((len(fps), len(STRUCT_KEYS)), np.nan, dtype=np.float32)
    for i, f in enumerate(fps):
        for j, k in enumerate(STRUCT_KEYS):
            v = f.get(k)
            if isinstance(v, (int, float)):
                S[i, j] = v
    col_med = np.nanmedian(S, axis=0)
    inds = np.where(np.isnan(S))
    S[inds] = np.take(col_med, inds[1])
    mu, sd = S.mean(0), S.std(0) + 1e-6
    Sz = (S - mu) / sd
    Sz = np.clip(Sz, -4, 4)
    metinsiz = np.array([f.get("metinsiz", 1) for f in fps])
    Sz[metinsiz == 1] *= 0.10                      # metinsizlerde yapisala neredeyse guvenme

    # gorsel matris: piksel-bazli z-skor (satir-L2 degil) -> ward icin daha stabil
    V = np.vstack([f["_vis"] for f in fps]).astype(np.float32)
    V = (V - V.mean(0)) / (V.std(0) + 1e-6)
    V = np.clip(V, -4, 4)
    # gorsel bloklari toplam varyans yapisala benzer olsun diye olcekle
    V *= math.sqrt(len(STRUCT_KEYS) / V.shape[1])
    W_STRUCT, W_VIS = 1.4, 0.7
    X = np.hstack([Sz * W_STRUCT, V * W_VIS]).astype(np.float64)

    from sklearn.metrics import pairwise_distances
    from sklearn.cluster import AgglomerativeClustering
    D = pairwise_distances(X, metric="euclidean")
    tri = D[np.triu_indices_from(D, k=1)]
    p2, p5, p10, p25, med = (float(np.percentile(tri, q)) for q in (2, 5, 10, 25, 50))
    print(f"\nmesafe dagilimi: p2={p2:.2f} p5={p5:.2f} p10={p10:.2f} p25={p25:.2f} med={med:.2f}")

    # ward linkage, hedef ~ N/3.5 kume  (kaba sablon aileleri)
    n_target = max(20, round(len(fps) / 3.5))
    cl = AgglomerativeClustering(n_clusters=n_target, linkage="ward").fit_predict(X)
    cl_fine = AgglomerativeClustering(n_clusters=min(len(fps) - 1, round(len(fps) / 2.2)),
                                      linkage="ward").fit_predict(X)
    ncl = len(set(cl))
    csize = collections.Counter(cl)
    thr = p10
    print(f"ward n_target={n_target} -> {ncl} kume  (en buyuk {csize.most_common(1)[0][1]}, "
          f"tekil {sum(1 for v in csize.values() if v==1)})")

    # en yakin komsu
    Dnn = D.copy(); np.fill_diagonal(Dnn, np.inf)
    nn = Dnn.argmin(1); nnd = Dnn.min(1)

    # ---- CSV ----
    out_csv = os.path.join(PI_DIR, "sablon_parmakizi.csv")
    cols = (["makale_id", "PRIMARY", "TIER", "dil", "gold_journal", "journal_dir",
             "meta_class", "producer", "n_fonts", "commercial_font", "generic_font",
             "sablon_taklit", "metinsiz", "n_cols", "gutter_center", "margin_l", "margin_r",
             "title_y", "title_ratio", "title_cx", "leading", "med_fontsize",
             "cluster", "cluster_size", "cluster_fine", "nn_id", "nn_dist", "fonts"])
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for i, f in enumerate(fps):
            r = f["_row"]
            # sablon-taklit: ticari-yayinci geometrisi (2 kolon, dar ust margin, ortali kucuk baslik, serifli)
            #                ama uretici word/other + jenerik font
            comm_geo = (f.get("n_cols") == 2 and f.get("margin_t", 1) < 0.11
                        and f.get("title_ratio", 1) < 1.8 and f.get("title_cx", 0.5) > 0.33
                        and f.get("title_cx", 0.5) < 0.67)
            taklit = int(comm_geo and f.get("commercial_font", 0) == 0
                         and f.get("meta_class") in ("word", "other", "bos")
                         and f.get("generic_font", 0) == 1)
            w.writerow({
                "makale_id": f["makale_id"], "PRIMARY": r.get("PRIMARY"), "TIER": r.get("TIER"),
                "dil": r.get("dil"), "gold_journal": r.get("gold_journal"), "journal_dir": r.get("journal_dir"),
                "meta_class": f.get("meta_class"), "producer": f.get("producer"),
                "n_fonts": f.get("n_fonts"), "commercial_font": f.get("commercial_font"),
                "generic_font": f.get("generic_font"), "sablon_taklit": taklit,
                "metinsiz": f.get("metinsiz"), "n_cols": f.get("n_cols"),
                "gutter_center": f.get("gutter_center"), "margin_l": f.get("margin_l"),
                "margin_r": f.get("margin_r"), "title_y": f.get("title_y"),
                "title_ratio": f.get("title_ratio"), "title_cx": f.get("title_cx"),
                "leading": f.get("leading"), "med_fontsize": f.get("med_fontsize"),
                "cluster": int(cl[i]), "cluster_size": csize[cl[i]], "cluster_fine": int(cl_fine[i]),
                "nn_id": ids[nn[i]], "nn_dist": round(float(nnd[i]), 3),
                "fonts": f.get("fonts", ""),
            })
    print("->", out_csv)

    # ---- yakin kopya raporu ----
    rep = os.path.join(PI_DIR, "yakin_kopya_raporu.txt")
    ndthr = min(p2, 0.45 * med)
    pairs = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            if D[i, j] < ndthr:
                pairs.append((D[i, j], i, j))
    pairs.sort()
    with open(rep, "w", encoding="utf-8") as fh:
        fh.write(f"# mesafe < {ndthr:.2f} (min(p2, 0.45*med))  -> {len(pairs)} cift  (ayni sablon suphesi)\n")
        fh.write(f"# ayni cluster_fine + dusuk mesafe = neredeyse ikiz sablon\n\n")
        for dst, i, j in pairs[:600]:
            a, b = fps[i]["_row"], fps[j]["_row"]
            fh.write(f"{dst:5.2f}  {ids[i]:>9} [{a.get('PRIMARY'):16} {a.get('gold_journal','')[:34]:34}] "
                     f"<->  {ids[j]:>9} [{b.get('PRIMARY'):16} {b.get('gold_journal','')[:34]:34}]\n")
    print("->", rep, f"({len(pairs)} yakin cift)")

    # ---- kume ozeti ----
    ks = os.path.join(PI_DIR, "kume_ozeti.txt")
    with open(ks, "w", encoding="utf-8") as fh:
        fh.write(f"esik={thr:.2f}  kume={ncl}  toplam={len(fps)}\n\n")
        for c, n in csize.most_common():
            idx = [i for i in range(len(fps)) if cl[i] == c]
            mc = collections.Counter(fps[i].get("meta_class") for i in idx)
            pc = collections.Counter(fps[i]["_row"].get("PRIMARY") for i in idx)
            jc = collections.Counter(fps[i]["_row"].get("gold_journal") or fps[i]["_row"].get("journal_dir") for i in idx)
            tk = sum(1 for i in idx if fps[i].get("metinsiz"))
            fh.write(f"[kume {c:3}] n={n:3}  meta={dict(mc)}  metinsiz={tk}\n")
            fh.write(f"           PRIMARY={dict(pc.most_common(4))}\n")
            fh.write(f"           dergi(ilk5)={[x for x,_ in jc.most_common(5)]}\n")
            fh.write(f"           ornek id={ [ids[i] for i in idx[:8] ] }\n\n")
    print("->", ks)

    np.save(os.path.join(PI_DIR, "dist_matrix.npy"), D)
    json.dump({"ids": ids, "thr": thr, "p5": p5, "p10": p10, "p25": p25},
              open(os.path.join(PI_DIR, "meta.json"), "w"), ensure_ascii=False, indent=1)
    print("\n=== KUME BOYUT DAGILIMI ===")
    for sz, cnt in sorted(collections.Counter(csize.values()).items()):
        print(f"  {cnt:3} kume x {sz:3} belge")


if __name__ == "__main__":
    main()
