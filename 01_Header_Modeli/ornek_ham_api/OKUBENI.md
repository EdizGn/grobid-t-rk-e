# TR Dizin ham API cevabı — 14 makalelik örnek

Bu üç dosya, TR Dizin API'sinin **tam cevabını** saklayan tek yerdir.

Toplayıcı betikler (`header_metadata_cek.py`,
`04_Genisletilmis_Egitim/adim1_veri_topla.py`) API'den geleni ayrıştırıp
veritabanına yalnızca **10 alan** yazıyor:

```
id, dosya_adi, gercek_baslik, gercek_ozet, gercek_yazarlar,
gercek_anahtar_kelimeler, gercek_yil, gercek_dergi, gercek_doi, durum
```

Ham cevapta ise **~38 alan** var. Veritabanına girmeyen, ama ileride işe
yarayabilecek olanlar:

| Alan | Ne işe yarayabilir |
|---|---|
| `authors` | Yazarların kurumları ve şehirleri — `affiliation-address` modeli eğitmek için |
| `facetAuthorInstitution`, `facetAuthorCity`, `facetAuthorCountry` | Kurum normalizasyonu |
| `subjects` | Konu başlıkları — alan bazlı hata analizi |
| `references`, `citedReferences` | Kaynakça — `citation` modeli eğitmek için |
| `language`, `docType`, `publicationType` | Belge türüne göre ayrıştırma |
| `startPage`, `endPage`, `issue` | Künye alanları |
| `projectnumber`, `projectGroup` | Fon bilgisi — `funding-acknowledgement` için |

## Dosyalar

| Dosya | Makale |
|---|---|
| `secili_makaleler_metadata.json` | 3 |
| `yuksek_id_makaleler_metadata.json` | 3 |
| `8_makale_1163610_1180311_metadata.json` | 8 |

Yapı: `{ "<id>": { "pub_id", "db_record", "trdizin_raw_api_metadata" } }`

## Neden önemli

Projede yazar alanı bir duvara tosladı: model vakaların %47.6'sında hiç
yazar üretmiyor ve etiket kalitesini düzeltmek bunu çözmedi. Kurum
satırlarının yazar bloğuna karışması sorunun bir parçası.
`trdizin_raw_api_metadata.authors` alanı her yazarın kurumunu ayrı ayrı
veriyor — yani yeni veri toplamadan, sadece API'den gelen alanı saklayarak
kurum/yazar ayrımı için etiketli veri üretilebilir.

Bunu yapmak için `adim1_veri_topla.py`'nin ham cevabı da diske yazması yeterli.
Şu an atıyor.
