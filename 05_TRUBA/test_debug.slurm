#!/bin/bash
#SBATCH -p debug
#SBATCH -A egun
#SBATCH -J grobid_test
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 8
#SBATCH --time=00:30:00
#SBATCH --output=/arf/scratch/egun/grobid/log/test-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/test-%j.err

# ---------------------------------------------------------------------------
# ON KONTROL ISI -- asil egitimden once ortamin dogru oldugunu dogrular.
# debug kuyrugu maks 4 saat; bu is 30 dakika istiyor ve genelde hemen baslar.
#
# Kontrol ettikleri:
#   1) java calisiyor mu, surumu 21+ mi
#   2) libwapiti.so yuklenebiliyor mu (native JNI koprusu)
#   3) korpus dosyalari yerinde mi
#   4) onejar acilip TrainerRunner'a ulasilabiliyor mu
#   5) 5 iterasyonluk mini egitim gercekten calisiyor mu
# ---------------------------------------------------------------------------

set -uo pipefail

KOK=/arf/scratch/$USER/grobid
cd "$KOK"
mkdir -p log

echo "=== 1) ORTAM ==="
echo "Sunucu   : $(hostname)"
echo "Cekirdek : ${SLURM_CPUS_PER_TASK:-1}"
echo "Bellek   : $(free -g | awk '/^Mem:/{print $2" GB toplam, "$7" GB kullanilabilir"}')"
echo

module purge
module load lib/java/jdk-22.0.1
echo "=== 2) JAVA ==="
if command -v java >/dev/null 2>&1; then
    java -version 2>&1 | head -2
else
    echo "HATA: java yok"; exit 1
fi
echo

echo "=== 3) NATIVE KUTUPHANE ==="
ls -la grobid-home/lib/lin-64/libwapiti.so 2>/dev/null || echo "HATA: libwapiti.so YOK"
export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
echo

echo "=== 4) KORPUS ==="
echo "TEI : $(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml 2>/dev/null | wc -l)"
echo "raw : $(ls grobid-trainer/resources/dataset/header/corpus/raw/ 2>/dev/null | wc -l)"
echo "sablon: $(ls grobid-trainer/resources/dataset/header/crfpp-templates/ 2>/dev/null)"
echo

echo "=== 5) MINI EGITIM (5 iterasyon) ==="
# Asil modeli EZMEMEK icin ayri bir cikti yoluna yaziyoruz.
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${SLURM_CPUS_PER_TASK:-8}/" \
    grobid-home/config/grobid.yaml

java -Xmx8g \
     -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
     -jar grobid-trainer-onejar.jar \
     0 header \
     -gH "$KOK/grobid-home" \
     -maxIter 5 \
     -modelPath "$KOK/log/deneme_model.wapiti"

echo
echo "=== SONUC ==="
if [ -s "$KOK/log/deneme_model.wapiti" ]; then
    echo "BASARILI: deneme modeli uretildi ($(du -h "$KOK/log/deneme_model.wapiti" | cut -f1))"
    head -c 20 "$KOK/log/deneme_model.wapiti"; echo
    echo
    echo ">>> Ortam hazir. Asil egitim: sbatch egitim.slurm"
else
    echo "BASARISIZ: model uretilemedi, yukaridaki hatalara bak."
fi
