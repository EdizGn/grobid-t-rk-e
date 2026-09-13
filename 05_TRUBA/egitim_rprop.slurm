#!/bin/bash
#SBATCH -p barbun
#SBATCH -A egun
#SBATCH -J grobid_hdr_rprop
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 40
#SBATCH --mem=120G
#SBATCH --time=04:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/rprop-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/rprop-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header CRF -- rprop varyanti
#
# GROBID kaynaginda Wapiti algoritmasi sabitti (l-bfgs); --algo satiri
# WapitiTrainer.java:61'de yorum halindeydi. Kucuk bir yama ile sistem
# ozelliginden okunur hale getirildi:
#     -Dgrobid.wapiti.algo=rprop
# Deger verilmezse davranis eskisiyle birebir ayni (l-bfgs).
#
# YEREL OLCUM (40 belgelik mini korpus, ayni epsilon/window):
#     l-bfgs : 1.43 sn/iter, 40. iterasyonda egitim hatasi %1.92, hala dusuyor
#     rprop  : 1.20 sn/iter, 31. iterasyonda %0.00 -- erken durma tetiklendi
# Yani hem iterasyon %16 ucuz hem de cok daha az iterasyon gerekiyor.
# rprop ayrica l-bfgs gecmis vektorlerini tutmadigi icin cok daha az bellek
# harciyor (l-bfgs koşusu 38.3 GB MaxRSS kullanmisti).
#
# UYARI: Wapiti belgeleri rprop icin "daha hizli ama biraz daha az dogru"
# diyor ve yerel test 40 belgelik bir korpusta yapildi (ezberleme riski).
# GERCEK KARAR TUTULAN TEST KUMESINDEKI SKORLA VERILECEK. Bu is bittikten
# sonra egitim_hizli.slurm (l-bfgs) ile karsilastirilmali.
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
module load lib/java/jdk-22.0.1

if ! command -v java >/dev/null 2>&1; then
    echo "HATA: java bulunamadi."; exit 1
fi
echo "Java: $(java -version 2>&1 | head -1)"

T=${SLURM_CPUS_PER_TASK:-8}
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${T}/" \
    grobid-home/config/grobid.yaml
echo "nbThreads -> ${T}"

export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"

echo "TEI dosyasi: $(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml | wc -l)"
echo

java -Xmx16g \
     -Dgrobid.wapiti.algo=rprop \
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
