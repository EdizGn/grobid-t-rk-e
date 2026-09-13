#!/usr/bin/env bash
# ADIM 2/4 -- PDF'lerden GROBID egitim verisi (raw feature + TEI) uretir.
#
# Neden Docker: pdfalto (C++) Windows'ta yok (grobid-home/pdfalto/win-64 bos),
# bu yuzden CreateProcess error=2 aliniyor. Linux binary'si (lin-64) mevcut,
# o yuzden islemi bir JDK container'i icinde calistiriyoruz.
#
# Kullanim:
#   ./adim2_createTraining.sh [girdi_pdf_dizini] [cikti_dizini] [parca_boyutu]

set -euo pipefail

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
GROBID="$KOK/grobid"
GIRDI="${1:-$KOK/03_Test_ve_Degerlendirme/altin_test/pdf}"
CIKTI="${2:-$KOK/03_Test_ve_Degerlendirme/altin_test/kapak_metni}"
PARCA="${3:-250}"

JAR="grobid-core/build/libs/grobid-core-0.9.2-SNAPSHOT-onejar.jar"
if [ ! -f "$GROBID/$JAR" ]; then
  echo "HATA: onejar yok. Once: cd grobid && ./gradlew :grobid-core:shadowJar"
  exit 1
fi

mkdir -p "$CIKTI"
TOPLAM=$(ls "$GIRDI"/*.pdf 2>/dev/null | wc -l)
echo "girdi PDF   : $TOPLAM"
echo "cikti       : $CIKTI"
echo "parca boyutu: $PARCA"
echo

# Bellek tasmasini onlemek icin parca parca isliyoruz; ayrica bir parca
# coktugunde tum kosu degil sadece o parca kaybedilir.
CALISMA="$KOK/03_Test_ve_Degerlendirme/altin_test/.parca"
rm -rf "$CALISMA"; mkdir -p "$CALISMA"

i=0; parca_no=0
for f in "$GIRDI"/*.pdf; do
  ad=$(basename "$f")
  # zaten islenmisse atla
  if [ -f "$CIKTI/${ad%.pdf}.training.header" ]; then continue; fi
  if [ $((i % PARCA)) -eq 0 ]; then
    parca_no=$((parca_no + 1))
    mkdir -p "$CALISMA/p$parca_no"
  fi
  cp "$f" "$CALISMA/p$parca_no/"
  i=$((i + 1))
done

if [ "$i" -eq 0 ]; then echo "Islenecek yeni PDF yok."; rm -rf "$CALISMA"; exit 0; fi
echo "islenecek: $i PDF, $parca_no parca"
echo

for p in "$CALISMA"/p*; do
  n=$(ls "$p"/*.pdf 2>/dev/null | wc -l)
  echo "--- $(basename "$p") ($n PDF) ---"
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$(cygpath -w "$GROBID")":/opt/grobid \
    -v "$(cygpath -w "$p")":/data/in \
    -v "$(cygpath -w "$CIKTI")":/data/out \
    -w /opt/grobid \
    --memory=6g \
    eclipse-temurin:21-jdk \
    java -Xmx5g -jar "$JAR" \
      -gH grobid-home -dIn /data/in -dOut /data/out -exe createTraining \
    2>&1 | grep -viE "^\s*$|INFO|DEBUG" | tail -5 || true
  # createTraining butun modeller icin veri uretiyor (fulltext, figure,
  # references, segmentation...). Bize sadece header lazim; disk %99 dolu
  # oldugu icin gerisini her parcadan sonra siliyoruz (3000 belgede ~4.3 GB fark).
  find "$CIKTI" -maxdepth 1 -type f -name "*.training.*"        ! -name "*.training.header" ! -name "*.training.header.tei.xml"        -delete 2>/dev/null || true
  uretilen=$(ls "$CIKTI"/*.training.header 2>/dev/null | wc -l)
  echo "    toplam uretilen header dosyasi: $uretilen"
done

rm -rf "$CALISMA"
echo
echo "BITTI"
echo "  .training.header      : $(ls "$CIKTI"/*.training.header 2>/dev/null | wc -l)"
echo "  .training.header.tei.xml: $(ls "$CIKTI"/*.training.header.tei.xml 2>/dev/null | wc -l)"
