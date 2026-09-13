import json
with open('dashboard/data.js', 'r', encoding='utf-8') as f:
    data = f.read().replace('const kiyaslamaVerileri = ', '').strip().rstrip(';')
data = json.loads(data)
keys = ['Yazar Bulma Oranı (%)', 'Özet Bulma Oranı (%)', 'Başlık Bulma Oranı (%)', 'Kelime Bulma Oranı (%)']
for k in keys:
    vals = [d[k] for d in data if d.get(k) is not None]
    if vals: print(f'{k}: {round(sum(vals)/len(vals), 2)}')
