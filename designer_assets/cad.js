'use strict';
// Original schematic drawings informed by IEA SHC Task 55, not copied details.
const CAD=(()=>{
const n=x=>Number(x).toFixed(2),tx=(x,y,t,size=14)=>`<text x="${x}" y="${y}" font-size="${size}">${t}</text>`;
const ln=(a,b,c,d,cls='')=>`<line x1="${a}" y1="${b}" x2="${c}" y2="${d}" class="${cls}"/>`;
function dh(x1,x2,y,from,label){return ln(x1,from,x1,y+8,'thin')+ln(x2,from,x2,y+8,'thin')+`<path d="M${x1},${y} H${x2}" class="dim"/>`+tx((x1+x2)/2-35,y-7,label);}
function dv(y1,y2,x,from,label){return ln(from,y1,x+8,y1,'thin')+ln(from,y2,x+8,y2,'thin')+`<path d="M${x},${y1} V${y2}" class="dim"/>`+`<text transform="translate(${x-8},${(y1+y2)/2}) rotate(-90)" text-anchor="middle">${label}</text>`;}
function base(title,id){return `<defs><marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="#18252d"/></marker><pattern id="earth" width="9" height="9" patternUnits="userSpaceOnUse"><path d="M0 9 L9 0" stroke="#aaa" stroke-width=".6"/></pattern><pattern id="ins" width="16" height="12" patternUnits="userSpaceOnUse"><path d="M0 6 L4 0 L12 12 L16 6" fill="none" stroke="#456854" stroke-width="1"/></pattern></defs><style>text{font-family:Arial,sans-serif;fill:#17242d;font-size:14px}line,path,rect,polygon{stroke:#17242d;stroke-width:1.5;fill:none}.thin{stroke-width:.6}.axis{stroke:#657986;stroke-width:.8;stroke-dasharray:12 4 2 4}.water{stroke:#197fa4;stroke-width:1.7}.bottom{stroke-dasharray:6 4;stroke:#7c654f}.dim{stroke-width:.7;marker-start:url(#arr);marker-end:url(#arr)}</style><rect x="18" y="18" width="1154" height="806"/><text x="42" y="52" style="font-size:23px;font-weight:bold">${title}</text>${tx(42,78,'PRELIMINARY DESIGN EXAMPLE — NOT FOR CONSTRUCTION')}${ln(18,715,1172,715)}${ln(770,715,770,824)}${ln(970,715,970,824)}${tx(38,740,'PTES / Mühlhausen · Parametric geometry')}${tx(38,766,'Datum: rim = ±0.00 m, local reference only. No surveyed levels.')}${tx(38,792,'Units: metres unless stated · Do not scale dimensions from screen.')}${tx(785,740,'Drawing: '+id)}${tx(785,766,'Revision: P02')}${tx(785,792,'11 September 2026')}${tx(985,740,'DESIGN STUDY')}${tx(985,766,'Scale: graphic / NTS')}${tx(985,792,'Approval: pending')}`;}
function scale(x,y,k,g){const length=Math.max(1,Math.round(g.L/5/5)*5);return ln(x,y,x+length*k,y)+ln(x,y-5,x,y+5)+ln(x+length*k,y-5,x+length*k,y+5)+tx(x,y+22,'0')+tx(x+length*k-25,y+22,length+' m');}
function render(g,p,kind){let s='';
if(kind==='plan'){
 s=base('GENERAL ARRANGEMENT / PLAN','PTES-GA-001');const perm=Number(p.permanentPerimeter||0),work=Number(p.temporaryWorking||0),outer=perm+work,planL=g.L+2*outer,planB=g.B+2*outer,k=Math.min(570/planL,440/planB),cx=410,cy=370;
 const rect=(L,B,cl)=>`<rect x="${cx-L*k/2}" y="${cy-B*k/2}" width="${L*k}" height="${B*k}" class="${cl}"/>`;
 s+=rect(planL,planB,'thin')+rect(g.L+2*perm,g.B+2*perm,'thin')+rect(g.L,g.B,'')+rect(g.l,g.b,'bottom')+rect(g.wl,g.wb,'water');
 s+=ln(cx-g.L*k/2-35,cy,cx+g.L*k/2+35,cy,'axis')+tx(cx-g.L*k/2-48,cy-10,'A')+tx(cx+g.L*k/2+38,cy-10,'A');
 s+=ln(cx,cy-g.B*k/2-25,cx,cy+g.B*k/2+25,'axis')+tx(cx+24,cy-g.B*k/2-12,'B')+tx(cx+24,cy+g.B*k/2+22,'B');
 s+=dh(cx-g.L*k/2,cx+g.L*k/2,115,cy-g.B*k/2,n(g.L)+' overall');
 s+=dh(cx-g.l*k/2,cx+g.l*k/2,635,cy+g.b*k/2,n(g.l)+' bottom');
 s+=dv(cy-g.B*k/2,cy+g.B*k/2,70,cx-g.L*k/2,n(g.B)+' overall');
 s+=tx(800,160,'GEOMETRY REGISTER',17)+tx(800,198,'Water volume: '+n(g.waterVolume)+' m³')+tx(800,228,'Water depth: '+n(g.h)+' m')+tx(800,258,'Freeboard: '+n(g.f)+' m')+tx(800,288,'Bottom: '+n(g.l)+' × '+n(g.b)+' m')+tx(800,318,'Water: '+n(g.wl)+' × '+n(g.wb)+' m')+tx(800,365,'PLAN ENVELOPES',17)+ln(800,395,850,395,'thin')+tx(862,400,'Temporary construction')+ln(800,425,850,425,'thin')+tx(862,430,'Permanent perimeter')+ln(800,455,850,455)+tx(862,460,'Excavation rim');
 s+=tx(800,515,'Permanent perimeter: '+n(perm)+' m')+tx(800,540,'Temporary working: '+n(work)+' m')+tx(800,565,'Envelopes are planning geometry,')+tx(800,590,'not final embankment design.');s+=scale(110,675,k,g);
}else if(kind==='sections'){
 s=base('SECTIONS A–A / B–B','PTES-SE-002');
 for(const [i,name,L,b]of [[0,'A–A longitudinal',g.L,g.l],[1,'B–B transverse',g.B,g.b]]){
 const k=Math.min(700/L,115/g.H),cx=445,y=175+i*260,bot=y+g.H*k,x1=cx-L*k/2,x2=cx+L*k/2,bl=cx-b*k/2,br=cx+b*k/2,water=y+g.f*k;
 s+=tx(75,y-55,name+' · H:V drawing scale = 1:1',18);
 s+=`<path d="M${x1-20},${y} L${x1},${y} L${bl},${bot} L${br},${bot} L${x2},${y} L${x2+20},${y} L${x2+20},${bot+18} H${x1-20} Z" style="fill:url(#earth);stroke:none"/>`;
 s+=`<path d="M${x1},${y} L${bl},${bot} H${br} L${x2},${y}" style="stroke-width:2.5"/>`+ln(x1, y, x2,y,'axis')+ln(x1+g.s*g.f*k,water,x2-g.s*g.f*k,water,'water');
 s+=dh(x1,x2,y-25,y,n(L))+dh(bl,br,bot+32,bot,n(b))+dv(y,bot,45,x1,n(g.H)+' depth');
 s+=tx(880,y-6,'▽ RIM ±0.00 m')+tx(880,y+27,'▽ WATER −'+n(g.f)+' m')+tx(880,y+60,'▽ BOTTOM −'+n(g.H)+' m')+tx(880,y+94,'Freeboard '+n(g.f)+' m')+tx(880,y+120,'Slope '+n(g.s)+'H : 1V');
 }
 s+=tx(75,680,'Heavy line: liner boundary, thickness not to scale. Ground profile and embankment geometry require survey/geotechnical design.');
}else{
 s=base('COVER / LINER ASSEMBLY PRINCIPLES','PTES-DE-003');s+=tx(70,130,'D1 — FLOATING COVER: CONCEPT ONLY / NTS',18);
 s+=`<rect x="90" y="200" width="490" height="90" style="fill:url(#ins)"/>`+ln(90,194,580,194)+ln(90,296,580,296)+ln(90,325,580,325,'water');
 s+=ln(580,194,670,175)+tx(690,180,'Weather membrane / drainage design: TBD')+ln(580,245,670,245)+tx(690,250,'Insulation '+n(p.coverThickness)+' mm — user input')+ln(580,296,670,305)+tx(690,310,'Floating barrier / vapour control: TBD')+tx(140,352,'WATER')+dv(200,290,65,90,n(p.coverThickness)+' mm (diagram NTS)');
 s+=tx(70,410,'D2 — PIT LINER: CONCEPT ONLY / NTS',18)+`<rect x="90" y="500" width="490" height="75" style="fill:url(#earth)"/>`+ln(90,485,580,485)+ln(90,494,580,494);
 s+=ln(580,485,670,465)+tx(690,470,'Liner '+n(p.linerThickness)+' mm — user input')+ln(580,494,670,505)+tx(690,510,'Protection / geotextile: specification TBD')+ln(580,555,670,555)+tx(690,560,'Prepared subgrade: geotechnical design');
 s+=tx(70,625,'Reference: IEA SHC Task 55.C-D2, pp. 3 and 7–11 (lining, floating cover and connections).')+tx(70,650,'Original schematic, not a manufacturer assembly. Anchorage, seams, penetrations and drainage require specialist details.')+tx(70,680,'Do not assume any selected material is temperature-compatible or structurally adequate.');
}return s;}
function dxf(g){let pairs=['0','SECTION','2','HEADER','9','$ACADVER','1','AC1009','0','ENDSEC','0','SECTION','2','ENTITIES'];
const seg=(a,b,layer)=>pairs.push('0','LINE','8',layer,'10',String(a[0]),'20',String(a[1]),'30','0','11',String(b[0]),'21',String(b[1]),'31','0');
const poly=(ps,layer,close=false)=>{for(let i=1;i<ps.length;i++)seg(ps[i-1],ps[i],layer);if(close)seg(ps.at(-1),ps[0],layer);};
const label=(x,y,t,h=2)=>pairs.push('0','TEXT','8','ANNOTATION','10',String(x),'20',String(y),'30','0','40',String(h),'1',t);
for(const [l,b,layer]of [[g.L,g.B,'RIM'],[g.wl,g.wb,'WATER'],[g.l,g.b,'BOTTOM']])poly([[-l/2,-b/2],[l/2,-b/2],[l/2,b/2],[-l/2,b/2]],layer,true);
label(-g.L/2,g.B/2+8,`PLAN - metres - rim ${n(g.L)} x ${n(g.B)}`);
let y=-g.B/2-40;
for(const [L,b,name]of [[g.L,g.l,'SECTION_A'],[g.B,g.b,'SECTION_B']]){poly([[-L/2,y],[-b/2,y-g.H],[b/2,y-g.H],[L/2,y]],name);seg([-L/2+g.s*g.f,y-g.f],[L/2-g.s*g.f,y-g.f],'WATER');label(-L/2,y+6,`${name}: top ${n(L)}, bottom ${n(b)}, depth ${n(g.H)}`);y-=g.H+35;}
label(-g.L/2,y,'PRELIMINARY - NOT FOR CONSTRUCTION - LOCAL DATUM');pairs.push('0','ENDSEC','0','EOF');return pairs.join('\r\n')+'\r\n';}
return {render,dxf};})();
