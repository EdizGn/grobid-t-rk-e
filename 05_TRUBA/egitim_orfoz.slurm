#!/bin/bash
#SBATCH -p orfoz
#SBATCH -A egun
#SBATCH -J grobid_hdr_v4
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 56
#SBATCH --mem=110G
# 150G idi: orfoz dugumunde cekirdek basina ~2.2 GB var, SLURM 150G'yi
# MinCPUsNode=71'e ceviriyordu -- yani "-c 56" yazdigimiz halde is 71
# cekirdeklik yer ariyordu ve zamanlanamiyordu. Olculen kullanim 40
# thread'le 38 GB'di; 110G fazlasiyla yeter ve 56 cekirdege sigar.
#SBATCH --time=05:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/orfoz-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/orfoz-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=edizgunn@gmail.com

# ---------------------------------------------------------------------------
# GROBID header CRF -- v4 korpusu, TAM egitim (600 iterasyon)
#
# NEDEN orfoz -c 56: olcum.slurm ile 2153 belgelik gercek korpusta olculdu
#
#   barbun13  40 cekirdek  l-bfgs   41.53 sn/iter
#   hamsi18   56 cekirdek  l-bfgs   42.71 sn/iter
#   orfoz208 112 cekirdek  l-bfgs   31.39 sn/iter
#   orfoz217  56 cekirdek  l-bfgs   14.20 sn/iter   <-- SECILEN
#   barbun14  40 cekirdek  rprop    38.73 sn/iter
#
# orfoz 56 cekirdekle barbun'dan 2.9 KAT hizli. Ayni soket sayisi (2), ama
# soket basina 56 cekirdek ve cok daha yeni mimari/bellek bandi.
# 112 cekirdek 56'dan YAVAS: is diziler uzerinde paralellesiyor, 2153 diziyi
# 112'ye bolunce paralel kisim kuculuyor, seri L-BFGS guncellemesi sabit
# kaliyor. smp (orkinos, 16 soket) 312 sn/iter ile zaten elenmisti.
#
# 600 x 14.20 = 8520 sn = 2 saat 22 dk (+ veri yukleme ~10 dk).
#
# ITERASYON KISILMADI. Onceki tamamlanmis kosunun logu 600'de modelin hala
# yakinsamadigini gosterdi (590->600 bagil azalma 3.3e-4, Wapiti esigi 2e-5;
# sekans hatasi 200. iterasyonda %10.00, 600'de %7.50). Hiz kazanci tamamen
# donanimdan geliyor, egitimden kisilmiyor.
#
# HIPERPARAMETRELER ONCEKI KOSUYLA BIREBIR AYNI: -epsilon / -w gecilmiyor,
# grobid.yaml'daki 1e-6 / 30 kullaniliyor, maxIter 600. Boylece 6333466 ile
# tek fark KORPUS oluyor (v3 2627 belge -> v4 2153 belge) ve olculen skor
# farki dogrudan etiketleme degisikligine yazilabiliyor.
# ---------------------------------------------------------------------------

set -uo pipefail

KOK=/arf/scratch/$USER/grobid
cd "$KOK"
mkdir -p log

echo "=========================================="
echo "Is    : $SLURM_JOB_ID   Kuyruk: $SLURM_JOB_PARTITION"
echo "Sunucu: $SLURM_NODELIST"
echo "Cekirdek: ${SLURM_CPUS_PER_TASK:-1}"
echo "Baslangic: $(date)"
echo "=========================================="
lscpu 2>/dev/null | grep -E "^Model name|^Socket|^Core\(s\) per socket|^NUMA node\(s\)" || true
echo

# --- Java ------------------------------------------------------------------
# 6340411 burada olmustu: orfoz hesaplama dugumunde "module" batch kabugunda
# TANIMLI DEGIL. "module load" sessizce basarisiz oldu, sistem varsayilani
# Java 11 kullanildi ve GROBID (Java 21 bytecode, class version 65) aninda
# UnsupportedClassVersionError verdi. Modul sistemini elle basliyoruz ve
# surumu ACIKCA dogruluyoruz -- sessiz geri dusme bir daha olmasin.
if ! command -v module >/dev/null 2>&1; then
    for f in /etc/profile.d/modules.sh \
             /usr/share/Modules/init/bash \
             /usr/share/lmod/lmod/init/bash \
             /etc/profile.d/lmod.sh; do
        if [ -f "$f" ]; then
            echo "modul sistemi yukleniyor: $f"
            # shellcheck disable=SC1090
            . "$f"
            break
        fi
    done
fi

if command -v module >/dev/null 2>&1; then
    module purge 2>/dev/null
    module load lib/java/jdk-22.0.1 2>/dev/null || \
        echo "UYARI: jdk-22.0.1 modulu yuklenemedi."
else
    echo "UYARI: modul sistemi bulunamadi, PATH'teki java kullanilacak."
fi

command -v java >/dev/null 2>&1 || { echo "HATA: java bulunamadi."; exit 1; }
JAVA_SATIR=$(java -version 2>&1 | head -1)
echo "Java: $JAVA_SATIR"
JV=$(echo "$JAVA_SATIR" | sed -n 's/.*version "\([0-9][0-9]*\).*/\1/p')
if [ -z "$JV" ] || [ "$JV" -lt 21 ]; then
    echo "HATA: Java ${JV:-?} bulundu; GROBID en az 21 gerektiriyor."
    echo "      Mevcut java modulleri: "
    module avail 2>&1 | grep -i java || true
    exit 1
fi

# ISE OZEL grobid-home: nbThreads yalnizca grobid.yaml'dan okunuyor. Paylasilan
# dosyaya "sed -i" yapmak, ayni anda baska bir is kostugunda ayarlarin
# birbirini ezmesine yol aciyor -- 6340293 isi "-c 112" ile gonderildigi halde
# logunda "nb threads: 40" yazmisti. Agir klasorler sembolik bag, config gercek
# kopya; models bagi uzerinden yazma paylasilan dizine gectigi icin model yine
# dogru yere kaydediliyor.
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
echo "nbThreads -> ${T}   (ise ozel config: $GH)"
grep -n "nbThreads:" "$GH/config/grobid.yaml"

export LD_LIBRARY_PATH="$KOK/grobid-home/lib/lin-64:${LD_LIBRARY_PATH:-}"
export TMPDIR="${TMPDIR:-/tmp}"

BELGE=$(ls grobid-trainer/resources/dataset/header/corpus/tei/*.xml 2>/dev/null | wc -l)
echo "TEI dosyasi: ${BELGE}"
if [ "$BELGE" -ne 2153 ]; then
    echo "UYARI: 2153 bekleniyordu, ${BELGE} bulundu. v4 paketi dogru acildi mi?"
fi
echo

BASLA=$(date +%s)

java -Xmx16g \
     -Djava.library.path="$KOK/grobid-home/lib/lin-64" \
     -jar grobid-trainer-onejar.jar \
     0 header \
     -gH "$GH" \
     -maxIter 600
RC=$?
rm -rf "$GH"

BITIS=$(date +%s)
echo
echo "cikis kodu : ${RC}"
echo "sure       : $((BITIS - BASLA)) sn  (~$(( (BITIS - BASLA) / 60 )) dk)"
echo "Bitis      : $(date)"
ls -la grobid-home/models/header/
sacct -j "$SLURM_JOB_ID" --format=JobID,State,Elapsed,MaxRSS 2>/dev/null || true
