#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BENCHMARK 300 kurucu (tek script) — dil + siddet ayarli
  problemli havuz (391) + kolay-tr adaylari (kolay_adaylar.csv) -> 300
  parametreler:
    --toplam 300  --kolay 120  --tr-oran 0.65  --agir-hedef 0.17
    --en-max <problemlide en fazla saf-ingilizce>  --twin 2.2  --kopyala
Cikti: secim/benchmark_300.csv (+ sikinti_skoru/siddet) , secim/ozet_300.txt , secim/pdf300/...
"""
import os, csv, json, math, shutil, collections, argparse
import numpy as np

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani")
PI = os.path.join(OUT, "parmak_izi")
SEC = os.path.join(OUT, "secim")
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
KOLAYHAM = os.path.join(OUT, "kolay_ham_hepsi.csv")
KOLAYADAY = os.path.join(OUT, "kolay_adaylar.csv")
os.makedirs(SEC, exist_ok=True)

RARE = {"bozuk-font", "taranmis", "govde-yok", "dusuk-benzerlik", "ozet-yok",
        "yazar-eksik", "baslik-cift-dilli"}   # havuzda az -> tamami korunur
BIG = {"header-title-yok", "baslik-dergi-adi", "karakter-anomali", "baslik-yanlis", "ozet-eksik"}


def fnum(d, k, dv=0.0):
    v = (d or {}).get(k, "")
    try:
        return float(v) if v not in ("", "None", None) else dv
    except Exception:
        return dv


def severity(src, flags, kolay=False):
    cpp, harf = fnum(src, "chars_per_page"), fnum(src, "harf_orani", 100)
    repl, anom = fnum(src, "replacement"), fnum(src, "anomali_promil")
    body = fnum(src, "stock_body_len")
    tsim, asim, arec = src.get("title_sim", ""), src.get("abstract_sim", ""), src.get("author_recall", "")
    crash = (src.get("stock_hdr", "200") != "200") if not kolay else (src.get("grobid_ok", "1") != "1")
    scanned = (cpp and cpp < 120) or harf < 8
    s = 0.0
    if scanned: s += 45
    elif harf < 45: s += 32
    elif harf < 60: s += 10
    if crash and not scanned: s += 28
    if not scanned and not crash:
        if str(tsim) not in ("", "None"): s += (1 - float(tsim)) * 22
        if str(asim) in ("", "None"): s += 10
        elif float(asim) < 0.45: s += (1 - float(asim)) * 12
        if str(arec) not in ("", "None"): s += (1 - float(arec)) * 10
        if body and body < 500: s += 14
        s += min(anom, 15) + min(repl * 1.5, 10)
    s += max(0, len(set(x for x in flags if x and x != "temiz")) - 1) * 4
    s = min(100, round(s))
    return s, ("hafif" if s < 20 else "orta" if s <= 50 else "agir")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toplam", type=int, default=300)
    ap.add_argument("--kolay", type=int, default=120)
    ap.add_argument("--crash", type=int, default=20, help="problemlide en fazla grobid-crash")
    ap.add_argument("--crash-aile", type=int, default=5, help="crash: gorsel aile basina tavan")
    ap.add_argument("--en-max", type=int, default=55, help="problemlide en fazla saf-ingilizce")
    ap.add_argument("--twin", type=float, default=2.2)
    ap.add_argument("--kopyala", action="store_true")
    a = ap.parse_args()
    n_prob = a.toplam - a.kolay

    T = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
    KH = {r["makale_id"]: r for r in csv.DictReader(open(KOLAYHAM, encoding="utf-8-sig"))}
    KA = list(csv.DictReader(open(KOLAYADAY, encoding="utf-8-sig")))
    v2 = {r["makale_id"]: r for r in csv.DictReader(open(os.path.join(PI, "sablon_parmakizi_v2.csv"), encoding="utf-8-sig"))}
    meta = json.load(open(os.path.join(PI, "meta_v2.json"), encoding="utf-8"))
    D = np.load(os.path.join(PI, "dist_matrix_v2.npy"))
    gi = {m: i for i, m in enumerate(meta["ids"])}

    for r in T.values():
        r["_sev"], r["_sd"] = severity(r, (r.get("FLAGS") or "").split(";"))
    nontemiz = [r for r in T.values() if r["PRIMARY"] != "temiz" and r["makale_id"] in gi]
    byc = collections.defaultdict(list)
    for r in nontemiz:
        byc[r["PRIMARY"]].append(r)

    def fp(cands, k, seedpool=None, clustcap=3, prefer_tr=True, twin=0.0):
        """farthest-point; twin: bu mesafeden yakin adayi (secilenlere) atla."""
        if len(cands) <= k and twin <= 0:
            return list(cands)
        idx = {r["makale_id"]: gi[r["makale_id"]] for r in cands}
        rr = {r["makale_id"]: r for r in cands}
        def clof(m): return rr[m].get("cluster") or v2.get(m, {}).get("cluster")
        clc = collections.Counter()
        seedg = list(seedpool or [])
        if seedg:
            first = max(idx, key=lambda m: min(D[idx[m], s] for s in seedg))
        else:
            first = next(iter(idx))
        sel = [first]; clc[clof(first)] += 1
        pool = [m for m in idx if m != first]
        while pool and len(sel) < k:
            base = seedg + [idx[m] for m in sel]
            allowed = [m for m in pool if (twin <= 0 or min(D[idx[m], b] for b in base) >= twin)
                       and clc[clof(m)] < clustcap]
            search = allowed or [m for m in pool if twin <= 0 or min(D[idx[m], b] for b in base) >= twin] or pool
            def sc(m):
                d = min(D[idx[m], b] for b in base)
                pen = (-0.4 if prefer_tr and rr[m].get("dil") == "en" else 0)
                if clc[clof(m)] >= clustcap: pen -= 100
                return d + pen
            m = max(search, key=sc)
            sel.append(m); pool.remove(m); clc[clof(m)] += 1
        return [rr[m] for m in sel]

    prob = []
    # 1) nadir siniflar tam
    for c in RARE:
        prob += byc.get(c, [])
    # 2) grobid-crash: sinirli + gorsel aile tavani + ikiz filtresi
    gc = byc.get("grobid-crash", [])
    prob += fp(gc, min(a.crash, len(gc)), clustcap=a.crash_aile, prefer_tr=False, twin=a.twin)
    # 3) buyuk 5: kalan kotayi doldur, tr-yanli, ikiz filtresi
    big = [r for c in BIG for r in byc.get(c, [])]
    probg0 = [gi[r["makale_id"]] for r in prob]
    kalan = n_prob - len(prob)
    prob += fp(big, max(0, kalan), seedpool=probg0, clustcap=3, prefer_tr=True, twin=a.twin)

    # 4b) problemli ici yakin-ikiz sweep: cift < twin ise dusuk-degerliyi at, buyuk-5 artigi ile doldur
    classfreq = collections.Counter(r["PRIMARY"] for r in nontemiz)
    def val(r):
        return (-classfreq[r["PRIMARY"]], r.get("onarilmis_var") == "1", r["_sev"])
    used = {r["makale_id"] for r in prob}
    refill = [r for r in big if r["makale_id"] not in used]
    guard = 0
    while guard < 80:
        guard += 1
        pg = {r["makale_id"]: gi[r["makale_id"]] for r in prob}
        twin_pair = None
        ids_ = list(pg)
        for i in range(len(ids_)):
            for j in range(i + 1, len(ids_)):
                if D[pg[ids_[i]], pg[ids_[j]]] < a.twin:
                    twin_pair = (ids_[i], ids_[j]); break
            if twin_pair: break
        if not twin_pair:
            break
        ia, ib = twin_pair
        ra = next(r for r in prob if r["makale_id"] == ia)
        rb = next(r for r in prob if r["makale_id"] == ib)
        loser = ra if val(ra) <= val(rb) else rb
        prob = [r for r in prob if r["makale_id"] != loser["makale_id"]]
        pgl = [gi[r["makale_id"]] for r in prob]
        cand = [r for r in refill if r["dil"] != "en" or loser["dil"] == "en"]
        cand = [r for r in cand if min(D[gi[r["makale_id"]], g] for g in pgl) >= a.twin] or \
               [r for r in refill if min(D[gi[r["makale_id"]], g] for g in pgl) >= a.twin]
        if cand:
            add = max(cand, key=lambda r: min(D[gi[r["makale_id"]], g] for g in pgl))
            prob.append(add); refill.remove(add)

    # 4c) saf-ingilizce tavani (EN SON): fazlaysa en dusuk siddetli EN'i at, en uzak tr/mix ile doldur
    used2 = {r["makale_id"] for r in prob}
    trmix_left = [r for r in big if r["makale_id"] not in used2 and r["dil"] != "en"]
    guard = 0
    while sum(1 for r in prob if r["dil"] == "en") > a.en_max and trmix_left and guard < 80:
        guard += 1
        drop = min((r for r in prob if r["dil"] == "en"), key=lambda r: r["_sev"])
        prob = [r for r in prob if r["makale_id"] != drop["makale_id"]]
        pg = [gi[r["makale_id"]] for r in prob]
        add = max(trmix_left, key=lambda r: min(D[gi[r["makale_id"]], p] for p in pg))
        prob.append(add); trmix_left.remove(add)

    prob = prob[:n_prob]
    probg = [gi[r["makale_id"]] for r in prob]

    # 5) kolay: tr/mix adaylardan, 300'un geri kalani, problemliye + birbirine uzak
    kol_cand = [r for r in KA if r["makale_id"] in gi and r["dil"] != "en"
                and min(D[gi[r["makale_id"]], p] for p in probg) >= a.twin]
    for r in kol_cand:
        r["cluster"] = v2.get(r["makale_id"], {}).get("cluster")
    kol = fp(kol_cand, a.toplam - len(prob), seedpool=probg, clustcap=4, prefer_tr=False)

    # ---- birlestir ----
    def mk(r, kaynak):
        src = T.get(r["makale_id"]) or KH.get(r["makale_id"]) or {}
        flags = (r.get("FLAGS") or T.get(r["makale_id"], {}).get("FLAGS") or "").split(";")
        sev, sd = severity(src, flags, kolay=(kaynak == "kolay"))
        vv = v2.get(r["makale_id"], {})
        return {
            "makale_id": r["makale_id"], "kaynak": kaynak,
            "PRIMARY": r.get("PRIMARY") if kaynak == "havuz" else "temiz-tr-taze",
            "TIER": r.get("TIER") if kaynak == "havuz" else "kolay",
            "FLAGS": r.get("FLAGS", "") if kaynak == "havuz" else "",
            "dil": r.get("dil", ""), "year": src.get("year", r.get("year", "")),
            "pages": src.get("pages", r.get("pages", "")),
            "gold_journal": r.get("gold_journal") or src.get("gold_journal", ""),
            "meta_class": vv.get("meta_class", ""), "cluster": vv.get("cluster", ""),
            "sablon_taklit": vv.get("sablon_taklit", ""),
            "sikinti_skoru": sev, "siddet": sd,
            "title_sim": src.get("title_sim", ""), "abstract_sim": src.get("abstract_sim", ""),
            "author_recall": src.get("author_recall", ""),
            "onarilmis_var": src.get("onarilmis_var", "0"),
            "path": r.get("path") or src.get("path", ""),
        }
    merged = [mk(r, "havuz") for r in prob] + [mk(r, "kolay") for r in kol]
    cols = list(merged[0].keys())
    outp = os.path.join(SEC, "benchmark_300.csv")
    with open(outp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(merged)

    def dist(k): return dict(collections.Counter((r.get(k) or "?") for r in merged).most_common())
    L = [f"BENCHMARK {len(merged)}  =  problemli {len(prob)} + kolay {len(kol)}",
         f"farkli sablon ailesi: {len(set(r['cluster'] for r in merged))}",
         f"farkli dergi: {len(set(r['gold_journal'] for r in merged))}",
         f"segmentation gold (TEI): {sum(1 for r in merged if str(r['onarilmis_var'])=='1')}",
         "",
         "dil    : " + json.dumps(dist("dil"), ensure_ascii=False),
         "siddet : " + json.dumps(dist("siddet"), ensure_ascii=False),
         "TIER   : " + json.dumps(dist("TIER"), ensure_ascii=False),
         "meta   : " + json.dumps(dist("meta_class"), ensure_ascii=False),
         "kaynak : " + json.dumps(dist("kaynak"), ensure_ascii=False),
         "", "PRIMARY:"]
    for k, v in dist("PRIMARY").items():
        L.append(f"  {k:20} {v}")
    L.append("")
    L.append("problemli 200 siddet: " + json.dumps(
        dict(collections.Counter(r["siddet"] for r in merged if r["kaynak"] == "havuz")), ensure_ascii=False))
    yb = collections.Counter()
    for r in merged:
        try: y = int(r["year"] or 0)
        except Exception: y = 0
        yb["<=2012" if y and y <= 2012 else "2013-2018" if y <= 2018 else "2019+" if y else "?"] += 1
    L.append("yil    : " + json.dumps(dict(yb), ensure_ascii=False))
    open(os.path.join(SEC, "ozet_300.txt"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L)); print("\n->", outp)

    if a.kopyala:
        pdir = os.path.join(SEC, "pdf300")
        if os.path.isdir(pdir): shutil.rmtree(pdir)
        n = 0
        for r in merged:
            dst = os.path.join(pdir, r["TIER"] or "?", r["PRIMARY"] or "?")
            os.makedirs(dst, exist_ok=True)
            if r["path"] and os.path.exists(r["path"]):
                shutil.copy2(r["path"], os.path.join(dst, f"makale_{r['makale_id']}.pdf")); n += 1
        print(f"{n} PDF -> {pdir}")


if __name__ == "__main__":
    main()
