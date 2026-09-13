import os
import json
import random
import shutil

dashboard_path = r'C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\dashboard\data.js'
pdf_dir = r'C:\Users\EG\Desktop\Tubitak___is\1500_random_test\makaleler'
out_dir = r'C:\Users\EG\Desktop\Tubitak___is\test_failed_100'

with open(dashboard_path, 'r', encoding='utf-8') as f:
    js_icerik = f.read().replace('const kiyaslamaVerileri = ', '').strip().rstrip(';')
    data = json.loads(js_icerik)

# Başlık bulamayanları ayıkla
failed_data = [d for d in data if d.get('Başlık Bulma Oranı (%)') == 0.0 or d.get('Başlık Bulma Oranı (%)') is None]

# 100 tanesini rastgele seç
sample_100 = random.sample(failed_data, min(100, len(failed_data)))

# Dosyaları kopyala ve referans sözlüğü oluştur
titles_map = {}
copied_count = 0

for d in sample_100:
    mid = str(d['Makale ID'])
    pdf_path = os.path.join(pdf_dir, f"makale_{mid}.pdf")
    
    if os.path.exists(pdf_path):
        shutil.copy(pdf_path, os.path.join(out_dir, f"makale_{mid}.pdf"))
        titles_map[mid] = d['Orijinal Başlık']
        copied_count += 1

with open(os.path.join(out_dir, 'titles_map.json'), 'w', encoding='utf-8') as f:
    json.dump(titles_map, f, ensure_ascii=False, indent=2)

print(f"Başarıyla {copied_count} adet sorunlu PDF kopyalandı ve haritalandırıldı.")
