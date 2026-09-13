# -*- coding: utf-8 -*-
"""
Egitim bittikten sonra header modelini devreye alir.

Egitim sonrasi iki tuzak var, ikisi de bu projede yasandi:
  1) Wapiti egitimi sonucu 'model.wapiti.new' olarak yazilir; 'model.wapiti'
     bazen eski haliyle kalir. Kontrol edilmezse eski model test edilir.
  2) Windows'ta uretilen model CRLF satir sonlu olur; Docker icindeki Wapiti
     (C kutuphanesi) sadece LF bekler ve "invalid format" verip coker.

Bu script ikisini de halleder, modeli container'a kopyalar ve dogrular.

Kullanim:
    python model_kur.py                 # header modeli
    python model_kur.py --model segmentation
"""
import os
import re
import time
import shutil
import argparse
import subprocess


def calistir(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def container_bul():
    r = calistir(["docker", "ps", "--format", "{{.ID}} {{.Image}}"])
    for satir in r.stdout.strip().split("\n"):
        if "grobid" in satir.lower():
            return satir.split()[0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="header")
    ap.add_argument("--grobid-home",
                    default=r"C:\Users\EG\Desktop\Tubitak___is\grobid\grobid-home")
    ap.add_argument("--no-docker", action="store_true")
    ap.add_argument("--kaynak", default=None,
                    help="Kurulacak model dosyasi. TRUBA'dan indirilen modeli "
                         "dogrudan vermek icin kullanilir; verilmezse yerel "
                         "egitimin urettigi model.wapiti.new aranir.")
    a = ap.parse_args()

    d = os.path.join(a.grobid_home, "models", a.model)
    aktif = os.path.join(d, "model.wapiti")
    yeni = aktif + ".new"

    if a.kaynak:
        kaynak = a.kaynak
        if not os.path.exists(kaynak):
            print("HATA: %s bulunamadi" % kaynak)
            return
    elif not os.path.exists(yeni):
        print("UYARI: %s yok. Egitim '.new' uretmemis olabilir;" % yeni)
        print("       bu durumda model.wapiti zaten guncellenmis olabilir.")
        kaynak = aktif
    else:
        kaynak = yeni

    ham = open(kaynak, "rb").read()
    crlf = ham.count(b"\r\n")
    print("kaynak : %s" % kaynak)
    print("boyut  : %d byte, CRLF: %d" % (len(ham), crlf))
    m = re.match(rb'#mdl#\d+#(\d+)', ham[:40])
    print("oznitelik sayisi: %s" % (m.group(1).decode() if m else "?"))

    if os.path.exists(aktif) and kaynak != aktif:
        yedek = aktif + ".ONCEKI"
        if not os.path.exists(yedek):
            shutil.copy2(aktif, yedek)
            print("onceki model yedeklendi -> %s" % os.path.basename(yedek))

    duzeltilmis = ham.replace(b"\r\n", b"\n")
    if duzeltilmis != ham:
        print("CRLF -> LF donusumu yapildi (%d -> %d byte)" % (len(ham), len(duzeltilmis)))
    with open(aktif, "wb") as f:
        f.write(duzeltilmis)
    print("kuruldu: %s" % aktif)

    if a.no_docker:
        return

    cid = container_bul()
    if not cid:
        print("\nCalisan grobid container'i bulunamadi; Docker adimi atlandi.")
        return
    print("\ncontainer: %s" % cid)
    hedef = "/opt/grobid/grobid-home/models/%s/model.wapiti" % a.model
    r = calistir(["docker", "cp", aktif, "%s:%s" % (cid, hedef)])
    if r.returncode != 0:
        print("docker cp HATASI: %s" % r.stderr.strip())
        return
    print("container'a kopyalandi: %s" % hedef)

    # engine wapiti mi?
    r = calistir(["docker", "exec", cid, "sh", "-c",
                  "grep -A3 'name: \"%s\"' /opt/grobid/grobid-home/config/grobid.yaml" % a.model])
    # Yorum satirlarini atla: imajda "#engine: \"delft\"" satiri bulunuyor
    # ve duz substring kontrolu yanlis alarm veriyordu.
    etkin = [l for l in r.stdout.splitlines() if not l.strip().startswith("#")]
    if any('engine: "delft"' in l for l in etkin):
        print("\n*** DIKKAT: config'de %s icin engine hala \"delft\"." % a.model)
        print("    Wapiti modeli OKUNMAZ. grobid.yaml'da wapiti yapilmali.")

    print("\ncontainer yeniden baslatiliyor...")
    calistir(["docker", "restart", cid])
    for i in range(60):
        r = calistir(["curl", "-s", "-m", "5", "http://127.0.0.1:8070/api/isalive"])
        if r.stdout.strip() == "true":
            print("GROBID ayakta (%d sn)" % (i * 3))
            break
        time.sleep(3)
    else:
        print("GROBID ayaga kalkmadi. 'docker logs %s' ile bak." % cid)
        return
    print("\nSonraki adim:")
    print("  cd 03_Test_ve_Degerlendirme\\1500_random_test && python test_yeni.py")
    print("  python birlesik_cikti.py")
    print("  cd .. && python grobid_standart_eval.py --dil iki")


if __name__ == "__main__":
    main()
