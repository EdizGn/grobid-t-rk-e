# -*- coding: utf-8 -*-
"""HTML arayuzu -- adim3_sunucu.py tarafindan kullanilir."""

SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<title>Altin Test Kumesi Dogrulama</title><style>
:root{--bg:#faf9f7;--kart:#fff;--cizgi:#e3e0da;--metin:#22201d;--soluk:#6b675f;
      --ok:#1a7f4b;--duzelt:#b8860b;--yok:#a03030;--vurgu:#2563a8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--metin);
     font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:9;background:var(--kart);
       border-bottom:1px solid var(--cizgi);padding:10px 16px;
       display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:15px;margin:0;font-weight:600}
.ilerleme{flex:1;min-width:180px;height:7px;background:#e8e5e0;border-radius:4px;overflow:hidden}
.ilerleme div{height:100%;background:var(--ok);width:0;transition:width .2s}
button{font:inherit;padding:5px 11px;border:1px solid var(--cizgi);
       background:var(--kart);border-radius:6px;cursor:pointer}
button:hover{background:#f0eee9}
button.ana{background:var(--vurgu);color:#fff;border-color:var(--vurgu);font-weight:600}
.sayac{font-variant-numeric:tabular-nums;color:var(--soluk);white-space:nowrap}
main{max-width:1500px;margin:0 auto;padding:16px}
.ust{display:flex;justify-content:space-between;align-items:baseline;
     margin-bottom:10px;gap:12px;flex-wrap:wrap}
.kimlik{font-size:12px;color:var(--soluk)}
.duzen{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}
@media(max-width:1000px){.duzen{grid-template-columns:1fr}}
.kutu{background:var(--kart);border:1px solid var(--cizgi);border-radius:9px;overflow:hidden}
.kutu>h2{margin:0;padding:9px 13px;font-size:12px;font-weight:600;
         letter-spacing:.04em;text-transform:uppercase;color:var(--soluk);
         border-bottom:1px solid var(--cizgi);background:#f7f5f2}
.kapak{padding:13px;white-space:pre-wrap;font-size:12.5px;line-height:1.5;
       max-height:78vh;overflow:auto;font-family:ui-monospace,Menlo,Consolas,monospace}
.alan{padding:12px 13px;border-bottom:1px solid var(--cizgi)}
.alan:last-child{border-bottom:none}
.alan-ad{font-size:11px;font-weight:600;text-transform:uppercase;
         letter-spacing:.04em;color:var(--soluk);margin-bottom:5px}
textarea{width:100%;border:1px solid var(--cizgi);border-radius:6px;padding:7px 9px;
         font:inherit;background:#fdfdfc;resize:vertical;min-height:38px}
textarea:focus{outline:2px solid var(--vurgu);outline-offset:-1px}
.secim{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}
.secim button{font-size:12px;padding:3px 9px}
.secim button[data-aktif="1"][data-d="dogru"]{background:var(--ok);color:#fff;border-color:var(--ok)}
.secim button[data-aktif="1"][data-d="duzeltildi"]{background:var(--duzelt);color:#fff;border-color:var(--duzelt)}
.secim button[data-aktif="1"][data-d="yok"]{background:var(--yok);color:#fff;border-color:var(--yok)}
mark{background:#fff3a3;padding:0 1px;border-radius:2px}
.bos{color:var(--yok);font-style:italic;font-weight:400;text-transform:none;letter-spacing:0}
kbd{font:11px ui-monospace,monospace;background:#eeebe5;border:1px solid var(--cizgi);
    border-bottom-width:2px;border-radius:4px;padding:1px 5px}
.yardim{font-size:12px;color:var(--soluk);margin-top:14px;line-height:1.9}
</style></head><body>
<header>
  <h1>Altin Test Kumesi</h1>
  <div class="ilerleme"><div id="cubuk"></div></div>
  <span class="sayac" id="sayac">-</span>
  <button id="geri">&larr; Onceki</button>
  <button id="ileri" class="ana">Ileri &rarr;</button>
</header>
<main>
  <div class="ust">
    <div class="kimlik" id="kimlik"></div>
    <div class="kimlik">Kaydetme otomatik &middot; <kbd>Ctrl</kbd>+<kbd>&rarr;</kbd> ileri &middot; <kbd>Ctrl</kbd>+<kbd>&larr;</kbd> geri</div>
  </div>
  <div class="duzen">
    <div class="kutu"><h2>TR Dizin kaydı &mdash; düzeltilecek alan</h2><div id="alanlar"></div></div>
    <div class="kutu"><h2>Makalenin kapak metni (PDF'ten)</h2><div class="kapak" id="kapak"></div></div>
  </div>
  <div class="yardim">
    <b>Dogru</b>: TR Dizin degeri makaleyle uyusuyor &middot;
    <b>Duzeltildi</b>: metni degistirdin, makaledeki hali yazildi &middot;
    <b>Makalede yok</b>: bu alan makalenin kapaginda hic gecmiyor
  </div>
</main>
<script>
let V=[], K={}, i=0;
const $=s=>document.querySelector(s);
const ALANLAR=__ALANLAR__;

function kacis(s){return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

function isaretle(kapak, degerler){
  let kelimeler=new Set();
  degerler.forEach(d=>(d||"").split(/[\s,;]+/).forEach(w=>{
    w=w.replace(/[^0-9A-Za-zÀ-ɏ]/g,"");
    if(w.length>3) kelimeler.add(w.toLocaleLowerCase('tr'));
  }));
  if(!kelimeler.size) return kacis(kapak);
  return kacis(kapak).split(/(\s+)/).map(p=>{
    const t=p.replace(/[^0-9A-Za-zÀ-ɏ]/g,"").toLocaleLowerCase('tr');
    return (t.length>3&&kelimeler.has(t))?"<mark>"+p+"</mark>":p;
  }).join("");
}

function ciz(){
  const v=V[i]; if(!v) return;
  $("#kimlik").textContent="ID "+v.id+"  ·  "+(v.dergi||"(dergi yok)")+"  ·  "+(v.yil||"");
  const kayit=K[v.id]||{};
  $("#alanlar").innerHTML=ALANLAR.map(function(par){
    const ad=par[0], etiket=par[1];
    const deger=(kayit[ad]!==undefined&&kayit[ad]!==null)?kayit[ad]:v[ad];
    const durum=kayit[ad+"_durum"]||"";
    const bos=!v[ad]?'<span class="bos">TR Dizin\'de bos</span>':'';
    const secenekler=["dogru","duzeltildi","yok"].map(function(d){
      const yazi={dogru:"✓ Dogru",duzeltildi:"✎ Duzeltildi",yok:"✕ Makalede yok"}[d];
      return '<button data-ad="'+ad+'" data-d="'+d+'" data-aktif="'+(durum===d?1:0)+'">'+yazi+'</button>';
    }).join("");
    return '<div class="alan"><div class="alan-ad">'+etiket+' '+bos+'</div>'+
      '<textarea data-ad="'+ad+'" rows="'+(ad==='ozet'?6:2)+'">'+kacis(deger)+'</textarea>'+
      '<div class="secim">'+secenekler+'</div></div>';
  }).join("");
  $("#kapak").innerHTML=isaretle(v.kapak, ALANLAR.map(p=>v[p[0]]))
      || '<i style="color:#a03030">Kapak metni cikarilamadi</i>';
  $("#alanlar").querySelectorAll("button").forEach(b=>b.onclick=function(){
    const ad=b.dataset.ad;
    $("#alanlar").querySelectorAll('button[data-ad="'+ad+'"]').forEach(x=>x.dataset.aktif="0");
    b.dataset.aktif="1"; topla();
  });
  $("#alanlar").querySelectorAll("textarea").forEach(t=>t.oninput=function(){
    const ad=t.dataset.ad;
    if(t.value!==(V[i][ad]||"")){
      $("#alanlar").querySelectorAll('button[data-ad="'+ad+'"]').forEach(x=>x.dataset.aktif="0");
      $('#alanlar button[data-ad="'+ad+'"][data-d="duzeltildi"]').dataset.aktif="1";
    }
    topla();
  });
  guncelleSayac();
}

function guncelleSayac(){
  $("#sayac").textContent=(i+1)+" / "+V.length+"  ·  "+Object.keys(K).length+" kayitli";
  $("#cubuk").style.width=(100*Object.keys(K).length/Math.max(V.length,1))+"%";
}

function topla(){
  const v=V[i], k={id:v.id};
  $("#alanlar").querySelectorAll("textarea").forEach(t=>k[t.dataset.ad]=t.value);
  let herhangi=false;
  ALANLAR.forEach(function(par){
    const ad=par[0];
    const b=$('#alanlar button[data-ad="'+ad+'"][data-aktif="1"]');
    k[ad+"_durum"]=b?b.dataset.d:"";
    if(b) herhangi=true;
  });
  if(herhangi){ K[v.id]=k; kaydet(k); }
  guncelleSayac();
}

let bekle=null;
function kaydet(k){
  clearTimeout(bekle);
  bekle=setTimeout(function(){
    fetch("/kaydet",{method:"POST",headers:{"Content-Type":"application/json"},
                     body:JSON.stringify(k)});
  },400);
}

function git(d){ i=Math.max(0,Math.min(V.length-1,i+d)); ciz(); window.scrollTo(0,0); }
$("#ileri").onclick=function(){git(1);};
$("#geri").onclick=function(){git(-1);};
document.addEventListener("keydown",function(e){
  if(e.ctrlKey&&e.key==="ArrowRight"){e.preventDefault();git(1);}
  if(e.ctrlKey&&e.key==="ArrowLeft"){e.preventDefault();git(-1);}
});

fetch("/veri").then(r=>r.json()).then(function(d){
  V=d.kayitlar; K=d.altin;
  const ilk=V.findIndex(v=>!K[v.id]);
  i=ilk<0?0:ilk;
  ciz();
});
</script></body></html>"""
