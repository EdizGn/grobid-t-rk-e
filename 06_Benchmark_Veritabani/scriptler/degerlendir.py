#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark-300 degerlendirme girisi — HERHANGI bir GROBID surumunu/modelini olcer.

Kullanim:
  # calisan bir GROBID'e 300 PDF'i gonder ve skorla
  python degerlendir.py --ad truba2 --url http://localhost:8072/api/processHeaderDocument

  # zaten uretilmis TEI klasorunu skorla (PDF gondermeden)
  python degerlendir.py --ad truba --tei-dir ../truba_tei

  # iki kosuyu karsilastir
  python degerlendir.py --ad yeni --tei-dir ... --kiyas stok

Cikti: sonuc/<ad>/tei/*.xml , sonuc/<ad>/skor.csv , sonuc/<ad>/rapor.txt

Skorlama scriptler/skor.py'deki tek kanonik metrigi kullanir; boylece her kosu
ayni gold (secim/gold300) ve ayni esiklerle olculur.
"""
import os, sys, csv, glob, json, time, argparse, collections
import statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skor

BASE = r"C:\Users\EG\Desktop\Tubitak___is"
OUT = os.path.join(BASE, "06_Benchmark_Veritabani")
SEC = os.path.join(OUT, "secim")
GOLD300 = os.path.join(SEC, "gold300")
V2 = os.path.join(SEC, "benchmark_300_v2.csv")
SONUC = os.path.join(OUT, "sonuc")


def tei_getir(mid, path, url, cache_dir, timeout=180, deneme=3):
    cache = os.path.join(cache_dir, mid + ".xml")
    if os.path.exists(cache) and os.path.getsize(cache) > 40:
        return open(cache, encoding="utf-8", errors="ignore").read()
    if not url:
        return ""
    import requests
    for k in range(deneme):
        try:
            with open(path, "rb") as fh:
                r = requests.post(url, files={"input": (os.path.basename(path), fh, "application/pdf")},
                                  timeout=timeout)
            if r.status_code == 200 and r.text.strip():
                open(cache, "w", encoding="utf-8").write(r.text)
                return r.text
            if r.status_code in (400, 500, 503):
                open(cache, "w", encoding="utf-8").write("")
                return ""
        except Exception:
            time.sleep(2 * (k + 1))
    return ""


def kosu(ad, url, tei_dir, rows):
    kdir = os.path.join(SONUC, ad)
    cache = tei_dir or os.path.join(kdir, "tei")
    os.makedirs(cache, exist_ok=True)
    os.makedirs(kdir, exist_ok=True)
    out = []
    for i, r in enumerate(rows, 1):
        mid = r["makale_id"]
        g = json.load(open(os.path.join(GOLD300, mid + ".json"), encoding="utf-8"))
        x = tei_getir(mid, r["path"], url, cache)
        t, a, nm = skor.tei_parse(x)
        b = skor.baslik_skor(t, g["titles"])
        y = skor.yazar_skor(nm, g["authors"])
        o = skor.ozet_skor(a, g["abstracts"])
        out.append({
            "makale_id": mid, "TIER": r["TIER"], "PRIMARY": r["PRIMARY"], "dil": r["dil"],
            "siddet": r["siddet"], "metin_katmani": r["metin_katmani"],
            "uretti": int(bool(x.strip())),
            "t_sim": b["sim"], "t_kapsama": b["kapsama"], "t_fazlalik": b["fazlalik"],
            "t_ok": int(b["ok"]), "t_birlesik": int(b["birlesik"]),
            "y_recall": y["recall"], "y_precision": y["precision"], "y_f1": y["f1"],
            "y_siki_f1": y["siki_f1"],
            "y_ok": "" if y["recall"] is None else int(y["recall"] >= skor.AUTHOR_ESIK),
            "o_sim": "" if o is None else o,
            "baslik": t[:150],
        })
        if url and i % 25 == 0:
            print("  %d/%d" % (i, len(rows)))
    with open(os.path.join(kdir, "skor.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return out


def rapor(ad, out, kiyas=None, kiyas_ad=""):
    def f(v, d=0.0):
        try:
            return float(v)
        except Exception:
            return d
    L = ["BENCHMARK 300 — kosu: %s   (%s)" % (ad, time.strftime("%Y-%m-%d %H:%M")),
         "metrik: skor.py | baslik ok = sim>=%.2f VEYA (kapsama>=%.2f ve fazlalik<=%.2f) | yazar ok = recall>=%.2f"
         % (skor.TITLE_SIM_ESIK, skor.TITLE_KAPSAMA_ESIK, skor.TITLE_FAZLALIK_TAVAN, skor.AUTHOR_ESIK), ""]
    n = len(out)
    L.append("cikti uretti: %d/%d" % (sum(r["uretti"] for r in out), n))
    L.append("")
    L.append("### BASLIK ###")
    L.append("  %-22s %5s %8s %8s %8s" % ("kirilim", "n", "cozulen", "%", "ort_sim"))

    def blok(baslik, anahtar):
        L.append("  -- %s --" % baslik)
        gr = collections.defaultdict(list)
        for r in out:
            gr[r[anahtar]].append(r)
        for k in sorted(gr, key=lambda z: -len(gr[z])):
            g = gr[k]
            ok = sum(r["t_ok"] for r in g)
            L.append("  %-22s %5d %8d %7.0f%% %8.3f"
                     % (k, len(g), ok, 100 * ok / len(g), st.mean([f(r["t_sim"]) for r in g])))

    ok = sum(r["t_ok"] for r in out)
    L.append("  %-22s %5d %8d %7.0f%% %8.3f" % ("TOPLAM", n, ok, 100 * ok / n,
                                                st.mean([f(r["t_sim"]) for r in out])))
    for b, k in (("TIER", "TIER"), ("dil", "dil"), ("metin katmani", "metin_katmani"), ("sinif", "PRIMARY")):
        blok(b, k)
    L.append("")
    L.append("  cift dilli birlesik baslik (kapsama kolu ile kurtarilan): %d"
             % sum(r["t_birlesik"] for r in out))
    L.append("")
    L.append("### YAZAR ###")
    rr = [f(r["y_recall"]) for r in out if r["y_recall"] not in ("", None)]
    pp = [f(r["y_precision"]) for r in out if r["y_precision"] not in ("", None)]
    ff = [f(r["y_f1"]) for r in out if r["y_f1"] not in ("", None)]
    sf = [f(r["y_siki_f1"]) for r in out if r["y_siki_f1"] not in ("", None)]
    L.append("  recall=%.3f  precision=%.3f  F1=%.3f  siki_F1=%.3f  cozulen=%d/%d  hic yazar yok=%d"
             % (st.mean(rr), st.mean(pp), st.mean(ff), st.mean(sf),
                sum(1 for r in out if str(r["y_ok"]) == "1"), n,
                sum(1 for r in out if r["y_recall"] == 0)))
    oo = [f(r["o_sim"]) for r in out if r["o_sim"] != ""]
    L.append("")
    L.append("### OZET ###")
    L.append("  ort_sim=%.3f  >=0.70: %d/%d" % (st.mean(oo), sum(1 for x in oo if x >= 0.70), len(oo)))

    if kiyas:
        K = {r["makale_id"]: r for r in kiyas}
        L.append("")
        L.append("### %s vs %s ###" % (kiyas_ad, ad))
        for alan, ka in (("BASLIK", "t_ok"), ("YAZAR", "y_ok")):
            c = collections.Counter()
            for r in out:
                k = K.get(r["makale_id"])
                if not k:
                    continue
                a, b = str(k[ka]) == "1", str(r[ka]) == "1"
                c["ikisi_de_cozdu" if a and b else "yeni_duzeltti" if b and not a
                  else "yeni_bozdu" if a and not b else "ikisi_de_cozemedi"] += 1
            L.append("  %-7s %s" % (alan, dict(c)))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ad", required=True, help="kosu adi (sonuc/<ad>/ altina yazilir)")
    ap.add_argument("--url", default="", help="GROBID processHeaderDocument uc noktasi")
    ap.add_argument("--tei-dir", default="", help="hazir TEI klasoru (<id>.xml)")
    ap.add_argument("--kiyas", default="", help="kiyaslanacak onceki kosu adi, ya da 'stok'")
    a = ap.parse_args()
    if not a.url and not a.tei_dir:
        ap.error("--url ya da --tei-dir gerekli")

    rows = list(csv.DictReader(open(V2, encoding="utf-8-sig")))
    out = kosu(a.ad, a.url, a.tei_dir, rows)

    kiyas = None
    if a.kiyas == "stok":
        kiyas = [{"makale_id": r["makale_id"], "t_ok": r["stok_t_ok"], "y_ok": r["stok_y_ok"]} for r in rows]
    elif a.kiyas:
        p = os.path.join(SONUC, a.kiyas, "skor.csv")
        if os.path.exists(p):
            kiyas = list(csv.DictReader(open(p, encoding="utf-8-sig")))
        else:
            print("uyari: kiyas kosusu bulunamadi: %s" % p)
    txt = rapor(a.ad, out, kiyas, a.kiyas or "")
    open(os.path.join(SONUC, a.ad, "rapor.txt"), "w", encoding="utf-8").write(txt)
    print("\n" + txt)
    print("\n-> sonuc/%s/skor.csv , sonuc/%s/rapor.txt" % (a.ad, a.ad))


if __name__ == "__main__":
    main()
