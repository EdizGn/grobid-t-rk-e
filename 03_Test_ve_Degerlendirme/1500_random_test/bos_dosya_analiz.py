#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bos_dosya_analiz.py
=====================
Segmentation modelinin <front> ÜRETEMEDİĞİ (tamamen boş header dönen) 338
makalenin ORTAK ÖRÜNTÜSÜNÜ bulmak için analitik script.
"""

import argparse
import csv
import json
import os
import sys
import sqlite3
from pathlib import Path
from collections import Counter

try:
    from pypdf import PdfReader
except ImportError:
    print("HATA: pypdf kurulu değil. Önce şunu çalıştırın: pip install pypdf")
    sys.exit(1)


def read_id_list(path):
    ids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().strip(",")
            if not line:
                continue
            for part in line.split(","):
                part = part.strip()
                if part:
                    ids.append(part)
    return ids


def analyze_pdf(pdf_path):
    result = {
        "dosya_var_mi": False,
        "boyut_kb": None,
        "sayfa_sayisi": None,
        "ort_karakter_sayfa": None,
        "muhtemelen_taranmis": None,
        "hata": "",
    }
    if not pdf_path.exists():
        result["hata"] = "PDF bulunamadı"
        return result

    result["dosya_var_mi"] = True
    result["boyut_kb"] = round(pdf_path.stat().st_size / 1024, 1)

    try:
        reader = PdfReader(str(pdf_path))
        n_pages = len(reader.pages)
        result["sayfa_sayisi"] = n_pages

        sample_pages = reader.pages[: min(3, n_pages)]
        total_chars = 0
        for page in sample_pages:
            try:
                total_chars += len(page.extract_text() or "")
            except Exception:
                pass
        avg_chars = total_chars / max(1, len(sample_pages))
        result["ort_karakter_sayfa"] = round(avg_chars, 1)
        result["muhtemelen_taranmis"] = avg_chars < 100
    except Exception as e:
        result["hata"] = f"PDF okunamadı: {e}"

    return result


def load_db_lookup(db_path):
    lookup = {}
    if not db_path or not Path(db_path).exists():
        return lookup
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, gercek_dergi, gercek_yil FROM orijinal_metadatalar")
        for row in cur.fetchall():
            mid, dergi, yil = row
            lookup[str(mid)] = {
                "dergi": dergi or "",
                "yil": yil or "",
                "accessType": ""
            }
        conn.close()
    except Exception as e:
        print(f"DB okuma uyarısı: {e}")
    return lookup


def load_json_lookup(json_dir):
    lookup = {}
    if not json_dir:
        return lookup
    json_dir = Path(json_dir)
    if not json_dir.exists():
        return lookup

    for jf in json_dir.glob("makale_*.json"):
        try:
            pub_id = jf.stem.split("_", 1)[1]
            data = json.loads(jf.read_text(encoding="utf-8"))
            src = None
            if "hits" in data:
                hits = data.get("hits", {}).get("hits", [])
                if hits:
                    src = hits[0].get("_source", {})
            elif pub_id in data:
                entry = data[pub_id]
                src = entry.get("trdizin_raw_api_metadata") or {}
            if src:
                journal = (src.get("journal") or {}).get("name", "")
                lookup[pub_id] = {
                    "dergi": journal,
                    "yil": src.get("publicationYear", ""),
                    "accessType": src.get("accessType", ""),
                }
        except Exception:
            continue
    return lookup


def find_segmentation_feature_file(seg_dir, article_id):
    if not seg_dir:
        return None
    seg_dir = Path(seg_dir)
    for pattern in (f"makale_{article_id}_training.segmentation",
                     f"makale_{article_id}.training.segmentation"):
        p = seg_dir / pattern
        if p.exists():
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Tam-boş segmentation dosyalarının örüntü analizi")
    ap.add_argument("--id-listesi", required=True, help="Boş dönen makale ID'lerinin listesi")
    ap.add_argument("--pdf-klasoru", required=True, help="PDF'lerin bulunduğu klasör (makale_<id>.pdf)")
    ap.add_argument("--segmentation-klasoru", default=None, help="(opsiyonel) .training.segmentation ham dosyalarının klasörü")
    ap.add_argument("--json-klasoru", default=None, help="(opsiyonel) makale_<id>.json metadata dosyalarının klasörü")
    ap.add_argument("--db", default=None, help="(opsiyonel) test_metadatalar.db sqlite veritabanı yolu")
    ap.add_argument("--out", default="bos_dosya_analiz.csv")
    args = ap.parse_args()

    ids = read_id_list(args.id_listesi)
    print(f"Toplam {len(ids)} ID okundu.")

    pdf_dir = Path(args.pdf_klasoru)
    
    # Metadata lookup (DB veya JSON)
    meta_lookup = {}
    if args.db:
        meta_lookup.update(load_db_lookup(args.db))
    if args.json_klasoru:
        meta_lookup.update(load_json_lookup(args.json_klasoru))

    rows = []
    for article_id in ids:
        pdf_path = pdf_dir / f"makale_{article_id}.pdf"
        info = analyze_pdf(pdf_path)

        seg_file = find_segmentation_feature_file(args.segmentation_klasoru, article_id)
        seg_satir_sayisi = ""
        if seg_file:
            try:
                seg_satir_sayisi = sum(1 for _ in open(seg_file, encoding="utf-8", errors="replace"))
            except Exception:
                seg_satir_sayisi = "okunamadı"

        meta = meta_lookup.get(str(article_id), {})

        rows.append({
            "id": article_id,
            "dosya_var_mi": info["dosya_var_mi"],
            "boyut_kb": info["boyut_kb"],
            "sayfa_sayisi": info["sayfa_sayisi"],
            "ort_karakter_sayfa": info["ort_karakter_sayfa"],
            "muhtemelen_taranmis": info["muhtemelen_taranmis"],
            "segmentation_ham_satir_sayisi": seg_satir_sayisi,
            "dergi": meta.get("dergi", ""),
            "yil": meta.get("yil", ""),
            "accessType": meta.get("accessType", ""),
            "hata": info["hata"],
        })

    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # --- Özet istatistikler ---
    n = len(rows)
    n_missing = sum(1 for r in rows if not r["dosya_var_mi"])
    n_scanned = sum(1 for r in rows if r["muhtemelen_taranmis"] is True)
    page_counts = [r["sayfa_sayisi"] for r in rows if isinstance(r["sayfa_sayisi"], int)]
    n_1page = sum(1 for p in page_counts if p == 1)

    print("\n" + "=" * 50)
    print(f"Toplam analiz edilen: {n}")
    print(f"PDF bulunamayan: {n_missing}")
    print(f"Muhtemelen TARANMIŞ/OCR'sız (metin katmanı yok): {n_scanned} (%{100*n_scanned/n:.1f})")
    print(f"Tek sayfalık (muhtemelen duyuru/erratum): {n_1page} (%{100*n_1page/n:.1f})")
    if page_counts:
        print(f"Ortalama sayfa sayısı: {sum(page_counts)/len(page_counts):.1f}")
        print(f"Medyan sayfa sayısı: {sorted(page_counts)[len(page_counts)//2]}")

    if meta_lookup:
        dergi_sayaci = Counter(r["dergi"] for r in rows if r["dergi"])
        if dergi_sayaci:
            print("\nEn sık geçen dergiler (bu 338 dosya içinde):")
            for dergi, sayi in dergi_sayaci.most_common(10):
                print(f"  {sayi:>3}  {dergi}")
        
        yil_sayaci = Counter(r["yil"] for r in rows if r["yil"])
        if yil_sayaci:
            print("\nYıllara göre dağılım (İlk 5):")
            for yil, sayi in yil_sayaci.most_common(5):
                print(f"  {sayi:>3}  {yil}")

    print(f"\nDetaylı sonuç: {args.out}")


if __name__ == "__main__":
    main()
