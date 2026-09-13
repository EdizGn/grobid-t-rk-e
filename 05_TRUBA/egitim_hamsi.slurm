#!/bin/bash
#SBATCH -p hamsi
#SBATCH -A egun
#SBATCH -J grobid_hamsi
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 56
#SBATCH --mem=90G
#SBATCH --time=12:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/egitim-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/egitim-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header CRF modeli egitimi (Wapiti)
#
# Neden TRUBA: yerel makinede 15.7 GB RAM yetmedi. 2999 belgelik korpus
# 97 milyon oznitelik uretiyor; Wapiti'nin L-BFGS'i oznitelik basina ~12
# vektor tutuyor (~9.3 GB sabit) + thread basina 0.78 GB gradyan tamponu.
# hamsi: Xeon Gold 6338 (2021) -- barbun'un 6248R'sinden (2019) bir nesil
# yeni, orfoz'dan eski ama kuyrugu cok daha kisa (55 bekleyen is / orfoz 272).
# DIKKAT: dokumantasyon "en az 28 cekirdek" diyor ama QOS politikasi
# node basina 56 cekirdek dayatiyor (28 ile gonderim reddediliyor).
# Cekirdek basina 3420 MB, 56 cekirdek = 191 GB; 12 thread ile ihtiyac ~20 GB.
#
# Gradle KULLANILMIYOR: tum bagimliliklar onejar icinde, internet gerekmez.
# pdfalto GEREKMIYOR: createTraining adimi yerelde tamamlandi.
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
# TRUBA'da iki Java modulu var: jdk-17 ve jdk-22.0.1
# GROBID Java 21 bytecode uretiyor (class major=65), jdk-17 CALISTIRAMAZ.
module load lib/java/jdk-22.0.1

if ! command -v java >/dev/null 2>&1; then
    echo "HATA: java bulunamadi."; exit 1
fi
echo "Java: $(java -version 2>&1 | head -1)"

# Wapiti thread sayisini SLURM'den alinan cekirdek sayisiyla esitle.
# (GROBID bunu grobid.yaml'daki nbThreads'ten okuyor, komut satirindan gecilemiyor.)
# DIKKAT: thread sayisi bilerek cekirdek sayisindan AZ.
# Olcum: orfoz'da 8 thread = 25 sn/iterasyon, barbun'da 40 thread = 57 sn.
# Is bellek-bagimli (97M oznitelik x 776 MB/thread gradyan tamponu); thread
# eklemek bellek bant genisligini doyuruyor ve NUMA trafigi yaratiyor.
# SLURM min 56 cekirdek istiyor ama Wapiti'ye 12 thread veriyoruz.
T=${WAPITI_THREADS:-12}
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${T}/" \
    grobid-home/config/grobid.yaml
echo "nbThreads -> ${T}"
grep -n "nbThreads" grobid-home/config/grobid.yaml

# Wapiti native kutuphanesi (libwapiti.so) java.library.path ile bulunur.
export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"

# Gecici dosyalar hizli yerel NVMe'de olsun (TRUBA /tmp NVMe olarak yapilandirilmis)
export TMPDIR="${TMPDIR:-/tmp}"

echo "TEI dosyasi: $(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml | wc -l)"
echo

# 0 = sadece egit.  Iterasyon sayisi komut satirindan geciliyor.
java -Xmx16g \
     -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
     -jar grobid-trainer-onejar.jar \
     0 header \
     -gH "$KOK/grobid-home" \
     -maxIter 600

echo
echo "Bitis: $(date)"
ls -la grobid-home/models/header/
sstat -j "$SLURM_JOB_ID" --format=JobID,MaxRSS,MaxVMSize 2>/dev/null || true
