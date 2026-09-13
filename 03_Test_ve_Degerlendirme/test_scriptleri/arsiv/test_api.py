import time
import requests
import sys

print("Waiting for Grobid API to start...")
for _ in range(100):
    try:
        r = requests.get('http://localhost:8070/api/isalive')
        if r.status_code == 200:
            print("\nGrobid is alive!")
            break
    except:
        pass
    sys.stdout.write(".")
    sys.stdout.flush()
    time.sleep(2)
else:
    print("\nGrobid did not start in time.")
    sys.exit(1)

pdf_file = r"C:\Users\EG\Desktop\Tubitak___is\grobid\dis_veriler\altin_veriseti\makale_12308.pdf"
print(f"Processing {pdf_file}...")

with open(pdf_file, 'rb') as f:
    files = {'input': (pdf_file, f, 'application/pdf')}
    r = requests.post('http://localhost:8070/api/processHeaderDocument', files=files)
    
if r.status_code == 200:
    print("\nSUCCESS! Grobid Output:\n")
    print(r.text)
else:
    print(f"Error {r.status_code}: {r.text}")
