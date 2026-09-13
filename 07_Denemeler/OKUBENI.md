# Denemeler

Buradaki hiçbir şey ölçüm sonucu değildir.

Bu klasör **denemeleri** barındırır: "bu komut çalışıyor mu", "çıktı nasıl
görünüyor", "boru hattı ayakta mı" sorularını cevaplamak için birkaç belgeyle
yapılmış küçük koşular. Değerlendirme (test) için değil, doğrulama için
yapıldılar ve rakamları hiçbir yerde raporlanmamalıdır.

**Ayrım neden önemli:** 15 belgeyle eğitilmiş bir modelin skoru ile 1435
belgelik test kümesindeki skor aynı tabloya konulamaz. İkisini karıştırmak bu
projede bir kez bir günlük ölçümü çöpe attırdı.

| Klasör | Ne | Kaç belge |
|---|---|---|
| `delft_15_belge/` | DeLFT boru hattı duman testi — korpus formatının okunduğunu, glove LMDB'nin yüklendiğini, GPU eğitiminin çalıştığını kanıtladı. 6 epoch, loss 1552→358. Model anlamsız, amaç o değildi. | 15 |
| `tek_makale_createTraining/` | `createTraining` komutunun ne ürettiğini görmek için tek makale (84409) üzerinde koşu — figure, fulltext, segmentation, header çıktıları bir arada | 1 |
| `segmentasyon_ornekleri/` | Segmentasyon TEI yapısının erken keşfi, birkaç örnek makale ve bir analiz notu | ~8 |
| `eski_loglar/` | `grobid-trainer.log` | — |

## Gerçek testler nerede

| Küme | Yer | Boyut |
|---|---|---|
| Türkçe değerlendirme | `03_Test_ve_Degerlendirme/1500_random_test/` | 1435 makale |
| İngilizce referans | `03_Test_ve_Degerlendirme/ingilizce_kiyas/` | 519 makale |
| Elle doğrulanmış altın küme | `03_Test_ve_Degerlendirme/altin_test/` | 300 makale (20'si doğrulandı) |
| Zorluk katmanlı benchmark | `06_Benchmark_Veritabani/` | 300 makale |

Ölçüm sonuçlarının tamamı `05_TRUBA/olcumler/` altında, okunabilir hali
`03_Test_ve_Degerlendirme/dashboard/olcumler.html` sayfasında.
