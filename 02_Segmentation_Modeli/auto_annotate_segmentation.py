#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_annotate_segmentation.py
===============================

GROBID segmentation modeli için `createTrainingSegmentation` çıktısı olan
*.training.segmentation.tei.xml dosyalarını, JSON/kural tabanlı bulgularla
DÜZELTİLMİŞ (ama YOK EDİLMEMİŞ) hale getirir.
"""

import argparse
import glob
import os
import re
import shutil
from lxml import etree

SENTINEL = "\u2028"

# GROBID'in zaten (muhtemelen doğru) verdiği, DOKUNULMAYACAK zone etiketleri.
PRESERVE_TAGS = {"note", "page", "listBibl", "figure", "table"}
# "Kaba" / yeniden değerlendirilecek zone etiketleri.
COARSE_TAGS = {"front", "body", "back", "annex"}

_TR_UP2LOW = {
    "İ": "i", "I": "ı", "Ç": "ç", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö",
    # eski/fontsuz Türkçe PDF'lerde İ->Ý, Ş->Þ, ğ->ð, ı->ý, ş->þ, Ğ->Ð bozulması
    "Ý": "i", "ý": "ı", "Þ": "ş", "þ": "ş", "Ð": "ğ", "ð": "ğ",
}

def tr_lower(text):
    return "".join(_TR_UP2LOW.get(c, c.lower()) for c in text)

INTRO_WORDS = {"giriş", "introduction", "genel bilgiler", "olgu sunumu", "olgu"}
REF_WORDS = {
    "kaynakça", "kaynaklar", "referanslar", "bibliyografya",
    "references", "reference", "kaynakca",
}
NUMBERING_RE = re.compile(r"^[ivxlcdm0-9]{1,4}[\.\)]?\s*", re.IGNORECASE)

def load_tree(path):
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    return etree.parse(path, parser)

def find_text_el(tree):
    root = tree.getroot()
    for el in root.iter():
        if etree.QName(el).localname == "text":
            return el
    return None

def chunk_to_raw(chunk_el):
    parts = [chunk_el.text or ""]
    for child in chunk_el:
        if etree.QName(child).localname == "lb":
            parts.append(SENTINEL)
        else:
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    return "".join(parts)

def get_chunks(text_el):
    chunks = []
    for child in text_el:
        tag = etree.QName(child).localname
        raw = chunk_to_raw(child)
        tail = child.tail or ""
        chunks.append((tag, raw, tail))
    return chunks

def build_flat(chunks):
    pieces = []
    offsets = []
    pos = 0
    n = len(chunks)
    for i, (tag, raw, tail) in enumerate(chunks):
        start = pos
        pieces.append(raw)
        pos += len(raw)
        pieces.append(tail)
        pos += len(tail)
        if i < n - 1:
            pieces.append(SENTINEL)
            pos += 1
        offsets.append((start, pos, tag))
    return "".join(pieces), offsets

def normalize_heading_line(line_text):
    t = tr_lower(line_text).strip()
    t = NUMBERING_RE.sub("", t)
    return t.strip()

def split_lines_with_offsets(flat):
    lines = []
    start = 0
    for i, ch in enumerate(flat):
        if ch == SENTINEL:
            lines.append((start, i))
            start = i + 1
    lines.append((start, len(flat)))
    return lines

def find_heading(flat, target_words, search_from=0, max_len=60):
    for s, e in split_lines_with_offsets(flat):
        if e <= search_from:
            continue
        if e - s > max_len:
            continue
        norm = normalize_heading_line(flat[s:e])
        if norm in target_words:
            return s
    return None

def retag_region(offsets, region_start, region_end, default_tag):
    result = []
    for start, end, tag in offsets:
        s = max(start, region_start)
        e = min(end, region_end)
        if s >= e:
            continue
        new_tag = tag if tag in PRESERVE_TAGS else default_tag
        if result and result[-1][2] == new_tag and result[-1][1] == s:
            result[-1] = (result[-1][0], e, new_tag)
        else:
            result.append((s, e, new_tag))
    return result

def rebuild_tei(chunks, offsets, flat, p_intro, p_ref):
    total_len = len(flat)
    segments = []

    if p_intro is None:
        front_end = 0
        for start, end, tag in offsets:
            if tag == "front":
                front_end = end
            else:
                break
        segments += retag_region(offsets, 0, front_end, "front")
        body_region_start = front_end
    else:
        segments += retag_region(offsets, 0, p_intro, "front")
        body_region_start = p_intro

    if p_ref is None:
        segments += retag_region(offsets, body_region_start, total_len, "body")
    else:
        segments += retag_region(offsets, body_region_start, p_ref, "body")
        segments += retag_region(offsets, p_ref, total_len, "listBibl")

    merged = []
    for s, e, tag in segments:
        if merged and merged[-1][2] == tag and merged[-1][1] == s:
            merged[-1] = (merged[-1][0], e, tag)
        else:
            merged.append((s, e, tag))

    new_chunks = [(tag, flat[s:e]) for s, e, tag in merged]
    return new_chunks

def serialize(tree, text_el, new_chunks):
    for child in list(text_el):
        text_el.remove(child)
    text_el.text = None
    for tag, raw in new_chunks:
        el = etree.SubElement(text_el, tag)
        if tag == "note":
            el.set("place", "headnote")
        parts = raw.split(SENTINEL)
        el.text = parts[0]
        for part in parts[1:]:
            lb = etree.SubElement(el, "lb")
            lb.tail = part
    return etree.tostring(tree, xml_declaration=True, encoding="UTF-8").decode("utf-8")

def process_file(in_path, out_path):
    tree = load_tree(in_path)
    text_el = find_text_el(tree)
    if text_el is None:
        return "HATA: <text> bulunamadı"

    chunks = get_chunks(text_el)
    flat, offsets = build_flat(chunks)

    p_intro = find_heading(flat, INTRO_WORDS, search_from=0)
    p_ref = None
    if p_intro is not None:
        p_ref = find_heading(flat, REF_WORDS, search_from=p_intro)
    else:
        p_ref = find_heading(flat, REF_WORDS, search_from=0)

    new_chunks = rebuild_tei(chunks, offsets, flat, p_intro, p_ref)
    xml_out = serialize(tree, text_el, new_chunks)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_out)

    durum = []
    durum.append("Giriş: BULUNDU" if p_intro is not None else "Giriş: bulunamadı (front/body sınırı DEĞİŞTİRİLMEDİ)")
    durum.append("Kaynakça: BULUNDU" if p_ref is not None else "Kaynakça: bulunamadı (body/listBibl sınırı DEĞİŞTİRİLMEDİ)")
    return " | ".join(durum)

def auto_annotate_segmentation(girdi_klasoru, cikti_klasoru):
    if not os.path.exists(cikti_klasoru):
        os.makedirs(cikti_klasoru)

    xml_dosyalari = glob.glob(os.path.join(girdi_klasoru, "*.training.segmentation.tei.xml"))
    print(f"Toplam {len(xml_dosyalari)} TEI XML bulundu.")

    tam_basarili = 0
    kismi_basarili = 0
    hata = 0

    for dosya in xml_dosyalari:
        dosya_adi = os.path.basename(dosya)
        hedef_dosya = os.path.join(cikti_klasoru, dosya_adi)
        try:
            durum = process_file(dosya, hedef_dosya)
        except Exception as exc:
            print(f"[HATA] {dosya_adi}: {exc}")
            hata += 1
            continue

        if "bulunamadı" in durum:
            kismi_basarili += 1
            print(f"[KISMİ] {dosya_adi}: {durum}")
            nihai_hedef = os.path.join(cikti_klasoru, "kismi_standart")
        else:
            tam_basarili += 1
            print(f"[TAM] {dosya_adi}: {durum}")
            nihai_hedef = os.path.join(cikti_klasoru, "altin_standart")
            
        if not os.path.exists(nihai_hedef):
            os.makedirs(nihai_hedef)
            
        # Taşıma işlemi: Oluşturulan dosyayı doğru alt klasöre taşı
        os.rename(hedef_dosya, os.path.join(nihai_hedef, dosya_adi))

        ham_dosya_adi = dosya_adi.replace(".tei.xml", "")
        ham_dosya = os.path.join(girdi_klasoru.replace("tei", "raw"), ham_dosya_adi)
        if os.path.exists(ham_dosya):
            shutil.copy(ham_dosya, os.path.join(nihai_hedef, ham_dosya_adi))

    print("\nİşlem Tamamlandı!")
    print(f"Tam düzeltilen (Giriş+Kaynakça ikisi de bulundu): {tam_basarili}")
    print(f"Kısmi düzeltilen (biri veya ikisi de bulunamadı, MANUEL KONTROL GEREKİR): {kismi_basarili}")
    print(f"Hata: {hata}")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    default_in = os.path.join(BASE_DIR, "makaleler_segmentation", "grobid_training_out")
    default_out = os.path.join(BASE_DIR, "makaleler_segmentation", "temiz_xml")
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--girdi", default=default_in)
    ap.add_argument("--cikti", default=default_out)
    args = ap.parse_args()
    
    auto_annotate_segmentation(args.girdi, args.cikti)
