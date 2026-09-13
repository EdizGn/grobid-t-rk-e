# GROBID Header Modeli — TRUBA Eğitimi

## Neden TRUBA

Yerel makinede (15.7 GB RAM) eğitim üç kez OOM verdi. Sebep matematiksel:

```
2999 belge → 5.392.070 blok → 97.057.566 öznitelik
```

Wapiti'nin L-BFGS'i öznitelik başına ~12 vektör tutuyor (~9.3 GB sabit),
üstüne thread başına 0.78 GB gradyan tamponu. 20 thread ile ~24 GB gerekiyor.

`barbun` kuyruğunda çekirdek başına 9600 MB var → 40 çekirdek = 375 GB.

## Paketin içinde ne var

| Dosya | Neden |
|---|---|
| `grobid-trainer-onejar.jar` | Tüm bağımlılıklar içinde. **Gradle ve internet gerekmiyor.** |
| `grobid-home/lib/lin-64/libwapiti.so` | Native CRF eğitim kütüphanesi (Linux) |
| `grobid-home/config/grobid.yaml` | Eğitim parametreleri |
| `grobid-home/lexicon/` | Öznitelik üretimi |
| `grobid-trainer/resources/.../corpus/{tei,raw}` | 2153 etiketli belge (v4) |
| `egitim.slurm` | Asıl eğitim işi |
| `test_debug.slurm` | Ön kontrol (30 dk, debug kuyruğu) |

| `grobid-home/pdfalto/lin-64/` | Eğitimde **çalıştırılmıyor**, ama `GrobidProperties` başlarken varlığını doğruluyor — yoksa çöküyor |

PDF→feature dönüşümü (createTraining) yerelde tamamlandı; pdfalto TRUBA'da hiç
çalışmayacak, sadece başlangıç doğrulamasını geçmek için pakette.

## v4 korpusu (paket_v4.tar.gz) — 9 Eylül 2026

Eğitilen önceki model (v1 etiketlemesi, 2999 belge) İngilizce
makalelerin %53.8'inde hiç başlık, %79.4'ünde hiç yazar üretmiyordu
(stok modelde bu oranlar %1.9 ve %1.3). Sebep etiketleme:

**CRF'te etiketsiz token = açık olumsuz örnek.** Bulunamayan alanı boş
bırakmak modele "bu alan burada yoktur" diye öğretiyor.

İki değişiklik yapıldı (`01_Header_Modeli/header_auto_annotate.py`):

1. **İngilizce başlık da `<docTitle>` olarak etiketleniyor.** v3'te İngilizce
   başlığı kapakta bulunan 1847 belgenin 1825'inde (%98.8) bu blok etiketsizdi.
   Özette TR+EN'i birlikte etiketliyorduk ve stoktan iyi olan tek alan o oldu.
   v4'te belgelerin %72.7'sinde iki başlık da etiketli.
2. **Yazar etiketi bulunamayan belge karantinaya gidiyor.** v3'te 471 belgede
   (%17.9) hiç `<docAuthor>` yoktu; v4'te %0.
   (`--yazar-zorunlu-degil` ile eski davranışa dönülebilir.)

Bedeli: korpus 2627 → 2153 belge (−%18).

| | v3 | v4 |
|---|---|---|
| belge | 2627 | 2153 |
| iki dilli başlık | %0 | %72.7 |
| `docAuthor` hiç yok | %17.9 | %0 |
| `keyword` hiç yok | %7.3 | %6.9 |
| `abstract` hiç yok | %0.5 | %0.5 |

Eski korpus `grobid-trainer/resources/dataset/header/corpus/tei_V3_YEDEK_*`
altında duruyor.

## Komut kartı — nerede çalıştırılır (9 Eylül 2026)

Karışmaması için ayrılmıştır. `[YEREL]` = Windows'taki Git Bash,
`[TRUBA]` = `ssh $KULLANICI@$TRUBA_SUNUCU` sonrası kabuk.

Asagidaki ornekleri kullanmadan once kendi degerlerinizi verin:

```bash
KULLANICI=truba_kullanici_adiniz
TRUBA_SUNUCU=172.16.6.11          # TRUBA giris dugumu (VPN arkasinda)
KOK=/klonladiginiz/depo/yolu
```

### 1. Paket / betik gönderme  — [YEREL]
```bash
scp "$KOK/05_TRUBA/paket_v4.tar.gz" $KULLANICI@$TRUBA_SUNUCU:/arf/scratch/$USER/
```
```bash
scp "$KOK/05_TRUBA/egitim_orfoz.slurm" "$KOK/05_TRUBA/egitim_barbun.slurm" "$KOK/05_TRUBA/olcum.slurm" $KULLANICI@$TRUBA_SUNUCU:/arf/scratch/$USER/grobid/
```

### 2. Paketi açma  — [TRUBA]
```bash
cd /arf/scratch/$USER/grobid && mv grobid-trainer/resources/dataset/header/corpus corpus_v3_yedek && tar xzf ../paket_v4.tar.gz && ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml | wc -l
```
`2153` görülmeli.

### 3. Eğitimi başlatma  — [TRUBA]
```bash
sbatch egitim_orfoz.slurm; sbatch egitim_barbun.slurm; squeue -u $USER
```

### 4. Takip  — [TRUBA]
```bash
squeue -u $USER --start
```
```bash
sacct -j <JOBID> --format=JobID,State,Elapsed,ExitCode,MaxRSS
```
```bash
grep -E "^Java:|nb threads" log/orfoz-*.out; grep -E "^ *\[" log/orfoz-*.err | head -3
```

### 5. Biteni al, diğerini kapat  — [TRUBA]
```bash
scancel <hala_kosan_isin_idsi>
```

### 6. Modeli indirme  — [YEREL]
```bash
scp $KULLANICI@$TRUBA_SUNUCU:"/arf/scratch/$USER/grobid/grobid-home/models/header/model*.wapiti*" "$KOK/05_TRUBA/"
```

### 7. Ölçüm  — [YEREL]  (Docker Desktop açık olmalı)
```bash
cd "$KOK/05_TRUBA" && ./olc_model.sh model.wapiti v4_600
```

### Çıktı yolları
| İş | Model dosyası |
|---|---|
| orfoz | `grobid-home/models/header/model.wapiti` |
| barbun | `grobid-home/models/header/model_barbun.wapiti` |

## Adımlar

### 1. Paketi yerelde hazırla
```bash
cd /c/Users/EG/Desktop/Tubitak___is/05_TRUBA
./paket_hazirla.sh
tar czf paket_v4.tar.gz -C paket .
```

### 2. TRUBA'ya gönder (OpenVPN açık olmalı)
```bash
scp paket_v4.tar.gz $KULLANICI@$TRUBA_SUNUCU:/arf/scratch/$USER/
```

### 3. TRUBA'da aç
```bash
ssh $KULLANICI@$TRUBA_SUNUCU
mkdir -p /arf/scratch/$USER/grobid
cd /arf/scratch/$USER/grobid
tar xzf ../paket_v4.tar.gz
mkdir -p log
ls    # egitim.slurm, test_debug.slurm, grobid-home, grobid-trainer görünmeli
```

### 4. Önce ön kontrol (ŞART)
```bash
sbatch test_debug.slurm
squeue -u $USER          # işin durumu
```
Bittiğinde:
```bash
cat log/test-*.out
```
"BAŞARILI: deneme modeli üretildi" görürsen ortam hazır.

### 5. Asıl eğitim
```bash
sbatch egitim.slurm
squeue -u $USER
```
Canlı takip:
```bash
tail -f log/egitim-*.out
```

### 6. Modeli geri al
```bash
# TRUBA'da:
ls -la /arf/scratch/$USER/grobid/grobid-home/models/header/

# Yerelde:
scp $KULLANICI@$TRUBA_SUNUCU:/arf/scratch/$USER/grobid/grobid-home/models/header/model.wapiti* .
```

## Önemli uyarılar

- **Arayüz sunucusunda (arf-ui1) iş çalıştırma** — hesap askıya alınabilir.
  Her şey `sbatch` ile kuyruğa gitmeli. Paket açma / dosya kopyalama sorun değil.
- TRUBA dosya sistemleri **yedeklenmiyor**. Model üretilince hemen indir.
- pdfalto Linux binary'si pakette olmalı — yoksa iş
  `GrobidPropertyException: Path to pdfalto doesn't exists` ile düşer.
- Java: TRUBA'da `jdk-17` ve `jdk-22.0.1` var. GROBID **Java 21 bytecode**
  üretiyor (class major=65), bu yüzden **jdk-17 çalışmaz**. Betikler
  `lib/java/jdk-22.0.1` yüklüyor.

## Faydalı komutlar

```bash
lssrv                      # kuyruk doluluk durumu
squeue -u $USER            # kendi işlerim
scancel <JOBID>            # iş iptal
sacct -j <JOBID> --format=JobID,State,Elapsed,MaxRSS   # bitmiş işin özeti
scontrol show job <JOBID>  # detay
```

## Eğitim bitince (yerelde)

```bash
# CRLF/.new tuzaklarını halleden kurulum
python 01_Header_Modeli/model_kur.py

# Ölçüm
cd 03_Test_ve_Degerlendirme/1500_random_test
python test_yeni.py && python birlesik_cikti.py
cd .. && python grobid_standart_eval.py --dil iki
```
