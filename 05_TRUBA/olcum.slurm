#!/bin/bash
#SBATCH -p debug
#SBATCH -A egun
#SBATCH -J grobid_olcum
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 40
#SBATCH --mem=100G
#SBATCH --time=00:50:00
#SBATCH --output=/arf/scratch/egun/grobid/log/olcum-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/olcum-%j.err

# ---------------------------------------------------------------------------
# DONANIM / ALGORITMA KIYASI -- gercek korpusta 5 iterasyon kosup
# sn/iterasyon raporlar. Model uretmez, sadece olcer.
#
# NEDEN: 600 iterasyonluk barbun kosusunun logu, modelin 600'de HALA
# yakinsamadigini gosterdi (590->600 bagil azalma 3.3e-4, Wapiti'nin durma
# esigi 2e-5). Yani iterasyon kismak dogrudan kalite kaybi. Geriye kaliteye
# dokunmayan iki yol kaliyor: daha hizli donanim, daha iyi optimizasyon.
# Ikisi de tahminle degil olcumle secilmeli.
#
# BILINEN REFERANS:
#     barbun, 40 thread, l-bfgs, 2999 belge  ->  58 sn/iterasyon
#     smp   , 112 thread, l-bfgs, 2999 belge -> 312 sn/iterasyon
#
# DONANIM (scontrol show node):
#     barbun  : 20 cekirdek/soket x 2 soket =  40   384 GB
#     hamsi   : 28 cekirdek/soket x 2 soket =  56   191 GB
#     orfoz   : 56 cekirdek/soket x 2 soket = 112   256 GB   <- en yeni, denenmedi
#     orkinos : 14 cekirdek/soket x 16 soket = 224    4 TB   <- smp'nin 312 sn'si
#                                                              16 NUMA bolgesinden;
#                                                              bu kuyruk elendi.
# Bu betik v4 korpusu (2153 belge) ile kostugu icin rakamlar dogrudan
# barbun'un 58'iyle kiyaslanamaz; ONCE barbun'da bir kez kosturup kendi
# taban degerini uret, digerlerini ona gore oku.
#
# KULLANIM (sbatch satirindan kuyruk/cekirdek/algoritma degistirilebilir):
#     sbatch -C barbun -c 40                 olcum.slurm     # taban
#     sbatch -C orfoz  -c 112                olcum.slurm
#     sbatch -C orfoz  -c 56                 olcum.slurm     # NUMA testi
#     sbatch -C hamsi  -c 56                 olcum.slurm
#     ALGO=rprop sbatch -C barbun -c 40      olcum.slurm
#
# Sonuclari toplu gormek icin:
#     grep -H "SONUC" log/olcum-*.out
# ---------------------------------------------------------------------------

set -uo pipefail

KOK=/arf/scratch/$USER/grobid
cd "$KOK"
mkdir -p log

ALGO="${ALGO:-l-bfgs}"
ITER=5

echo "=========================================="
echo "Is       : ${SLURM_JOB_ID:-yerel}"
echo "Kuyruk   : ${SLURM_JOB_PARTITION:-?}"
echo "Sunucu   : ${SLURM_NODELIST:-?}"
echo "Cekirdek : ${SLURM_CPUS_PER_TASK:-1}"
echo "Algoritma: ${ALGO}"
echo "=========================================="
lscpu 2>/dev/null | grep -E "^Model name|^Socket|^Core\(s\) per socket|^CPU MHz|^NUMA node\(s\)" || true
echo

# Java: bazi dugumlerde (orn. orfoz) "module" batch kabugunda tanimli degil;
# module load sessizce basarisiz olup sistem Java 11'ine dusuyor ve GROBID
# (class version 65) UnsupportedClassVersionError veriyor. Elle basliyoruz.
if ! command -v module >/dev/null 2>&1; then
    for f in /etc/profile.d/modules.sh /usr/share/Modules/init/bash \
             /usr/share/lmod/lmod/init/bash /etc/profile.d/lmod.sh; do
        [ -f "$f" ] && . "$f" && break
    done
fi
if command -v module >/dev/null 2>&1; then
    module purge 2>/dev/null
    module load lib/java/jdk-22.0.1 2>/dev/null || echo "UYARI: java modulu yuklenemedi"
fi
command -v java >/dev/null 2>&1 || { echo "HATA: java yok"; exit 1; }
JAVA_SATIR=$(java -version 2>&1 | head -1)
echo "Java: $JAVA_SATIR"
JV=$(echo "$JAVA_SATIR" | sed -n 's/.*version "\([0-9][0-9]*\).*/\1/p')
if [ -z "$JV" ] || [ "$JV" -lt 21 ]; then
    echo "HATA: Java ${JV:-?}; en az 21 gerekiyor."
    exit 1
fi

# --- ISE OZEL grobid-home -------------------------------------------------
# ONEMLI: nbThreads grobid.yaml'dan okunuyor ve komut satirindan gecilemiyor.
# Bu betigin ilk surumu paylasilan grobid-home/config/grobid.yaml uzerinde
# "sed -i" yapiyordu; ayni anda birden fazla olcum gonderilince isler
# birbirinin ayarini eziyordu. 6340293 isi "-c 112" ile gonderildigi halde
# logunda "nb threads: 40" yaziyordu -- yani olculen degerler yanlis
# konfigurasyona atfediliyordu.
#
# Cozum: agir klasorler sembolik bag, config/ gercek kopya. Boylece her is
# kendi yaml'ini yazar, paralel gonderim guvenli olur.
T=${SLURM_CPUS_PER_TASK:-8}
GH="$KOK/gh-${SLURM_JOB_ID:-0}"
rm -rf "$GH"; mkdir -p "$GH"
for d in "$KOK"/grobid-home/*; do
    ad=$(basename "$d")
    [ "$ad" = "config" ] && continue
    ln -s "$d" "$GH/$ad"
done
cp -r "$KOK/grobid-home/config" "$GH/config"
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${T}/" \
    "$GH/config/grobid.yaml"
echo "ise ozel grobid-home: $GH"
grep -n "nbThreads:" "$GH/config/grobid.yaml"

export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"

BELGE=$(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml 2>/dev/null | wc -l)
echo "TEI dosyasi: ${BELGE}"
[ "$BELGE" -lt 100 ] && { echo "HATA: korpus eksik"; exit 1; }

# Modeli bozmamak icin ciktiyi ayri bir yola yaziyoruz.
mkdir -p olcum_ciktisi
LOG=log/olcum-ham-${SLURM_JOB_ID:-0}.log

java -Xmx16g \
     -Dgrobid.wapiti.algo="${ALGO}" \
     -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
     -jar grobid-trainer-onejar.jar \
     0 header \
     -gH "$GH" \
     -epsilon 0.00002 \
     -w 5 \
     -maxIter "$ITER" \
     -modelPath "$KOK/olcum_ciktisi/olcum.wapiti" > "$LOG" 2>&1
RC=$?

echo
grep -E "nb blocks|nb features|nb train|Train the model" "$LOG" || true
echo
grep -E "^[[:space:]]*\[" "$LOG" || true

# Ilk iterasyon isinma iceriyor; 2..son'un ortalamasini aliyoruz.
ORT=$(sed -n 's/.*time=\([0-9.]*\)s\/.*/\1/p' "$LOG" | tail -n +2 |
      awk '{t+=$1; n++} END{if(n) printf "%.2f", t/n; else print "?"}')

echo
echo "=========================================="
echo "SONUC  kuyruk=${SLURM_JOB_PARTITION:-?}  sunucu=${SLURM_NODELIST:-?}  cekirdek=${T}  algo=${ALGO}  belge=${BELGE}  sn/iter=${ORT}  rc=${RC}"
echo "=========================================="

if [ $RC -ne 0 ]; then
    echo "HATA: kosu ${RC} ile dondu. Son satirlar:"
    tail -n 25 "$LOG"
fi

rm -rf olcum_ciktisi "$GH"
