// Referenzfälle aus der echten App-Rechnung (Spengler-Digital-V1 js/29) erzeugen
const fs=require("fs"),vm=require("vm");
const src=fs.readFileSync(process.argv[2],"utf8");
function fn(name){const i=src.indexOf("function "+name+"(");let d=0,j=src.indexOf("{",i);for(let k=j;k<src.length;k++){if(src[k]=="{")d++;else if(src[k]=="}"){d--;if(!d)return src.slice(i,k+1)}}}
const code=["ebaStueckliste","ebaSchnittfuge","ebaStreifenJeAbschnitt","ebaRestBreite","ebaVerteile","ebaPackeInStreifen","ebaPackeMehrereAbschnitte"].map(fn).join("\n");
const ctx={blechSchnittfuge:0};vm.createContext(ctx);
vm.runInContext("const ebaZahl=v=>{const n=Number(v);return Number.isFinite(n)?n:0};\n"+code+"\nthis.api={ebaPackeInStreifen,ebaPackeMehrereAbschnitte,ebaStreifenJeAbschnitt,ebaRestBreite}",ctx);
const A=ctx.api, out=[];
const bl=(ls)=>ls.map((l,i)=>({nr:i+1,laenge:l}));
const faelle=[
 {fuge:0,L:2000,laengen:[1200,800,700,600,500,300,200]},
 {fuge:3,L:2000,laengen:[1200,800,700,600,500,300,200]},
 {fuge:0,L:3000,laengen:[2900,2500,1500,1500,1000,600,500,400,100]},
 {fuge:2,L:2070,laengen:[2070,1035,1034,1000,1000,70]},
 {fuge:0,L:1000,laengen:[400,400,300,300,300,300]},
 {fuge:0,L:500,laengen:[600,200]},
];
for(const f of faelle){ctx.blechSchnittfuge=f.fuge;const r=A.ebaPackeInStreifen(bl(f.laengen),f.L);
 out.push({art:"packe",...f,erg:{optimal:r.optimal,streifen:r.streifen&&r.streifen.map(s=>({nr:s.stuecke.map(x=>x.nr),rest:s.rest})),zuLang:(r.zuLang||[]).map(x=>x.nr)}});}
const mf=[{fuge:0,je:2,laengen:[4020,4020,4020,4020,2510,2510,2510,2510]},{fuge:3,je:3,laengen:[3000,2500,2500,2000,1500,1000,800,500]}];
for(const f of mf){ctx.blechSchnittfuge=f.fuge;const r=A.ebaPackeMehrereAbschnitte(bl(f.laengen),f.je);
 out.push({art:"mehrfach",...f,erg:{optimal:r.optimal,abschnitte:r.abschnitte.map(a=>({laenge:a.laenge,streifen:a.streifen.map(s=>({nr:s.stuecke.map(x=>x.nr),rest:s.rest}))}))}});}
for(const [B,Aw,fu] of [[1000,250,0],[1000,250,3],[1250,333,2],[200,250,0],[670,330,5]]){ctx.blechSchnittfuge=fu;const n=A.ebaStreifenJeAbschnitt(B,Aw);out.push({art:"quer",B,A:Aw,fuge:fu,n,rest:A.ebaRestBreite(B,Aw,n)});}
console.log(JSON.stringify({quelle:"Spengler-Digital-V1 js/29-einlaufblech-aufnahme.js (Stand v3.416)",faelle:out},null,1));
