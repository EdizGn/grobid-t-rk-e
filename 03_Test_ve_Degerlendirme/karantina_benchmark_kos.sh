#!/usr/bin/env bash
# createTraining bitene kadar bekler, sonra GROBID'i ayaga kaldirip
# karantina benchmark'ini kosar. Ikisini ayni anda calistirmak GROBID
# container'ini OOM'a sokuyordu (daha once 137 ile olmustu).
set -u
# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PARCA="$KOK/04_Genisletilmis_Egitim/.parca"
CIKTI="$KOK/04_Genisletilmis_Egitim/egitim_verisi"

echo "[1/5] createTraining bitmesi bekleniyor..."
bekleme=0
son=-1
durgun=0
while [ -d "$PARCA" ]; do
  sayi=$(ls "$CIKTI"/*.training.header 2>/dev/null | wc -l)
  if [ "$sayi" -eq "$son" ]; then durgun=$((durgun+1)); else durgun=0; fi
  son=$sayi
  # 20 dk hic ilerleme yoksa cokmustur, bekleme
  if [ "$durgun" -ge 40 ]; then
    echo "    UYARI: 20 dk ilerleme yok ($sayi dosya). createTraining cokmus olabilir."
    echo "    benchmark yine de baslatiliyor."
    break
  fi
  bekleme=$((bekleme+1))
  if [ $((bekleme % 10)) -eq 1 ]; then echo "    ... $sayi header dosyasi"; fi
  sleep 30
done
echo "    createTraining durdu. header dosyasi: $(ls "$CIKTI"/*.training.header 2>/dev/null | wc -l)"

echo "[2/5] GROBID baslatiliyor"
docker start grobid >/dev/null 2>&1
for i in $(seq 1 60); do
  if curl -s -m 3 http://127.0.0.1:8070/api/isalive | grep -qi true; then break; fi
  sleep 5
done
if ! curl -s -m 3 http://127.0.0.1:8070/api/isalive | grep -qi true; then
  echo "HATA: GROBID ayaga kalkmadi."; exit 1
fi
echo "    ayakta"

echo "[3/5] kurulu model dogrulamasi"
for m in header segmentation; do
  oz=$(docker exec grobid sh -c "head -c 40 /opt/grobid/grobid-home/models/$m/model.wapiti" 2>/dev/null | grep -oE '#mdl#[0-9]+#[0-9]+')
  echo "    $m : $oz"
done

echo "[4/5] 1051 PDF isleniyor"
cd "$KOK/03_Test_ve_Degerlendirme" || exit 1
python karantina_benchmark.py --isle --is-sayisi 4

echo "[5/5] skorlaniyor"
python grobid_standart_eval.py \
  --xml "$KOK/03_Test_ve_Degerlendirme/karantina_benchmark/grobid_xml" \
  --db "$KOK/04_Genisletilmis_Egitim/egitim_metadatalar.db" \
  --diakritik-yoksay \
  | tee "$KOK/05_TRUBA/olcumler/TR_v4_karantina1051.txt"
echo "BITTI"
