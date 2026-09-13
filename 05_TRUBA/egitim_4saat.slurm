#!/bin/bash
#SBATCH -p barbun
#SBATCH -A egun
#SBATCH -J grobid_hdr_4s
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 40
#SBATCH --mem=120G
#SBATCH --time=04:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/4saat-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/4saat-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header CRF -- 4 SAATLIK BUTCEYE GORE TASARLANMIS EGITIM
#
# SORUN: Wapiti modeli SADECE egitim bittiginde diske yaziyor. SLURM sure
# limitine takilirsa is CANCELLED olur ve ELDE HICBIR SEY KALMAZ. Bu daha
# once iki kez yasandi:
#     6333606  hamsi  CANCELLED  00:32:00
#     6333834  smp    CANCELLED  00:09:49
# Ikisi de model uretmeden oldu.
#
# COZUM: iterasyon sayisini tahmin etmiyoruz, OLCUYORUZ.
#   1) Gercek korpusta 3 iterasyonluk kalibrasyon kosusu -> sn/iterasyon
#   2) Kalan sureden guvenlik payi dusulup maxIter hesaplaniyor
#   3) Asil egitim o maxIter ile kosuyor, sure limitine takilmadan bitiyor
#
# Kalibrasyonun bedeli ~10 dk (veri yukleme + 3 iterasyon). Karsiliginda
# "acaba yetisir mi" belirsizligi tamamen kalkiyor.
#
# Referans olcumler:
#   barbun, 40 thread, 2999 belge (1.86M token), l-bfgs : 64 sn/iterasyon
#   v4 korpusu 1.54M token -> l-bfgs ~53, rprop ~45 sn/iterasyon beklentisi
# Bunlar sadece beklenti; betik gercek degeri kendisi olcuyor.
# ---------------------------------------------------------------------------

set -uo pipefail

KOK=/arf/scratch/$USER/grobid
cd "$KOK"
mkdir -p log

# --- ayarlar ---------------------------------------------------------------
ALGO="${ALGO:-rprop}"        # rprop | l-bfgs  (l-bfgs icin: ALGO=l-bfgs sbatch ...)
BUTCE=14400                  # 4 saat, saniye
PAY=900                      # sondaki model yazma + guvenlik payi (15 dk)
KALIB_ITER=3                 # kalibrasyon iterasyonu
MAXITER_TAVAN=400            # bundan fazlasina zaten gerek yok
MAXITER_TABAN=40             # olcum saçmalarsa en az bu kadar kos
# ---------------------------------------------------------------------------

BASLANGIC=$(date +%s)

echo "=========================================="
echo "Is    : ${SLURM_JOB_ID:-yerel}   Kuyruk: ${SLURM_JOB_PARTITION:-?}"
echo "Sunucu: ${SLURM_NODELIST:-?}"
echo "Cekirdek: ${SLURM_CPUS_PER_TASK:-1}   Algoritma: ${ALGO}"
echo "Butce: ${BUTCE} sn (pay ${PAY} sn)"
echo "Baslangic: $(date)"
echo "=========================================="

module purge
module load lib/java/jdk-22.0.1
command -v java >/dev/null 2>&1 || { echo "HATA: java bulunamadi."; exit 1; }
echo "Java: $(java -version 2>&1 | head -1)"

T=${SLURM_CPUS_PER_TASK:-8}
sed -i -E "s/^([[:space:]]*)nbThreads:[[:space:]]*[0-9]+/\1nbThreads: ${T}/" \
    grobid-home/config/grobid.yaml
echo "nbThreads -> ${T}"

export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"

BELGE=$(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml 2>/dev/null | wc -l)
echo "TEI dosyasi: ${BELGE}"
if [ "$BELGE" -lt 100 ]; then
    echo "HATA: korpus bos veya eksik gorunuyor. Paket dogru acildi mi?"
    exit 1
fi

egit() {   # $1 = maxIter, $2 = log dosyasi
    java -Xmx16g \
         -Dgrobid.wapiti.algo="${ALGO}" \
         -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
         -jar grobid-trainer-onejar.jar \
         0 header \
         -gH "$KOK/grobid-home" \
         -epsilon 0.00002 \
         -w 5 \
         -maxIter "$1" > "$2" 2>&1
}

# --- 1) KALIBRASYON --------------------------------------------------------
echo
echo "--- 1/2  Kalibrasyon (${KALIB_ITER} iterasyon) ---"
K0=$(date +%s)
egit "$KALIB_ITER" log/kalibrasyon-${SLURM_JOB_ID:-0}.log
KRC=$?
K1=$(date +%s)
KALIB_SURE=$((K1 - K0))

if [ $KRC -ne 0 ]; then
    echo "HATA: kalibrasyon kosusu ${KRC} ile dondu. Son satirlar:"
    tail -n 30 log/kalibrasyon-${SLURM_JOB_ID:-0}.log
    exit 1
fi

grep -E "^[[:space:]]*\[" log/kalibrasyon-${SLURM_JOB_ID:-0}.log || true

# Wapiti satiri:  [   3] obj=... err=...  time=1.20s/3.64s
# Ilk alan iterasyonun kendi suresi; SON iterasyonunkini aliyoruz
# (ilk iterasyon isinma yuzunden yaniltici olabiliyor).
SN_ITER=$(sed -n 's/.*time=\([0-9.]*\)s\/.*/\1/p' \
          log/kalibrasyon-${SLURM_JOB_ID:-0}.log | tail -1)

# Veri yukleme suresi = toplam kalibrasyon - iterasyonlarin suresi
YUKLEME=$(awk -v k="$KALIB_SURE" -v s="${SN_ITER:-0}" -v n="$KALIB_ITER" \
          'BEGIN{v=k-(s*n); if(v<0)v=0; printf "%d", v}')

echo
echo "kalibrasyon toplam : ${KALIB_SURE} sn"
echo "sn/iterasyon       : ${SN_ITER:-OLCULEMEDI}"
echo "veri yukleme       : ${YUKLEME} sn  (asil kosuda tekrar edecek)"

# --- 2) MAXITER HESABI -----------------------------------------------------
SIMDI=$(date +%s)
GECEN=$((SIMDI - BASLANGIC))
KALAN=$((BUTCE - GECEN - PAY - YUKLEME))

if [ -z "$SN_ITER" ]; then
    echo "UYARI: sn/iterasyon okunamadi, guvenli varsayilan kullaniliyor."
    MAXITER=120
else
    MAXITER=$(awk -v k="$KALAN" -v s="$SN_ITER" 'BEGIN{printf "%d", k/s}')
fi
[ "$MAXITER" -gt "$MAXITER_TAVAN" ] && MAXITER=$MAXITER_TAVAN
[ "$MAXITER" -lt "$MAXITER_TABAN" ] && MAXITER=$MAXITER_TABAN

echo
echo "gecen sure         : ${GECEN} sn"
echo "asil kosuya kalan  : ${KALAN} sn"
echo ">>> maxIter        : ${MAXITER}"
if [ -n "${SN_ITER:-}" ]; then
    TAHMIN=$(awk -v m="$MAXITER" -v s="$SN_ITER" -v y="$YUKLEME" \
             'BEGIN{printf "%d", m*s+y}')
    echo "    tahmini sure   : ${TAHMIN} sn  (~$((TAHMIN / 60)) dk)"
fi

# --- 3) ASIL EGITIM --------------------------------------------------------
echo
echo "--- 2/2  Asil egitim (maxIter=${MAXITER}) ---"
E0=$(date +%s)
egit "$MAXITER" log/egitim-${SLURM_JOB_ID:-0}.log
ERC=$?
E1=$(date +%s)

grep -E "^[[:space:]]*\[" log/egitim-${SLURM_JOB_ID:-0}.log | tail -20
echo
echo "egitim suresi      : $((E1 - E0)) sn"
echo "toplam             : $(( E1 - BASLANGIC )) sn / ${BUTCE} sn butce"
echo "cikis kodu         : ${ERC}"

if [ $ERC -ne 0 ]; then
    echo "HATA: egitim ${ERC} ile dondu. Son satirlar:"
    tail -n 30 log/egitim-${SLURM_JOB_ID:-0}.log
fi

echo
echo "Bitis: $(date)"
ls -la grobid-home/models/header/
sacct -j "${SLURM_JOB_ID:-0}" --format=JobID,State,Elapsed,MaxRSS 2>/dev/null || true
