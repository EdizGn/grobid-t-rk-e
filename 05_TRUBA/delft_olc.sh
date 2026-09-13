#!/usr/bin/env bash
# GROBID 0.9.1-full (DeLFT) ile header olcumu.
#
#   ./delft_olc.sh [etiket]        # varsayilan etiket: delft091
#
# NEDEN: elimizdeki DeLFT olcumu (olcumler/delft_*.txt) GROBID 0.8.0 ile
# uretilmisti; diger tum olcumler 0.9.1. Farkli surum = farkli stok
# segmentasyon modeli, farkli oznitelik uretimi. Yani o rakamlar CRF
# rakamlariyla yan yana konulamazdi. Bu betik ayni 0.9.1 hattinda
# DeLFT olcumu uretir, boylece stok CRF (olcumler/TR_stok091.txt) ile
# dogrudan karsilastirilabilir olur.
#
# CRF container'ina DOKUNMAZ: full imaj 8071'de ayri container olarak kosar.
set -uo pipefail

# Depo nereye klonlanirsa klonlansin dogru yeri gosterir.
KOK="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
O="$KOK/05_TRUBA/olcumler"
ETIKET="${1:-delft091}"
IMAJ="grobid/grobid:0.9.1-full"
AD="grobid_delft"
PORT=8071
URL="http://127.0.0.1:$PORT"

mkdir -p "$O"

if ! docker image inspect "$IMAJ" >/dev/null 2>&1; then
    echo "HATA: $IMAJ yerelde yok. Indirme bitti mi?"
    echo "      docker images | grep grobid"
    exit 1
fi

echo "=== 1/7  Onceki delft container'i temizleniyor ==="
docker rm -f "$AD" >/dev/null 2>&1
echo "=== 2/7  $IMAJ baslatiliyor (port $PORT) ==="
docker run -d --name "$AD" -p "$PORT:8070" "$IMAJ" >/dev/null || exit 1

echo "    ayaga kalkmasi bekleniyor (DeLFT/TensorFlow yuklemesi uzun surer)..."
for i in $(seq 1 120); do
    if [ "$(curl -s -m 5 "$URL/api/isalive" 2>/dev/null)" = "true" ]; then
        echo "    ayakta ($((i * 5)) sn)"
        break
    fi
    sleep 5
done
if [ "$(curl -s -m 5 "$URL/api/isalive" 2>/dev/null)" != "true" ]; then
    echo "HATA: GROBID ayaga kalkmadi."
    docker logs --tail 40 "$AD"
    exit 1
fi

echo
echo "=== 3/7  header modeli DeLFT'e cevriliyor ==="
# Imajdaki config'de header icin engine satiri "wapiti"; delft satiri yorumda.
# Yorum satirlarina DOKUNMADAN yalnizca etkin satiri degistiriyoruz.
docker exec "$AD" python3 - <<'PYEOF'
import re, io
p = "/opt/grobid/grobid-home/config/grobid.yaml"
s = io.open(p, encoding="utf-8").read()
m = re.search(r'(- name: "header".*?)(?=\n    - name: |\Z)', s, re.S)
if not m:
    print("HATA: header blogu bulunamadi"); raise SystemExit(1)
blok = m.group(1)
yeni = re.sub(r'^(\s*)engine:\s*"[^"]*"', r'\1engine: "delft"', blok, count=1, flags=re.M)
if yeni == blok:
    print("UYARI: engine satiri degismedi");
s = s[:m.start(1)] + yeni + s[m.end(1):]
io.open(p, "w", encoding="utf-8").write(s)
print("--- header blogu (etkin satirlar) ---")
for l in yeni.split("\n")[:6]:
    if l.strip() and not l.strip().startswith("#"):
        print(l)
PYEOF
[ $? -ne 0 ] && { echo "HATA: config degistirilemedi"; exit 1; }

echo
echo "=== 4/7  container yeniden baslatiliyor ==="
docker restart "$AD" >/dev/null
for i in $(seq 1 180); do
    [ "$(curl -s -m 5 "$URL/api/isalive" 2>/dev/null)" = "true" ] && { echo "    ayakta ($((i * 5)) sn)"; break; }
    sleep 5
done

echo
echo "=== 5/7  DeLFT gercekten devrede mi? ==="
# Tek bir PDF gonderip container loglarinda DeLFT/TensorFlow izini ariyoruz.
ORNEK=$(ls "$KOK/03_Test_ve_Degerlendirme/1500_random_test/makaleler"/*.pdf | head -1)
curl -s -m 300 -F "input=@$ORNEK" "$URL/api/processHeaderDocument" -o /dev/null
echo "--- container loglari (son 30 satir) ---"
docker logs --tail 30 "$AD" 2>&1 | grep -iE "delft|tensorflow|wapiti|engine|BidLSTM|loading" | tail -15
echo
echo "--- config dogrulamasi ---"
docker exec "$AD" sh -c 'grep -A4 "name: \"header\"" /opt/grobid/grobid-home/config/grobid.yaml | grep -v "^\s*#"'
echo
echo "Yukarida header icin engine: \"delft\" ve DeLFT/BidLSTM yuklendigine dair"
echo "satir GORMUYORSAN DURDUR -- olcum wapiti ile yapiliyor demektir."
echo "Devam etmek icin Enter, iptal icin Ctrl+C."
read -r _

isle() {  # $1 = pdf dizini, $2 = cikti dizini
  PYTHONIOENCODING=utf-8 python -u - "$1" "$2" "$URL" <<'PYEOF'
import glob, os, sys, requests, concurrent.futures
PDF, OUT, URL = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
pdfs = sorted(glob.glob(os.path.join(PDF, "*.pdf")))
def isle(p):
    mid = os.path.basename(p).replace("makale_", "").replace(".pdf", "")
    o = os.path.join(OUT, "makale_%s.xml" % mid)
    if os.path.exists(o):
        return "atlandi"
    try:
        with open(p, "rb") as f:
            r = requests.post(URL + "/api/processHeaderDocument",
                              files={"input": (os.path.basename(p), f, "application/pdf")},
                              headers={"Accept": "application/xml"}, timeout=600)
        if r.status_code == 200:
            open(o, "w", encoding="utf-8").write(r.text)
            return "ok"
        return "http%s" % r.status_code
    except Exception:
        return "hata"
say = {}
# DeLFT CPU'da yavas; es zamanlilik dusuk tutuluyor.
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    for i, s in enumerate(ex.map(isle, pdfs), 1):
        say[s] = say.get(s, 0) + 1
        if i % 100 == 0:
            print("  %d/%d %s" % (i, len(pdfs), say), flush=True)
print("  bitti: %d %s" % (len(pdfs), say), flush=True)
PYEOF
}

TR_XML="$KOK/03_Test_ve_Degerlendirme/1500_random_test/grobid_xml_$ETIKET"
EN_XML="$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/grobid_xml_$ETIKET"

echo
echo "=== 6/7  Turkce isleniyor (1435) -- DeLFT CPU'da yavas, saatler surebilir ==="
isle "$KOK/03_Test_ve_Degerlendirme/1500_random_test/makaleler" "$TR_XML"

echo "=== 6/7  Ingilizce isleniyor (519) ==="
isle "$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/makaleler" "$EN_XML"

cd "$KOK/03_Test_ve_Degerlendirme" || exit 1
echo
echo "=== 7/7  olculuyor ==="
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$TR_XML" --dil iki --diakritik-yoksay > "$O/TR_$ETIKET.txt" 2>&1
PYTHONIOENCODING=utf-8 python -u grobid_standart_eval.py \
  --xml "$EN_XML" --db "$KOK/03_Test_ve_Degerlendirme/ingilizce_kiyas/ingilizce_metadatalar.db" \
  --dil tr > "$O/ING_$ETIKET.txt" 2>&1

echo
echo "=== Levenshtein >= 0.8 ==="
for f in "$O/TR_$ETIKET.txt" "$O/ING_$ETIKET.txt"; do
  echo "--- $(basename "$f")"
  awk '/Levenshtein/{p=1; next} p&&/^\| (title|authors|first_author|abstract|keywords)/{print} p&&/Ratcliff/{exit}' "$f"
done
echo
echo "Karsilastirma icin ayni hattaki stok CRF: $O/TR_stok091.txt ve $O/ING_stok091.txt"
echo "Container hala ayakta ($AD, port $PORT). Kaldirmak icin: docker rm -f $AD"
