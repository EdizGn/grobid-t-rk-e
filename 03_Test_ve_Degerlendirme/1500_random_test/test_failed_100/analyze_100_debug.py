import os
import glob
import json
import re

out_dir = r"C:\Users\EG\Desktop\Tubitak___is\test_failed_100_out"
xml_files = glob.glob(os.path.join(out_dir, "*.training.header.tei.xml"))

with open(r"C:\Users\EG\Desktop\Tubitak___is\test_failed_100\titles_map.json", "r", encoding="utf-8") as f:
    titles = json.load(f)

header_error = 0
segmentation_error = 0
total = len(titles)

# Bazı başlıklar çok uzun veya noktalama içeriyorsa bulunması zor olabilir
# Karşılaştırma yaparken ilk 3-4 kelimeyi veya alfasayısal karakterleri baz almak daha güvenli
def normalize(text):
    return re.sub(r'[^a-zA-Z0-9]', '', str(text).lower())

for mid, true_title in titles.items():
    # Bu makalenin XML dosyasını bul
    xml_path = os.path.join(out_dir, f"makale_{mid}.training.header.tei.xml")
    if not os.path.exists(xml_path):
        segmentation_error += 1
        continue
        
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    norm_content = normalize(content)
    
    # Gerçek başlığın ilk 4 kelimesini arayalım (fazla uzunsa XML'de line break vs yüzünden bulunamayabilir)
    words = str(true_title).split()[:4]
    search_str = normalize(" ".join(words))
    
    if search_str and search_str in norm_content:
        header_error += 1
    else:
        # Eğer ilk 4 kelime yoksa bir de bütüne bakalım (kısa başlıksa diye)
        if normalize(true_title) in norm_content:
            header_error += 1
        else:
            segmentation_error += 1

print("=== 100 MAKALELİK BÜYÜK HATA ANALİZİ ===")
print(f"Toplam Test Edilen: {total}")
print(f"Header Modeli Hatası (Başlık XML içinde VAR ama model işaretlememiş): {header_error} makale (%{(header_error/total)*100:.1f})")
print(f"Segmentasyon Modeli Hatası (Başlık XML içinde YOK, model bloğu çöpe atmış): {segmentation_error} makale (%{(segmentation_error/total)*100:.1f})")
