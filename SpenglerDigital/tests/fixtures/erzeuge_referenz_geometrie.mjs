import { berechne, kontur } from "./geometrie.mjs";
const S=(L)=>({typ:"schenkel",L}), B=(winkel,ri=null,modus="sharp")=>({typ:"biegung",winkel,ri,modus});
const faelle=[
 {start:0,ops:[S(100),B(90),S(25)],t:0.7,ri:1,k:0.4},
 {start:0,ops:[S(100),B(90),S(25),B(180,null,"hem"),S(7)],t:0.7,ri:1,k:0.4},
 {start:30,ops:[S(150),B(-90,3),S(40),B(45),S(10)],t:1,ri:1.5,k:0.38},
 {start:0,ops:[S(60),B(-180,1.4,"hem"),S(40)],t:0.6,ri:0.8,k:0.4},
 {start:0,ops:[S(80),B(120,10,"tangent"),S(30)],t:0.8,ri:1.2,k:0.38},
];
const out=faelle.map(f=>{const r=berechne(f.start,f.ops,f.t,f.ri,f.k);const ko=kontur(r.pfad,f.t,4);
 return {...f,erg:{zuschnitt:r.zuschnitt,biegungen:r.biegungen.map(b=>({pos:b.pos,von:b.von,bis:b.bis})),endpunkt:r.pfad.at(-1).p2,konturPunkte:ko.length,beschriftungen:r.beschriftungen,konturErster:ko[0],konturLetzter:ko.at(-1)}}});
let fehler=null;try{berechne(0,[S(1),B(90,5),S(1)],1,1,0.4)}catch(e){fehler=e.message}
console.log(JSON.stringify({quelle:"Spengler-Digital-CAD kern/geometrie.js (Branch claude/tauri-windows-github-action-ltlved)",faelle:out,fehlerFall:{ops:[S(1),B(90,5),S(1)],t:1,ri:1,k:0.4,meldung:fehler}},null,1));
