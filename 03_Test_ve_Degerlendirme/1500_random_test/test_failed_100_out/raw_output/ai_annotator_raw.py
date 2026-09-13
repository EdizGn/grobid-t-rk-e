import os
import json
import re

dashboard_path = r'C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\dashboard\data.js'
xml_dir = r'C:\Users\EG\Desktop\Tubitak___is\03_Test_ve_Degerlendirme\1500_random_test\test_failed_100_out\raw_output'

# Veritabanını yükle
with open(dashboard_path, 'r', encoding='utf-8') as f:
    js_icerik = f.read().replace('const kiyaslamaVerileri = ', '').strip().rstrip(';')
    data = json.loads(js_icerik)

data_dict = {str(d['Makale ID']): d for d in data}

def get_word_spans(text):
    spans = []
    for match in re.finditer(r'[a-zA-Z0-9ığüşöçİĞÜŞÖÇ]+', text):
        spans.append({'word': match.group().lower(), 'start': match.start(), 'end': match.end()})
    return spans

def find_subsequence(text_spans, search_words):
    if not search_words or not text_spans:
        return None
    search_len = len(search_words)
    best_match = None
    best_score = 0
    for i in range(len(text_spans) - search_len + 1):
        score = 0
        for j in range(search_len):
            if text_spans[i+j]['word'] == search_words[j]:
                score += 1
        if score / search_len >= 0.75 and score > best_score:
            best_score = score
            best_match = (text_spans[i]['start'], text_spans[i+search_len-1]['end'])
    return best_match

success_title = 0
success_author = 0
total_files = 0

for filename in os.listdir(xml_dir):
    if not filename.endswith('.xml'):
        continue
        
    mid = filename.split('_')[1].split('.')[0]
    filepath = os.path.join(xml_dir, filename)
    
    if mid not in data_dict:
        continue
        
    total_files += 1
    true_title = data_dict[mid]['Orijinal Başlık']
    true_authors = data_dict[mid]['Orijinal Yazarlar']
    
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
        
    spans = get_word_spans(text)
    inserts = []
    
    # 1. Başlık Etiketleme
    title_words = [w.lower() for w in re.findall(r'[a-zA-Z0-9ığüşöçİĞÜŞÖÇ]+', str(true_title))]
    title_match = find_subsequence(spans, title_words)
    if title_match:
        # Etiket zaten var mı kontrol et
        if "<titlePart>" not in text[max(0, title_match[0]-25):title_match[0]]:
            inserts.append((title_match[1], "</titlePart></docTitle>"))
            inserts.append((title_match[0], "<docTitle><titlePart>"))
            success_title += 1
            
    # 2. Yazar Etiketleme
    author_list = [a.strip() for a in str(true_authors).split(',')]
    for author in author_list:
        if not author: continue
        author_words = [w.lower() for w in re.findall(r'[a-zA-Z0-9ığüşöçİĞÜŞÖÇ]+', author)]
        a_match = find_subsequence(spans, author_words)
        if a_match:
            if "<docAuthor>" not in text[max(0, a_match[0]-25):a_match[0]]:
                inserts.append((a_match[1], "</docAuthor></byline>"))
                inserts.append((a_match[0], "<byline><docAuthor>"))
                success_author += 1
                
    # İndekslerin kaymaması için tersten ekle
    inserts.sort(key=lambda x: x[0], reverse=True)
    new_text = text
    for idx, tag in inserts:
        new_text = new_text[:idx] + tag + new_text[idx:]
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_text)

print(f"Bitti! Toplam {total_files} dosya tarandi.")
print(f"Otomatik Eklenen Baslik Etiketi: {success_title}")
print(f"Otomatik Eklenen Yazar Etiketi: {success_author}")

