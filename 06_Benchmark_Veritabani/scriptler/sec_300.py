#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BENCHMARK 300 = kilitli 200 (secim/benchmark_pool.csv) + 100 kolay-tr-taze
  kolay 100: kolay_adaylar icinden farthest-point
    - 200'e mesafesi TWIN altinda olan atlanir (problemli-benzeri istemeyiz)
    - sablon-ailesi tavani (cluster_v2) tum 300 uzerinde <= KAP
    - dergi basina <= 3
Cikti: secim/benchmark_300.csv , secim/ozet_300.txt , (--kopyala) secim/pdf300/<TIER>/<PRIMARY>/
"""
import os, csv, json, shutil, collections, argparse
import numpy as np

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
OUT = os.path.join(BASE, r"06_Benchmark_Veritabani")
PI = os.path.join(OUT, "parmak_izi")
SEC = os.path.join(OUT, "secim")
POOL200 = os.path.join(SEC, "benchmark_pool.csv")

TWIN = 2.2
CLUSTER_KAP = 4
DERGI_KAP = 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kolay-hedef", type=int, default=100)
    ap.add_argument("--twin", type=float, default=TWIN)
    ap.add_argument("--kopyala", action="store_true")
    a = ap.parse_args()

    v2 = {r["makale_id"]: r for r in csv.DictReader(open(os.path.join(PI, "sablon_parmakizi_v2.csv"), encoding="utf-8-sig"))}
    meta = json.load(open(os.path.join(PI, "meta_v2.json"), encoding="utf-8"))
    D = np.load(os.path.join(PI, "dist_matrix_v2.npy"))
    gi = {m: i for i, m in enumerate(meta["ids"])}

    p200 = list(csv.DictReader(open(POOL200, encoding="utf-8-sig")))
    ids200 = [r["makale_id"] for r in p200]
    S200 = [gi[m] for m in ids200 if m in gi]
    print(f"kilitli 200: {len(ids200)}  (v2'de {len(S200)})")

    kolay = [r for r in v2.values() if r.get("kaynak") == "kolay" and r["makale_id"] in gi]
    print(f"kolay aday: {len(kolay)}")

    # 200'e cok yakin kolaylari ele
    def dmin_to_200(mid):
        g = gi[mid]
        return float(min(D[g, s] for s in S200))
    kolay = [r for r in kolay if dmin_to_200(r["makale_id"]) >= a.twin]
    print(f"  200'e uzak (>= {a.twin}) kalan: {len(kolay)}")

    # sablon + dergi sayaci: 200'den baslat
    clcnt = collections.Counter(v2[m]["cluster"] for m in ids200 if m in v2)
    jcnt = collections.Counter((v2[m].get("gold_journal") or v2[m].get("journal_dir")) for m in ids200 if m in v2)

    sel = []
    selg = []
    # seed: 200'e en uzak kolay
    kolay.sort(key=lambda r: -dmin_to_200(r["makale_id"]))
    pool = kolay[:]

    def can(r):
        if clcnt[r["cluster"]] >= CLUSTER_KAP:
            return False
        j = r.get("gold_journal") or r.get("journal_dir")
        if j and jcnt[j] >= DERGI_KAP:
            return False
        return True

    while pool and len(sel) < a.kolay_hedef:
        # aday: mevcut secim(kolay)+hicbirine cok yakin degil, farthest
        best, bestd = None, -1.0
        relax = False
        for r in pool:
            if not can(r):
                continue
            g = gi[r["makale_id"]]
            d = dmin_to_200(r["makale_id"]) if not selg else min(min(D[g, s] for s in selg),
                                                                 dmin_to_200(r["makale_id"]))
            if d > bestd:
                bestd, best = d, r
        if best is None:                     # tavanlar doldu -> gevset
            for r in pool:
                g = gi[r["makale_id"]]
                d = dmin_to_200(r["makale_id"]) if not selg else min(min(D[g, s] for s in selg),
                                                                     dmin_to_200(r["makale_id"]))
                if d > bestd:
                    bestd, best = d, r
            relax = True
        sel.append(best)
        selg.append(gi[best["makale_id"]])
        clcnt[best["cluster"]] += 1
        j = best.get("gold_journal") or best.get("journal_dir")
        if j:
            jcnt[j] += 1
        pool.remove(best)
    print(f"secilen kolay: {len(sel)}  (tavan gevsetildi: {relax if sel else '-'})")

    # ---- birlestir + yaz ----
    cols = ["makale_id", "kaynak", "PRIMARY", "TIER", "FLAGS", "dil", "year", "gold_journal",
            "journal_dir", "meta_class", "sablon_taklit", "metinsiz", "n_cols",
            "cluster", "cluster_fine", "nn_id", "nn_dist", "onarilmis_var",
            "title_sim", "abstract_sim", "author_recall", "path"]

    def rowify(r):
        return {k: r.get(k, "") for k in cols}

    merged = []
    for r in p200:
        vr = v2.get(r["makale_id"], {})
        m = rowify({**r, **{k: vr.get(k) for k in ("kaynak", "cluster", "cluster_fine", "nn_id", "nn_dist", "meta_class", "sablon_taklit")}})
        m["kaynak"] = "havuz"
        merged.append(m)
    for r in sel:
        m = rowify(r)
        m["kaynak"] = "kolay"
        merged.append(m)

    outp = os.path.join(SEC, "benchmark_300.csv")
    with open(outp, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(merged)

    # ---- ozet ----
    def dist(key, rows=merged):
        return dict(collections.Counter((r.get(key) or "?") for r in rows).most_common())
    L = [f"BENCHMARK 300  =  {len(merged)} belge  (havuz {len(p200)} + kolay {len(sel)})",
         f"farkli sablon ailesi (cluster_v2): {len(set(r['cluster'] for r in merged))}",
         f"farkli dergi: {len(set((r.get('gold_journal') or r.get('journal_dir')) for r in merged))}",
         f"segmentation gold (TEI hazir): {sum(1 for r in merged if str(r.get('onarilmis_var'))=='1')}",
         "",
         "TIER : " + json.dumps(dist("TIER"), ensure_ascii=False),
         "dil  : " + json.dumps(dist("dil"), ensure_ascii=False),
         "meta : " + json.dumps(dist("meta_class"), ensure_ascii=False),
         "kaynak:" + json.dumps(dist("kaynak"), ensure_ascii=False),
         "",
         "PRIMARY:"]
    for k, v in dist("PRIMARY").items():
        L.append(f"  {k:20} {v}")
    cc = collections.Counter(r["cluster"] for r in merged)
    L.append("")
    L.append("en kalabalik sablon aileleri: " + ", ".join(f"k{c}:{n}" for c, n in cc.most_common(8)))
    yb = collections.Counter()
    for r in merged:
        try:
            y = int(r.get("year") or 0)
        except Exception:
            y = 0
        yb["<=2012" if y and y <= 2012 else "2013-2018" if y <= 2018 else "2019+" if y else "?"] += 1
    L.append("yil  : " + json.dumps(dict(yb), ensure_ascii=False))
    open(os.path.join(SEC, "ozet_300.txt"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("\n->", outp)

    if a.kopyala:
        pdir = os.path.join(SEC, "pdf300")
        n = 0
        for r in merged:
            dst = os.path.join(pdir, r.get("TIER") or "?", r.get("PRIMARY") or "?")
            os.makedirs(dst, exist_ok=True)
            if os.path.exists(r["path"]):
                shutil.copy2(r["path"], os.path.join(dst, f"makale_{r['makale_id']}.pdf"))
                n += 1
        print(f"{n} PDF -> {pdir}")


if __name__ == "__main__":
    main()
