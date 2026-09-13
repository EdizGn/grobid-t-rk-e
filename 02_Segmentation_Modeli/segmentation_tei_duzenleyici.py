# -*- coding: utf-8 -*-
"""
mutlak_segmentation_tei_duzenleyici
====================================

GROBID SEGMENTATION modeli eğitim üçlüsünü (*.rawtxt, *.segmentation,
*_segmentation_tei.xml) doğrulayan; front/body/listBibl gibi kritik
bloklar eksik/bozuksa TRDizin JSON'unu "ground truth" kabul ederek
sıfırdan (ya da kısmen) tutarlı bir TEI iskeleti üreten araç.

TASARIM İLKELERİ
-----------------
1) RAWLAR DOKUNULMAZ: *.rawtxt ve *.segmentation (özellik/etiket) dosyaları
   asla düzenlenmez / üzerine yazılmaz. Onlar zaten "gerçek" belge
   metnidir; bozukluk hep TEI (etiketleme) tarafındadır.
2) HİZALAMA KRİTİKTİR: GROBID segmentation eğitimi, rawtxt'teki her
   satırı TEI XML içindeki karşılık gelen bloğun etiketiyle eşleştirir.
   Bu yüzden üretilen/onarılan TEI'nin, satır satır (boş satırlar hariç)
   rawtxt ile birebir aynı metni içermesi ZORUNLUDUR. Script bunu
   `validate()` ile ölçer, `rebuild_front_body_listbibl()` ile de bunu
   bozmadan onarır (metne tek bir karakter bile eklemez/çıkarmaz,
   sadece <front>/<body>/<listBibl>/<note>/<page> zarflarını yeniden
   dağıtır).
3) SADECE İŞE YARAYAN PARÇALAR: header/fulltext/references/table/figure
   gibi diğer alt-modellerin training çıktıları segmentation eğitiminde
   KULLANILMAZ; sadece çapraz-teşhis (diagnostik) amacıyla okunabilir
   (örn. figure modelinin gövde metnini yanlışlıkla yutup yutmadığını
   raporlamak gibi) — segmentation TEI'sine asla enjekte edilmez.

KULLANIM
--------
    python3 segmentation_tei_duzenleyici.py <klasör> [--json meta.json]

    <klasör> içinde "<isim>_training.segmentation" (feature dosyası,
    opsiyonel), "<isim>_training_segmentation.rawtxt" ve
    "<isim>_training_segmentation_tei.xml" üçlüsünü otomatik bulur,
    her biri için validate() çalıştırır; sorunlu olanları --json ile
    verilen TRDizin JSON'u kullanarak (varsa) onarır ve
    "<isim>_segmentation_tei.FIXED.xml" olarak yazar. Sağlam dosyalara
    dokunmaz.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------
# 1. TRDizin JSON'undan "ground truth" meta çıkarımı
# --------------------------------------------------------------------------

@dataclass
class GroundTruth:
    titles: list[str] = field(default_factory=list)          # TR + EN başlık
    abstracts: list[str] = field(default_factory=list)       # TR + EN özet
    authors: list[str] = field(default_factory=list)         # "Hakan ÇELİK" vb.
    keywords_lines: list[str] = field(default_factory=list)  # ham anahtar kelime satırları


def load_json_meta(json_path: Path) -> GroundTruth:
    """TRDizin arama-API çıktısından (hits[0]._source) meta alanlarını çeker."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    hits = data.get("hits", {}).get("hits") if isinstance(data.get("hits"), dict) else data.get("hits")
    if not hits:
        return GroundTruth()
    source = hits[0].get("_source", {})

    gt = GroundTruth()
    for ab in source.get("abstracts") or []:
        if ab.get("title"):
            gt.titles.append(ab["title"].strip())
        if ab.get("abstract"):
            gt.abstracts.append(ab["abstract"].strip())
        if ab.get("keywords"):
            gt.keywords_lines.append(str(ab["keywords"]).strip())
    for au in source.get("authors") or []:
        name = au.get("inPublicationName")
        if name:
            gt.authors.append(name.strip())
    return gt


# --------------------------------------------------------------------------
# 2. rawtxt <-> TEI hizalama doğrulaması
# --------------------------------------------------------------------------

LB_TAG = re.compile(r"<lb/?>")
ANY_TAG = re.compile(r"<[^>]+>")
TEXT_BLOCK = re.compile(r"<text[^>]*>(.*)</text>", re.S)

REQUIRED_TOP_LEVEL = ("front", "body", "listBibl")


def _tr_upper(s: str) -> str:
    """Python'un str.upper() metodu Türkçe 'i' harfini İngilizce kuralıyla
    'I' yapar (İ değil) — bu yüzden 'Bireysel'.upper() ile metindeki
    'BİREYSEL' asla birebir eşleşmez. Karşılaştırma amaçlı Türkçe-güvenli
    büyütme burada yapılır (yalnız eşleştirme için; TEI'ye yazılan metne
    dokunulmaz)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


@dataclass
class ValidationReport:
    name: str
    well_formed: bool = True
    has_front: bool = False
    has_body: bool = False
    has_listBibl: bool = False
    tag_counts: dict = field(default_factory=dict)
    raw_nonempty_lines: int = 0
    tei_nonempty_lines: int = 0
    mismatches: list = field(default_factory=list)  # (index, raw_line, tei_line)

    @property
    def aligned(self) -> bool:
        return (
            self.raw_nonempty_lines == self.tei_nonempty_lines
            and not self.mismatches
        )

    @property
    def ok(self) -> bool:
        return (
            self.well_formed
            and self.has_front
            and self.has_body
            and self.has_listBibl
            and self.aligned
        )

    def summary(self) -> str:
        lines = [f"[{self.name}]"]
        if not self.well_formed:
            lines.append("  ✗ XML iyi biçimlendirilmemiş (well-formed değil)")
        for tag in REQUIRED_TOP_LEVEL:
            present = getattr(self, f"has_{tag}")
            lines.append(f"  {'✓' if present else '✗'} <{tag}> bloğu {'var' if present else 'YOK'}")
        lines.append(f"  Blok sayıları: {self.tag_counts}")
        lines.append(
            f"  Hizalama: raw={self.raw_nonempty_lines} satır, "
            f"tei={self.tei_nonempty_lines} satır, "
            f"uyumsuz={len(self.mismatches)}"
        )
        lines.append(f"  SONUÇ: {'SAĞLAM ✅' if self.ok else 'ONARIM GEREKİYOR ⚠️'}")
        return "\n".join(lines)


def _extract_tei_lines(tei_text: str) -> tuple[list[str], dict]:
    """TEI içindeki <text>...</text> gövdesini satırlara ayırır (<lb/> -> \\n)
    ve tüm etiketleri atarak düz metin satırlarını döndürür. Ayrıca üst
    seviye etiket sayımını da döner."""
    m = TEXT_BLOCK.search(tei_text)
    if not m:
        return [], {}
    inner = m.group(1)

    tag_counts: dict = {}
    for tag in re.findall(r"<(\w+)(?:\s+[^>]*)?>", inner):
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    plain = LB_TAG.sub("\n", inner)
    plain = ANY_TAG.sub("", plain)
    plain = html.unescape(plain)
    lines = [ln.strip() for ln in plain.split("\n")]
    return lines, tag_counts


def validate(rawtxt_path: Path, tei_path: Path) -> ValidationReport:
    name = tei_path.name
    report = ValidationReport(name=name)

    try:
        tei_text = tei_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        report.well_formed = False
        return report

    tei_lines, tag_counts = _extract_tei_lines(tei_text)
    report.tag_counts = tag_counts
    report.has_front = tag_counts.get("front", 0) > 0
    report.has_body = tag_counts.get("body", 0) > 0
    report.has_listBibl = tag_counts.get("listBibl", 0) > 0

    raw_text = rawtxt_path.read_text(encoding="utf-8")
    raw_lines = [ln.strip() for ln in raw_text.split("\n")]

    raw_nonempty = [ln for ln in raw_lines if ln]
    tei_nonempty = [ln for ln in tei_lines if ln]
    report.raw_nonempty_lines = len(raw_nonempty)
    report.tei_nonempty_lines = len(tei_nonempty)

    for i, (a, b) in enumerate(zip(raw_nonempty, tei_nonempty)):
        if a != b:
            report.mismatches.append((i, a, b))
            if len(report.mismatches) >= 20:  # rapor şişmesin
                break

    return report


# --------------------------------------------------------------------------
# 3. Bozuk dosyalar için: front / body / listBibl iskeletini yeniden kurma
# --------------------------------------------------------------------------

# Kaynakça başlangıcını tespit etmek için sık kullanılan başlıklar
REFERENCE_HEADINGS = re.compile(
    r"^(KAYNAKÇA|KAYNAKLAR|REFERENCES|BİBLİYOGRAFYA|BIBLIOGRAPHY)\s*$",
    re.IGNORECASE,
)

# Gövdenin başladığını gösteren tipik "1. GİRİŞ" / "1. INTRODUCTION" kalıpları
BODY_START = re.compile(
    r"^(1\.?\s*(GİRİŞ|GIRIS|INTRODUCTION)\b)", re.IGNORECASE
)


def _find_running_headers(raw_lines: list[str], min_repeat: int = 3) -> set[str]:
    """Akademik PDF'lerde her sayfanın üstünde/altında tekrar eden başlık/
    dergi adı gibi satırları tespit eder (örn. makale başlığı her sayfada
    üst bilgi olarak basılmışsa). Bu satırlar, front/kaynakça sınırı
    ararken YANLIŞ İPUCU verir (belgenin sonuna kadar 'başlık' görünür),
    bu yüzden sınır tespitinden dışlanır."""
    from collections import Counter
    counts = Counter(ln.strip() for ln in raw_lines if ln.strip())
    return {line for line, n in counts.items() if n >= min_repeat and len(line) > 8}


def _locate_front_end(raw_lines: list[str], gt: GroundTruth) -> int:
    """Front bloğunun bitiş indexini döndürür.

    ÖNCELİK SIRASI (öğrenilen ders: PDF'ten çıkan ham metinde cümleler
    satır ortasında bölünür — örn. 'at the end ' / 'of current research.'
    iki ayrı satıra düşebilir — bu yüzden özet/başlık METİN PARÇACIĞI
    eşleştirmesi tek başına GÜVENİLMEZ; sık geçen ortak ifadeler de
    (örn. 'müşteri ilişkileri') gövdenin derinliklerinde yanlış eşleşme
    üretebilir. Bunun yerine en güvenilir sinyal, '1. GİRİŞ' / '1.
    INTRODUCTION' gibi FİZİKSEL bölüm başlığıdır — akademik makalelerde
    front matter neredeyse istisnasız bundan önce biter):

      1) '1. GİRİŞ'/'1. INTRODUCTION' başlığı bulunursa -> DOĞRUDAN onu
         kullan (en güvenilir).
      2) Bulunamazsa: JSON başlık/özetinin (running header'lar hariç)
         belgede geçtiği en son nokta -> zayıf yedek sinyal.
      3) O da yoksa: belgenin ilk %25'i (güvenli varsayılan).
    """
    for i, line in enumerate(raw_lines):
        if BODY_START.search(line.strip()):
            return i

    running_headers = _find_running_headers(raw_lines)
    best_idx = -1

    for title in gt.titles:
        words = title.split()
        if len(words) < 3:
            continue
        snippet = " ".join(words[:5])[:40]
        if not snippet:
            continue
        for i, line in enumerate(raw_lines):
            if line.strip() in running_headers:
                continue
            if _tr_upper(snippet) in _tr_upper(line):
                best_idx = max(best_idx, i)
                break  # sadece ilk geçiş

    for abstract in gt.abstracts:
        words = abstract.split()
        if len(words) < 6:
            continue
        tail_snippet = " ".join(words[-6:])[:40]
        for i, line in enumerate(raw_lines):
            if tail_snippet[:15] and tail_snippet[:15] in line:
                best_idx = max(best_idx, i)

    if best_idx >= 0:
        return best_idx + 1

    return max(1, len(raw_lines) // 4)


def _locate_references_start(raw_lines: list[str]) -> Optional[int]:
    for i, line in enumerate(raw_lines):
        if REFERENCE_HEADINGS.match(line.strip()):
            return i
    return None


def rebuild_front_body_listbibl(
    raw_text: str, gt: GroundTruth
) -> str:
    """Bozuk/eksik bir segmentation TEI'sinin yerine, rawtxt'i HİÇ
    değiştirmeden (tek karakter bile eklemeden/çıkarmadan) front/body/
    listBibl zarflarına yeniden dağıtan minimal-ama-geçerli bir TEI
    üretir. Sayfa içi tekrar eden üstbilgi/altbilgi (<note>) veya sayfa
    numarası (<page>) ayrımı burada YAPILMAZ — bu, gerçek GROBID eğitim
    verisindeki ince taneli (sayfa başına) yapının yerini tutmaz; sadece
    "hiç front/body/listBibl yoktu" felaketini önleyen bir GÜVENLİ TABAN
    (fallback) iskeletidir. Elle ince ayar için başlangıç noktasıdır.
    """
    # rawtxt'i blok bloklarına ayırmadan, olduğu gibi satırlara bölüyoruz;
    # boş satırlar orijinal blok sınırlarını korumak için <lb/> olarak DEĞİL,
    # paragraf arası boşluk olarak bırakılıyor (rawtxt formatıyla tutarlı).
    lines = raw_text.split("\n")

    front_end = _locate_front_end(lines, gt)
    refs_start = _locate_references_start(lines)
    if refs_start is None or refs_start <= front_end:
        refs_start = len(lines)  # kaynakça bulunamazsa hepsini body'e bırak

    def wrap(segment_lines: list[str]) -> str:
        # rawtxt'teki satırları <lb/> ile birleştir; boş satırları da koru
        # ki hizalama (validate) sonradan satır satır birebir tutsun.
        out = []
        for ln in segment_lines:
            out.append(ln)
            out.append("<lb/>")
        return "".join(
            (ln + ("" if ln == "<lb/>" else "")) for ln in out
        )

    def xml_escape(s: str) -> str:
        # rawtxt içinde '<1 Yıl', 'A & B' gibi ham metinler geçebilir;
        # bunlar TEI içine gömülürken kaçırılmazsa XML'i bozar / validate()
        # aşamasında satırları kaydırır. html.unescape ile validate() bunu
        # geri çözer, dolayısıyla hizalama korunur.
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def join_raw(seg: list[str]) -> str:
        pieces = []
        for ln in seg:
            if ln == "":
                pieces.append("\n")
            else:
                pieces.append(xml_escape(ln) + " <lb/>\n")
        return "".join(pieces)

    front_seg = lines[:front_end]
    body_seg = lines[front_end:refs_start]
    refs_seg = lines[refs_start:]

    parts = ['<?xml version="1.0" ?>', '<tei xml:space="preserve">']
    parts.append("\t<teiHeader>\n\t\t<fileDesc/>\n\t</teiHeader>")
    parts.append('\t<text xml:lang="tr">')
    parts.append("\t\t<front>" + join_raw(front_seg) + "</front>")
    parts.append("\t\t<body>" + join_raw(body_seg) + "</body>")
    if refs_seg:
        parts.append("\t\t<listBibl>" + join_raw(refs_seg) + "</listBibl>")
    parts.append("\t</text>")
    parts.append("</tei>")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# 4. Diğer alt-modellerde (figure vb.) gövde metni sızıntısı teşhisi
#    (Segmentation TEI'sine ENJEKTE EDİLMEZ — sadece raporlanır.)
# --------------------------------------------------------------------------

SECTION_HEADING_LEAK = re.compile(
    r"(H\s*\d+\s*:|(?<!\d)\d\.\d+\.\s+[A-ZÇĞİÖŞÜ])"
)


def scan_figure_leakage(figure_tei_path: Path) -> list[str]:
    """figure modeli eğitim TEI'sinde, gerçek bir şekil/figür açıklaması
    yerine hipotez cümleleri / bölüm başlıkları gibi GÖVDE METNİ
    sızıntısı olup olmadığını tespit eder. Sadece bilgi amaçlıdır;
    segmentation eğitimini etkilemez."""
    if not figure_tei_path.exists():
        return []
    content = figure_tei_path.read_text(encoding="utf-8")
    warnings = []
    for i, block in enumerate(re.findall(r"<figure>.*?</figure>", content, re.S)):
        plain = html.unescape(ANY_TAG.sub(" ", block))
        if SECTION_HEADING_LEAK.search(plain) and len(plain) > 800:
            warnings.append(
                f"  figure[{i}]: {len(plain)} karakter — muhtemelen gövde metni "
                f"'figure' olarak yanlış etiketlenmiş (örn: "
                f"{plain.strip()[:80]!r}...)"
            )
    return warnings


def cross_check_header_against_json(header_tei_path: Path, gt: GroundTruth) -> list[str]:
    """header alt-modelinin çıktısındaki <docTitle>/<docAuthor> alanlarını,
    ELLE DOĞRULANMIŞ JSON'daki başlık/yazar listesiyle karşılaştırır.
    JSON gold kabul edildiğinden burada bir fark bulunması, segmentation
    değil header modelinin (veya PDF katmanının) hatalı olduğu anlamına
    gelir. Segmentation TEI'sine hiç dokunmaz — yalnız raporlar."""
    if not header_tei_path.exists():
        return []
    content = header_tei_path.read_text(encoding="utf-8")
    warnings = []

    title_match = re.search(r"<titlePart>(.*?)</titlePart>", content, re.S)
    extracted_title = html.unescape(ANY_TAG.sub(" ", title_match.group(1))).strip() if title_match else ""
    extracted_title_norm = _tr_upper(re.sub(r"\s+", " ", extracted_title))

    if gt.titles:
        if not any(
            _tr_upper(re.sub(r"\s+", " ", t))[:20] in extracted_title_norm
            or extracted_title_norm[:20] in _tr_upper(re.sub(r"\s+", " ", t))
            for t in gt.titles
        ):
            warnings.append(
                f"  BAŞLIK uyuşmuyor -> header modeli: {extracted_title[:70]!r} "
                f"| JSON (gold): {gt.titles[0][:70]!r}"
            )

    author_match = re.search(r"<docAuthor>(.*?)</docAuthor>", content, re.S)
    extracted_authors = html.unescape(ANY_TAG.sub(" ", author_match.group(1))).strip() if author_match else ""
    for au in gt.authors:
        last_name = au.split()[-1] if au.split() else au
        if last_name and _tr_upper(last_name) not in _tr_upper(extracted_authors):
            warnings.append(f"  YAZAR JSON'da var ama header çıktısında bulunamadı: {au!r}")

    return warnings


# --------------------------------------------------------------------------
# 5. CLI
# --------------------------------------------------------------------------

def find_triplets(folder: Path):
    """<isim>_training_segmentation.rawtxt / _segmentation_tei.xml
    çiftlerini klasörde bulur."""
    for rawtxt in sorted(folder.glob("*_training_segmentation.rawtxt")):
        stem = rawtxt.name[: -len("_training_segmentation.rawtxt")]
        tei = folder / f"{stem}_training_segmentation_tei.xml"
        yield stem, rawtxt, tei


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--json", type=Path, default=None, help="TRDizin JSON dosyası (isteğe bağlı, onarım için)")
    ap.add_argument("--fix", action="store_true", help="Sorunlu dosyalar için .FIXED.xml üret")
    args = ap.parse_args()

    gt = load_json_meta(args.json) if args.json else GroundTruth()

    any_broken = False
    for stem, rawtxt_path, tei_path in find_triplets(args.folder):
        report = validate(rawtxt_path, tei_path)
        print(report.summary())

        fig_tei = args.folder / f"{stem}_training_figure_tei.xml"
        leaks = scan_figure_leakage(fig_tei)
        if leaks:
            print("  --- ilişkili figure modelinde teşhis (segmentation'a dokunmaz) ---")
            print("\n".join(leaks))

        if gt.titles or gt.authors:
            header_tei = args.folder / f"{stem}_training_header_tei.xml"
            header_warnings = cross_check_header_against_json(header_tei, gt)
            if header_warnings:
                print("  --- header modeli JSON (gold) ile uyuşmuyor (segmentation'a dokunmaz) ---")
                print("\n".join(header_warnings))

        if not report.ok:
            any_broken = True
            if args.fix:
                raw_text = rawtxt_path.read_text(encoding="utf-8")
                fixed = rebuild_front_body_listbibl(raw_text, gt)
                out_path = args.folder / f"{stem}_segmentation_tei.FIXED.xml"
                out_path.write_text(fixed, encoding="utf-8")
                fixed_report = validate(rawtxt_path, out_path)
                print(f"  -> onarım yazıldı: {out_path.name}  ({'SAĞLAM ✅' if fixed_report.ok else 'HALA SORUNLU ⚠️'})")
        print()

    sys.exit(1 if any_broken else 0)


if __name__ == "__main__":
    main()
