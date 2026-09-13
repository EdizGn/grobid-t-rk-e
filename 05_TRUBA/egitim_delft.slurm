#!/bin/bash
#SBATCH -p akya-cuda
#SBATCH -A egun
#SBATCH -J grobid_delft
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 10
#SBATCH --gres=gpu:1
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/delft-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/delft-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header modeli -- DeLFT (BidLSTM_CRF_FEATURES), akya-cuda GPU
#
# Once delft_truba_kur.sh calistirilmis olmali.
#
# Neden Apptainer: TRUBA'da Docker yok. Imaj (37.4 GB) TensorFlow 2.17 +
# CUDA yigini + glove-840B LMDB (4.3 GB) iceriyor; bunlarin hicbiri SIF
# disina cikarilamaz, o yuzden konteyner icinde kosuyoruz.
#
# Neden --nv: Apptainer'in NVIDIA suruculerini konteynere gecirme bayragi.
# Bu olmadan TensorFlow GPU gormez ve CPU'ya duser (saatler yerine gunler).
#
# akya dugumleri: 40 cekirdek, 375 GB, Gres=gpu:4. Bir GPU istiyoruz.
#
# YAZILABILIRLIK: SIF salt-okunur. Egitim ciktisi grobid-home/models altina
# yazildigi icin grobid-home'un yazilabilir bir KOPYASI bind ediliyor.
# Korpus da ayni sekilde disaridan bind ediliyor -- imajda
# /opt/grobid/grobid-trainer YOK.
# ---------------------------------------------------------------------------

set -uo pipefail

W=/arf/scratch/$USER/delft
SIF=/arf/scratch/$USER/grobid_091_full.sif
mkdir -p /arf/scratch/$USER/grobid/log "$W/tmp"

echo "=========================================="
echo "Is    : $SLURM_JOB_ID   Kuyruk: $SLURM_JOB_PARTITION"
echo "Sunucu: $SLURM_NODELIST"
echo "Cekirdek: ${SLURM_CPUS_PER_TASK:-1}   GPU: ${CUDA_VISIBLE_DEVICES:-yok}"
echo "Baslangic: $(date)"
echo "=========================================="

for f in "$SIF" "$W/grobid-home/config/grobid.yaml"; do
    [ -e "$f" ] || { echo "HATA: $f yok. Once delft_truba_kur.sh calistir."; exit 1; }
done

echo "--- GPU (host) ---"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv 2>&1 || \
    echo "UYARI: nvidia-smi host'ta yok"

echo
echo "--- konteyner icinde GPU gorunuyor mu ---"
apptainer exec --nv "$SIF" python3 -c "
import tensorflow as tf
g = tf.config.list_physical_devices('GPU')
print('TF', tf.__version__, '| GPU:', g)
if not g:
    print('*** UYARI: TensorFlow GPU GORMUYOR -- egitim CPU''da kosar, cok yavas.')
" 2>&1 | grep -vE "^20[0-9]{2}-|oneDNN|cuFFT|cuDNN|cuBLAS|TF-TRT|successful NUMA"

echo
echo "--- header engine ayari ---"
grep -A6 'name: "header"' "$W/grobid-home/config/grobid.yaml" | grep -vE "^\s*#" | head -8

N=$(ls "$W/grobid-trainer/resources/dataset/header/corpus/tei/"*.xml 2>/dev/null | wc -l)
echo
echo "TEI dosyasi: $N"
[ "$N" -lt 100 ] && { echo "HATA: korpus eksik"; exit 1; }

# --- istege bagli: erken durma ayarlarini degistirme -----------------------
# GROBID DeLFT'i alt surec olarak cagiriyor (DeLFTModel.train) ve yalnizca
# --architecture / --max-sequence-length / --batch-size / --incremental
# geciyor. max_epoch ve patience GECMIYOR; degerler grobidTagger.py'nin
# kendi varsayilanlarindan geliyor: max_epoch=60, patience=5, early_stop=True.
# (-maxIter DeLFT'e hic ulasmiyor: DeLFTTrainer.setNbMaxIterations bos metot.)
#
# VARSAYILAN DAVRANIS: dokunma. Bu ayarlar GROBID'in kendi yayinlanmis
# modellerini urettigi ayarlar; karsilastirma yapacaksak korumak lehimize.
# 15 belgelik yerel testin 6 epoch'ta durmasi kucuk dogrulama kumesinin
# gurultusundendi, 2153 belgede beklenmiyor.
#
# Gerekirse:  PATIENCE=15 MAXEPOCH=120 sbatch egitim_delft.slurm
BIND_EK=""
if [ -n "${PATIENCE:-}" ] || [ -n "${MAXEPOCH:-}" ]; then
    echo
    echo "--- erken durma ayari degistiriliyor: patience=${PATIENCE:-varsayilan} max_epoch=${MAXEPOCH:-varsayilan} ---"
    YAMA="$W/grobidTagger_yama.py"
    apptainer exec "$SIF" cat /usr/local/lib/python3.11/dist-packages/delft/applications/grobidTagger.py > "$YAMA"
    if [ -n "${PATIENCE:-}" ]; then
        sed -i -E "s/^(\s*)patience = 5\s*$/\1patience = ${PATIENCE}/" "$YAMA"
    fi
    if [ -n "${MAXEPOCH:-}" ]; then
        sed -i -E "s/^(\s*)max_epoch = 60\s*$/\1max_epoch = ${MAXEPOCH}/" "$YAMA"
    fi
    echo "    yamalanan satirlar:"
    grep -nE "^\s*(patience|max_epoch) = [0-9]+" "$YAMA" | head
    BIND_EK="--bind $YAMA:/usr/local/lib/python3.11/dist-packages/delft/applications/grobidTagger.py"
fi

echo
echo "=== egitim basliyor ==="
BASLA=$(date +%s)

apptainer exec --nv \
    --bind "$W/grobid-home:/opt/grobid/grobid-home" \
    --bind "$W/grobid-trainer:/opt/grobid/grobid-trainer" \
    --bind "$W/tmp:/tmp" \
    $BIND_EK \
    "$SIF" \
    java -Xmx24g \
         -cp "/opt/grobid/grobid-service/lib/*" \
         org.grobid.trainer.TrainerRunner \
         0 header \
         -gH /opt/grobid/grobid-home
RC=$?

BITIS=$(date +%s)
echo
echo "cikis kodu : ${RC}"
echo "sure       : $((BITIS - BASLA)) sn  (~$(( (BITIS - BASLA) / 60 )) dk)"
echo "Bitis      : $(date)"
echo
echo "--- uretilen model ---"
ls -la "$W/grobid-home/models/" | grep -i header
du -sh "$W"/grobid-home/models/header* 2>/dev/null
