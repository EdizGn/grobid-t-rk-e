# TR Dizin Header Benchmark — 300 belge

TR Dizin makalelerinde başlık / yazar / özet çıkarımını ölçen, zorluk katmanlı
bir referans kümesi. Türkçe ağırlıklıdır (172 tr / 73 en / 55 mix) — TR Dizin'in
gerçek dil dağılımını yansıtması için bilinçli olarak böyle seçilmiştir.

## Ne var

| Yol | İçerik |
|---|---|
| `secim/pdf300/<TIER>/<PRIMARY>/makale_<id>.pdf` | 300 PDF, zorluk ve sıkıntı sınıfına göre klasörlenmiş |
| `secim/gold300/<id>.json` | **Referans veri (gold)** — tek şema, 300/300 kapsam |
| `secim/benchmark_300_v2.csv` | Ana tablo: etiketler + stok/TRUBA skorları + metin katmanı teşhisi |
| `secim/ozet_v2.txt` | Özet rapor |
| `secim/segmentation_gold.csv` | Onarılmış TEI'si hazır 31 belge (segmentation eğitimi/testi için) |
| `render_p1/<id>.png` | 1. sayfa görüntüsü (300/300) — gözle kontrol için |
| `parmak_izi/` | Şablon parmak izi + mesafe matrisi (çeşitlilik seçiminde kullanıldı) |
| `secim/benchmark_300.csv` | v1 tablo (tarihsel; skorları eski metrikle) |

`gold300/<id>.json` şeması:

```json
{"titles": ["TR başlık", "EN başlık", ...], "abstracts": [...],
 "authors": ["Ad Soyad", ...], "year": 2020, "journal": "...", "doi": "", "found": true}
```

Başlık ve yazar 300/300 belgede dolu; özet 298/300 (`1334937`, `1225818` boş —
bu ikisi özet metriğinde skorlanmaz). DOI 133 belgede boş.

## Kompozisyon

- **TIER**: kolay 120 · orta 67 · zor 113
- **Şiddet**: hafif 164 · orta 93 · ağır 43
- **Dil**: tr 172 · en 73 · mix 55
- **Üretim aracı**: other 99 · InDesign 76 · Word 66 · LaTeX 42 · boş 16 · scan 1
- **Çeşitlilik**: 239 farklı dergi, 170 farklı şablon ailesi, birebir aynı PDF yok
- **Yıl**: 1997–2026 (medyan 2020) — ≤2012: 71 · 2013–2018: 53 · 2019+: 176
- 4.355 sayfa, ~284 MB

Sıkıntı sınıfları (`PRIMARY`) çok etiketlidir; tam liste `FLAGS` kolonunda,
180 problemli belgenin 107'si birden fazla sıkıntı taşır.

## Metrik — `scriptler/skor.py`

Tek kanonik modül. Her koşu aynı gold ve aynı eşiklerle ölçülür.

**Başlık** üç sayı üretir:

- `sim` — difflib oranı, gold başlık varyantlarının en iyisi
- `kapsama` — tahmin, bir gold başlığın tüm token'larını içeriyor mu (0–1)
- `fazlalik` — gold başlığa göre fazladan token oranı (0 = tıpatıp)

Karar: **`sim ≥ 0.70` VEYA (`kapsama ≥ 0.90` ve `fazlalik ≤ 1.30`)**

İkinci kol, TR+EN başlık bloğunu bitişik döndüren *doğru* çıkarımları kurtarır.
`fazlalik` tavanı, "tüm sayfayı başlık diye yapıştır" tipi çıktıların puan
kazanmasını engeller. İki ayrı gold başlık birden kapsanıyorsa `birlesik=1`
işaretlenir.

**Yazar**: gevşek eşleşme (≥3 harfli ortak token) ve sıkı eşleşme (soyad
eşitliği + en az bir ortak token) için ayrı ayrı recall / precision / F1.
Karar eşiği: gevşek recall ≥ 0.50.

**Özet**: gold özet varyantlarına karşı en iyi difflib oranı.

## Yeni bir modeli ölçmek

```bash
python scriptler/degerlendir.py --ad yeni_model --url http://localhost:8072/api/processHeaderDocument --kiyas stok
```

Hazır TEI klasörü varsa PDF göndermeden:

```bash
python scriptler/degerlendir.py --ad yeni_model --tei-dir /yol/tei --kiyas stok
```

Çıktı: `sonuc/<ad>/skor.csv` (belge başına) ve `sonuc/<ad>/rapor.txt`
(TIER / dil / metin katmanı / sınıf kırılımları + kıyas tablosu).
`--kiyas stok` referans GROBID ile, `--kiyas <baska_kosu>` önceki bir koşuyla
karşılaştırır.

## Referans sonuçlar (v2 metrik)

Stok GROBID 0.9.1-crf — başlık çözülen belge:

| TIER | n | stok | TRUBA header modeli |
|---|---|---|---|
| kolay | 120 | 113 (94%) | 94 (78%) |
| orta | 67 | 51 (76%) | 34 (51%) |
| zor | 113 | 15 (13%) | 22 (19%) |
| **toplam** | **300** | **179 (60%)** | **150 (50%)** |

Yazar: stok recall 0.660 / F1 0.469 · TRUBA recall 0.163 / F1 0.168.
TRUBA modeli 300 belgenin 244'ünde hiç yazar döndürmüyor; TEI'lerin 163'ünde
`<author>` etiketi hiç yok, 80 belgede başlığı doğru bulup yazarı hiç
etiketlemiyor. Bu, serileştirme değil model davranışıdır ve önce bu
araştırılmalıdır.

## v1 → v2'de ne değişti, neden

1. **Tek gold.** Stok skorları tek başlıklı `gold` ile, TRUBA skorları çok
   başlıklı `gold2` ile hesaplanmıştı; karşılaştırma stok aleyhine eğikti
   (14 belgede stok haksız yere düşük puan almıştı). Artık ikisi de `gold300`.
2. **Çift dilli başlık.** `sim` dağılımında 0.60–0.70 bandında 40 belgelik
   yığılma vardı; bunlar GROBID'in TR+EN başlığı bitişik döndürdüğü *doğru*
   çıkarımlardı. Kapsama kolu 41'ini kurtardı (38'i `birlesik` işaretli).
   Stok başlık başarısı 47% → 60%, kolay katmanda 69% → 94%.
   Sonuç niteliksel olarak da değişti: v1'de TRUBA başlıkta nötr görünüyordu
   (53 düzeltti / 50 bozdu), v2'de net gerileme (28 düzeltti / 57 bozdu).
3. **Yazar metriği** recall'a ek olarak precision/F1 ve sıkı eşleşme.
4. **Metin katmanı ölçümle teşhis edildi** (`metin_katmani` kolonu):
   `metinsiz` 20 · `bozuk_kodlama` 13 · `kismen_bozuk` 1 · `saglam` 266.
   Buna göre 5 belge `taranmis` → `bozuk-font` olarak düzeltildi (metin
   katmanları var, sadece kodlaması bozuk; gerçek taranmışlar `grobid-crash`
   grubunda ve orada metin hiç yok). `618882`'nin FLAGS'ine `bozuk-font`
   eklendi.
5. **`makale_29094.pdf`** başındaki 128 baytlık çöp ön-ek ve sondaki NUL dolgu
   temizlendi (orijinali `makale_29094.pdf.bozuk` olarak duruyor). Dosya
   `%PDF-` ile başlamadığı için katı ayrıştırıcılar reddediyordu — bu,
   `ozet-eksik` test niyetine karışan istenmeyen bir bozulmaydı.
6. **`segmentation_gold.csv`** yenilendi; eski dosya bir önceki seçim turundan
   kalmaydı (26 satır, 24'ü 300'de). Yenisi 300 içindeki 31 onarılmış TEI'yi
   XML yoluyla listeler.

Düzeltmelerin tam dökümü: `secim/duzeltme_log.txt`.

## Bilinen sınırlar

- **`95366`** kolay katmanda ama metin kodlaması bozuk. `kolay_supheli=1` ile
  işaretlendi, PDF yerinde bırakıldı — 120 sayısını bozmamak için. Değiştirilmek
  istenirse `kolay_adaylar.csv` havuzundan yerine bir belge seçilmeli.
- **Kolay katmanda saf İngilizce belge yok** (106 tr + 14 mix). Zor katmanda
  39 en + 37 mix var. Bu, TIER ile dili birbirine karıştırır: `en`/`mix`
  belgelerdeki düşük skorun zorluktan mı dilden mi geldiği bu tasarımla
  ayrıştırılamaz. Dil dağılımının Türkçe ağırlıklı kalması istendiği için
  kabul edilmiş bir sınırdır; dil etkisi ayrıca ölçülecekse kolay katmana bir
  miktar temiz İngilizce belge eklemek gerekir.
- **7 belge** şablon ikiz eşiğinin (2.2) altında, en yakın çift 0.41 mesafede
  (`1159082`–`1190046`). Nadir sınıflar bütün alındığı için ikiz filtresi
  atlanmış; çeşitlilik açısından ihmal edilebilir ama not edilmiştir.
- **Stok TEI 280/300** belgede var; eksik 20 belge `grobid-crash` sınıfı,
  GROBID gerçekten çıktı üretmiyor (metin katmanı yok, OCR şart).
- `benchmark_300.csv` (v1) tarihsel referans olarak duruyor; yeni ölçümlerde
  `benchmark_300_v2.csv` kullanılmalı.

## Script'ler

| Script | İş |
|---|---|
| `skor.py` | Kanonik metrik + TEI ayrıştırma + gold yükleme |
| `degerlendir.py` | Yeni model koşusu + rapor (**günlük kullanım burası**) |
| `yeniden_skorla.py` | v1 → v2 yeniden skorlama, gold birleştirme, metin katmanı teşhisi |
| `duzeltmeler.py` | Etiket/PDF düzeltmeleri (idempotent) |
| `benchmark_kur.py` | 300'ü havuzdan seçen kurucu (tarihsel) |
| `sablon_parmakizi.py` | Şablon parmak izi ve mesafe matrisi |
