#!/usr/bin/env bash
# TRUBA'ya gonderilecek kendi kendine yeten egitim paketini hazirlar.
#
# Neden bu yaklasim: TRUBA hesaplama dugumlerinde internet erisimi genelde
# kapalidir; Gradle bagimlilik indiremez. Bunun yerine tum bagimliliklari
# iceren "onejar" yerelde derlenip gonderilir, TRUBA'da sadece:
#     java -jar grobid-trainer-onejar.jar 0 header -gH grobid-home ...
# calistirilir. Gradle, internet, Docker gerekmez.
#
# NOT: pdfalto egitim sirasinda CALISTIRILMAZ (createTraining adimi yerelde
# bitti), ama GrobidProperties baslarken varliginI DOGRULUYOR ve yoksa
# "Path to pdfalto doesn't exists" hatasiyla cokuyor. Bu yuzden Linux
# binary'sini (lin-64, 39 MB) pakete dahil ediyoruz.

set -euo pipefail

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
G="$KOK/grobid"
OUT="$KOK/05_TRUBA/paket"

JAR="$G/grobid-trainer/build/libs/grobid-trainer-0.9.2-SNAPSHOT-onejar.jar"
if [ ! -f "$JAR" ]; then
  echo "HATA: trainer onejar yok. Once:"
  echo "  cd grobid && ./gradlew --no-daemon :grobid-trainer:shadowJar"
  exit 1
fi

rm -rf "$OUT"
mkdir -p "$OUT"/{grobid-home,grobid-trainer/resources/dataset/header}

echo "1/5  onejar kopyalaniyor (194 MB)..."
cp "$JAR" "$OUT/grobid-trainer-onejar.jar"

echo "2/5  grobid-home (sadece gerekli parcalar)..."
# config    : GrobidProperties baslatmak icin sart
# lib       : libwapiti.so -- native CRF egitimi, Linux binary'si
# lexicon   : ozellik uretimi sirasinda okunuyor
# models/header: egitilmis model buraya yazilacak
for d in config lib lexicon schemas language-detection sentence-segmentation; do
  if [ -d "$G/grobid-home/$d" ]; then
    cp -r "$G/grobid-home/$d" "$OUT/grobid-home/"
  fi
done
# pdfalto: sadece Linux binary'si (diger platformlar 120 MB fazladan yer kaplar)
mkdir -p "$OUT/grobid-home/pdfalto"
cp -r "$G/grobid-home/pdfalto/lin-64" "$OUT/grobid-home/pdfalto/"
chmod +x "$OUT/grobid-home/pdfalto/lin-64/pdfalto"          "$OUT/grobid-home/pdfalto/lin-64/pdfalto_server" 2>/dev/null || true

mkdir -p "$OUT/grobid-home/models/header" "$OUT/grobid-home/tmp"

echo "3/5  egitim korpusu (tei + raw)..."
cp -r "$G/grobid-trainer/resources/dataset/header/corpus" \
      "$OUT/grobid-trainer/resources/dataset/header/"
cp -r "$G/grobid-trainer/resources/dataset/header/crfpp-templates" \
      "$OUT/grobid-trainer/resources/dataset/header/"
# yedek klasorleri gonderme -- gereksiz yer kaplar
rm -rf "$OUT/grobid-trainer/resources/dataset/header/corpus"/*_YEDEK*

echo "4/5  SLURM betikleri..."
cp "$KOK/05_TRUBA"/*.slurm "$OUT/" 2>/dev/null || true
cp "$KOK/05_TRUBA/OKUBENI.md" "$OUT/" 2>/dev/null || true

echo "5/5  ozet"
echo
echo "  TEI dosyasi : $(ls "$OUT/grobid-trainer/resources/dataset/header/corpus/tei/"*.xml 2>/dev/null | wc -l)"
echo "  raw dosyasi : $(ls "$OUT/grobid-trainer/resources/dataset/header/corpus/raw/" 2>/dev/null | wc -l)"
echo "  libwapiti.so: $([ -f "$OUT/grobid-home/lib/lin-64/libwapiti.so" ] && echo VAR || echo 'YOK -- SORUN!')"
echo "  pdfalto     : $([ -f "$OUT/grobid-home/pdfalto/lin-64/pdfalto" ] && echo VAR || echo 'YOK -- SORUN!')"
echo "  toplam      : $(du -sh "$OUT" 2>/dev/null | cut -f1)"
echo "  dosya sayisi: $(find "$OUT" -type f | wc -l)   (TRUBA inode kotasi: 500K)"
echo
echo "Paket: $OUT"
echo
echo "TRUBA'ya gondermek icin (once OpenVPN baglantisi aktif olmali):"
echo "  cd \"$KOK/05_TRUBA\""
echo "  tar czf paket.tar.gz -C paket ."
echo "  scp paket.tar.gz <kullanici>@172.16.6.11:/arf/scratch/<kullanici>/"
