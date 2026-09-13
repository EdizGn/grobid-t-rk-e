import pypdf # veya fitz (PyMuPDF) / pdfplumber

pdf_yolu = "c:/Users/EG/Desktop/Tubitak___is/03_Test_ve_Degerlendirme/makaleler_test/makale_88823.pdf"

try:
    reader = pypdf.PdfReader(pdf_yolu)
    print(f"Toplam Sayfa Sayısı: {len(reader.pages)}")
    
    ilk_sayfa_metni = reader.pages[0].extract_text()
    
    if not ilk_sayfa_metni or len(ilk_sayfa_metni.strip()) == 0:
        print("\n❌ TEŞHİS: 1. AŞAMA HATASI (OCR / Taranmış PDF)")
        print("PDF'in ilk sayfasında hiç dijital metin bulunamadı. Bu dosya taranmış bir resim olabilir.")
    else:
        print(f"\n✅ 1. Aşama Başarılı! Okunan İlk 200 Karakter:\n{ilk_sayfa_metni[:200]}")
        print("\n👉 Eğer metin okunuyorsa ama GROBID XML boşsa, sorun kesinlikle 2. AŞAMADADIR (Segmentation Modeli).")
except Exception as e:
    print(f"Hata: {e}")
