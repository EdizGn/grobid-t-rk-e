# Sıkıntılı PDF Envanteri

- Üretim: 2026-09-08  
- Kaynak: `03_Test_ve_Degerlendirme/sıkıntılı_pdfler` → `teshis_refined.csv` (391 PDF) + `sablon_parmakizi.csv`
- Referans ayrıştırıcı: **stock GROBID 0.9.1-crf** (mount edilen eğitim modeli değil)
- Bu 391 PDF'in **151'i** stock GROBID'e karşı sıkıntısız çıktı (başlık+özet+yazar doğru). Sıkıntısız oldukları için bu envantere **alınmadılar**; ID'leri en alttaki ters indekste `PRIMARY = temiz` satırlarında görülebilir. (Not: bu grup çoğunlukla eğitimdeki mount modelini zorluyor ama referans ayrıştırıcı için kolay.)
- **Çakışma var:** bir PDF birden çok başlıkta görünebilir (138 PDF ≥2 sıkıntı taşıyor). Her PDF'in tüm etiketleri için ters indekse bakın.

---

## A. Metin katmanı sıkıntıları

_PDF'in kendi içeriğinden kaynaklanan, ayrıştırıcıdan bağımsız sorunlar. Metin daha okunmadan bozuk._

### A1 · Taranmış / resim PDF

Sayfa bir görüntü olarak gömülü; seçilebilir metin katmanı yok (harf oranı ≈ %0). OCR olmadan hiçbir alan okunamaz, GROBID boş döner.

**(46)** 8733 8878 8909 8933 8936 8947 8953 8954 8962 8964 9764 9776 9783 9792 9809 83079 83233 83281 83327 83332 83611 83957 83972 83986 83989 83992 85729 86244 86273 86787 86948 88321 88341 88346 88363 88385 88395 88823 88824 88826 91457 93789 97887 98469 98492 99645

### A2 · Bozuk font / ToUnicode yok

Yazı görünüyor ama fontun karakter eşleme tablosu eksik/yanlış. Kopyalanan metin anlamsız glif dizisi olur; harf oranı %1–45. GROBID metni alır ama içerik çöptür.

**(8)** 905 93429 93436 93529 94905 94920 94931 1290885

### A3 · Karakter anomalisi / mojibake

Metin katmanı var ama içinde beklenmeyen karakterler yoğun: U+FFFD (kayıp glif), PUA kodları, yön kontrol işaretleri, Latin-1'den bozuk dönmüş harfler (Ã, Å), Türkçe harflerin yanlış kodlanması. Kısmen okunur ama alan sınırları kayar.

**(26)** 3545 14635 23390 59503 69354 75285 77704 181727 233442 242639 242903 297232 304796 350658 376495 456177 485532 495064 517431 1161713 1212123 1218730 1241544 1345386 1382739 1392420

---

## B. GROBID pipeline sıkıntıları

_Metin katmanı yeterli ama dış model (stock GROBID) belgeyi bölütleyemiyor — segmentation/header adımı yapıyı yanlış çıkarıyor._

### B1 · GROBID header çöküyor

`processHeaderDocument` boş gövde ya da hata döndürüyor — genelde metin katmanı yok (taranmış) ya da PDF yapısı bozuk. Hiç header çıktısı üretilemiyor.

**(40)** 8733 8878 8909 8933 8936 8947 8953 8954 8962 8964 9764 9776 9783 9792 9809 83079 83233 83281 83327 83332 83957 83972 83986 83989 83992 85729 86244 86273 86787 86948 88321 88341 88346 88363 88385 88395 91457 93789 97887 99645

### B2 · Başlık çıkmıyor

GROBID çalışıyor, özet/anahtar kelimeyi buluyor ama `<title type=main>` boş. Segmentation başlık satırını 'header' bölgesine sokamamış; başlık gövde ya da not sanılmış.

**(51)** 3545 14635 23390 64640 68150 69354 73595 83611 88823 88824 88826 93436 93529 94905 94920 94931 98469 98492 99668 117033 127220 140813 142221 186467 202819 240323 242903 268910 298868 315379 315616 318514 338587 365957 404394 411572 418481 427429 609016 618644 618882 620896 1116232 1132305 1152267 1152916 1190046 1225818 1238132 1290885 1372269

### B3 · Başlık yerine dergi adı

GROBID sayfa üstündeki dergi künyesini / running-header'ı başlık olarak etiketliyor. Çıktıda başlık yerine 'Journal of…', '… Arşivi', 'Faculty of…' gibi ifadeler görünüyor.

**(28)** 113263 148080 164997 218573 311918 350983 353342 357894 393465 419553 445465 449311 456806 499279 534977 1168459 1178310 1183123 1187586 1200501 1270517 1290383 1314085 1360724 1360929 1381852 1388658 1406707

### B4 · Gövde çıkmıyor

Fulltext TEI'de `<body>` neredeyse boş (<500 karakter). Segmentation gövde bloğunu bulamamış; makale metni dağılmış.

**(8)** 94905 94920 94931 161699 213306 234112 411572 1426985

---

## C. Metadata-diff sıkıntıları

_GROBID bir çıktı üretiyor ama TR Dizin altın verisiyle (gold) karşılaştırınca tutmuyor. Sıkıntı çıktının doğruluğunda._

### C1 · Başlık yanlış

GROBID bir başlık üretiyor ama gold başlıkla benzerlik < 0.72 — yanlış satır alınmış, ortadan kesilmiş ya da başka metinle karışmış.

**(29)** 905 82510 93429 139017 223236 286729 287138 294195 307857 363181 385039 410053 455033 484795 489933 517266 517431 523022 1141273 1152923 1205788 1235830 1238017 1253201 1259954 1309073 1333758 1334937 1390563

### C2 · Çift dilli başlık birleşik

Makalenin hem Türkçe hem İngilizce başlığı ard arda basılı; GROBID ikisini tek başlık olarak birleştirmiş (benzerlik 0.6–0.9).

**(24)** 56451 75285 87709 93101 107634 161699 166931 301143 359885 360657 373809 380686 383196 524616 535321 536308 1142114 1146308 1159082 1178761 1211913 1223983 1331207 1392420

### C3 · Düşük benzerlik

Başlık büyük ölçüde doğru ama tam değil (0.72–0.85): fazladan kelime, eksik ek, noktalama/tire farkı.

**(9)** 102273 256197 328577 363482 391579 1212123 1253198 1373827 1394769

### C4 · Özet eksik / kısmi

Özet çıkarılmış ama gold ile benzerlik < 0.45 — ortadan kesilmiş, girişe taşmış ya da yanlış dildeki özet alınmış.

**(53)** 3545 29094 59503 69354 75904 87709 93436 98469 127220 166594 181727 197842 213306 234112 242903 277193 287138 294250 298081 301143 305244 315616 359643 373502 380686 383653 385039 399854 410053 411572 418481 449311 484795 489933 509295 523022 533725 534977 535321 1121357 1152267 1161713 1161917 1177813 1183123 1211913 1212123 1219618 1235830 1382041 1382972 1388658 1394769

### C5 · Özet yok

En az 6 sayfalık (yani özeti olması beklenen) bir makalede GROBID özet bloğunu hiç bulamıyor.

**(81)** 905 8733 8909 8947 8954 64640 83079 83233 83281 83327 83332 83611 83957 83972 83986 83989 83992 86244 86273 88321 88341 88363 88385 88395 88823 88826 91457 93429 93529 93789 94905 94920 94931 97887 99645 139017 161699 186467 242639 268910 294195 298868 309841 311918 315379 342803 357894 383196 398124 404394 427429 445465 495546 499279 512095 609016 618644 618882 620896 1116232 1123845 1132305 1142114 1146308 1152916 1152923 1159082 1188330 1188683 1190046 1221441 1238017 1238132 1270517 1290383 1290885 1293408 1333758 1381852 1390563 1395540

### C6 · Yazarlar eksik / karışık

Gold yazar listesinin yarıdan fazlası çıktıda yok, ya da yazar alanına künye/afiliasyon metni ('Ekim 2018', dergi adı) yerleşmiş.

**(50)** 905 13162 64640 69354 73595 93429 93436 93529 94905 94920 94931 105791 112629 113263 117033 127220 139017 140813 142221 166594 166931 186467 202819 240323 268910 287138 311918 353342 357894 383295 424296 445465 479245 609016 618644 618882 620896 1116232 1123845 1152267 1180757 1219618 1235830 1238132 1290885 1313113 1333758 1360929 1381852 1390563

---

## D. Mizanpaj / şablon sıkıntıları

_Belgenin görsel tasarımı / üretim biçimi kaynaklı. Doğrudan 'hata' olmayabilir ama ayrıştırmayı zorlar ve benchmark'ta tasarım çeşitliliğini belirler._

### D1 · Şablon taklidi

Sayfa geometrisi ticari yayıncı şablonuna benziyor (dar üst boşluk, ortalı küçük başlık, iki kolon) ama üretici MS Word ve fontlar jenerik (Times/Arial) — yani lisanslı şablonun taklidi.

**(27)** 61601 102273 113030 170263 184920 268910 291466 326008 386509 410094 420614 455033 463679 468827 522968 532256 1178166 1180757 1180797 1180849 1246038 1257234 1313113 1314085 1342790 1388658 1406707

### D2 · Döndürülmüş sayfa (rotation ≠ 0)

Sayfada `/Rotate ≠ 0` — 90/180/270° döndürülmüş kaydedilmiş; metin çıkarma yönü ve sırası bozulur.

**(25)** 8909 8933 8936 8947 8953 8954 8962 8964 63585 83079 83233 83281 83327 88341 88346 88363 88385 88395 91457 93789 99645 298868 299555 305244 326008

### D3 · Landscape ilk sayfa

İlk sayfa yatay (genişlik > yükseklik) — genelde geniş tablo/şekil sayfası makalenin önüne düşmüş.

**(2)** 88321 242903

### D4 · Çok kolonlu düzen (2 kolon)

İlk sayfa iki kolonlu. Başlık/yazar bloğu tek kolon, gövde çift kolon olduğunda segmentation zorlanır; kolon kırılması reading-order'ı bozabilir.

**(234)** 905 13162 52927 56451 63585 64640 69354 75904 77704 81672 82510 83072 83447 83611 88823 88824 88826 94905 94920 94931 98469 99229 102273 105791 107634 112629 113030 113263 117033 126560 132757 140813 148080 161699 166594 166931 170263 181727 184920 186467 191670 199190 202819 204617 205664 210357 212282 213306 218573 221906 223236 233442 240323 240441 242639 242903 256197 261973 268910 277193 281990 286729 289155 291466 294023 294250 298868 299555 301143 303407 303541 304796 305244 309841 310150 310939 311918 315379 315616 319303 326008 328577 334352 337526 342803 350658 350983 351663 353342 357894 359240 359885 360657 363482 365957 365961 373502 373809 376495 379690 380686 383005 383196 383295 383653 385039 385283 386509 391579 393465 398124 399854 404394 404522 405707 406637 406683 410053 410094 411572 418481 419553 427429 427651 449311 449844 455033 456177 456806 459053 463679 466415 466936 468827 473004 477964 484795 485532 486620 489933 495064 495546 499279 500044 512095 517266 517431 522479 522968 523022 524616 532256 534977 535321 535677 536308 609016 1116232 1121357 1123845 1131929 1139983 1141142 1141273 1142114 1146308 1152267 1159082 1161713 1178310 1178438 1178761 1180757 1180797 1180849 1183323 1190046 1193660 1200501 1207129 1211913 1212123 1218730 1219618 1219902 1221441 1223983 1238017 1238434 1242138 1246038 1246751 1257015 1257234 1259954 1266209 1268152 1270517 1276080 1284535 1290126 1290383 1290885 1293408 1294441 1294914 1308457 1313057 1313113 1314085 1329407 1331207 1333641 1333758 1334937 1336929 1338210 1338865 1341940 1342790 1345386 1353371 1360724 1372269 1381852 1382041 1384709 1388658 1390563 1390641 1392420 1394769 1414299 1451290

### D5 · Üretici: LaTeX

PDF `pdfTeX/XeTeX/LuaTeX` ile üretilmiş. Genelde temiz metin akışı ama matematik/ligatür ve özel karakter gömme sorunları buradan çıkar.

**(54)** 905 64640 77704 83072 85729 86244 86273 93429 93436 93529 142221 181727 197842 199190 202819 204283 204617 205664 210357 212282 218573 219813 221906 233442 234112 240323 240441 242639 242903 256197 261973 277193 281990 286729 297232 350658 363181 379690 383295 485532 495064 500044 1161713 1205788 1218730 1228079 1235830 1238017 1238132 1241544 1290383 1345386 1382739 1394769

### D6 · Üretici: InDesign / FrameMaker / Arbortext

Profesyonel dizgi yazılımı. Karmaşık kutu yapısı; metin görsel sırayla içerik akışı sırası uyuşmayabilir.

**(88)** 3545 13162 29094 45011 52924 52927 56451 69354 73595 75285 81672 82510 87709 91555 98469 98492 105791 112629 113263 117033 126560 127220 132757 139017 148080 161699 164997 166931 168513 180843 186467 223236 291689 294023 294195 298081 303407 303541 310939 311918 315616 338334 338587 353342 380686 383005 383653 404394 414839 451149 460195 466936 477964 484795 486620 534977 1127957 1131929 1159082 1162628 1188330 1188683 1190046 1190772 1225818 1246751 1250862 1268278 1270517 1290126 1299565 1309073 1329407 1331207 1338865 1353371 1360929 1369792 1382041 1382972 1384709 1390641 1402745 1407054 1407315 1414299 1426985 1451290

### D7 · Üretici: MS Word / WPS

Ofis yazılımı çıktısı. DergiPark varsayılan şablonları çoğunlukla buradan; farklı dergiler aynı Word şablonunu paylaşabilir.

**(78)** 63585 107634 170263 184920 315379 319303 323600 328577 342803 350983 351663 359885 368121 386509 391579 393465 398124 398499 399854 404522 455033 468827 473004 479507 495546 499279 512095 524616 609016 618882 1121357 1132305 1139983 1141142 1142114 1146308 1152267 1152916 1152923 1161917 1178166 1180757 1180797 1180849 1182209 1183123 1183323 1193660 1200501 1207129 1211913 1212123 1219618 1219902 1221441 1223983 1246038 1253198 1253201 1257015 1266209 1291416 1293408 1294441 1294914 1308457 1313057 1313113 1314085 1338210 1342790 1347087 1354926 1373827 1381852 1395540 1406707 1412541

### D8 · Üretici metası boş

Producer/Creator alanı hiç yazılmamış — çoğu taranmış ya da elde birleştirilmiş/yeniden basılmış PDF.

**(20)** 9764 9776 9783 9792 9809 59503 83957 83972 83986 83989 83992 91457 97887 99645 298868 299555 305244 1334937 1341940 1360724

### D9 · Metinsiz ilk sayfa

İlk sayfada 5'ten az metin satırı — kapak, iç kapak, künye ya da tam sayfa görsel. GROBID ilk 2 sayfaya baktığı için başlık/yazarı hiç göremeyebilir.

**(42)** 8733 8878 8909 8933 8936 8947 8953 8954 8962 8964 9764 9776 9783 9792 9809 83079 83233 83281 83327 83332 83957 83972 83986 83989 83992 85729 86244 86273 86787 86948 88321 88341 88346 88363 88385 88395 91457 93789 97887 99645 297232 309841

---

## E. İçerik-tipi kaynaklı

_Dosya teknik olarak sağlam ama belge türü / dili 'standart makale' varsayan modelleri zorlar._

### E1 · Çok kısa belge (≤4 sayfa)

Olgu sunumu, editöre mektup, kitap tanıtımı, kısa bildiri. Çoğunda IMRaD yapısı ve bazen özet yok.

**(72)** 8878 8933 8936 8953 8962 9764 9809 13162 23390 29094 52924 52927 56451 59503 68150 75285 82510 86787 87709 93101 98492 99229 99668 105791 126560 140813 142221 166594 166931 202819 204283 213306 223236 234112 286729 287138 289155 291466 294023 294250 298081 299555 303407 315616 325302 338587 383653 385039 410053 411572 424296 425857 455033 459053 479245 484795 517266 532256 1110700 1170842 1178761 1205788 1242138 1259954 1276080 1294441 1334937 1341940 1388658 1402745 1407054 1407315

### E2 · Çok uzun derleme (≥30 sayfa)

Geniş derleme / çok bölümlü çalışma. Uzun referans listesi ve çok sayıda iç başlık segmentation'ı zorlar.

**(17)** 99645 319303 337526 517431 523022 609016 618644 620896 1121357 1139983 1152267 1152916 1152923 1188683 1238017 1238132 1299565

### E3 · Saf İngilizce metin

Türk dergisinde İngilizce yayımlanmış makale. Bu havuzda oran yüksek çünkü sıkıntılı örnekler çoğunlukla İngilizce dergilerden toplanmış.

**(243)** 13162 23390 29094 45011 52924 52927 56451 61601 68150 73595 75285 77704 87709 88824 91555 99229 99668 105791 107634 112629 113030 127220 132757 140813 148080 164997 166594 168513 180843 184920 191670 197842 199190 202819 204283 204617 205664 210357 212282 213306 218573 219813 221906 223236 233442 234112 240323 240441 242639 256197 261973 281990 286729 289155 291466 291689 293454 294023 297232 298081 299555 303407 303541 304796 307857 310150 313560 315616 318514 319303 323600 325302 326008 328577 337526 338334 338587 342803 350658 350983 351663 357894 359240 359643 363181 365957 365961 368121 369855 373502 374483 376495 379690 383005 383295 383653 385283 391579 393465 398124 398499 399854 405707 406637 406683 410053 410094 411572 414839 418481 419553 420614 422461 424296 425857 427429 427651 449311 449844 451149 455033 456177 459053 460195 463679 466415 466936 468827 469602 473004 477964 479245 479507 484795 485532 486620 486762 495064 495546 500044 512095 517266 522479 522968 523022 523621 524616 532256 532527 533725 535321 535677 536308 1110700 1123845 1127957 1131929 1139983 1141273 1161713 1161917 1162628 1165244 1168459 1170842 1176120 1178166 1178310 1178438 1178761 1180757 1180797 1182209 1187586 1189398 1190772 1193660 1200501 1205788 1207129 1218730 1219618 1219902 1221441 1223983 1228079 1238017 1238434 1241544 1242138 1246038 1246751 1250862 1253198 1253201 1255067 1257015 1257234 1259954 1268152 1268278 1276080 1284535 1290126 1291416 1294441 1294914 1308457 1309073 1313057 1313113 1314085 1329407 1331207 1333445 1333641 1333758 1336929 1338210 1338865 1341940 1342790 1345386 1347087 1354926 1360724 1360929 1369792 1381852 1382041 1382739 1384709 1390563 1390641 1392420 1395540 1402745 1406707 1407054 1407315 1412541 1414299 1426985

### E4 · Karışık dil (TR+EN gövde)

Türkçe ve İngilizce bölümler paralel/iç içe (çift özet, çift başlık, iki dilli tam metin).

**(67)** 8733 8878 8909 8933 8936 8947 8953 8954 8962 8964 9764 9776 9783 9792 9809 83079 83233 83281 83327 83332 83611 83957 83972 83986 83989 83992 85729 86244 86273 86787 86948 88321 88341 88346 88363 88385 88395 88823 88826 91457 93429 93436 93529 93789 94905 94920 94931 97887 98469 98492 99645 113263 181727 315379 334352 385039 386509 489933 1152267 1159082 1190046 1212123 1290383 1290885 1299565 1353371 1373827

### E5 · Saf Türkçe metin

Gövde ağırlıklı Türkçe — hedef dil profili.

**(81)** 905 3545 14635 59503 63585 64640 69354 75904 81672 82510 83072 83447 93101 102273 117033 126560 139017 142221 161699 166931 170263 186467 242903 268910 277193 287138 294195 294250 298868 301143 305244 309841 310939 311918 353342 359885 360657 363482 373809 380686 383196 404394 404522 445465 456806 499279 509295 517431 534977 609016 618644 618882 620896 1116232 1120026 1121357 1132305 1141142 1142114 1146308 1152916 1152923 1177813 1180849 1183123 1183323 1188330 1188683 1211913 1225818 1235830 1238132 1266209 1270517 1293408 1334937 1372269 1382972 1388658 1394769 1451290

---

## Ters indeks — her PDF'in tüm etiketleri

`PRIMARY` = baskın sıkıntı · `FLAGS` = tüm sıkıntılar · `temiz` satırları envantere alınmadı.

| makale_id | PRIMARY | TIER | FLAGS | sf | dil | yıl | meta | küme | dergi |
|---|---|---|---|---|---|---|---|---|---|
| 905 | bozuk-font | zor | bozuk-font;baslik-yanlis;yazar-eksik;ozet-yok | 6 | tr | 2004 | latex | 99 | ARI The Bulletin of the Istanbul Technic |
| 3545 | karakter-anomali | zor | karakter-anomali;header-title-yok;ozet-eksik | 18 | tr | 2004 | indesign | 34 | Bilgi Dünyası |
| 8733 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 6 | mix | 1999 | other | 60 | Selcuk Medical Journal |
| 8878 | grobid-crash | zor | grobid-crash;taranmis | 4 | mix | 1999 | scan | 10 | Türk Hijyen ve Deneysel Biyoloji Dergisi |
| 8909 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 8 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8933 | grobid-crash | zor | grobid-crash;taranmis | 2 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8936 | grobid-crash | zor | grobid-crash;taranmis | 2 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8947 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 16 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8953 | grobid-crash | zor | grobid-crash;taranmis | 4 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8954 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 9 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8962 | grobid-crash | zor | grobid-crash;taranmis | 3 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 8964 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 1999 | other | 60 | Türk Kardiyoloji Derneği Arşivi |
| 9764 | grobid-crash | zor | grobid-crash;taranmis | 4 | mix | 1999 | bos | 78 | Ulusal Travma Dergisi |
| 9776 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 1999 | bos | 1 | Ulusal Travma Dergisi |
| 9783 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 1999 | bos | 1 | Ulusal Travma Dergisi |
| 9792 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 1999 | bos | 1 | Ulusal Travma Dergisi |
| 9809 | grobid-crash | zor | grobid-crash;taranmis | 4 | mix | 1999 | bos | 1 | Ulusal Travma Dergisi |
| 13162 | yazar-eksik | orta | yazar-eksik | 3 | en | 2001 | indesign | 0 | Anadolu Kardiyoloji Dergisi |
| 14635 | karakter-anomali | zor | karakter-anomali;header-title-yok | 5 | tr | 2001 | other | 109 | Klinik Psikofarmakoloji Bülteni |
| 23390 | karakter-anomali | zor | karakter-anomali;header-title-yok | 3 | en | 2003 | other | 76 | Ulusal Travma Dergisi |
| 29094 | ozet-eksik | orta | ozet-eksik | 4 | en | 2002 | indesign | 13 | Turkish Journal of Agriculture and Fores |
| 45011 | temiz | kolay | temiz | 5 | en | 2004 | indesign | 13 | Turkish Journal of Medical Sciences |
| 52924 | temiz | kolay | temiz | 3 | en | 2004 | indesign | 41 | Turkish Journal of Medical Sciences |
| 52927 | temiz | kolay | temiz | 4 | en | 2004 | indesign | 13 | Turkish Journal of Medical Sciences |
| 56451 | baslik-cift-dilli | orta | baslik-cift-dilli | 3 | en | 2005 | indesign | 31 | Türk Göğüs Kalp Damar Cerrahisi Dergisi |
| 59503 | karakter-anomali | zor | karakter-anomali;ozet-eksik | 4 | tr | 2004 | bos | 56 | Kartal Eğitim ve Araştırma Hastanesi Tıp |
| 61601 | temiz | kolay | temiz | 8 | en | 2005 | other | 9 | Istanbul University Journal of Electrica |
| 63585 | temiz | kolay | temiz | 6 | tr | 2006 | word | 98 | Muhasebe ve Finansman Dergisi (. e-Muhas |
| 64640 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 25 | tr | 2006 | latex | 14 | Gazi Üniversitesi Ticaret ve Turizm Eğit |
| 68150 | header-title-yok | zor | header-title-yok | 4 | en | 2007 | other | 110 | Anadolu Kardiyoloji Dergisi |
| 69354 | karakter-anomali | zor | karakter-anomali;header-title-yok;yazar-eksik;ozet-eksik | 17 | tr | 2007 | indesign | 29 | Türk Otolarengoloji Arşivi |
| 73595 | header-title-yok | zor | header-title-yok;yazar-eksik | 6 | en | 2008 | indesign | 49 | Journal of Applied Biological Sciences |
| 75285 | karakter-anomali | zor | karakter-anomali;baslik-cift-dilli | 3 | en | 2007 | indesign | 9 | Kulak Burun Boğaz İhtisas Dergisi |
| 75904 | ozet-eksik | orta | ozet-eksik | 13 | tr | 2007 | other | 66 | Dil Dergisi |
| 77704 | karakter-anomali | zor | karakter-anomali | 15 | en | 2008 | latex | 13 | İlköğretim Online (elektronik) |
| 81672 | temiz | kolay | temiz | 16 | tr | 2007 | indesign | 4 | Erdem |
| 82510 | baslik-yanlis | orta | baslik-yanlis | 3 | tr | 2008 | indesign | 27 | Trakya Üniversitesi Tıp Fakültesi Dergis |
| 83072 | temiz | kolay | temiz | 8 | tr | 2008 | latex | 43 | Mühendislik Bilimleri Dergisi |
| 83079 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 10 | mix | 2005 | other | 10 | ÖNERİ |
| 83233 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 13 | mix | 2006 | other | 10 | ÖNERİ |
| 83281 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 13 | mix | 2006 | other | 10 | ÖNERİ |
| 83327 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 11 | mix | 2006 | other | 10 | ÖNERİ |
| 83332 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 13 | mix | 2007 | other | 10 | ÖNERİ |
| 83447 | temiz | kolay | temiz | 7 | tr | 2008 | scan | 5 | Atatürk Üniversitesi Ziraat Fakültesi De |
| 83611 | taranmis | zor | taranmis;header-title-yok;ozet-yok | 6 | mix | 2008 | other | 57 | Harran Üniversitesi Ziraat Fakültesi Der |
| 83957 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 16 | mix | 2005 | bos | 78 | İstanbul Üniversitesi İktisat Fakültesi  |
| 83972 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 8 | mix | 2005 | bos | 78 | İstanbul Üniversitesi İktisat Fakültesi  |
| 83986 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 13 | mix | 2005 | bos | 78 | İstanbul Üniversitesi İktisat Fakültesi  |
| 83989 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 19 | mix | 2005 | bos | 78 | İstanbul Üniversitesi İktisat Fakültesi  |
| 83992 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 17 | mix | 2005 | bos | 78 | İstanbul Üniversitesi İktisat Fakültesi  |
| 85729 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 2008 | latex | 10 | Solunum |
| 86244 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 8 | mix | 2008 | latex | 10 | İstanbul Üniversitesi Florence Nightinga |
| 86273 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 7 | mix | 2008 | latex | 10 | İstanbul Üniversitesi Florence Nightinga |
| 86787 | grobid-crash | zor | grobid-crash;taranmis | 4 | mix | 2008 | other | 10 | Haydarpaşa Numune Eğitim ve Araştırma Ha |
| 86948 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 2008 | other | 60 | İzmir Tepecik Eğitim Hastanesi Dergisi |
| 87709 | ozet-eksik | orta | ozet-eksik;baslik-cift-dilli | 2 | en | 2009 | indesign | 9 | Türk Kardiyoloji Derneği Arşivi |
| 88321 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 8 | mix | 2007 | other | 1 | İstanbul Üniversitesi Orman Fakültesi De |
| 88341 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 10 | mix | 2008 | other | 10 | ÖNERİ |
| 88346 | grobid-crash | zor | grobid-crash;taranmis | 5 | mix | 2008 | other | 10 | ÖNERİ |
| 88363 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 6 | mix | 2008 | other | 10 | ÖNERİ |
| 88385 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 13 | mix | 2008 | other | 10 | ÖNERİ |
| 88395 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 16 | mix | 2008 | other | 10 | ÖNERİ |
| 88823 | taranmis | zor | taranmis;header-title-yok;ozet-yok | 9 | mix | 2009 | other | 57 | Harran Üniversitesi Ziraat Fakültesi Der |
| 88824 | taranmis | zor | taranmis;header-title-yok | 5 | en | 2009 | other | 57 | Harran Üniversitesi Ziraat Fakültesi Der |
| 88826 | taranmis | zor | taranmis;header-title-yok;ozet-yok | 7 | mix | 2009 | other | 57 | Harran Üniversitesi Ziraat Fakültesi Der |
| 91457 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 20 | mix | 2009 | bos | 10 | Tarih İncelemeleri Dergisi |
| 91555 | temiz | kolay | temiz | 6 | en | 2008 | indesign | 2 | Uluslararası Hematoloji-Onkoloji Dergisi |
| 93101 | baslik-cift-dilli | orta | baslik-cift-dilli | 3 | tr | 2009 | other | 22 | Yeni Üroloji Dergisi |
| 93429 | bozuk-font | zor | bozuk-font;baslik-yanlis;yazar-eksik;ozet-yok | 10 | mix | 2008 | latex | 72 | Türk Kültürü ve Hacı Bektaş Veli Araştır |
| 93436 | bozuk-font | zor | bozuk-font;header-title-yok;yazar-eksik;ozet-eksik | 10 | mix | 2008 | latex | 72 | Türk Kültürü ve Hacı Bektaş Veli Araştır |
| 93529 | bozuk-font | zor | bozuk-font;header-title-yok;yazar-eksik;ozet-yok | 22 | mix | 2008 | latex | 72 | Türk Kültürü ve Hacı Bektaş Veli Araştır |
| 93789 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 6 | mix | 2009 | other | 10 | Türk Oftalmoloji Dergisi |
| 94905 | bozuk-font | zor | bozuk-font;govde-yok;header-title-yok;yazar-eksik;ozet-yok | 10 | mix | 2010 | other | 55 | Eğitim ve Bilim |
| 94920 | bozuk-font | zor | bozuk-font;govde-yok;header-title-yok;yazar-eksik;ozet-yok | 15 | mix | 2010 | other | 55 | Eğitim ve Bilim |
| 94931 | bozuk-font | zor | bozuk-font;govde-yok;header-title-yok;yazar-eksik;ozet-yok | 14 | mix | 2010 | other | 55 | Eğitim ve Bilim |
| 97887 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 24 | mix | 2007 | bos | 10 | Selçuk Üniversitesi İktisadi ve İdari Bi |
| 98469 | taranmis | zor | taranmis;header-title-yok;ozet-eksik | 7 | mix | 2010 | indesign | 80 | Trakya Üniversitesi Tıp Fakültesi Dergis |
| 98492 | taranmis | zor | taranmis;header-title-yok | 3 | mix | 2010 | indesign | 80 | Trakya Üniversitesi Tıp Fakültesi Dergis |
| 99229 | temiz | kolay | temiz | 4 | en | 2009 | other | 0 | TSK Koruyucu Hekimlik Bülteni |
| 99645 | grobid-crash | zor | grobid-crash;taranmis;ozet-yok | 30 | mix | 2009 | bos | 10 | Tarih İncelemeleri Dergisi |
| 99668 | header-title-yok | zor | header-title-yok | 3 | en | 2009 | other | 51 | Turkish Neurosurgery |
| 102273 | dusuk-benzerlik | orta | dusuk-benzerlik | 7 | tr | 2010 | other | 5 | Anadolu Tarım Bilimleri Dergisi |
| 105791 | yazar-eksik | orta | yazar-eksik | 4 | en | 2010 | indesign | 101 | Çocuk Enfeksiyon Dergisi |
| 107634 | baslik-cift-dilli | orta | baslik-cift-dilli | 5 | en | 2010 | word | 31 | Tekstil ve Konfeksiyon |
| 112629 | yazar-eksik | orta | yazar-eksik | 6 | en | 2010 | indesign | 51 | Turkish Neurosurgery |
| 113030 | temiz | kolay | temiz | 9 | en | 2011 | other | 27 | International journal of thermodynamics |
| 113263 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik | 5 | mix | 2011 | indesign | 25 | Türk Nefroloji Diyaliz ve Transplantasyo |
| 117033 | header-title-yok | zor | header-title-yok;yazar-eksik | 12 | tr | 2011 | indesign | 25 | Aile ve Toplum |
| 126560 | temiz | kolay | temiz | 4 | tr | 2011 | indesign | 35 | Şişli Etfal Hastanesi Tıp Bülteni |
| 127220 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-eksik | 25 | en | 2011 | indesign | 74 | Perceptions: Journal of International Af |
| 132757 | temiz | kolay | temiz | 6 | en | 2012 | indesign | 89 | Turkish Journal of Field Crops |
| 139017 | baslik-yanlis | zor | baslik-yanlis;yazar-eksik;ozet-yok | 7 | tr | 2012 | indesign | 38 | Spor Bilimleri Dergisi |
| 140813 | header-title-yok | zor | header-title-yok;yazar-eksik | 3 | en | 2012 | other | 96 | GORM:Gynecology Obstetrics & Reproductiv |
| 142221 | header-title-yok | zor | header-title-yok;yazar-eksik | 3 | tr | 2012 | latex | 1 | Türk Kütüphaneciliği |
| 148080 | baslik-dergi-adi | zor | baslik-dergi-adi | 18 | en | 2013 | indesign | 37 | Kaygı. Uludağ Üniversitesi Fen-Edebiyat  |
| 161699 | govde-yok | zor | govde-yok;baslik-cift-dilli;ozet-yok | 16 | tr | 2014 | indesign | 24 | Anadolu Üniversitesi Sosyal Bilimler Der |
| 164997 | baslik-dergi-adi | zor | baslik-dergi-adi | 8 | en | 2014 | indesign | 21 | Tarım Bilimleri Dergisi |
| 166594 | yazar-eksik | orta | yazar-eksik;ozet-eksik | 2 | en | 2013 | other | 31 | Harran Üniversitesi Tıp Fakültesi Dergis |
| 166931 | yazar-eksik | orta | yazar-eksik;baslik-cift-dilli | 3 | tr | 2014 | indesign | 92 | Kartal Eğitim ve Araştırma Hastanesi Tıp |
| 168513 | temiz | kolay | temiz | 7 | en | 2014 | indesign | 3 | Archives of Rheumatology |
| 170263 | temiz | kolay | temiz | 7 | tr | 2014 | word | 5 | Gaziosmanpaşa Üniversitesi Ziraat Fakült |
| 180843 | temiz | kolay | temiz | 8 | en | 2015 | indesign | 74 | Turkish Journal of Medical Sciences |
| 181727 | karakter-anomali | zor | karakter-anomali;ozet-eksik | 8 | mix | 2015 | latex | 77 | GIDA |
| 184920 | temiz | kolay | temiz | 7 | en | 2014 | word | 27 | Turkish Journal of Fisheries and Aquatic |
| 186467 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 12 | tr | 2015 | indesign | 35 | Ege Akademik Bakış |
| 191670 | temiz | kolay | temiz | 6 | en | 2015 | other | 0 | Türk Spor ve Egzersiz Dergisi |
| 197842 | ozet-eksik | orta | ozet-eksik | 7 | en | 2015 | latex | 71 | Diagnostic and Interventional Radiology |
| 199190 | temiz | kolay | temiz | 7 | en | 2016 | latex | 11 | Turkish Journal of Hematology |
| 202819 | header-title-yok | zor | header-title-yok;yazar-eksik | 4 | en | 2016 | latex | 46 | Journal of Clinical Research in Pediatri |
| 204283 | temiz | kolay | temiz | 4 | en | 2016 | latex | 2 | Molecular Imaging and Radionuclide Thera |
| 204617 | temiz | kolay | temiz | 10 | en | 2016 | latex | 27 | Celal Bayar Üniversitesi Fen Bilimleri D |
| 205664 | temiz | kolay | temiz | 24 | en | 2016 | latex | 36 | Kadın/Woman 2000 - Kadın Araştırmaları D |
| 210357 | temiz | kolay | temiz | 6 | en | 2016 | latex | 8 | Düşünen Adam - Psikiyatri ve Nörolojik B |
| 212282 | temiz | kolay | temiz | 11 | en | 2016 | latex | 54 | Anadolu Üniversitesi Bilim ve Teknoloji  |
| 213306 | govde-yok | zor | govde-yok;ozet-eksik | 1 | en | 2015 | other | 29 | The Anatolian Journal of Cardiology |
| 218573 | baslik-dergi-adi | zor | baslik-dergi-adi | 14 | en | 2015 | latex | 39 | Journal of Aquaculture Engineering and F |
| 219813 | temiz | kolay | temiz | 19 | en | 2009 | latex | 53 | Bogazici Journal: Review of Social, Econ |
| 221906 | temiz | kolay | temiz | 5 | en | 2014 | latex | 96 | GORM:Gynecology Obstetrics & Reproductiv |
| 223236 | baslik-yanlis | orta | baslik-yanlis | 2 | en | 2016 | indesign | 12 | Türk Göğüs Kalp Damar Cerrahisi Dergisi |
| 233442 | karakter-anomali | zor | karakter-anomali | 11 | en | 2013 | latex | 54 | Mathematical and Computational Applicati |
| 234112 | govde-yok | zor | govde-yok;ozet-eksik | 1 | en | 2017 | latex | 47 | European Journal of Rheumatology |
| 240323 | header-title-yok | zor | header-title-yok;yazar-eksik | 5 | en | 2017 | latex | 77 | Bilge Strateji |
| 240441 | temiz | kolay | temiz | 7 | en | 2015 | latex | 76 | Turkish Journal of Pediatrics |
| 242639 | karakter-anomali | zor | karakter-anomali;ozet-yok | 12 | en | 2013 | latex | 54 | Journal of the Entomological Research So |
| 242903 | karakter-anomali | zor | karakter-anomali;header-title-yok;ozet-eksik | 8 | tr | 2013 | latex | 65 | Adli Tıp Dergisi |
| 256197 | dusuk-benzerlik | orta | dusuk-benzerlik | 18 | en | 2017 | latex | 81 | GENÇLİK ARAŞTIRMALARI DERGİSİ |
| 261973 | temiz | kolay | temiz | 5 | en | 2014 | latex | 63 | Journal of FisheriesSciences.com |
| 268910 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 9 | tr | 2015 | other | 5 | Frankofoni |
| 277193 | ozet-eksik | orta | ozet-eksik | 22 | tr | 2017 | latex | 38 | İnsan ve Toplum Bilimleri Araştırmaları  |
| 281990 | temiz | kolay | temiz | 12 | en | 2017 | latex | 5 | İnönü Üniversitesi Eğitim Fakültesi Derg |
| 286729 | baslik-yanlis | orta | baslik-yanlis | 2 | en | 2017 | latex | 12 | Türk Göğüs Kalp Damar Cerrahisi Dergisi |
| 287138 | baslik-yanlis | zor | baslik-yanlis;yazar-eksik;ozet-eksik | 3 | tr | 2018 | other | 8 | Türk Dermatoloji Dergisi |
| 289155 | temiz | kolay | temiz | 4 | en | 2018 | other | 109 | Turkish Journal of Gastroenterology |
| 291466 | temiz | kolay | temiz | 4 | en | 2018 | other | 27 | Celal Bayar Üniversitesi Fen Bilimleri D |
| 291689 | temiz | kolay | temiz | 5 | en | 2018 | indesign | 88 | Erciyes Medical Journal |
| 293454 | temiz | kolay | temiz | 7 | en | 2018 | other | 74 | Anatomy |
| 294023 | temiz | kolay | temiz | 4 | en | 2017 | indesign | 3 | Kafkas Tıp Bilimleri Dergisi |
| 294195 | baslik-yanlis | orta | baslik-yanlis;ozet-yok | 6 | tr | 2017 | indesign | 68 | Bilgi Dünyası |
| 294250 | ozet-eksik | orta | ozet-eksik | 4 | tr | 2017 | other | 49 | Karaelmas Fen ve Mühendislik Dergisi |
| 297232 | karakter-anomali | zor | karakter-anomali | 19 | en | 2018 | latex | 10 | Hacettepe Journal of Mathematics and Sta |
| 298081 | ozet-eksik | orta | ozet-eksik | 2 | en | 2018 | indesign | 109 | Turkish Journal of Gastroenterology |
| 298868 | header-title-yok | zor | header-title-yok;ozet-yok | 18 | tr | 2018 | bos | 20 | Ahi Evran Üniversitesi Kırşehir Eğitim F |
| 299555 | temiz | kolay | temiz | 3 | en | 2018 | bos | 74 | Turkish Journal of Physical Medicine and |
| 301143 | ozet-eksik | orta | ozet-eksik;baslik-cift-dilli | 8 | tr | 2018 | other | 104 | Toplum ve Hekim |
| 303407 | temiz | kolay | temiz | 2 | en | 2018 | indesign | 16 | Turkish Journal of Urology |
| 303541 | temiz | kolay | temiz | 5 | en | 2019 | indesign | 26 | Turkish Journal of Urology |
| 304796 | karakter-anomali | zor | karakter-anomali | 7 | en | 2018 | other | 53 | Journal of Thermal Engineering |
| 305244 | ozet-eksik | orta | ozet-eksik | 23 | tr | 2018 | bos | 17 | Van Yüzüncü Yıl Üniversitesi Eğitim Fakü |
| 307857 | baslik-yanlis | orta | baslik-yanlis | 6 | en | 2018 | other | 16 | Üroonkoloji Bülteni |
| 309841 | ozet-yok | orta | ozet-yok | 8 | tr | 2017 | other | 60 | Emek Araştırma Dergisi |
| 310150 | temiz | kolay | temiz | 9 | en | 2018 | other | 48 | Dokuz Eylül Üniversitesi Mühendislik Fak |
| 310939 | temiz | kolay | temiz | 20 | tr | 2017 | indesign | 48 | International Journal of Social Inquiry |
| 311918 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik;ozet-yok | 20 | tr | 2018 | indesign | 50 | Addicta: The Turkish Journal on Addictio |
| 313560 | temiz | kolay | temiz | 6 | en | 2019 | other | 7 | Sakarya Üniversitesi Fen Bilimleri Ensti |
| 315379 | header-title-yok | zor | header-title-yok;ozet-yok | 26 | mix | 2019 | word | 106 | Atatürk Üniversitesi Türkiyat Araştırmal |
| 315616 | header-title-yok | zor | header-title-yok;ozet-eksik | 4 | en | 2019 | indesign | 2 | Türkiye Klinikleri Journal of Case Repor |
| 318514 | header-title-yok | zor | header-title-yok | 10 | en | 2019 | other | 11 | Balkan Journal of Electrical and Compute |
| 319303 | temiz | kolay | temiz | 30 | en | 2019 | word | 84 | Business and Management Studies: An Inte |
| 323600 | temiz | kolay | temiz | 12 | en | 2018 | word | 23 | Gazi University Journal of Science |
| 325302 | temiz | kolay | temiz | 4 | en | 2019 | other | 74 | Düşünen Adam - Psikiyatri ve Nörolojik B |
| 326008 | temiz | kolay | temiz | 6 | en | 2018 | other | 94 | Türk Tarım - Gıda Bilim ve Teknoloji der |
| 328577 | dusuk-benzerlik | orta | dusuk-benzerlik | 24 | en | 2018 | word | 62 | Eurasian Journal of Applied Linguistics |
| 334352 | temiz | kolay | temiz | 14 | mix | 2019 | other | 48 | Istanbul Ticaret Üniversitesi Sosyal Bil |
| 337526 | temiz | kolay | temiz | 31 | en | 2019 | other | 5 | KAFKAS ÜNİVERSİTESİ İKTİSADİ ve İDARİ Bİ |
| 338334 | temiz | kolay | temiz | 7 | en | 2020 | indesign | 81 | Turkish Journal of Anaesthesiology and R |
| 338587 | header-title-yok | zor | header-title-yok | 4 | en | 2019 | indesign | 97 | European Mechanical Science |
| 342803 | ozet-yok | orta | ozet-yok | 12 | en | 2019 | word | 2 | Turkish Studies - Economics, Finance, Po |
| 350658 | karakter-anomali | zor | karakter-anomali | 7 | en | 2018 | latex | 2 | Turkish Journal of Mathematics and Compu |
| 350983 | baslik-dergi-adi | zor | baslik-dergi-adi | 19 | en | 2019 | word | 2 | Turkish Studies - Information Technologi |
| 351663 | temiz | kolay | temiz | 13 | en | 2019 | word | 2 | Turkish Studies (Elektronik) |
| 353342 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik | 11 | tr | 2018 | indesign | 12 | Selcuk Medical Journal |
| 357894 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik;ozet-yok | 18 | en | 2019 | other | 50 | Addicta: The Turkish Journal on Addictio |
| 359240 | temiz | kolay | temiz | 12 | en | 2019 | other | 54 | Eskişehir Technical University Journal o |
| 359643 | ozet-eksik | orta | ozet-eksik | 5 | en | 2019 | other | 90 | International Journal of Agriculture, En |
| 359885 | baslik-cift-dilli | orta | baslik-cift-dilli | 14 | tr | 2018 | word | 17 | Ekonomi, Politika & Finans Araştırmaları |
| 360657 | baslik-cift-dilli | orta | baslik-cift-dilli | 5 | tr | 2020 | other | 100 | Androloji Bülteni |
| 363181 | baslik-yanlis | orta | baslik-yanlis | 5 | en | 2020 | latex | 8 | Journal of Turkish Spinal Surgery |
| 363482 | dusuk-benzerlik | orta | dusuk-benzerlik | 23 | tr | 2020 | other | 44 | Sosyoekonomi |
| 365957 | header-title-yok | zor | header-title-yok | 5 | en | 2020 | other | 11 | Turkish Journal of Hematology |
| 365961 | temiz | kolay | temiz | 5 | en | 2020 | other | 11 | Turkish Journal of Hematology |
| 368121 | temiz | kolay | temiz | 16 | en | 2020 | word | 36 | Journal of Tourism and Gastronomy Studie |
| 369855 | temiz | kolay | temiz | 5 | en | 2020 | other | 76 | An International Journal of Optimization |
| 373502 | ozet-eksik | orta | ozet-eksik | 10 | en | 2018 | other | 21 | IOJET |
| 373809 | baslik-cift-dilli | orta | baslik-cift-dilli | 7 | tr | 2020 | other | 0 | ANKEM Dergisi |
| 374483 | temiz | kolay | temiz | 24 | en | 2020 | other | 73 | Insight Turkey |
| 376495 | karakter-anomali | zor | karakter-anomali | 14 | en | 2018 | other | 17 | European Journal of Technique |
| 379690 | temiz | kolay | temiz | 6 | en | 2020 | latex | 96 | GORM:Gynecology Obstetrics & Reproductiv |
| 380686 | ozet-eksik | orta | ozet-eksik;baslik-cift-dilli | 11 | tr | 2019 | indesign | 45 | Cukurova Medical Journal |
| 383005 | temiz | kolay | temiz | 8 | en | 2019 | indesign | 102 | OPUS Uluslararası Toplum Araştırmaları D |
| 383196 | baslik-cift-dilli | orta | baslik-cift-dilli;ozet-yok | 9 | tr | 2018 | other | 25 | Medeniyet Medical Journal |
| 383295 | yazar-eksik | orta | yazar-eksik | 14 | en | 2020 | latex | 17 | Erciyes Üniversitesi İktisadi ve İdari B |
| 383653 | ozet-eksik | orta | ozet-eksik | 2 | en | 2019 | indesign | 45 | Cukurova Medical Journal |
| 385039 | baslik-yanlis | orta | baslik-yanlis;ozet-eksik | 3 | mix | 2020 | other | 0 | Kulak Burun Boğaz ve Baş Boyun Cerrahisi |
| 385283 | temiz | kolay | temiz | 25 | en | 2019 | other | 64 | ICONARP International Journal Of Archite |
| 386509 | temiz | kolay | temiz | 20 | mix | 2019 | word | 102 | OPUS Uluslararası Toplum Araştırmaları D |
| 391579 | dusuk-benzerlik | orta | dusuk-benzerlik | 19 | en | 2019 | word | 62 | Eurasian Journal of Applied Linguistics |
| 393465 | baslik-dergi-adi | zor | baslik-dergi-adi | 10 | en | 2019 | word | 82 | GIDA |
| 398124 | ozet-yok | orta | ozet-yok | 15 | en | 2019 | word | 66 | Nevşehir Hacı Bektaş Veli Üniversitesi S |
| 398499 | temiz | kolay | temiz | 13 | en | 2019 | word | 33 | RumeliDE Dil ve Edebiyat Araştırmaları D |
| 399854 | ozet-eksik | orta | ozet-eksik | 24 | en | 2020 | word | 14 | Necatibey Eğitim Fakültesi Elektronik Fe |
| 404394 | header-title-yok | zor | header-title-yok;ozet-yok | 29 | tr | 2021 | indesign | 102 | OPUS Uluslararası Toplum Araştırmaları D |
| 404522 | temiz | kolay | temiz | 14 | tr | 2020 | word | 37 | Iğdır Üniversitesi Sosyal Bilimler Dergi |
| 405707 | temiz | kolay | temiz | 8 | en | 2019 | other | 52 | Uluslararası Mühendislik Araştırma ve Ge |
| 406637 | temiz | kolay | temiz | 5 | en | 2021 | other | 15 | Bağcılar Tıp Bülteni |
| 406683 | temiz | kolay | temiz | 15 | en | 2021 | other | 53 | Journal of Thermal Engineering |
| 410053 | baslik-yanlis | orta | baslik-yanlis;ozet-eksik | 2 | en | 2021 | other | 76 | İstanbul Kuzey Klinikleri |
| 410094 | temiz | kolay | temiz | 6 | en | 2020 | other | 0 | Türkiye Klinikleri Journal of Case Repor |
| 411572 | govde-yok | zor | govde-yok;header-title-yok;ozet-eksik | 1 | en | 2020 | other | 35 | European Journal of Rheumatology |
| 414839 | temiz | kolay | temiz | 5 | en | 2021 | indesign | 3 | Marmara Medical Journal |
| 418481 | header-title-yok | zor | header-title-yok;ozet-eksik | 12 | en | 2020 | other | 54 | Turkish Studies (Elektronik) |
| 419553 | baslik-dergi-adi | zor | baslik-dergi-adi | 18 | en | 2020 | other | 54 | Turkish Studies - Social Sciences  |
| 420614 | temiz | kolay | temiz | 6 | en | 2020 | other | 9 | The Turkish Journal of Ear Nose and Thro |
| 422461 | temiz | kolay | temiz | 8 | en | 2020 | other | 76 | Turkish Journal of Pediatrics |
| 424296 | yazar-eksik | orta | yazar-eksik | 3 | en | 2020 | other | 88 | Erciyes Medical Journal |
| 425857 | temiz | kolay | temiz | 3 | en | 2020 | other | 93 | Turkish Journal of Anaesthesiology and R |
| 427429 | header-title-yok | zor | header-title-yok;ozet-yok | 28 | en | 2021 | other | 106 | Atatürk Üniversitesi Türkiyat Araştırmal |
| 427651 | temiz | kolay | temiz | 7 | en | 2020 | other | 25 | Haseki Tıp Bülteni |
| 445465 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik;ozet-yok | 6 | tr | 2021 | other | 16 | Süleyman Demirel Üniversitesi Tıp Fakült |
| 449311 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-eksik | 14 | en | 2020 | other | 18 | Annales de la Faculté de Droit d Istanbu |
| 449844 | temiz | kolay | temiz | 7 | en | 2021 | other | 54 | International Journal of Environment and |
| 451149 | temiz | kolay | temiz | 24 | en | 2021 | indesign | 34 | ARTS: Artuklu sanat ve beşeri bilimler d |
| 455033 | baslik-yanlis | orta | baslik-yanlis | 4 | en | 2020 | word | 5 | Sağlık Bilimleri Dergisi |
| 456177 | karakter-anomali | zor | karakter-anomali | 11 | en | 2019 | other | 4 | TWMS (Turkic World Mathematical Society) |
| 456806 | baslik-dergi-adi | zor | baslik-dergi-adi | 5 | tr | 2021 | other | 100 | Androloji Bülteni |
| 459053 | temiz | kolay | temiz | 4 | en | 2020 | other | 46 | Bezmiâlem Science |
| 460195 | temiz | kolay | temiz | 9 | en | 2021 | indesign | 71 | Türk Fizyoterapi ve Rehabilitasyon Dergi |
| 463679 | temiz | kolay | temiz | 8 | en | 2020 | other | 9 | Alınteri Zirai Bilimler Dergisi |
| 466415 | temiz | kolay | temiz | 5 | en | 2021 | other | 44 | Europan Journal of Science and Technolog |
| 466936 | temiz | kolay | temiz | 5 | en | 2020 | indesign | 30 | Joint diseases and related surgery |
| 468827 | temiz | kolay | temiz | 8 | en | 2019 | word | 27 | ACADEMIC PLATFORM-JOURNAL OF ENGINEERING |
| 469602 | temiz | kolay | temiz | 9 | en | 2021 | other | 7 | Sakarya Üniversitesi Fen Bilimleri Ensti |
| 473004 | temiz | kolay | temiz | 9 | en | 2020 | word | 53 | European Journal of Technique |
| 477964 | temiz | kolay | temiz | 8 | en | 2021 | indesign | 93 | Turkish Journal of Anaesthesiology and R |
| 479245 | yazar-eksik | orta | yazar-eksik | 3 | en | 2021 | other | 67 | Alpha psychiatry (Online) |
| 479507 | temiz | kolay | temiz | 9 | en | 2021 | word | 36 | Dicle Üniversitesi Mühendislik Fakültesi |
| 484795 | baslik-yanlis | orta | baslik-yanlis;ozet-eksik | 3 | en | 2021 | indesign | 24 | Türk Nöroloji Dergisi |
| 485532 | karakter-anomali | zor | karakter-anomali | 10 | en | 2014 | latex | 4 | Hacettepe Journal of Mathematics and Sta |
| 486620 | temiz | kolay | temiz | 10 | en | 2021 | indesign | 68 | Genel Türk Tarihi Araştırmaları Dergisi |
| 486762 | temiz | kolay | temiz | 6 | en | 2021 | other | 88 | Erciyes Medical Journal |
| 489933 | baslik-yanlis | orta | baslik-yanlis;ozet-eksik | 24 | mix | 2021 | other | 38 | Türk İslam Medeniyeti Akademik Araştırma |
| 495064 | karakter-anomali | zor | karakter-anomali | 13 | en | 2021 | latex | 6 | Hacettepe Journal of Mathematics and Sta |
| 495546 | ozet-yok | orta | ozet-yok | 7 | en | 2021 | word | 31 | International Journal of Automotive Scie |
| 499279 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-yok | 28 | tr | 2021 | word | 48 | Kahramanmaraş Sütçü İmam Üniversitesi İl |
| 500044 | temiz | kolay | temiz | 6 | en | 2021 | latex | 54 | Yüzüncü Yıl Üniversitesi Tarım Bilimleri |
| 509295 | ozet-eksik | orta | ozet-eksik | 14 | tr | 2022 | other | 21 | Gazi Üniversitesi Mühendislik Mimarlık F |
| 512095 | ozet-yok | orta | ozet-yok | 10 | en | 2022 | word | 31 | International Journal of Automotive Scie |
| 517266 | baslik-yanlis | orta | baslik-yanlis | 1 | en | 2020 | other | 15 | The Anatolian Journal of Cardiology |
| 517431 | karakter-anomali | zor | karakter-anomali;baslik-yanlis | 31 | tr | 2021 | other | 61 | Beytulhikme An International Journal of  |
| 522479 | temiz | kolay | temiz | 8 | en | 2022 | other | 30 | Joint diseases and related surgery |
| 522968 | temiz | kolay | temiz | 12 | en | 2022 | other | 9 | An International Journal of Optimization |
| 523022 | baslik-yanlis | orta | baslik-yanlis;ozet-eksik | 60 | en | 2022 | other | 54 | Yargıtay Dergisi |
| 523621 | temiz | kolay | temiz | 5 | en | 2022 | other | 26 | Diagnostic and Interventional Radiology |
| 524616 | baslik-cift-dilli | orta | baslik-cift-dilli | 11 | en | 2022 | word | 45 | Cukurova Medical Journal |
| 532256 | temiz | kolay | temiz | 3 | en | 2020 | other | 90 | Turkish journal of emergency medicine (O |
| 532527 | temiz | kolay | temiz | 12 | en | 2022 | other | 68 | Research on Engineering Structures and M |
| 533725 | ozet-eksik | orta | ozet-eksik | 21 | en | 2022 | other | 23 | Journal of Construction Engineering, Man |
| 534977 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-eksik | 7 | tr | 2022 | indesign | 100 | Androloji Bülteni |
| 535321 | ozet-eksik | orta | ozet-eksik;baslik-cift-dilli | 9 | en | 2022 | other | 0 | Türkiye Klinikleri Adli Tıp ve Adli Bili |
| 535677 | temiz | kolay | temiz | 26 | en | 2022 | other | 48 | Teknik Dergi |
| 536308 | baslik-cift-dilli | orta | baslik-cift-dilli | 7 | en | 2019 | other | 30 | Hemşirelikte Eğitim ve Araştırma |
| 609016 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 86 | tr | 2008 | word | 40 | Bilinmeyen_Dergi |
| 618644 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 76 | tr | 2016 | other | 59 | Bilinmeyen_Dergi |
| 618882 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 27 | tr | 2019 | word | 59 | Bilinmeyen_Dergi |
| 620896 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 94 | tr | 2019 | other | 40 | Bilinmeyen_Dergi |
| 1110700 | temiz | kolay | temiz | 4 | en | 2022 | other | 96 | GORM:Gynecology Obstetrics & Reproductiv |
| 1116232 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 26 | tr | 2021 | other | 48 | Ankara Avrupa Çalışmaları Dergisi |
| 1120026 | temiz | kolay | temiz | 17 | tr | 2022 | other | 22 | Muhafazakar Düşünce Dergisi |
| 1121357 | ozet-eksik | orta | ozet-eksik | 40 | tr | 2022 | word | 20 | Ahi Evran Üniversitesi Kırşehir Eğitim F |
| 1123845 | yazar-eksik | orta | yazar-eksik;ozet-yok | 7 | en | 2022 | other | 18 | GENÇLİK ARAŞTIRMALARI DERGİSİ |
| 1127957 | temiz | kolay | temiz | 7 | en | 2022 | indesign | 79 | Clinical and Experimental Health Science |
| 1131929 | temiz | kolay | temiz | 9 | en | 2022 | indesign | 90 | Cumhuriyet Science Journal |
| 1132305 | header-title-yok | zor | header-title-yok;ozet-yok | 26 | tr | 2022 | word | 61 | Beytulhikme An International Journal of  |
| 1139983 | temiz | kolay | temiz | 33 | en | 2022 | word | 68 | Dil Eğitimi ve Araştırmaları Dergisi |
| 1141142 | temiz | kolay | temiz | 23 | tr | 2021 | word | 54 | Nevşehir Hacı Bektaş Veli Üniversitesi S |
| 1141273 | baslik-yanlis | orta | baslik-yanlis | 13 | en | 2022 | other | 75 | Turkish Journal of Agriculture and Fores |
| 1142114 | baslik-cift-dilli | orta | baslik-cift-dilli;ozet-yok | 16 | tr | 2022 | word | 24 | Nevşehir Hacı Bektaş Veli Üniversitesi S |
| 1146308 | baslik-cift-dilli | orta | baslik-cift-dilli;ozet-yok | 21 | tr | 2022 | word | 17 | Buca Eğitim Fakültesi Dergisi |
| 1152267 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-eksik | 38 | mix | 2022 | word | 38 | EMakalat Mezhep Araştırmaları Dergisi |
| 1152916 | header-title-yok | zor | header-title-yok;ozet-yok | 192 | tr | 2020 | word | 105 | Bilinmeyen_Dergi |
| 1152923 | baslik-yanlis | orta | baslik-yanlis;ozet-yok | 153 | tr | 2020 | word | 111 | Bilinmeyen_Dergi |
| 1159082 | baslik-cift-dilli | orta | baslik-cift-dilli;ozet-yok | 15 | mix | 2023 | indesign | 7 | Osmanlı Mirası Araştırmaları Dergisi |
| 1161713 | karakter-anomali | zor | karakter-anomali;ozet-eksik | 19 | en | 2022 | latex | 6 | Hacettepe Journal of Mathematics and Sta |
| 1161917 | ozet-eksik | orta | ozet-eksik | 14 | en | 2022 | word | 2 | International journal of energy studies  |
| 1162628 | temiz | kolay | temiz | 6 | en | 2023 | indesign | 79 | Clinical and Experimental Health Science |
| 1165244 | temiz | kolay | temiz | 9 | en | 2022 | other | 97 | Annals of Medical Research |
| 1168459 | baslik-dergi-adi | zor | baslik-dergi-adi | 22 | en | 2022 | other | 20 | Yakın Dönem Türkiye Araştırmaları |
| 1170842 | temiz | kolay | temiz | 4 | en | 2023 | other | 74 | Türk Patoloji Dergisi |
| 1176120 | temiz | kolay | temiz | 6 | en | 2023 | other | 91 | Erciyes Medical Journal |
| 1177813 | ozet-eksik | orta | ozet-eksik | 10 | tr | 2023 | other | 26 | Çocuk ve Gençlik Ruh Sağlığı Dergisi |
| 1178166 | temiz | kolay | temiz | 20 | en | 2023 | word | 5 | Journal of the Turkish Chemical Society, |
| 1178310 | baslik-dergi-adi | zor | baslik-dergi-adi | 7 | en | 2021 | other | 9 | Uluslararası Hematoloji-Onkoloji Dergisi |
| 1178438 | temiz | kolay | temiz | 13 | en | 2023 | other | 3 | Archives of Rheumatology |
| 1178761 | baslik-cift-dilli | orta | baslik-cift-dilli | 3 | en | 2023 | other | 46 | Ulusal Romatoloji Dergisi |
| 1180757 | yazar-eksik | orta | yazar-eksik | 23 | en | 2022 | word | 5 | İnönü Üniversitesi Eğitim Fakültesi Derg |
| 1180797 | temiz | kolay | temiz | 15 | en | 2022 | word | 87 | İnönü Üniversitesi Eğitim Fakültesi Derg |
| 1180849 | temiz | kolay | temiz | 20 | tr | 2023 | word | 5 | Sinop Üniversitesi sosyal bilimler dergi |
| 1182209 | temiz | kolay | temiz | 8 | en | 2023 | word | 58 | Journal of Innovative Science and Engine |
| 1183123 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-eksik | 24 | tr | 2023 | word | 7 | Journal of universal history studies (On |
| 1183323 | temiz | kolay | temiz | 7 | tr | 2023 | word | 19 | JOURNAL OF ANATOLIAN ENVIRONMENTAL AND A |
| 1187586 | baslik-dergi-adi | zor | baslik-dergi-adi | 8 | en | 2023 | other | 32 | Turkish archives of pediatrics (Online) |
| 1188330 | ozet-yok | orta | ozet-yok | 29 | tr | 2022 | indesign | 86 | Dil ve Tarih-Coğrafya Fakültesi Dergisi |
| 1188683 | ozet-yok | orta | ozet-yok | 38 | tr | 2022 | indesign | 86 | Dil ve Tarih-Coğrafya Fakültesi Dergisi |
| 1189398 | temiz | kolay | temiz | 5 | en | 2023 | other | 3 | Ulusal Travma ve Acil Cerrahi Dergisi |
| 1190046 | header-title-yok | zor | header-title-yok;ozet-yok | 23 | mix | 2023 | indesign | 7 | Osmanlı Mirası Araştırmaları Dergisi |
| 1190772 | temiz | kolay | temiz | 9 | en | 2023 | indesign | 79 | Clinical and Experimental Health Science |
| 1193660 | temiz | kolay | temiz | 13 | en | 2023 | word | 20 | Uluslararası Tarım ve Yaban Hayatı Bilim |
| 1200501 | baslik-dergi-adi | zor | baslik-dergi-adi | 20 | en | 2023 | word | 20 | Uluslararası Ekonomi, İşletme ve Politik |
| 1205788 | baslik-yanlis | orta | baslik-yanlis | 4 | en | 2023 | latex | 16 | Annals of Medical Research |
| 1207129 | temiz | kolay | temiz | 19 | en | 2023 | word | 43 | Turkish Journal of Education |
| 1211913 | ozet-eksik | orta | ozet-eksik;baslik-cift-dilli | 26 | tr | 2023 | word | 17 | Uludağ Üniversitesi Eğitim Fakültesi Der |
| 1212123 | karakter-anomali | zor | karakter-anomali;ozet-eksik;dusuk-benzerlik | 17 | mix | 2023 | word | 14 | Van ilahiyat Dergisi  |
| 1218730 | karakter-anomali | zor | karakter-anomali | 12 | en | 2023 | latex | 2 | Turkish Journal of Mathematics and Compu |
| 1219618 | yazar-eksik | orta | yazar-eksik;ozet-eksik | 23 | en | 2023 | word | 37 | Sakarya University Journal of Education |
| 1219902 | temiz | kolay | temiz | 7 | en | 2024 | word | 39 | Black Sea Journal of Agriculture |
| 1221441 | ozet-yok | orta | ozet-yok | 18 | en | 2023 | word | 54 | International Journal of Public Finance  |
| 1223983 | baslik-cift-dilli | orta | baslik-cift-dilli | 19 | en | 2024 | word | 34 | Fiscaoeconomia |
| 1225818 | header-title-yok | zor | header-title-yok | 12 | tr | 2024 | indesign | 42 | Reflektif Sosyal Bilimler Dergisi |
| 1228079 | temiz | kolay | temiz | 28 | en | 2024 | latex | 4 | Communications Faculty of Sciences Unive |
| 1235830 | baslik-yanlis | zor | baslik-yanlis;yazar-eksik;ozet-eksik | 9 | tr | 2023 | latex | 107 | Bilinmeyen_Dergi |
| 1238017 | baslik-yanlis | orta | baslik-yanlis;ozet-yok | 37 | en | 2024 | latex | 63 | GÜMÜŞHANE ÜNİVERSİTESİ İLAHİYAT FAKÜLTES |
| 1238132 | header-title-yok | zor | header-title-yok;yazar-eksik;ozet-yok | 52 | tr | 2023 | latex | 107 | Bilinmeyen_Dergi |
| 1238434 | temiz | kolay | temiz | 5 | en | 2023 | other | 18 | International Dental Research |
| 1241544 | karakter-anomali | zor | karakter-anomali | 24 | en | 2024 | latex | 58 | Constructive mathematical analysis (Onli |
| 1242138 | temiz | kolay | temiz | 2 | en | 2023 | other | 11 | Turkish Journal of Hematology |
| 1246038 | temiz | kolay | temiz | 19 | en | 2024 | word | 5 | Gümüşhane Üniversitesi Sağlık Bilimleri  |
| 1246751 | temiz | kolay | temiz | 13 | en | 2024 | indesign | 28 | Ordu Üniversitesi Bilim ve Teknoloji Der |
| 1250862 | temiz | kolay | temiz | 9 | en | 2024 | indesign | 79 | Clinical and Experimental Health Science |
| 1253198 | dusuk-benzerlik | orta | dusuk-benzerlik | 8 | en | 2024 | word | 5 | Sağlık Bilimleri Dergisi |
| 1253201 | baslik-yanlis | orta | baslik-yanlis | 8 | en | 2024 | word | 5 | Sağlık Bilimleri Dergisi |
| 1255067 | temiz | kolay | temiz | 19 | en | 2023 | other | 77 | Journal of Thermal Engineering |
| 1257015 | temiz | kolay | temiz | 13 | en | 2022 | word | 34 | Düzce Üniversitesi Bilim ve Teknoloji De |
| 1257234 | temiz | kolay | temiz | 10 | en | 2023 | other | 94 | Türk Tarım - Gıda Bilim ve Teknoloji der |
| 1259954 | baslik-yanlis | orta | baslik-yanlis | 3 | en | 2024 | other | 75 | Turkish Journal of Medical Sciences |
| 1266209 | temiz | kolay | temiz | 17 | tr | 2024 | word | 54 | Osmaniye Korkut Ata Üniversitesi Fen Bil |
| 1268152 | temiz | kolay | temiz | 20 | en | 2024 | other | 28 | Adıyaman Üniversitesi Mühendislik Biliml |
| 1268278 | temiz | kolay | temiz | 20 | en | 2024 | indesign | 23 | Spiritual Psychology and Counseling |
| 1270517 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-yok | 16 | tr | 2024 | indesign | 0 | Düzce Üniversitesi Orman Fakültesi Orman |
| 1276080 | temiz | kolay | temiz | 4 | en | 2023 | other | 9 | Eurasian Journal of Pulmonology |
| 1284535 | temiz | kolay | temiz | 20 | en | 2024 | other | 68 | Research on Engineering Structures and M |
| 1290126 | temiz | kolay | temiz | 18 | en | 2024 | indesign | 69 | International Journal of 3D Printing Tec |
| 1290383 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-yok | 26 | mix | 2024 | latex | 39 | Hitit ilahiyat dergisi |
| 1290885 | bozuk-font | zor | bozuk-font;header-title-yok;yazar-eksik;ozet-yok | 7 | mix | 2024 | other | 103 | Genel Tıp Dergisi |
| 1291416 | temiz | kolay | temiz | 12 | en | 2024 | word | 23 | Sakarya University Journal of Computer a |
| 1293408 | ozet-yok | orta | ozet-yok | 22 | tr | 2024 | word | 2 | İnönü Üniversitesi Uluslararası Sosyal B |
| 1294441 | temiz | kolay | temiz | 4 | en | 2024 | word | 17 | Türk Doğa ve Fen Dergisi |
| 1294914 | temiz | kolay | temiz | 10 | en | 2024 | word | 19 | JOURNAL OF ANATOLIAN ENVIRONMENTAL AND A |
| 1299565 | temiz | kolay | temiz | 30 | mix | 2024 | indesign | 54 | Türkiye Adalet Akademisi Dergisi |
| 1308457 | temiz | kolay | temiz | 18 | en | 2024 | word | 33 | Yönetim ve Ekonomi Araştırmaları Dergisi |
| 1309073 | baslik-yanlis | orta | baslik-yanlis | 8 | en | 2024 | indesign | 16 | Haseki Tıp Bülteni |
| 1313057 | temiz | kolay | temiz | 12 | en | 2025 | word | 28 | Bartın Üniversitesi Eğitim Fakültesi Der |
| 1313113 | yazar-eksik | orta | yazar-eksik | 20 | en | 2025 | word | 87 | İnönü Üniversitesi Eğitim Fakültesi Derg |
| 1314085 | baslik-dergi-adi | zor | baslik-dergi-adi | 15 | en | 2025 | word | 5 | Acta Aquatica Turcica |
| 1329407 | temiz | kolay | temiz | 7 | en | 2025 | indesign | 94 | Türk Tarım - Gıda Bilim ve Teknoloji der |
| 1331207 | baslik-cift-dilli | orta | baslik-cift-dilli | 14 | en | 2025 | indesign | 42 | Reflektif Sosyal Bilimler Dergisi |
| 1333445 | temiz | kolay | temiz | 7 | en | 2025 | other | 47 | Şişli Etfal Hastanesi Tıp Bülteni |
| 1333641 | temiz | kolay | temiz | 6 | en | 2024 | other | 95 | Alpha psychiatry (Online) |
| 1333758 | baslik-yanlis | zor | baslik-yanlis;yazar-eksik;ozet-yok | 10 | en | 2025 | other | 75 | Turkish Journal of Medical Sciences |
| 1334937 | baslik-yanlis | orta | baslik-yanlis | 3 | tr | 2025 | bos | 67 | Türk Kardiyoloji Derneği Arşivi |
| 1336929 | temiz | kolay | temiz | 14 | en | 2024 | other | 89 | Bulletin of the mineral research and exp |
| 1338210 | temiz | kolay | temiz | 9 | en | 2025 | word | 44 | Journal of research in pharmacy (online) |
| 1338865 | temiz | kolay | temiz | 10 | en | 2025 | indesign | 94 | Türk Tarım - Gıda Bilim ve Teknoloji der |
| 1341940 | temiz | kolay | temiz | 3 | en | 2024 | bos | 32 | Turkish archives of pediatrics (Online) |
| 1342790 | temiz | kolay | temiz | 9 | en | 2024 | word | 94 | Türk Tarım - Gıda Bilim ve Teknoloji der |
| 1345386 | karakter-anomali | zor | karakter-anomali | 16 | en | 2025 | latex | 6 | Hacettepe Journal of Mathematics and Sta |
| 1347087 | temiz | kolay | temiz | 15 | en | 2025 | word | 23 | Gazi University Journal of Science Part  |
| 1353371 | temiz | kolay | temiz | 21 | mix | 2025 | indesign | 83 | Sanat & Tasarım Dergisi |
| 1354926 | temiz | kolay | temiz | 20 | en | 2025 | word | 54 | Gazi İktisat ve İşletme Dergisi |
| 1360724 | baslik-dergi-adi | zor | baslik-dergi-adi | 12 | en | 2024 | bos | 95 | The Anatolian Journal of Cardiology |
| 1360929 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik | 13 | en | 2025 | indesign | 3 | Environmental Research & Technology |
| 1369792 | temiz | kolay | temiz | 7 | en | 2025 | indesign | 3 | Medicine Science |
| 1372269 | header-title-yok | zor | header-title-yok | 25 | tr | 2025 | other | 86 | Dil ve Tarih-Coğrafya Fakültesi Dergisi |
| 1373827 | dusuk-benzerlik | orta | dusuk-benzerlik | 14 | mix | 2025 | word | 108 | Oksident |
| 1381852 | baslik-dergi-adi | zor | baslik-dergi-adi;yazar-eksik;ozet-yok | 14 | en | 2025 | word | 28 | Mobilya ve ahşap malzeme araştırmaları d |
| 1382041 | ozet-eksik | orta | ozet-eksik | 13 | en | 2025 | indesign | 70 | Turkish Journal of Pediatrics |
| 1382739 | karakter-anomali | zor | karakter-anomali | 17 | en | 2025 | latex | 6 | Hacettepe Journal of Mathematics and Sta |
| 1382972 | ozet-eksik | orta | ozet-eksik | 11 | tr | 2025 | indesign | 104 | Toplum ve Hekim |
| 1384709 | temiz | kolay | temiz | 5 | en | 2026 | indesign | 26 | Molecular Imaging and Radionuclide Thera |
| 1388658 | baslik-dergi-adi | zor | baslik-dergi-adi;ozet-eksik | 4 | tr | 2023 | other | 9 | Anatolia: Turizm Araştırmaları Dergisi |
| 1390563 | baslik-yanlis | zor | baslik-yanlis;yazar-eksik;ozet-yok | 20 | en | 2025 | other | 75 | Turkish Journal of Agriculture and Fores |
| 1390641 | temiz | kolay | temiz | 8 | en | 2026 | indesign | 90 | Cumhuriyet Science Journal |
| 1392420 | karakter-anomali | zor | karakter-anomali;baslik-cift-dilli | 23 | en | 2026 | other | 75 | Turkish Journal of Mathematics |
| 1394769 | ozet-eksik | orta | ozet-eksik;dusuk-benzerlik | 18 | tr | 2025 | latex | 52 | Yüzüncü Yıl Üniversitesi Sosyal Bilimler |
| 1395540 | ozet-yok | orta | ozet-yok | 13 | en | 2026 | word | 23 | İşletme Araştırmaları Dergisi |
| 1402745 | temiz | kolay | temiz | 3 | en | 2026 | indesign | 26 | Diagnostic and Interventional Radiology |
| 1406707 | baslik-dergi-adi | zor | baslik-dergi-adi | 5 | en | 2026 | word | 90 | KONURALP TIP DERGİSİ |
| 1407054 | temiz | kolay | temiz | 4 | en | 2026 | indesign | 47 | Anatolian journal of obstetrics and gyne |
| 1407315 | temiz | kolay | temiz | 4 | en | 2026 | indesign | 16 | Balkan Medical Journal |
| 1412541 | temiz | kolay | temiz | 11 | en | 2026 | word | 82 | Iğdır Üniversitesi Sosyal Bilimler Dergi |
| 1414299 | temiz | kolay | temiz | 6 | en | 2026 | indesign | 85 | European oral research (Online) |
| 1426985 | govde-yok | zor | govde-yok | 5 | en | 2026 | indesign | 74 | Anatolian Current Medical Journal |
| 1451290 | temiz | kolay | temiz | 16 | tr | 2026 | indesign | 19 | Food and Health |

## Sayısal özet (FLAG frekansı)

- `temiz` — 151
- `ozet-yok` — 81
- `ozet-eksik` — 53
- `header-title-yok` — 51
- `yazar-eksik` — 50
- `taranmis` — 46
- `grobid-crash` — 40
- `baslik-yanlis` — 29
- `baslik-dergi-adi` — 28
- `karakter-anomali` — 26
- `baslik-cift-dilli` — 24
- `dusuk-benzerlik` — 9
- `bozuk-font` — 8
- `govde-yok` — 8

Flag sayısı dağılımı: 1 flag: 253 · 2 flag: 75 · 3 flag: 54 · 4 flag: 6 · 5 flag: 3
