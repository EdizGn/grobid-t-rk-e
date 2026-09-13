import json
ids = ['14635', '1302465', '59465', '301108', '63585']
with open('dashboard/data.js', 'r', encoding='utf-8') as f:
    js_icerik = f.read().replace('const kiyaslamaVerileri = ', '').strip().rstrip(';')
    data = json.loads(js_icerik)
for d in data:
    if str(d['Makale ID']) in ids:
        open('titles.txt', 'a', encoding='utf-8').write(f"{d['Makale ID']}: {d['Orijinal Başlık']}")
