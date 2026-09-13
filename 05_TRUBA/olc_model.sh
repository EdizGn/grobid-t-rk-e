#!/usr/bin/env bash
# Bir header modelini kurar, iki korpustan da gecirir, ayni protokolle olcer.
#
#   ./olc_model.sh <model_dosyasi> <etiket>
#
# ornek:
#   ./olc_model.sh v4_80603_2153belge_orfoz.wapiti v4_600
#
# Ciktilar: 05_TRUBA/olcumler/TR_<etiket>.txt  ve  ING_<etiket>.txt
#
# Iki korpus da AYNI GROBID, ayni stok segmentasyon modeli ve
# consolidateHeader=0 ile isleniyor; tek degisken header modeli.
set -uo pipefail

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
O="$KOK/05_TRUBA/olcumler"

MODEL="${1:-}"
ETIKET="${2:-}"
if [ -z "$MODEL" ] || [ -z "$ETIKET" ]; then
  echo "kullanim: ./olc_model.sh <model_dosyasi> <etiket>"
  exit 1
fi
if [ ! -f "$MODEL" ]; then
  echo "HATA: $MODEL yok"
  exit 1
fi
mkdir -p "$O"

TR_PDF="$KOK/03_Test_ve_Degerlendirme/1500_random_test/makaleler"
TR_XML="$KOK/03_Test_ve_Degerlendirme/1500_random_test/grobid_xml_$ETIKET"
EN_PDF="$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/makaleler"
EN_XML="$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/grobid_xml_$ETIKET"
EN_DB="$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/ingilizce_metadatalar.db"

echo "=== 1/5  Model kuruluyor: $(basename "$MODEL") ==="
python "$KOK/01_Header_Modeli/model_kur.py" --kaynak "$MODEL" || exit 1

isle() {  # $1 = pdf dizini, $2 = cikti dizini
  PYTHONIOENCODING=utf-8 python -u - "$1" "$2" <<'PYEOF'
import glob, os, sys, requests, concurrent.futures
PDF, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
pdfs = sorted(glob.glob(os.path.join(PDF, "*.pdf")))
def isle(p):
    mid = os.path.basename(p).replace("makale_", "").replace(".pdf", "")
    o = os.path.join(OUT, "makale_%s.xml" % mid)
    if os.path.exists(o):
        return "atlandi"
    try:
        with open(p, "rb") as f:
            r = requests.post("http://127.0.0.1:8070/api/processHeaderDocument",
                              files={"input": (os.path.basename(p), f, "application/pdf")},
                              headers={"Accept": "application/xml"}, timeout=180)
        if r.status_code == 200:
            open(o, "w", encoding="utf-8").write(r.text)
            return "ok"
        return "http%s" % r.status_code
    except Exception:
        return "hata"
say = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for i, s in enumerate(ex.map(isle, pdfs), 1):
        say[s] = say.get(s, 0) + 1
        if i % 200 == 0:
            print("  %d/%d %s" % (i, len(pdfs), say), flush=True)
print("  bitti: %d %s" % (len(pdfs), say), flush=True)
PYEOF
}

echo "=== 2/5  Turkce isleniyor ==="
isle "$TR_PDF" "$TR_XML"

echo "=== 3/5  Ingilizce isleniyor ==="
isle "$EN_PDF" "$EN_XML"

cd "$KOK/03_Test_ve_Degerlendirme" || exit 1

echo "=== 4/5  Turkce olculuyor ==="
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$TR_XML" --dil iki --diakritik-yoksay > "$O/TR_$ETIKET.txt" 2>&1

echo "=== 5/5  Ingilizce olculuyor ==="
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$EN_XML" --db "$EN_DB" --dil tr > "$O/ING_$ETIKET.txt" 2>&1

echo
echo "=== Levenshtein >= 0.8 ozeti ==="
for f in "$O/TR_$ETIKET.txt" "$O/ING_$ETIKET.txt"; do
  echo "--- $(basename "$f")"
  awk '/Levenshtein/{p=1; next} p&&/^\| (title|authors|first_author|abstract|keywords)/{print} p&&/Ratcliff/{exit}' "$f"
done
echo
echo "Dosyalar: $O/TR_$ETIKET.txt  ve  $O/ING_$ETIKET.txt"
