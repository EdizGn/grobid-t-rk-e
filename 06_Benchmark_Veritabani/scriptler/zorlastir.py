#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZORLASTIRILMIS BENCHMARK (v3)
  Kaynak: parmak_izi/sablon_parmakizi_v3.csv (855 belge) + dist_matrix_v3.npy
  Bloklar:
    AGIR  : taranmis / bozuk-font / grobid-crash  (OCR gerektirenler dahil)
    ZOR   : header-title-yok, baslik-dergi-adi, karakter-anomali, baslik-yanlis(zor), govde-yok
    ORTA  : baslik-yanlis(orta), ozet-eksik, ozet-yok, yazar-eksik, baslik-cift-dilli, dusuk-benzerlik
    KOLAY : temiz-tr-taze
  Her blokta farthest-point + sablon-ailesi tavani + yakin-ikiz filtresi.
Cikti: secim/benchmark_300_v3.csv , secim/ozet_v3.txt , (--kopyala) secim/pdf300_v3/
"""
import os, csv, json, shutil, collections, argparse
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.dirname(HERE)
PI = os.path.join(HERE, "parmak_izi")
SEC = os.path.join(HERE, "secim")
TESHIS = os.path.join(BASE, r"03_Test_ve_Degerlendirme\benchmark_teshis\teshis_refined.csv")
KH = os.path.join(HERE, "kolay_ham_hepsi.csv")

AGIR_SINIF = {"taranmis", "bozuk-font", "grobid-crash"}
ZOR_SINIF = {"header-title-yok", "baslik-dergi-adi", "karakter-anomali", "govde-yok"}
ORTA_SINIF = {"ozet-eksik", "ozet-yok", "yazar-eksik", "baslik-cift-dilli", "dusuk-benzerlik"}
SUPHELI = {"95366"}      # kolay katmanda duran bozuk-kodlamali belge (v2 isaretledi)


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
    ap.add_argument("--kolay", type=int, default=70)
    ap.add_argument("--agir", type=int, default=70)
    ap.add_argument("--orta", type=int, default=60)
    ap.add_argument("--twin", type=float, default=2.2)
    ap.add_argument("--agir-aile", type=int, default=8)
    ap.add_argument("--dergi", type=int, default=2, help="dergi basina tavan (normal bloklar)")
    ap.add_argument("--agir-dergi", type=int, default=4, help="dergi basina tavan (agir blok)")
    ap.add_argument("--kopyala", action="store_true")
    a = ap.parse_args()

    V = list(csv.DictReader(open(os.path.join(PI, "sablon_parmakizi_v3.csv"), encoding="utf-8-sig")))
    meta = json.load(open(os.path.join(PI, "meta_v3.json"), encoding="utf-8"))
    D = np.load(os.path.join(PI, "dist_matrix_v3.npy"))
    gi = {m: i for i, m in enumerate(meta["ids"])}
    T = {r["makale_id"]: r for r in csv.DictReader(open(TESHIS, encoding="utf-8-sig"))}
    K = {r["makale_id"]: r for r in csv.DictReader(open(KH, encoding="utf-8-sig"))}

    for r in V:
        mid = r["makale_id"]
        src = T.get(mid) or K.get(mid) or {}
        r["_src"] = src
        r["_sev"], r["_sd"] = severity(src, (r.get("FLAGS") or "").split(";"),
                                      kolay=(r["kaynak"] != "havuz"))
    V = [r for r in V if r["makale_id"] in gi and r["makale_id"] not in SUPHELI
         and r["PRIMARY"] != "temiz" and os.path.exists(r["path"])]

    def bucket(r):
        p = r["PRIMARY"]
        if p in AGIR_SINIF: return "agir"
        if p == "temiz-tr-taze": return "kolay"
        if p in ZOR_SINIF: return "zor"
        if p == "baslik-yanlis": return "zor" if r["TIER"] == "zor" else "orta"
        if p in ORTA_SINIF: return "orta"
        return None

    pools = collections.defaultdict(list)
    for r in V:
        b = bucket(r)
        if b: pools[b].append(r)
    print("havuzlar:", {k: len(v) for k, v in pools.items()})

    jrn_global = collections.Counter()        # dergi sayaci  - TUM secim boyunca ortak
    clc_global = collections.Counter()        # sablon ailesi - TUM secim boyunca ortak

    def fp(cands, k, seed=None, clustcap=3, twin=0.0, prefer_tr=True, dergicap=2):
        if k <= 0 or not cands: return []
        idx = {r["makale_id"]: gi[r["makale_id"]] for r in cands}
        rr = {r["makale_id"]: r for r in cands}
        def jof(m):
            j = (rr[m].get("gold_journal") or rr[m].get("journal_dir") or "").strip()
            return j or "(dergi-adi-yok)"      # bos dergi adi da tavana tabi
        def al(m):
            jrn_global[jof(m)] += 1; clc_global[rr[m]["cluster"]] += 1
        base0 = list(seed or [])
        if base0:
            first = max(idx, key=lambda m: min(D[idx[m], s] for s in base0))
        else:
            first = max(idx, key=lambda m: rr[m]["_sev"])
        sel = [first]; al(first)
        pool = [m for m in idx if m != first]
        while pool and len(sel) < k:
            base = base0 + [idx[m] for m in sel]
            def dm(m): return min(D[idx[m], b] for b in base)
            # DERGI TAVANI KATIDIR - asla gevsemez. Sablon tavani ve ikiz esigi gevseyebilir.
            dergi_ok = [m for m in pool if jrn_global[jof(m)] < dergicap]
            if not dergi_ok:
                break                      # bu bloktan daha fazla alinamaz; kota zor bloguna kalir
            allowed = [m for m in dergi_ok if dm(m) >= twin and clc_global[rr[m]["cluster"]] < clustcap]
            if not allowed:                # once sablon tavanini gevset
                allowed = [m for m in dergi_ok if dm(m) >= twin]
            if not allowed:                # sonra ikiz esigini gevset
                allowed = dergi_ok
            m = max(allowed, key=lambda m: dm(m) - (0.4 if prefer_tr and rr[m]["dil"] == "en" else 0))
            sel.append(m); pool.remove(m); al(m)
        return [rr[m] for m in sel]

    sel = []
    # 1) AGIR blok (OCR gerektirenler) - taranmis az dergiden geldigi icin dergi/aile tavani gevsek
    sel += fp(pools["agir"], a.agir, clustcap=a.agir_aile, twin=a.twin,
              prefer_tr=False, dergicap=a.agir_dergi)
    g = [gi[r["makale_id"]] for r in sel]
    # 2) ORTA blok
    sel += fp(pools["orta"], a.orta, seed=g, clustcap=3, twin=a.twin, dergicap=a.dergi)
    g = [gi[r["makale_id"]] for r in sel]
    # 3) KOLAY blok
    sel += fp(pools["kolay"], a.kolay, seed=g, clustcap=3, twin=a.twin,
              prefer_tr=False, dergicap=a.dergi)
    g = [gi[r["makale_id"]] for r in sel]
    # 4) ZOR blok - kalan kotayi doldurur
    sel += fp(pools["zor"], a.toplam - len(sel), seed=g, clustcap=3, twin=a.twin, dergicap=a.dergi)

    # ---- yaz ----
    cols = ["makale_id", "kaynak", "PRIMARY", "TIER", "FLAGS", "dil", "year", "pages",
            "gold_journal", "meta_class", "cluster", "sablon_taklit", "sikinti_skoru", "siddet",
            "title_sim", "abstract_sim", "author_recall", "onarilmis_var", "path"]
    out = []
    for r in sel:
        d = {k: r.get(k, "") for k in cols}
        d["sikinti_skoru"], d["siddet"] = r["_sev"], r["_sd"]
        for k in ("title_sim", "abstract_sim", "author_recall"):
            d[k] = r["_src"].get(k, "")
        d["onarilmis_var"] = r["_src"].get("onarilmis_var", "0")
        out.append(d)
    p = os.path.join(SEC, "benchmark_300_v3.csv")
    with open(p, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(out)

    def dist(k): return dict(collections.Counter((r.get(k) or "?") for r in out).most_common())
    agir_n = sum(1 for r in out if r["PRIMARY"] in AGIR_SINIF)
    L = [f"BENCHMARK v3 (zorlastirilmis) — {len(out)} belge",
         f"  AGIR blok (taranmis/bozuk-font/grobid-crash): {agir_n}  (%{100*agir_n//len(out)})",
         f"  farkli sablon ailesi: {len(set(r['cluster'] for r in out))}",
         f"  farkli dergi: {len(set(r['gold_journal'] for r in out))}",
         f"  segmentation gold (TEI): {sum(1 for r in out if str(r['onarilmis_var'])=='1')}", "",
         "kaynak : " + json.dumps(dist("kaynak"), ensure_ascii=False),
         "TIER   : " + json.dumps(dist("TIER"), ensure_ascii=False),
         "siddet : " + json.dumps(dist("siddet"), ensure_ascii=False),
         "dil    : " + json.dumps(dist("dil"), ensure_ascii=False),
         "meta   : " + json.dumps(dist("meta_class"), ensure_ascii=False), "", "PRIMARY:"]
    for k, v in dist("PRIMARY").items():
        L.append(f"  {k:20} {v}")
    cc = collections.Counter(r["cluster"] for r in out)
    L.append("")
    L.append("en kalabalik sablon aileleri: " + ", ".join(f"k{c}:{n}" for c, n in cc.most_common(6)))
    S = [gi[r["makale_id"]] for r in out]
    Dl = D[np.ix_(S, S)].copy(); np.fill_diagonal(Dl, np.inf)
    L.append(f"yakin-ikiz (komsu<{a.twin}): {int((Dl.min(1) < a.twin).sum())}")
    txt = "\n".join(L)
    open(os.path.join(SEC, "ozet_v3.txt"), "w", encoding="utf-8").write(txt)
    print("\n" + txt + f"\n\n-> {p}")

    if a.kopyala:
        pd = os.path.join(SEC, "pdf300_v3")
        if os.path.isdir(pd): shutil.rmtree(pd)
        n = 0
        for r in out:
            dst = os.path.join(pd, r["TIER"] or "?", r["PRIMARY"] or "?")
            os.makedirs(dst, exist_ok=True)
            shutil.copy2(r["path"], os.path.join(dst, f"makale_{r['makale_id']}.pdf")); n += 1
        print(f"{n} PDF -> {pd}")


if __name__ == "__main__":
    main()
