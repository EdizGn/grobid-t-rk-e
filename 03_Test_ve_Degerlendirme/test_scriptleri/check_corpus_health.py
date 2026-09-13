#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_corpus_health.py
========================

json_tei_duzenleyici.py (auto_annotator.py) ile etiketlemeden ÖNCE, bir klasördeki
TÜM ham *.training.header.tei.xml dosyaları için hızlı bir "kaç JSON alanı
eşleşiyor" ön-kontrolü yapar. Bu, iki farklı sorunu birbirinden ayırt etmenizi
sağlar:

  (a) PIPELINE HATASI  -> çoğu/tüm dosyada eşleşme oranı aniden 0'a düşer
                           (örn. yanlış zone tespiti, bozuk JSON eşlemesi)
  (b) KAYNAK PDF SORUNU -> yalnızca BAZI dosyalarda oran düşük; o belgenin
                           PDF'i muhtemelen ToUnicode tablosu olmayan bir
                           fontla üretilmiş ve pdfalto/GROBID metni temelden
                           yanlış okumuş. Bu durumda hiçbir eşleştirme
                           stratejisi (fuzzy dahil) o belgeyi kurtaramaz —
                           tek çözüm o belgeyi eğitim setinden çıkarmak ya da
                           PDF'i OCR ile yeniden işlemektir.

Kullanım:
    python3 check_corpus_health.py --raw-dir RAW_KLASORU --json-dir JSON_KLASORU

  (raw-dir'deki "makale_12345.training.header.tei.xml" ile json-dir'deki
   "makale_12345.json" eşleştirilir.)

Çıktı: her dosya için title/author eşleşme oranı + genel özet, oranı en düşük
dosyalar en üstte (öncelikle incelemeniz gerekenler).
"""

import argparse
import glob
import json as json_lib
import os
import sys

# auto_annotator.py ile aynı klasörde olmalı
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_annotator import (  # noqa: E402
    load_raw_tree, find_zone, strip_existing_labels, zone_to_raw,
    normalize_with_map, find_all_occurrences, author_name_candidates,
)


def load_record(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json_lib.load(f)
    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        return None
    return hits[0]


def check_one(raw_path, json_path):
    record = load_record(json_path)
    if record is None:
        return None
    src = record["_source"] if "_source" in record else record

    tree = load_raw_tree(raw_path)
    zone = find_zone(tree)
    strip_existing_labels(zone)
    raw = zone_to_raw(zone)
    norm_raw, idx_map = normalize_with_map(raw)

    checks = []

    for ab in src.get("abstracts") or []:
        title = ab.get("title")
        if title:
            hits = find_all_occurrences(raw, norm_raw, idx_map, title, min_len=8, max_hits=1)
            checks.append(("title", bool(hits)))

    for author in src.get("authors") or []:
        name = author.get("inPublicationName") or author.get("name") or ""
        if name.strip():
            cands = author_name_candidates(name)
            hits = find_all_occurrences(raw, norm_raw, idx_map, name, cands, min_len=4, max_hits=1)
            checks.append(("author", bool(hits)))

    if not checks:
        return None
    found = sum(1 for _, ok in checks if ok)
    total = len(checks)
    return found / total, found, total


def main():
    ap = argparse.ArgumentParser(description="Etiketleme öncesi korpus sağlık kontrolü")
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--json-dir", required=True)
    args = ap.parse_args()

    raw_files = sorted(glob.glob(os.path.join(args.raw_dir, "*.training.header.tei.xml")))
    if not raw_files:
        print(f"'{args.raw_dir}' içinde ham dosya bulunamadı.")
        return

    results = []
    for raw_path in raw_files:
        basename = os.path.basename(raw_path)
        try:
            m_id = basename.split("_")[1].split(".")[0]
        except Exception:
            continue
        json_path = os.path.join(args.json_dir, f"makale_{m_id}.json")
        if not os.path.exists(json_path):
            continue
        try:
            res = check_one(raw_path, json_path)
        except Exception as exc:
            print(f"HATA {basename}: {exc}")
            continue
        if res is None:
            continue
        ratio, found, total = res
        results.append((ratio, found, total, basename))

    results.sort(key=lambda r: r[0])  # en düşük oran üstte

    print(f"{'ORAN':>6}  {'BULUNAN/TOPLAM':>15}  DOSYA")
    for ratio, found, total, basename in results:
        print(f"{ratio*100:5.0f}%  {found:>6}/{total:<7}  {basename}")

    if results:
        n = len(results)
        zero = sum(1 for r in results if r[0] == 0)
        low = sum(1 for r in results if 0 < r[0] < 0.5)
        good = sum(1 for r in results if r[0] >= 0.8)
        print("\n" + "=" * 50)
        print(f"Toplam kontrol edilen: {n}")
        print(f"  %0 eşleşme (muhtemelen font/ToUnicode sorunu): {zero}")
        print(f"  Düşük eşleşme (%0-50)                        : {low}")
        print(f"  İyi eşleşme (%80+)                            : {good}")
        print("\nEğer %0 grubu büyükse VE dosyalar rastgele dağılmışsa (belirli bir")
        print("yayın yılı/dergiye özgü değilse), pipeline'da hâlâ sistemik bir sorun")
        print("olabilir (örn. yanlış zone tespiti). Eğer %0 grubu belirli eski/taranmış")
        print("dosyalarda yoğunlaşıyorsa, bu muhtemelen kaynak PDF'in font sorunu —")
        print("bu dosyaları eğitim setinden çıkarmanız gerekir.")


if __name__ == "__main__":
    main()
