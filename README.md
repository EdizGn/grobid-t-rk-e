# GROBID'in Türkçe Akademik Makalelere Uyarlanması

TÜBİTAK projesi. TR Dizin'deki Türkçe makalelerden başlık, yazar, özet ve
anahtar kelime çıkarmak için GROBID'in `header` ve `segmentation` modellerinin
yeniden eğitilmesi.

Son güncelleme: 11 Eylül 2026

---

## Özet: ne yapıldı, ne elde edildi

GROBID stok haliyle Türkçe makalelerde zayıf kalıyordu. TR Dizin'in kendi
metadatasını "altın veri" olarak kullanıp elle etiketleme yapmadan 2153
belgelik bir eğitim korpusu ürettik ve iki modeli yeniden eğittik.

**En iyi yapılandırma vs stok GROBID** (1435 Türkçe makale, Levenshtein ≥0.80, F1):

| Alan | Stok | Bizim | Fark |
|---|---|---|---|
| Başlık | 57.31 | **76.64** | **+19.33** |
| Yazar | 27.70 | **34.77** | **+7.07** |
| Özet | 70.25 | **76.26** | **+6.01** |
| Anahtar kelime | 25.68 | 22.22 | −3.46 |
| İlk yazar | 30.58 | 28.57 | −2.01 |

Ölçülen gürültü tabanı: başlık/özet/anahtar kelime ±0.6, yazar ±2.2 puan.
Buna göre ilk üç satır gerçek kazanç, dördüncü gerçek kayıp, beşinci gürültü.

**Kullanılması gereken modeller:**

| Model | Dosya | Öznitelik |
|---|---|---|
| header | `08_Modeller/header/v4_80603_2153belge_orfoz.wapiti` | 80.603 |
| segmentation | `08_Modeller/segmentation/tr_20803_0908.wapiti` | 20.803 |

---

## Bu depoda ne var, ne yok

Depo **yalnızca kodu ve ölçüm sonuçlarını** taşır (140 dosya, ~6 MB).
Proje diskte ~34 GB; geri kalanı üretilmiş veridir ve bilerek dışarıda
bırakıldı.

| Dışarıda | Neden | Nasıl edinilir |
|---|---|---|
| `grobid/` (9,9 GB) | GROBID'in kendisi, bizim işimiz değil | `docker pull grobid/grobid:0.9.1-crf` |
| Makale PDF'leri (~10.000) | Telifli akademik makaleler, halka açık depoya konulamaz | `04_Genisletilmis_Egitim/adim1_veri_topla.py` TR Dizin'den indirir |
| Eğitilmiş modeller (830 MB) | Bazıları 100 MB'ı aşıyor, GitHub reddeder | GitHub **Releases** bölümünden indirin |
| Eğitim/XML çıktıları | Betiklerden yeniden üretilebilir | `adim2_createTraining.sh` → `adim3_etiketle.py` → `adim4_korpusa_kur.py` |
| `05_TRUBA/paket*.tar.gz` (770 MB) | Derleme çıktısı | `05_TRUBA/` betikleri yeniden üretir |
| `00_Eski_Arsiv/` (6,3 GB) | Eski deneme arşivi, içinde 10.000 PDF var | — |

### Sıfırdan kurulum (depoyu klonlayan biri için)

Depo kendi kendine yeter: aşağıdaki adımlar kimseye bir şey sormadan
tamamlanır.

```bash
git clone <depo-adresi> && cd <depo>

# 1) GROBID
docker pull grobid/grobid:0.9.1-crf

# 2) Eğitilmiş modeller (Releases'ten, indirince parmak iziyle doğrulanır)
python 08_Modeller/model_indir.py --kur

# 3) Makaleleri indir -- hangi makale hangi kümede, kume_listeleri/ söyler
python 04_Genisletilmis_Egitim/adim1_veri_topla.py

# 4) Ölçüm
python 03_Test_ve_Degerlendirme/grobid_standart_eval.py --diakritik-yoksay
```

### Kümeler `kume_listeleri/` altında

Hangi makalenin test, hangisinin eğitim kümesinde olduğu bilgisi sadece
`.db` dosyalarının içindeydi; onlar da depoya giremiyor. Bu yüzden her küme
düz bir kimlik listesine döküldü:

| Dosya | Makale | Nedir |
|---|---|---|
| `test_1500.txt` | 1500 | **Ölçüm referansı.** Tüm TR ölçümleri bunun üzerinde |
| `egitim_v4_2153.txt` | 2153 | Kurulu header modelinin eğitildiği belgeler |
| `havuz_3992.txt` | 3992 | Genişletilmiş eğitim havuzu |
| `altin_test_300.txt` | 300 | Elle doğrulama havuzu (50'si doğrulandı) |
| `ingilizce_519.txt` | 519 | İngilizce kıyas kümesi (PMC) |
| `karantina_1051.txt` | 1051 | Etiketleyicinin elediği, eğitimde görülmemiş belgeler |

`python kume_listesi_uret.py` bu listeleri yeniden üretir ve **kesişim
kontrolü** yapar. Kontrol bir sızıntı buldu: `1229729` hem `test_1500`'de hem
`egitim_v4_2153`'te. Kaynağı eski 546'lık header kümesi — o küme test kümesi
tanımlanmadan önce, dışlama mantığı olmadan yapılmıştı. Etkisi 1435 belgede
1 (%0,07), ölçümleri değiştirmez; yeni boru hattı (`havuz_3992`) temiz.

### Yollar ve kişisel bilgi

Betiklerde makineye özel mutlak yol **yok**. Her biri kendi konumundan
`PROJE_KOK` (Python) veya `KOK` (kabuk) hesaplar, yani depo nereye
klonlanırsa çalışır. SLURM betiklerinde `#SBATCH -A TRUBA_HESABINIZ` yer
tutucusu var — kendi hesabınızla değiştirin, yoksa iş "geçersiz hesap"
hatasıyla durur (yanlış hesapla sessizce koşmasından iyidir).

**İçeride olan ve önemli olanlar:** tüm betikler, `05_TRUBA/olcumler/*.txt`
(bütün ölçüm sonuçları), `03_Test_ve_Degerlendirme/altin_test/` (50 makalenin
elle doğrulanmış altın kümesi — projenin en değerli özgün ürünü),
`dashboard/` (sonuç sayfaları, veri gömülü olarak çalışır).

> **Satır sonları.** `.gitattributes` bütün `.sh`, `.slurm` ve `.py`
> dosyalarını LF'te tutar. Bunu değiştirmeyin: Docker içindeki Wapiti ve
> TRUBA'daki SLURM CRLF gördüğünde "invalid format" verip çöküyor.

---

## Hızlı başlangıç

### Gereksinimler
- Docker Desktop (GROBID 0.9.1-crf imajı, 8070 portunda)
- Python 3.10+ (`requests`, `beautifulsoup4`, `lxml`)
- Modelleri eğitmek için: TRUBA hesabı (yerel 16 GB RAM yetmiyor)

### Modelleri kur

Modeller depoda değil; **Releases** bölümünden indirip `08_Modeller/` altına
koyun (klasör yapısı `header/` ve `segmentation/` şeklinde).

```bash
python 01_Header_Modeli/model_kur.py --kaynak 08_Modeller/header/v4_80603_2153belge_orfoz.wapiti
python 01_Header_Modeli/model_kur.py --model segmentation \
    --kaynak 08_Modeller/segmentation/tr_20803_0908.wapiti
```

**Modeli elle kopyalama.** Windows'ta üretilen dosyalar CRLF satır sonlu olur,
Docker içindeki Wapiti sadece LF kabul eder ve "invalid format" verip çöker.
`model_kur.py` bu dönüşümü, `.new` kontrolünü, container'a kopyalamayı ve
yeniden başlatmayı yapar.

### Ölçüm yap

```bash
cd 05_TRUBA && ./olc_model.sh <model_dosyasi> <etiket>
```

1435 Türkçe + 519 İngilizce makaleyi işler, GROBID'in kendi protokolüyle ölçer,
sonucu `05_TRUBA/olcumler/TR_<etiket>.txt` ve `ING_<etiket>.txt` olarak yazar.

### Sonuçları gör

```bash
python 03_Test_ve_Degerlendirme/olcum_sayfasi.py
```

`03_Test_ve_Degerlendirme/dashboard/olcumler.html` sayfasını üretir — tüm
ölçümler, dört eşleşme modu, kesinlik/duyarlılık/F1 seçimi.

**Yeni ölçüm eklerken** `olcum_sayfasi.py` içindeki `KAYIT` sözlüğüne satır
eklemek şart. Kayıtta olmayan dosya tabloya girmez, uyarı basılıp atlanır.
Bu bilinçli: bir kez "stok model" diye yanlış bir dosyayla ölçüm yapıp bir
günlük sonucu çöpe attık.

---

## Klasör düzeni

| Klasör | İçerik |
|---|---|
| `01_Header_Modeli/` | Otomatik etiketleyici (`header_auto_annotate.py`), TR Dizin API'sinden metadata çekme, model kurulumu. `ornek_ham_api/` — API'nin tam cevabı, 14 makale (`OKUBENI.md`) |
| `02_Segmentation_Modeli/` | Segmentasyon korpusu hazırlama ve etiketleme. `zorlu_pdfler/` altında 316 belgelik eğitim verisi (TR segmentasyon modelinin kaynağı) |
| `03_Test_ve_Degerlendirme/` | Ölçüm hattı, dashboard, GROBID protokolü. Test kümeleri: `1500_random_test/` (1435 makale), `ingilizce_kiyas/` (519 PMC), `altin_test/` (300 makale, 20'si elle doğrulandı) |
| `04_Genisletilmis_Egitim/` | 4 adımlı korpus üretim zinciri, v1–v4 etiketleme çıktıları |
| `05_TRUBA/` | SLURM betikleri, eğitim paketleri, ölçüm sonuçları, eğitilmiş modeller |
| `06_Benchmark_Veritabani/` | 300 belgelik zorluk katmanlı referans kümesi — gold veri, sayfa görüntüleri, şablon parmak izleri (`BENCHMARK.md`) |
| `07_Denemeler/` | Küçük doğrulama koşuları — **ölçüm sonucu değil** (`OKUBENI.md`) |
| `08_Modeller/` | Eğitilen modeller, stok referans ve tüm yedekler (`OKUBENI.md`) |
| `grobid/` | GROBID kaynak kodu ve `grobid-home` |

### Deneme ile test farkı

Klasörler bu ayrıma göre düzenlendi:

- **Deneme** (`07_Denemeler/`) — birkaç belgeyle yapılan "çalışıyor mu"
  koşuları. Boru hattını doğrular, performans ölçmez. Buradaki hiçbir rakam
  raporlanmamalıdır.
- **Test** (`03_Test_ve_Degerlendirme/`, `03_Test_ve_Degerlendirme/altin_test/`,
  `06_Benchmark_Veritabani/`) — yüzlerce/binlerce belgeyle yapılan gerçek
  değerlendirme. Raporlanan tüm sayılar buradan gelir.

İkisini karıştırmak bu projede bir kez bir günlük ölçümü çöpe attırdı.

`00_Eski_Arsiv` eski çalışmaların arşividir, ana hattın parçası değildir.

`08_Modeller/OKUBENI.md` — 33 model klasörünün tamamının
açıklaması, öznitelik sayılarıyla. Hangi dosyanın ne olduğunu anlamak için
oraya bak.

---

## Korpus nasıl üretiliyor

Elle etiketleme yok. TR Dizin'in kendi metadatası altın veri olarak kullanılıyor.

```
adim1_veri_topla.py     TR Dizin API'sinden PDF + metadata indir
adim2_createTraining.sh GROBID ile PDF'ten öznitelik (raw) ve TEI iskeleti üret
adim3_etiketle.py       DB'deki gerçek değerleri metinde bulup etiketle
adim4_korpusa_kur.py    Güvenilir olanları eğitim korpusuna kur
```

Etiketleyicinin çalışma mantığı (`01_Header_Modeli/header_auto_annotate.py`):

1. Mevcut etiketleri söker, metne **dokunmaz** — raw öznitelik dosyasıyla
   hizalama bozulmasın diye
2. DB'deki her alanı metinde bulanık arar (`db_span.py`)
3. Bulunamayan alanı sezgisel kurallarla doldurur
4. Çakışan span'ları önceliğe göre kırpar
5. Etiketler söküldüğünde metnin birebir aynı kaldığını doğrular — bozuksa
   belgeyi karantinaya atar

### Etiketleme sürümleri

`header_auto_annotate.py` dört kez elden geçti. Hangisinin eğitildiğine
dikkat: **v1'den doğrudan v4'e geçildi**, aradaki ikisi etiketlendi ama
hiç eğitilmedi.

| Sürüm | Altın belge | + eski korpus | Toplam | Eğitildi mi |
|---|---|---|---|---|
| v1 | 2505 | 494 | **2999** | ✅ 2. eğitim (7 Eylül) |
| v2 | 2411 | — | — | ❌ |
| v3 | 2208 | 419 | 2627 | ❌ paketlendi, eğitilmedi |
| v4 | 1827 | 326 | **2153** | ✅ 3. eğitim (10 Eylül) |

`04_Genisletilmis_Egitim/etiketli*/` klasörlerinde hepsi duruyor
(`altin/`, `karantina/`, `rapor.csv`), sürümler arası fark oradan görülebilir.

**Kritik kural: etiketsiz bırakmak "bu alan yok" demektir.** CRF eğitiminde
etiketsiz her token açık bir olumsuz örnektir. v3'te İngilizce başlığı
kapakta bulunan 1847 belgenin 1825'inde o blok etiketsizdi — yani modele
1825 kez "bu başlık değildir" öğretmişiz. Model de emin olamayıp susmuş:
İngilizce makalelerin %53.8'inde hiç başlık üretmiyordu. v4'te İngilizce
başlık da etiketlenince bu oran %22'ye indi, F1 49.28'den 80.09'a çıktı.

---

## Eğitim (TRUBA)

Yerel makinede eğitim yapılamıyor — 2153 belge yaklaşık 75 milyon öznitelik
üretiyor, Wapiti'nin L-BFGS'i 16 GB RAM'e sığmıyor.

`05_TRUBA/OKUBENI.md` içinde adım adım komut kartı var (`[YEREL]` / `[TRUBA]`
diye ayrılmış). Özet:

```bash
# [YEREL]
scp 05_TRUBA/paket_v4.tar.gz $KULLANICI@$TRUBA_SUNUCU:/arf/scratch/$USER/

# [TRUBA]
cd /arf/scratch/$USER/grobid && tar xzf ../paket_v4.tar.gz && sbatch egitim_orfoz.slurm
```

**Kuyruk seçimi ölçüldü** (2153 belge, iterasyon başına saniye):

| Düğüm | Çekirdek | sn/iter | 600 iterasyon |
|---|---|---|---|
| orfoz (Xeon 8480+) | 56 | ~15 | **2s 56dk** |
| barbun | 40 | ~47 | 7s 49dk |
| smp (orkinos, 16 soket) | 112 | 312 | kullanılamaz |

orfoz kullanın. smp'nin 16 NUMA bölgesi Wapiti'yi öldürüyor.

### TRUBA'da yaşanan tuzaklar

- **`module` komutu hesaplama düğümlerinde tanımlı olmayabilir.** Sessizce
  Java 11'e düşer, GROBID Java 21 bytecode olduğu için anında çöker.
  Betikler modül sistemini elle başlatıp sürümü doğruluyor.
- **Paylaşılan `grobid.yaml` yarışı.** `nbThreads` sadece yaml'dan okunuyor.
  Aynı anda birden fazla iş gönderilirse birbirinin ayarını ezerler — bir
  kıyas ölçümümüz tam bu yüzden geçersiz oldu. Betikler artık her işe kendi
  `grobid-home` kopyasını veriyor.
- **`--mem` çekirdek sayısına çevriliyor.** orfoz'da çekirdek başına ~2.2 GB
  var; `--mem=150G` istemek işi "en az 71 çekirdek" şartına sokar ve
  zamanlanamaz hale getirir. `-c 56` için üst sınır ~110G.
- **Arayüz sunucusunda ağır iş çalıştırmayın.** `apptainer pull` iki kez
  SIGKILL yedi. Hesaplama düğümlerinin interneti var, çekme işini de
  `sbatch` ile gönderin.

---

## Ölçüm hakkında bilinmesi gerekenler

### İki farklı metrik var, karıştırmayın

| | `grobid_standart_eval.py` | Dashboard `index.html` |
|---|---|---|
| Birim | Makale başına ikili: eşleşti / eşleşmedi | Makale başına kelime örtüşme yüzdesi |
| Eşik | Levenshtein ≥0.80 (ve 3 mod daha) | Eşik yok |
| Boş çıktı | Paydadan çıkarılır | 0 sayılıp ortalamaya girer |

Aynı model aynı çıktı için biri 88.13, diğeri 70.96 diyebilir. İkisi de
doğrudur, farklı soruları cevaplarlar. **Raporlama ve model seçimi için
`olcumler.html` kullanın** — GROBID'in kendi protokolü, literatürle
karşılaştırılabilir.

### Gürültü tabanı

Aynı korpus ve aynı hiperparametrelerle eğitilen iki model (orfoz ve barbun,
farklı thread düzeni) arasındaki fark ölçüldü:

- başlık / özet / anahtar kelime: **±0.6 puan**
- yazar / ilk yazar: **±2.2 puan**

Bunun altındaki farkları "iyileşme" diye yorumlamayın. Wapiti'nin gradyan
toplamı thread'lere bölündüğü için kayan nokta toplama sırası değişiyor,
L1 budaması farklı yerlerde duruyor.

### Eğitim ve test ayrı

2153 belgelik eğitim korpusu ile 1500'lük Türkçe test kümesinin kesişimi
**1 makale** (%0.07, id `1229729`). İngilizce test kümesi (PMC) tamamen ayrı
kaynak.

---

## Bilinen sınırlar

**Segmentasyon modelimiz Türkçeye özel.** 729 Türkçe makaleyle eğitildi.
İngilizce PMC makalelerinde stok modelden **kötü** (anahtar kelime −11.15,
özet −5.24). Genel bir iyileştirme değil, dile özelleşme. Türkçe dışı
belgelerde stok segmentasyon kullanılmalı.

**Yazar alanında model suskun.** Kesinlik stoktan iki kat iyi (29.46 → 61.38)
ama duyarlılık düşük (26.13 → 24.25). 1435 makalenin 683'ünde (%47.6) hiç
`<author>` üretmiyor. Sorun yanlış cevap vermek değil, cevap vermemek.

**`name/header` modeli stok İngilizce.** Türk isim yapısını bilmiyor:

```
DB : Gülin EKER ÖĞÜT       →  GROBID: ('Öğüt','Gülin') + ('','Eker')
DB : MURAT GÖKHAN DALYAN   →  GROBID: ('Gökhan','Murat') + ('','Dalyan')
```

Çift soyadları iki kişiye bölüyor, sırayı ters çeviriyor. Yazar kaybının
~%19'u buradan.

**Referans veri sınırları — ölçüldü.** 300 makalelik altın kümenin 50'si
elle doğrulandı (`03_Test_ve_Degerlendirme/altin_test/`), ayrıca 298 makalede
"referans değer metinde bulunabiliyor mu" ölçümü yapıldı.

TR Dizin kaydının makaleyle uyumu:

| Alan | Doğru | Düzeltme gerekti | Makalede yok |
|---|---|---|---|
| Başlık | 46/50 | 4 | 0 |
| Özet | 44/50 | 1 | 5 |
| Yazarlar | 22/50 | **26** | 2 |
| Anahtar kelime | 16/50 | **29** | 4 |

Düzeltme sebepleri (30 makalede gerekçe kaydedildi):

| Sebep | Makale |
|---|---|
| DB boş, makalede var | 12 |
| Sadece sıra farklı (içerik doğru) | 9 |
| Eksik/yanlış yazar — gerçek içerik hatası | 7 |
| İndeksleyici kendi terimlerini yazmış | 5 |
| Bozuk font / zorlu PDF | 2 |
| Yazar kapakta hiç yok | 2 |
| DB'de biçim hatası (eksik boşluk) | 2 |

**Ölçülen tavanlar** (referans değerin kapak metninde bulunabilme oranı, 298 makale):

| Alan | Tavan | Bizim skorumuz |
|---|---|---|
| Başlık | 96.3% | 76.64 |
| Özet | 86.0% | 76.26 |
| Yazarlar | 93.0% | 34.77 |
| Anahtar kelime | 77.8% | 22.22 |

Sonuç: **referans veri kalitesi bir sınır ama açığın büyük kısmı modelde.**
Özellikle yazarda tavan %93, skor 34.77 — arada ~58 puanlık model açığı var.

**`first_author` metriği güvenilmez.** 50 makalelik doğrulamada TR Dizin'in ilk
yazarı, makalenin gerçek ilk yazarı olma oranı yalnızca **%62**. Referansın
sıralaması keyfi olduğu için bu metriğin tavanı %62'dir ve ölçüm yöntemi
değiştirilerek düzeltilemez. (`authors` ve `keywords` metrikleri sırasızdır —
`grobid_standart_eval.py:138` içindeki `yazar_normalize` listeleri sıralayarak
karşılaştırır, orada sıra farkı ceza değildir.)

**Kalan iş: 250 makale.** Yukarıdaki oranlar 50 makaleye dayanıyor; küme
tamamlandıkça kesinleşir.

**DeLFT ölçülmedi.** Ortam kuruldu (`05_TRUBA/delft_truba_kur.sh`,
`egitim_delft.slurm`), eğitim TRUBA kuyruğunda kaldı. İmajda Türkçe kelime
gömmesi yok — sadece İngilizce glove-840B ve Fransızca. Karakter-BiLSTM ve
layout öznitelikleri dilden bağımsız çalışır ama sözcüksel ipuçları zayıf
kalır.

**Dashboard'da iki alan bozuk.** `index.html` kartlarında "Dergi Başarısı
%0.00" ve "Yıl %12.89" — muhtemelen `karsilastirma_yeni.py` içindeki
ayrıştırma hatası, modelin başarısızlığı değil. DOI aynı betikte %90.65
çalıştığına göre mantığın tamamı bozuk değil.

---

## Devam edilecekse: öncelik sırası

Sıra kanıta dayalı, tahmine değil. Etiket doğruluğu ölçüldü:

| Alan | Etiketlerin doğruluğu | Test F1 |
|---|---|---|
| Başlık | %93.9 | 76.64 |
| Yazar | %61.0 | 34.77 |
| Anahtar kelime | **%32.5** | 22.22 |

**1. Anahtar kelime etiketlemesi.** En kötü etiket kalitesi, en büyük açık
(tavan 43.4, mevcut 22.22). `header_auto_annotate.py` içindeki
`line_span_after` çok satırlı anahtar kelime listelerini yarım alıyor.
Yeni veri toplamak gerekmiyor, sadece kod. En yüksek getiri/maliyet oranı.

**2. Yazar etiketlemesi.** %61 doğruluk. `yazar_kirp` fonksiyonu kurum
satırlarını ve dipnot işaretlerini hâlâ karıştırıyor. Başlıkta işe yarayan
mekanizma (etiket doğruluğunu artır → model daha çok konuşur) burada da
çalışmalı.

**3. Altın test kümesini tamamla.** `03_Test_ve_Degerlendirme/altin_test/adim3_sunucu.py` çalıştır,
tarayıcıda aç, 21. makaleden devam et. Tavan iddialarımızı sağlamlaştırır.

**4. `name/header` eğitimi.** TR Dizin'deki `gercek_yazarlar` alanından
ad/soyad etiketli korpus türetilebilir. Vakaların ~%19'unu hedefler,
o yüzden 1 ve 2'den sonra.

**Not: API'den gelen veriyi atıyoruz.** `adim1_veri_topla.py` TR Dizin
cevabından yalnızca 10 alanı veritabanına yazıp gerisini siliyor. Ham cevapta
~38 alan var — yazarların kurumları, konu başlıkları, kaynakça, fon bilgisi.
Kurum satırlarının yazar bloğuna karışması bilinen bir sorunumuz ve API bu
ayrımı zaten veriyor. Betiğe ham cevabı da kaydettirmek tek satırlık bir
değişiklik ve ileride yeni veri toplamadan etiketli veri üretmeyi mümkün kılar.
Örnek: `01_Header_Modeli/ornek_ham_api/`.

**5. DeLFT.** Beklenti düşük tutulmalı. Türkçe fastText (`cc.tr.300.vec`)
indirilip LMDB'ye derlenirse daha anlamlı olur.

### Yapılmaması önerilenler

- **`maxIter` düşürerek hızlanmak.** 600 iterasyonluk koşunun logu modelin
  hâlâ yakınsamadığını gösterdi (590→600 bağıl azalma 3.3e-4, Wapiti eşiği
  2e-5). Kısmak doğrudan kalite kaybı. Hız donanımdan gelmeli.
- **`citation`, `date`, `figure`, `table`, `fulltext` modellerini eğitmek.**
  Header çıkarımında devreye girmiyorlar.
