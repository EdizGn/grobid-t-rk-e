#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Klasor yeniden numaralandigi icin bayatlamis 'path' kolonlarini duzeltir.
   0X_Benchmark_Veritabani -> gercek klasor adi. Her satiri dogrular."""
import os, csv, re, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ...\06_Benchmark_Veritabani
CUR = os.path.basename(HERE)
DOSYALAR = ["kolay_adaylar.csv", "zor_adaylar.csv", "kolay_ham_hepsi.csv",
            os.path.join("secim", "benchmark_300_v2.csv"),
            os.path.join("secim", "benchmark_300.csv")]
RX = re.compile(r"0\d_Benchmark_Veritabani")

for rel in DOSYALAR:
    p = os.path.join(HERE, rel)
    if not os.path.exists(p):
        print(f"  (yok) {rel}"); continue
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    if not rows or "path" not in rows[0]:
        print(f"  (path kolonu yok) {rel}"); continue
    fixed = kayip = 0
    for r in rows:
        old = r.get("path") or ""
        new = RX.sub(CUR, old)
        if new != old:
            r["path"] = new; fixed += 1
        if r["path"] and not os.path.exists(r["path"]):
            kayip += 1
    if fixed:
        shutil.copy2(p, p + ".yedek")
        with open(p, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    print(f"  {rel}: {len(rows)} satir, {fixed} yol duzeltildi, kalan kayip {kayip}"
          + ("  (yedek: .yedek)" if fixed else ""))
print(f"\nhedef klasor adi: {CUR}")
