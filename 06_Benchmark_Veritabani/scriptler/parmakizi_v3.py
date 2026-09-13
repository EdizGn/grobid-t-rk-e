#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v3 parmak izi: 391 havuz + kolay_adaylar + zor_adaylar, ORTAK normalizasyon
   Cikti: parmak_izi/sablon_parmakizi_v3.csv , dist_matrix_v3.npy , meta_v3.json"""
import os, csv, json, math, collections, re
import numpy as np
from sablon_parmakizi import fingerprint, STRUCT_KEYS, PI_DIR, BASE

TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
KOLAY = os.path.join(BASE, r"06_Benchmark_Veritabani\kolay_adaylar.csv")
ZOR = os.path.join(BASE, r"06_Benchmark_Veritabani\zor_adaylar.csv")
JOURNAL_WORDS = re.compile(r"\b(journal|dergi|review|archives|arşivi|bulletin|annales|proceedings|"
                           r"faculty|fakültesi|university|üniversitesi|research|araştırma)\b", re.I)


def rows_from(path, kaynak, defaults):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        d = dict(r)
        d["kaynak"] = kaynak
        for k, v in defaults.items():
            if not d.get(k):
                d[k] = v
        out.append(d)
    return out


def main():
    hav = rows_from(TESHIS, "havuz", {})
    kol = rows_from(KOLAY, "kolay", {"PRIMARY": "temiz-tr-taze", "TIER": "kolay", "FLAGS": "",
                                     "journal_dir": "", "MODEL_KACIRIYOR": "", "onarilmis_var": "0",
                                     "metinsiz": "0"})
    zor = rows_from(ZOR, "taze_zor", {"journal_dir": "", "MODEL_KACIRIYOR": "",
                                      "onarilmis_var": "0", "metinsiz": "0"})
    seen, rows = set(), []
    for r in hav + kol + zor:
        if r["makale_id"] in seen:
            continue
        seen.add(r["makale_id"]); rows.append(r)
    print(f"havuz {len(hav)} + kolay {len(kol)} + taze_zor {len(zor)} -> tekil {len(rows)}")

    fps = []
    for i, r in enumerate(rows, 1):
        if not os.path.exists(r["path"]):
            print("  YOK:", r["path"]); continue
        fp = fingerprint(r["makale_id"], r["path"])
        fp["_row"] = r
        fps.append(fp)
        if i % 100 == 0:
            print(f"  {i}/{len(rows)}")

    ids = [f["makale_id"] for f in fps]
    S = np.full((len(fps), len(STRUCT_KEYS)), np.nan, dtype=np.float32)
    for i, f in enumerate(fps):
        for j, k in enumerate(STRUCT_KEYS):
            v = f.get(k)
            if isinstance(v, (int, float)):
                S[i, j] = v
    cm = np.nanmedian(S, axis=0)
    ind = np.where(np.isnan(S)); S[ind] = np.take(cm, ind[1])
    Sz = np.clip((S - S.mean(0)) / (S.std(0) + 1e-6), -4, 4)
    metinsiz = np.array([1 if (f.get("metinsiz") in (1, "1", True)) else 0 for f in fps])
    Sz[metinsiz == 1] *= 0.10

    V = np.vstack([f["_vis"] for f in fps]).astype(np.float32)
    V = np.clip((V - V.mean(0)) / (V.std(0) + 1e-6), -4, 4)
    V *= math.sqrt(len(STRUCT_KEYS) / V.shape[1])
    X = np.hstack([Sz * 1.4, V * 0.7]).astype(np.float64)

    from sklearn.metrics import pairwise_distances
    from sklearn.cluster import AgglomerativeClustering
    D = pairwise_distances(X, metric="euclidean")
    tri = D[np.triu_indices_from(D, k=1)]
    p5, p10, p25, med = (float(np.percentile(tri, q)) for q in (5, 10, 25, 50))
    ncl = max(20, round(len(fps) / 3.5))
    cl = AgglomerativeClustering(n_clusters=ncl, linkage="ward").fit_predict(X)
    clf = AgglomerativeClustering(n_clusters=round(len(fps) / 2.2), linkage="ward").fit_predict(X)
    csz = collections.Counter(cl)
    print(f"mesafe med={med:.2f} p10={p10:.2f} | ward {ncl} kume, en buyuk {csz.most_common(1)[0][1]}")

    Dn = D.copy(); np.fill_diagonal(Dn, np.inf)
    nn, nnd = Dn.argmin(1), Dn.min(1)

    cols = ["makale_id", "kaynak", "PRIMARY", "TIER", "FLAGS", "dil", "year", "pages",
            "gold_journal", "journal_dir", "meta_class", "producer", "sablon_taklit", "metinsiz",
            "n_cols", "cluster", "cluster_size", "cluster_fine", "nn_id", "nn_dist",
            "title_sim", "abstract_sim", "author_recall", "onarilmis_var", "MODEL_KACIRIYOR", "path"]
    outc = os.path.join(PI_DIR, "sablon_parmakizi_v3.csv")
    with open(outc, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for i, f in enumerate(fps):
            r = f["_row"]
            cg = (f.get("n_cols") == 2 and f.get("margin_t", 1) < 0.11
                  and f.get("title_ratio", 1) < 1.8 and 0.33 < f.get("title_cx", 0.5) < 0.67)
            tk = int(cg and not f.get("commercial_font", 0)
                     and f.get("meta_class") in ("word", "other", "bos") and f.get("generic_font", 0) == 1)
            w.writerow({**{k: r.get(k, "") for k in cols},
                        "makale_id": f["makale_id"], "kaynak": r["kaynak"],
                        "meta_class": f.get("meta_class"), "producer": f.get("producer"),
                        "sablon_taklit": tk, "metinsiz": f.get("metinsiz", 0),
                        "n_cols": f.get("n_cols"), "cluster": int(cl[i]),
                        "cluster_size": int(csz[cl[i]]), "cluster_fine": int(clf[i]),
                        "nn_id": ids[nn[i]], "nn_dist": round(float(nnd[i]), 3),
                        "path": r["path"]})
    np.save(os.path.join(PI_DIR, "dist_matrix_v3.npy"), D)
    json.dump({"ids": ids, "p5": p5, "p10": p10, "p25": p25, "med": med},
              open(os.path.join(PI_DIR, "meta_v3.json"), "w"), ensure_ascii=False, indent=1)
    kk = collections.Counter(f["_row"]["kaynak"] for f in fps)
    print(f"-> {outc}\n-> dist_matrix_v3.npy {D.shape}   kaynak: {dict(kk)}")


if __name__ == "__main__":
    main()
