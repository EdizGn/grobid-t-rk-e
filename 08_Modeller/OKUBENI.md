# Modeller — ne nedir

Bu klasörde **bizim eğittiğimiz modeller ve tüm yedekler** duruyor.
Aktif modeller burada değil, GROBID'in kendi ağacında:
`grobid/grobid-home/models/<model>/model.wapiti`

| Klasör | İçerik |
|---|---|
| `header/` | Header modelleri — eğittiklerimiz + stok referans |
| `header/eski_yedekler/` | Kimliği belirsiz eski yedekler, ölçümde kullanılmaz |
| `segmentation/` | Segmentasyon modelleri |
| `segmentation/eski_yedekler/` | Aynı şekilde |
| `bozuk/` | Kullanılamaz dosyalar, kayıt olsun diye tutuluyor |

**Dosya adı kuralı:** `<sürüm>_<öznitelik sayısı>_<açıklama>.wapiti`. Öznitelik
sayısı isimde yazdığı için dosyanın kimliği adından okunur; aşağıdaki komutla
her zaman doğrulanabilir.

Son güncelleme: 11 Eylül 2026

Öznitelik sayısı her Wapiti modelinin **parmak izidir**: dosyanın ilk baytlarında
`#mdl#2#<sayı>` olarak yazılıdır. Bir dosyanın hangi model olduğundan emin
değilsen isme değil bu sayıya bak:

```bash
head -c 40 model.wapiti | grep -oE '^#mdl#[0-9]+#[0-9]+'
```

Bu tavsiye acı deneyimden geliyor — 8 Eylül'de o zamanki adıyla
`model.wapiti.STOK_YEDEK` olan dosyayı gerçek stok model sanıp bir günlük
ölçümü çöpe attık. Gerçek 0.9.1 stok modeli 15.545 öznitelikli, o dosya ise
10.792. Tam da bu yüzden dosya artık
`eski_yedekler/YANLIS-STOK_10792_0828.wapiti` adını taşıyor.

---

## 1. GROBID'in çalışan CRF modelleri

Bir PDF işlenirken devreye giren zincir. Hepsi Wapiti CRF, dosya adı
`model.wapiti`.

| Model | Öznitelik | Ne yapar |
|---|---|---|
| **segmentation** | 14.232 | **İlk çalışır.** PDF'i bölgelere ayırır: header, gövde, kaynakça, ek |
| **header** | *(bkz. §4)* | Header bölgesinden başlık/yazar/özet/anahtar kelime çıkarır — **bizim eğittiğimiz** |
| fulltext | 19.376 | Gövde yapısı: bölüm, paragraf, şekil/tablo yerleşimi |
| reference-segmenter | 1.726 | Kaynakça bloğunu tek tek künyelere böler |
| citation | 25.992 | Bir künyeyi alanlara ayırır: yazar, başlık, dergi, yıl |
| affiliation-address | 9.095 | Kurum satırını kurum/şehir/ülke olarak parçalar |
| name/header | 4.309 | Header'daki isim dizesini ad/soyad olarak ayırır |
| name/citation | 901 | Künyedeki isim dizesi için ayrı model — biçim farklı olduğu için ayrı eğitilmiş |
| date | 332 | Tarih dizelerini ayrıştırır |
| figure | 521 | Şekil başlıkları ve içeriği |
| table | 1.391 | Tablo başlıkları ve içeriği |
| funding-acknowledgement | 15.784 | Fon ve teşekkür ifadeleri |
| patent/citation | 12.943 | Patent atıfları |

**Projemizi ilgilendiren sadece `segmentation → header` zinciri.** Diğerleri
tam metin işlenirken devreye giriyor; header çıkarımında rol almıyorlar.

## 2. Belge türü varyantları

Aynı görev, farklı belge türü için ayrı eğitilmiş modeller:

| Yol | Öznitelik | Ne için |
|---|---|---|
| header/article/light | 20.911 | Sadeleştirilmiş etiket kümesi |
| header/article/light-ref | 21.245 | Sadeleştirilmiş + kaynakçalı |
| header/sdo/ietf | 880 | IETF standart dokümanları |
| segmentation/article/light | 18.625 | |
| segmentation/article/light-ref | 18.075 | |
| segmentation/sdo/ietf | 995 | |
| fulltext/article/light | 6.150 | |
| fulltext/article/light-ref | 6.150 | |

TR Dizin makalelerinde standart `header` ve `segmentation` kullanılıyor.

## 3. DeLFT (sinirsel) karşılıkları

Aynı görevin sinir ağı sürümleri. İçlerinde `model.wapiti` **yok**;
`config.json` + `model_weights.hdf5` + `preprocessor.json` var (~1.6 MB).

```
header-BidLSTM_CRF_FEATURES          header-BidLSTM_ChainCRF_FEATURES
header-article-light-*               header-article-light-ref-*
citation-BidLSTM_CRF_FEATURES        citation-BidLSTM_ChainCRF_FEATURES
reference-segmenter-*                affiliation-address-BidLSTM_CRF_FEATURES
name-header-*                        name-citation-*
date-*   figure-*   table-BidLSTM_CRF   patent-citation-*
funding-acknowledgement-*
```

Sonek mimariyi gösterir. Bunlar **yalnızca** `grobid.yaml`'da ilgili model için
`engine: "delft"` yazıyorsa okunur. Bizde `WAPITI` olduğu için şu an hiçbiri
kullanılmıyor.

Ayrıca iki GRU sınıflandırıcı var: `copyright_gru` ve `license_gru` — telif ve
lisans ifadelerini sınıflandırır, diğerlerinden farklı mimari.

## 4. Bizim ürettiğimiz dosyalar

Bunlar GROBID'den gelmiyor, bu projede üretildi. 11 Eylül 2026'da dosyalar
yeniden adlandırıldı ve SHA-256 ile doğrulanmış 5 birebir kopya silindi.

### header/

| Dosya | Öznitelik | Nedir |
|---|---|---|
| `stok_15545_imaj091.wapiti` | 15.545 | **Gerçek 0.9.1 stok modeli.** Docker imajından çıkarıldı. Tüm karşılaştırmaların referansı budur |
| `v0_26793_494belge.wapiti` | 26.793 | İlk genişletilmiş korpus (494 belge), 4 Eylül |
| `v1_113397_2999belge_barbun.wapiti` | 113.397 | **v1** etiketlemesi, 2999 belge (2505 altın + 494 eski), TRUBA barbun, 600 iterasyon, 7 Eylül |
| `v4_80603_2153belge_orfoz.wapiti` | 80.603 | **ŞU AN KURULU OLAN.** v4 korpusu (2153 belge), orfoz 56 çekirdek, 2s56dk — temiz koşu |
| `v4_85537_2153belge_barbun.wapiti` | 85.537 | Aynı korpus, barbun'da 40 çekirdekte 56 thread koştu |

### header/eski_yedekler/

| Dosya | Öznitelik | Nedir |
|---|---|---|
| `bilinmeyen_27591_0904.wapiti` | 27.591 | 4 Eylül'de kurulumdan önce alınan yedek, hangi eğitim olduğu bilinmiyor |
| `YANLIS-STOK_10792_0828.wapiti` | 10.792 | ⚠️ **STOK DEĞİL.** Uzun süre stok sanıldı. Bununla yapılan tüm ölçümler geçersiz — başlık F1 1.15, belgelerin %79'unda boş header |

### segmentation/

| Dosya | Öznitelik | Nedir |
|---|---|---|
| `stok_14232_imaj.wapiti` | 14.232 | Stok segmentasyon modeli, imajdan |
| `tr_20803_0908.wapiti` | 20.803 | **ŞU AN KURULU OLAN.** 729 Türkçe makaleyle eğitildi, 8 Eylül |

### segmentation/eski_yedekler/

| Dosya | Öznitelik | Nedir |
|---|---|---|
| `tr_20803_0903.wapiti` | 20.803 | Aynı parmak izi, farklı ağırlıklar → aynı korpusun 3 Eylül'deki daha erken koşusu (çıkarım) |
| `bilinmeyen_18481_0904.wapiti` | 18.481 | 4 Eylül yedeği |
| `bilinmeyen_18481_0828.wapiti` | 18.481 | 28 Ağustos yedeği. Aynı öznitelik sayısı ama **farklı dosya** — eski OKUBENI "aynı" diyordu, SHA-256 bunu yalanladı |
| `bilinmeyen_17495_0828.wapiti` | 17.495 | |
| `bilinmeyen_15321_0828.wapiti` | 15.321 | |

### Silinen kopyalar (11 Eylül)

Beşi de SHA-256 ile birebir aynı olduğu doğrulandıktan sonra silindi, her biri
için özdeş bir dosya klasörde duruyor:

| Silinen | Kalan eşi |
|---|---|
| `header/model_truba.wapiti` | `header/v1_113397_2999belge_barbun.wapiti` |
| `header/model.wapiti.STOK_YEDEK` | `header/eski_yedekler/YANLIS-STOK_10792_0828.wapiti` |
| `segmentation/model.wapiti.EGITILMIS` | `segmentation/tr_20803_0908.wapiti` |
| `segmentation/model.wapiti.ONCEKI` | `segmentation/stok_14232_imaj.wapiti` |
| `segmentation/model.wapiti.STOK_GERI_YUKLE` | `segmentation/stok_14232_imaj.wapiti` |

### Hangi segmentasyon modeli kullanılmalı

İkisinin de yeri var, karıştırmayın:

| Amaç | Model | Neden |
|---|---|---|
| **Üretim / Türkçe belge** | `tr_20803_0908.wapiti` | Türkçede stoktan iyi: anahtar kelime +4.56, özet +2.05 |
| **Header modellerini karşılaştırmak** | `stok_14232_imaj.wapiti` | Segmentasyon sabit kalsın, tek değişken header olsun diye |
| **Türkçe dışı belge** | `stok_14232_imaj.wapiti` | TR modeli İngilizcede stoktan **kötü**: anahtar kelime −11.15, özet −5.24 |

`tr_20803_0908` 729 Türkçe makaleyle eğitildi — genel bir iyileştirme değil,
Türkçe dergi düzenlerine özelleşme. Ölçüm karşılaştırmaları `olcumler/`
altında `TR_v4_600` (stok segmentasyon) ve `TR_v4_trseg` (TR segmentasyon)
dosyalarında.

---

## Uyarılar

**`.new` tuzağı.** Wapiti eğitim çıktısını bazen `model.wapiti.new` olarak
yazar, `model.wapiti` eski haliyle kalır. `model_kur.py` bunu ele alıyor.
Bu klasörde artık `.new` uzantılı dosya yok — hepsi kimliğine göre
adlandırıldı, çöp olanlar `bozuk/` altına alındı.

**Model kurmak için elle kopyalama yapma.** Windows'ta üretilen dosyalar CRLF
satır sonlu olur, Docker içindeki Wapiti sadece LF kabul eder ve
"invalid format" verip çöker. Doğrusu:

```bash
python 01_Header_Modeli/model_kur.py --kaynak 08_Modeller/header/v4_80603_2153belge_orfoz.wapiti
```

Bu betik CRLF→LF dönüşümünü, `.new` kontrolünü, container'a kopyalamayı,
`engine` ayarının wapiti olduğunu doğrulamayı ve yeniden başlatmayı yapar.

**`bozuk/` klasörü.** İki dosya kullanılamaz durumda, silinmedi ama
ayrıldı ki yanlışlıkla kurulmasınlar:

| Dosya | Sorun |
|---|---|
| `header_3255678_duman-testi.wapiti` | 3.255.678 öznitelik — 9 Eylül'de 40 belgelik duman testinden kaldı, gerçek model değil |
| `segmentation_utf16_okunamiyor.wapiti` | UTF-16 kodlu, Wapiti okuyamıyor, öznitelik başlığı bile çıkmıyor |

Diğer tüm dosyalar ölçüm geçmişinin kaydı olduğu için tutuluyor — özellikle
`header/stok_15545_imaj091.wapiti`, çünkü tüm karşılaştırmaların referansı o.
