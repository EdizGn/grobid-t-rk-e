#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SECICI  -  391 sikintili havuzdan 200 (temiz haric) benchmark adayi
  - temiz sinifi tamamen haric (kolay katman ayrica taze Turkce cekimle gelecek)
  - kucuk siniflar tamamen korunur
  - grobid-crash farthest-point ile 20'ye indirilir (gorsel-aile basina tavan)
  - kalan siniflar birlikte farthest-point + sablon-ailesi tavani (cluster<=3, cluster_fine<=2)
Cikti: secim/benchmark_pool.csv , secim/atlanan.csv , secim/haric_temiz.csv ,
       secim/ozet.txt , secim/segmentation_gold.csv , secim/pdf/<TIER>/<PRIMARY>/makale_<id>.pdf
"""
import os, csv, json, shutil, collections, argparse
import numpy as np

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
PROJE_KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = PROJE_KOK + r""
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
PI_DIR = os.path.join(BASE, r"06_Benchmark_Veritabani\parmak_izi")
OUTSEC = os.path.join(BASE, r"06_Benchmark_Veritabani\secim")
os.makedirs(OUTSEC, exist_ok=True)

HEDEF = 200
EXCLUDE = {"temiz"}
GROBID_CRASH_TAKE = 20          # 40 -> 20
CRASH_FAMILY_CAP = 5           # gorsel aile (cluster) basina en fazla
CLUSTER_CAP = 3               # kalan siniflarda cluster basina
CLUSTER_FINE_CAP = 2         # kalan siniflarda cluster_fine basina
SMALL_CLASS = 16             # bu boyut ve altindaki siniflar tamamen korunur


def load():
    t = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
    f = {r["makale_id"]: r for r in csv.DictReader(open(os.path.join(PI_DIR, "sablon_parmakizi.csv"),
                                                    encoding="utf-8-sig"))}
    meta = json.load(open(os.path.join(PI_DIR, "meta.json"), encoding="utf-8"))
    D = np.load(os.path.join(PI_DIR, "dist_matrix.npy"))
    idx = {mid: i for i, mid in enumerate(meta["ids"])}
    rows = []
    for mid, tr in t.items():
        if mid not in f or mid not in idx:
            continue
        r = dict(tr); r.update({k: v for k, v in f[mid].items() if k not in r})
        r["_gi"] = idx[mid]
        rows.append(r)
    return rows, D


def farthest_point(cand, k, D, cap_key=None, caps=None, seed_gi=None):
    """cand: list[row]; row['_gi'] global index. Return selected list[row], size<=k."""
    if len(cand) <= k:
        return list(cand)
    by_gi = {r["_gi"]: r for r in cand}
    gis = list(by_gi)
    counts = collections.defaultdict(int)

    def ok(gi):
        if not cap_key:
            return True
        r = by_gi[gi]
        for kf, cap in caps.items():
            if counts[(kf, r.get(kf))] >= cap:
                return False
        return True

    def bump(gi):
        if not cap_key:
            return
        r = by_gi[gi]
        for kf in caps:
            counts[(kf, r.get(kf))] += 1

    sel = [seed_gi if seed_gi in by_gi else gis[0]]
    bump(sel[0])
    pool = [g for g in gis if g != sel[0]]
    while len(sel) < k and pool:
        allowed = [g for g in pool if ok(g)]
        search = allowed if allowed else pool
        # argmax min-distance to selected
        best, bestd = None, -1.0
        for g in search:
            d = min(D[g, s] for s in sel)
            if d > bestd:
                bestd, best = d, g
        sel.append(best)
        bump(best)
        pool.remove(best)
    return [by_gi[g] for g in sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedef", type=int, default=HEDEF)
    ap.add_argument("--twin", type=float, default=2.2, help="yakin-ikiz mesafe esigi")
    ap.add_argument("--kopyala", action="store_true", help="PDF'leri secim/pdf altina kopyala")
    a = ap.parse_args()

    rows, D = load()
    print(f"havuz: {len(rows)} satir  (dist matrix {D.shape})")
    cand = [r for r in rows if r["PRIMARY"] not in EXCLUDE]
    temiz = [r for r in rows if r["PRIMARY"] in EXCLUDE]
    byclass = collections.defaultdict(list)
    for r in cand:
        byclass[r["PRIMARY"]].append(r)

    selected, dropped = [], []

    # 1) kucuk siniflar tam korunur
    small_classes = [c for c, v in byclass.items() if len(v) <= SMALL_CLASS and c != "grobid-crash"]
    for c in small_classes:
        selected += byclass[c]

    # 2) grobid-crash -> farthest-point, gorsel aile tavani
    if "grobid-crash" in byclass:
        gc = byclass["grobid-crash"]
        keep = farthest_point(gc, GROBID_CRASH_TAKE, D,
                              cap_key=True, caps={"cluster": CRASH_FAMILY_CAP})
        selected += keep
        dropped += [(r, "grobid-crash fazlasi (gorsel aile)") for r in gc if r not in keep]

    # 3) kalan buyuk siniflar birlikte -> hedefi doldur, sablon tavani
    big = [r for c in byclass for r in byclass[c]
           if c != "grobid-crash" and c not in small_classes]
    kalan_kota = a.hedef - len(selected)
    if kalan_kota < 0:
        # kucuk+crash zaten hedefi asti: buyukleri hic alma, kucukleri kirp
        print(f"UYARI: kucuk siniflar+crash = {len(selected)} > hedef {a.hedef}")
        kalan_kota = 0
    keepbig = farthest_point(big, kalan_kota, D, cap_key=True,
                             caps={"cluster": CLUSTER_CAP, "cluster_fine": CLUSTER_FINE_CAP})
    selected += keepbig
    dropped += [(r, "buyuk sinif farthest-point disi") for r in big if r not in keepbig]

    # 4) GLOBAL yakin-ikiz temizligi: secim ici mesafe < TWIN_THR olan ciftlerden
    #    birini at (nadir PRIMARY + TEI olani koru), sonra havuzdan farthest-point ile doldur
    TWIN_THR = a.twin
    classfreq = collections.Counter(r["PRIMARY"] for r in cand)

    def value(r):  # yuksek = daha degerli, korunur
        return (-classfreq[r["PRIMARY"]], r.get("onarilmis_var") == "1",
                r.get("PRIMARY") not in ("grobid-crash", "taranmis"))

    def twin_pairs(sel):
        gi = {r["makale_id"]: r["_gi"] for r in sel}
        ids_ = list(gi)
        out = []
        for i in range(len(ids_)):
            for j in range(i + 1, len(ids_)):
                d = D[gi[ids_[i]], gi[ids_[j]]]
                if d < TWIN_THR:
                    out.append((d, ids_[i], ids_[j]))
        return sorted(out)

    selmap = {r["makale_id"]: r for r in selected}
    remaining = [r for r in cand if r["makale_id"] not in selmap]
    atilan_ikiz = 0
    while True:
        tp = twin_pairs(list(selmap.values()))
        if not tp:
            break
        d, ida, idb = tp[0]
        loser = ida if value(selmap[ida]) <= value(selmap[idb]) else idb
        r = selmap.pop(loser)
        dropped.append((r, f"yakin-ikiz (mesafe {d:.2f})"))
        atilan_ikiz += 1
        # doldur: kendisi ikiz olmayan + sablon-ailesi tavani asilmamis + tercihen ayni PRIMARY
        selgis = [x["_gi"] for x in selmap.values()]
        clcnt = collections.Counter(x.get("cluster") for x in selmap.values())
        cands = []
        for c2 in remaining:
            if c2["makale_id"] in selmap:
                continue
            if clcnt[c2.get("cluster")] >= 5:
                continue
            dmin = min(D[c2["_gi"], g] for g in selgis)
            if dmin < TWIN_THR:
                continue
            same = c2["PRIMARY"] == r["PRIMARY"]
            cands.append((same, dmin, c2))
        cands.sort(key=lambda t: (t[0], t[1]), reverse=True)
        if cands:
            best = cands[0][2]
            selmap[best["makale_id"]] = best
            remaining.remove(best)
        if atilan_ikiz > 60:
            break
    selected = list(selmap.values())
    print(f"yakin-ikiz temizligi: {atilan_ikiz} degistirildi (esik {TWIN_THR})  -> {len(selected)} belge")

    # ---- TIER yeniden (temiz yok, kolay katman ayri gelecek) ----
    selset = {r["makale_id"] for r in selected}
    selected = [r for r in cand if r["makale_id"] in selset]  # orijinal sirada
    dropped = [(r, w) for (r, w) in dropped if r["makale_id"] not in selset]  # geri alinanlari cikar

    # ---- yaz ----
    cols = ["makale_id", "PRIMARY", "TIER", "FLAGS", "dil", "year", "pages",
            "gold_journal", "journal_dir", "meta_class", "sablon_taklit", "metinsiz",
            "n_cols", "cluster", "cluster_fine", "nn_id", "nn_dist", "onarilmis_var",
            "MODEL_KACIRIYOR", "title_sim", "abstract_sim", "author_recall", "path"]
    with open(os.path.join(OUTSEC, "benchmark_pool.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(selected)
    with open(os.path.join(OUTSEC, "atlanan.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["atlanma_sebebi"], extrasaction="ignore")
        w.writeheader()
        for r, why in dropped:
            rr = dict(r); rr["atlanma_sebebi"] = why
            w.writerow(rr)
    with open(os.path.join(OUTSEC, "haric_temiz.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(temiz)
    seg = [r for r in selected if r.get("onarilmis_var") == "1"]
    with open(os.path.join(OUTSEC, "segmentation_gold.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(seg)

    # ---- ozet ----
    def dist(key):
        return dict(collections.Counter(r.get(key) for r in selected).most_common())
    L = []
    L.append(f"SECIM  -  {len(selected)} belge (hedef {a.hedef}, temiz haric)")
    L.append(f"farkli sablon ailesi (cluster): {len(set(r['cluster'] for r in selected))}")
    L.append(f"farkli dergi: {len(set((r.get('gold_journal') or r['journal_dir']) for r in selected))}")
    L.append(f"sablon_taklit=1: {sum(1 for r in selected if r.get('sablon_taklit')=='1')}")
    L.append(f"segmentation gold (onarilmis TEI hazir): {len(seg)}")
    L.append("")
    L.append("PRIMARY: " + json.dumps(dist("PRIMARY"), ensure_ascii=False))
    L.append("TIER   : " + json.dumps(dist("TIER"), ensure_ascii=False))
    L.append("dil    : " + json.dumps(dist("dil"), ensure_ascii=False))
    L.append("meta   : " + json.dumps(dist("meta_class"), ensure_ascii=False))
    L.append("n_cols : " + json.dumps(dist("n_cols"), ensure_ascii=False))
    yb = collections.Counter()
    for r in selected:
        try:
            y = int(r.get("year") or 0)
        except Exception:
            y = 0
        yb["<=2012" if y and y <= 2012 else "2013-2018" if y <= 2018 else "2019+" if y else "?"] += 1
    L.append("yil    : " + json.dumps(dict(yb), ensure_ascii=False))
    # sinif basina kac sablon
    L.append("")
    L.append("PRIMARY sinifi -> secilen adet / farkli sablon:")
    bp = collections.defaultdict(list)
    for r in selected:
        bp[r["PRIMARY"]].append(r["cluster"])
    for c, cl in sorted(bp.items(), key=lambda x: -len(x[1])):
        L.append(f"  {c:18} {len(cl):3} belge  /  {len(set(cl)):3} sablon")
    # en cok tekrar eden sablon aileleri
    cc = collections.Counter(r["cluster"] for r in selected)
    L.append("")
    L.append("en kalabalik sablon aileleri (secimde): " +
             ", ".join(f"kume{c}:{n}" for c, n in cc.most_common(8)))
    open(os.path.join(OUTSEC, "ozet.txt"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))

    # ---- pdf kopya ----
    if a.kopyala:
        pdir = os.path.join(OUTSEC, "pdf")
        n = 0
        for r in selected:
            dst = os.path.join(pdir, r.get("TIER", "?"), r["PRIMARY"])
            os.makedirs(dst, exist_ok=True)
            src = r["path"]
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst, f"makale_{r['makale_id']}.pdf"))
                n += 1
        print(f"\n{n} PDF kopyalandi -> {pdir}")


if __name__ == "__main__":
    main()
