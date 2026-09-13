#!/usr/bin/env bash
#SBATCH -p debug
#SBATCH -A egun
#SBATCH -J sif_kur
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 16
#SBATCH --mem=100G
#SBATCH --time=03:00:00
#SBATCH --output=/arf/scratch/egun/grobid/log/sifkur-%j.out
#SBATCH --error=/arf/scratch/egun/grobid/log/sifkur-%j.err
#
# SBATCH ILE CALISTIRILIR:   sbatch delft_truba_kur.sh
#
# NEDEN arayuz sunucusunda DEGIL: iki denemede de "apptainer pull" tam
# "unpack layer" asamasinda SIGKILL yedi:
#     line 61: 4010189 Killed   apptainer pull ...
# Indirme her seferinde bitiyordu, olum acma asamasindaydi. Arayuz
# sunucusunda uzun sureli agir surecleri olduren bir sinir var (TRUBA
# dokumani zaten "arayuz sunucusunda is calistirmayin" diyor).
#
# Hesaplama dugumunun INTERNETI VAR -- test edildi:
#     srun -p debug curl ... registry-1.docker.io/v2/  ->  401
# (401 = sunucuya ulasildi, kimliksiz istege verilen normal cevap.)
# Dolayisiyla cekme+acma islemini bastan sona kuyruga veriyoruz.
#
# GROBID 0.9.1-full imajini Apptainer SIF'ine cevirir ve DeLFT egitimi icin
# yazilabilir calisma dizinini kurar.
#
# NEDEN boyle: TRUBA'da Docker yok (HPC merkezlerinde olmaz), Apptainer var
# (/usr/bin/apptainer, modul bile gerekmiyor). Docker Hub sadece bir DEPO --
# Apptainer katmanlari oradan kendisi indirip SIF uretir, Docker gerekmez.
#
# NEDEN yerelden yuklemiyoruz: imaj 37.4 GB, yerel diskte 16 GB bos var,
# "docker save" edip scp ile gondermek mumkun degil.
#
# NEDEN imajin kendi jar'i: /opt/grobid/grobid-service/lib/grobid-trainer-0.9.1.jar
# imajdaki delft python paketiyle AYNI surumden. Bizim 0.9.2-SNAPSHOT
# onejar'imizi bind etmek surum uyusmazligi riski tasir.
set -euo pipefail

# Lustre otomatik baglama gecikmesi: bir SLURM isinde
#   "couldn't chdir to /arf/scratch/...: No such file or directory"
# uyarisi gorulmustu. Dizine dokunup baglamayi tetikliyoruz.
ls /arf/scratch/$USER >/dev/null 2>&1 || sleep 5
cd /arf/scratch/$USER || { echo "HATA: /arf/scratch/$USER erisilemiyor"; exit 1; }
mkdir -p /arf/scratch/$USER/grobid/log

W=/arf/scratch/$USER/delft
SIF=/arf/scratch/$USER/grobid_091_full.sif
KAYNAK_KORPUS=/arf/scratch/$USER/grobid/grobid-trainer/resources/dataset/header

# Iki dizin de scratch'e alinmali:
#
# CACHEDIR : varsayilan ~/.apptainer/cache. TRUBA'da home kotasi kucuk.
# TMPDIR   : varsayilan /tmp. Apptainer imaji ONCE bir sandbox'a aciyor ve
#            bunu TMPDIR altinda yapiyor. /tmp cogu sistemde tmpfs, yani RAM.
#            37 GB'lik imaji RAM'e acmaya calisinca OOM killer sureci
#            olduruyor -- ilk denemede tam bunu yasadik:
#              "line 35: 3770883 Killed   apptainer pull ..."
export APPTAINER_CACHEDIR=/arf/scratch/$USER/apptainer_cache
export SINGULARITY_CACHEDIR=$APPTAINER_CACHEDIR
export APPTAINER_TMPDIR=/arf/scratch/$USER/apptainer_tmp
export SINGULARITY_TMPDIR=$APPTAINER_TMPDIR
export TMPDIR=$APPTAINER_TMPDIR
mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"

echo "--- ortam ---"
echo "  CACHEDIR: $APPTAINER_CACHEDIR"
echo "  TMPDIR  : $APPTAINER_TMPDIR"
df -h "$APPTAINER_TMPDIR" | tail -1
free -g 2>/dev/null | head -2

echo "=== 1/5  SIF cekiliyor (37 GB indirme + squashfs, uzun surer) ==="
if [ -f "$SIF" ]; then
    echo "    zaten var: $SIF ($(du -h "$SIF" | cut -f1)) -- atlaniyor"
else
    if ! apptainer pull "$SIF" docker://grobid/grobid:0.9.1-full; then
        echo
        echo "HATA: cekme basarisiz."
        echo "  'Killed' gordiysen bu OOM'dur. Kontrol:"
        echo "     df -h $APPTAINER_TMPDIR   (tmpfs OLMAMALI)"
        echo "     free -g"
        echo "  Arayuz sunucusunda bellek siniri varsa alternatif:"
        echo "     apptainer pull --disable-cache ...   (cift depolamayi onler)"
        echo "  ya da TRUBA destege 'container pull icin kaynak' talebi."
        rm -f "$SIF"
        exit 1
    fi
    echo "    SIF: $(du -h "$SIF" | cut -f1)"
fi
# Sandbox artiklarini birak durmasin -- scratch'te onlarca GB tutabilir.
rm -rf "${APPTAINER_TMPDIR:?}"/* 2>/dev/null || true

echo "=== 2/5  Yazilabilir grobid-home kopyalaniyor (604 MB) ==="
mkdir -p "$W"
if [ -d "$W/grobid-home" ]; then
    echo "    zaten var -- atlaniyor"
else
    apptainer exec "$SIF" cp -r /opt/grobid/grobid-home "$W/grobid-home"
fi

echo "=== 3/5  Korpus yerlestiriliyor ==="
mkdir -p "$W/grobid-trainer/resources/dataset/header" "$W/tmp"
for d in corpus crfpp-templates; do
    if [ -d "$KAYNAK_KORPUS/$d" ]; then
        rm -rf "${W:?}/grobid-trainer/resources/dataset/header/$d"
        cp -r "$KAYNAK_KORPUS/$d" "$W/grobid-trainer/resources/dataset/header/"
    else
        echo "    UYARI: $KAYNAK_KORPUS/$d yok"
    fi
done
N=$(ls "$W/grobid-trainer/resources/dataset/header/corpus/tei/"*.xml 2>/dev/null | wc -l)
echo "    TEI dosyasi: $N"
[ "$N" -lt 100 ] && { echo "HATA: korpus eksik"; exit 1; }

echo "=== 4/5  header modeli DeLFT'e cevriliyor ==="
apptainer exec --bind "$W/grobid-home:/gh" "$SIF" python3 - <<'PYEOF'
import re, io
p = "/gh/config/grobid.yaml"
s = io.open(p, encoding="utf-8").read()
m = re.search(r'(- name: "header".*?)(?=\n    - name: |\Z)', s, re.S)
if not m:
    print("HATA: header blogu bulunamadi"); raise SystemExit(1)
blok = m.group(1)
yeni = re.sub(r'^(\s*)engine:\s*"[^"]*"', r'\1engine: "delft"', blok, count=1, flags=re.M)
s = s[:m.start(1)] + yeni + s[m.end(1):]
io.open(p, "w", encoding="utf-8").write(s)
print("--- header blogu, etkin satirlar ---")
for l in yeni.split("\n")[:14]:
    if l.strip() and not l.strip().startswith("#"):
        print(l)
PYEOF

echo "=== 5/5  ozet ==="
echo "  SIF          : $SIF"
echo "  calisma dizini: $W"
echo "  korpus       : $N belge"
echo
echo "Sonraki adim:  sbatch egitim_delft.slurm"
