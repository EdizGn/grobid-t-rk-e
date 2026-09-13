#!/bin/bash
#SBATCH -p barbun
#SBATCH -A egun
#SBATCH -J grobid_hdr_hizli
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 40
#SBATCH --mem=120G
#SBATCH --time=06:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/hizli-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/hizli-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header CRF modeli -- HIZLI VARYANT
#
# egitim.slurm ile tek farki Wapiti durma olcutu:
#
#   GROBID varsayilani (grobid.yaml):  -e 0.000001  -w 30
#   Wapiti'nin kendi varsayilani    :  -e 0.00002   -w 5
#
# Wapiti'de -w = --stopwin, yani "goreli iyilesme -e'nin altinda kac
# iterasyon UST USTE kalirsa dur". GROBID'in ayari (20x daha sikı esik,
# 6x daha uzun pencere) pratikte hic tetiklenmiyor; is her zaman -i ile
# verilen iterasyon tavanini sonuna kadar yakiyor. 600 iterasyon ~10 saat.
#
# Burada Wapiti'nin kendi varsayilanina donuyoruz: model yakinsayinca
# kendi duruyor. -i 300 yalnizca tavan, beklenti ~150-250 iterasyon.
#
# NOT: -epsilon ve -w komut satirindan geciyor (TrainerRunner.java:119,131),
# grobid.yaml'a dokunmaya gerek yok.
# ---------------------------------------------------------------------------

set -euo pipefail

KOK=/arf/scratch/$USER/grobid
cd "$KOK"
mkdir -p log

echo "=========================================="
echo "Is    : $SLURM_JOB_ID   Kuyruk: $SLURM_JOB_PARTITION"
echo "Sunucu: $SLURM_NODELIST"
echo "Cekirdek: ${SLURM_CPUS_PER_TASK:-1}"
echo "Baslangic: $(date)"
echo "=========================================="

module purge
# GROBID Java 21 bytecode uretiyor (class major=65), jdk-17 CALISTIRAMAZ.
module load lib/java/jdk-22.0.1

if ! command -v java >/dev/null 2>&1; then
    echo "HATA: java bulunamadi."; exit 1
fi
echo "Java: $(java -version 2>&1 | head -1)"

# Wapiti thread sayisi grobid.yaml'dan okunuyor, komut satirindan gecilemiyor.
T=${SLURM_CPUS_PER_TASK:-8}
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${T}/" \
    grobid-home/config/grobid.yaml
echo "nbThreads -> ${T}"
grep -n "nbThreads" grobid-home/config/grobid.yaml

export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"

echo "TEI dosyasi: $(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml | wc -l)"
echo

java -Xmx16g \
     -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
     -jar grobid-trainer-onejar.jar \
     0 header \
     -gH "$KOK/grobid-home" \
     -epsilon 0.00002 \
     -w 5 \
     -maxIter 300

echo
echo "Bitis: $(date)"
ls -la grobid-home/models/header/
sacct -j "$SLURM_JOB_ID" --format=JobID,State,Elapsed,MaxRSS 2>/dev/null || true
