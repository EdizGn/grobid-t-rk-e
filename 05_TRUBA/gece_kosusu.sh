#!/usr/bin/env bash
# Gercek 0.9.1 stok modeliyle iki olcum: Ingilizce + Turkce
set -uo pipefail
# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
O="$KOK/05_TRUBA/olcumler"
mkdir -p "$O"

isle_klasor() {  # klasor, pdf_dizini, cikti_dizini
  PYTHONIOENCODING=utf-8 python - "$2" "$3" <<'PYEOF'
import glob, os, sys, requests, concurrent.futures
PDF, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
pdfs = sorted(glob.glob(os.path.join(PDF, "*.pdf")))
def isle(p):
    mid = os.path.basename(p).replace("makale_","").replace(".pdf","")
    o = os.path.join(OUT, "makale_%s.xml" % mid)
    if os.path.exists(o): return "atlandi"
    try:
        with open(p,"rb") as f:
            r = requests.post("http://127.0.0.1:8070/api/processHeaderDocument",
                              files={"input":(os.path.basename(p),f,"application/pdf")},
                              headers={"Accept":"application/xml"}, timeout=120)
        if r.status_code==200:
            open(o,"w",encoding="utf-8").write(r.text); return "ok"
        return "http"
    except Exception: return "hata"
say={}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for s in ex.map(isle, pdfs): say[s]=say.get(s,0)+1
print(PDF, "->", say, flush=True)
PYEOF
}

echo "=== 1/4  Ingilizce isleniyor (519) ==="
isle_klasor x "$KOK/08_Ingilizce_Kiyas/makaleler" "$KOK/08_Ingilizce_Kiyas/grobid_xml_stok091"

echo "=== 2/4  Turkce isleniyor (1500) ==="
isle_klasor x "$KOK/03_Test_ve_Degerlendirme/1500_random_test/makaleler" \
       "$KOK/03_Test_ve_Degerlendirme/1500_random_test/grobid_xml_stok091"

cd "$KOK/03_Test_ve_Degerlendirme"
echo "=== 3/4  Ingilizce olculuyor ==="
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$KOK/08_Ingilizce_Kiyas/grobid_xml_stok091" \
  --db  "$KOK/08_Ingilizce_Kiyas/ingilizce_metadatalar.db" \
  --dil tr > "$O/ING_stok091.txt" 2>&1
echo "  bitti"

echo "=== 4/4  Turkce olculuyor ==="
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$KOK/03_Test_ve_Degerlendirme/1500_random_test/grobid_xml_stok091" \
  --dil iki --diakritik-yoksay > "$O/TR_stok091.txt" 2>&1
echo "  bitti"
echo "=== TAMAMLANDI ==="
