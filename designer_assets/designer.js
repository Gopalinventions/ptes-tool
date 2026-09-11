'use strict';
const $=id=>document.getElementById(id),fmt=(n,d=1)=>n.toLocaleString('en-GB',{maximumFractionDigits:d,minimumFractionDigits:d});
let model=null,inputs=null,schedule=[];
const embedded=window.PTES_EMBEDDED;
const palette=document.createElement('div');palette.className='tools';
palette.innerHTML='<label>Water colour<input type="color" id="waterColor" value="#268cb8"></label><label>Cover colour<input type="color" id="coverColor" value="#368166"></label><label>Ground colour<input type="color" id="groundColor" value="#c1a184"></label>';
$('three').before(palette);
palette.querySelectorAll('input').forEach(e=>{e.style.cssText='width:60px;height:36px;padding:2px;flex-shrink:0';});
if(embedded){
 document.querySelector('aside').hidden=true;
 document.querySelector('main').style.gridTemplateColumns='1fr';
 document.querySelector('header p').textContent='Linked to Streamlit inputs · Change dimensions in the app sidebar · Preliminary geometry, not construction approval';
 for(const [key,value] of Object.entries(embedded.inputs)){if($(key))$(key).value=value;}
}
const drawingPanel=document.createElement('section');
drawingPanel.innerHTML=`<h2>Engineering drawing examples · Revision P02</h2><label>Drawing sheet<select id="sheetType"><option value="plan">GA-001 · General arrangement plan</option><option value="sections">SE-002 · True-proportion sections</option><option value="detail">DE-003 · Cover and liner principles</option></select></label><p class="muted">Dimension chains, section references and local levels. Zoom for drawing review. No surveyed ground levels are assumed.</p><label>Drawing zoom<select id="drawingZoom"><option value="100">Fit to panel</option><option value="150">150%</option><option value="200">200%</option></select></label><div style="overflow:auto"><svg id="cadSheet" viewBox="0 0 1190 842" style="background:white;max-width:none" role="img" aria-label="Engineering drawing sheet"></svg></div><button id="downloadSheet">Download drawing SVG</button><button id="downloadDXF">Download CAD geometry DXF</button><p class="muted">DXF model-space coordinates are in metres; set import units to metres. Geometry and labels are editable lines/text, not associative CAD dimensions. SVG sheets use a graphical scale, not a certified print scale.</p><p><a href="https://task55.iea-shc.org/Data/Sites/1/publications/IEA-SHC-T55-C-D.2-FACT-SHEET-Guidelines-seasonal-storages.pdf" target="_blank" rel="noopener">Reference: IEA SHC Task 55 — PTES materials and construction</a></p>`;
const oldDrawings=$('plan').closest('section');oldDrawings.before(drawingPanel);oldDrawings.hidden=true;
function drawCAD(){if(model)$('cadSheet').innerHTML=CAD.render(model,inputs,$('sheetType').value).replace(/<style>([\s\S]*?)<\/style>/,(_,css)=>'<style>'+css.replace(/([^{}]+)\{/g,(_,selectors)=>selectors.split(',').map(s=>'#cadSheet '+s.trim()).join(',')+'{')+'</style>');}
$('sheetType').onchange=drawCAD;
$('drawingZoom').onchange=()=>{$('cadSheet').style.width=$('drawingZoom').value+'%';};
$('downloadSheet').onclick=()=>{const s=$('cadSheet').cloneNode(true);s.setAttribute('xmlns','http://www.w3.org/2000/svg');s.style.width='1190px';save('ptes-'+$('sheetType').value+'-P02.svg','image/svg+xml',s.outerHTML);};
$('downloadDXF').onclick=()=>save('ptes-geometry-P02.dxf','application/dxf',CAD.dxf(model));
const numeric=['target','ratio','length','width','depth','slope','freeboard','linerThickness','linerDensity','allowance','coverThickness','coverDensity'];
const line=(x1,y1,x2,y2,color='#203c4c',dash='')=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="1.5" ${dash?'stroke-dasharray="'+dash+'"':''}/>`;
const text=(x,y,t)=>`<text x="${x}" y="${y}" text-anchor="middle">${t}</text>`;
function plan(g){const k=Math.min(470/g.L,280/g.B),cx=320,cy=220;
 function rect(l,b,color,dash=''){return `<rect x="${cx-l*k/2}" y="${cy-b*k/2}" width="${l*k}" height="${b*k}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="${dash}"/>`;}
 $('plan').innerHTML=rect(g.L,g.B,'#203c4c')+rect(g.l,g.b,'#956e49','5 4')+rect(g.wl,g.wb,'#248eb4')+
 line(cx-g.L*k/2,45,cx+g.L*k/2,45)+text(cx,33,`Rim length ${fmt(g.L)} m`)+text(cx,410,`Rim width ${fmt(g.B)} m`)+text(cx,205,`Bottom ${fmt(g.l)} × ${fmt(g.b)} m`)+text(cx,235,`Water ${fmt(g.wl)} × ${fmt(g.wb)} m`);
}
function sections(g){let svg='';for(const [i,title,top,bottom]of [[0,'Length section',g.L,g.l],[1,'Width section',g.B,g.b]]){
 const scale=470/top,y=65+i*205,dep=95,left=85,right=555,bl=320-bottom*scale/2,br=320+bottom*scale/2,wy=y+dep*g.f/g.H;
 svg+=text(320,y-30,`${title} · rim ${fmt(top)} m`)+`<path d="M${left},${y} L${bl},${y+dep} L${br},${y+dep} L${right},${y}" fill="#f3e8d8" stroke="#856441" stroke-width="2"/>`;
 const inset=g.s*g.f*scale;
 svg+=line(left+inset,wy,right-inset,wy,'#248eb4')+text(320,y+dep+23,`Bottom ${fmt(bottom)} m`)+text(320,y+45,`Water depth ${fmt(g.h)} m · freeboard ${fmt(g.f)} m`)+text(320,y+70,`Total ${fmt(g.H)} m · slope ${fmt(g.s)}H:1V`);
 }$('sections').innerHTML=svg;}
function three(g){const a=+$('angle').value*Math.PI/180,t=+$('tilt').value*Math.PI/180;
 const ring=(L,B,z)=>[[-L/2,-B/2,z],[L/2,-B/2,z],[L/2,B/2,z],[-L/2,B/2,z]];
 const bottom=ring(g.l,g.b,0),rim=ring(g.L,g.B,g.H),water=ring(g.wl,g.wb,g.h);
 const rotate=([x,y,z])=>{const u=x*Math.cos(a)-y*Math.sin(a),v=x*Math.sin(a)+y*Math.cos(a);return [u,v*Math.sin(t)-z*Math.cos(t),v*Math.cos(t)+z*Math.sin(t)];};
 const rr=[...bottom,...rim].map(rotate),xs=rr.map(p=>p[0]),ys=rr.map(p=>p[1]),mx=(Math.max(...xs)+Math.min(...xs))/2,my=(Math.max(...ys)+Math.min(...ys))/2;
 const scale=Math.min(740/(Math.max(...xs)-Math.min(...xs)),340/(Math.max(...ys)-Math.min(...ys)));
 const project=p=>{let q=rotate(p);return [450+(q[0]-mx)*scale,230+(q[1]-my)*scale,q[2]];};
 let faces=[{p:bottom,c:$('groundColor').value}];for(let i=0;i<4;i++)faces.push({p:[bottom[i],bottom[(i+1)%4],rim[(i+1)%4],rim[i]],c:$('groundColor').value});
 faces.forEach(f=>{f.q=f.p.map(project);f.z=f.q.reduce((n,p)=>n+p[2],0)/4;});faces.sort((a,b)=>a.z-b.z);
 let svg=faces.map(f=>`<polygon points="${f.q.map(p=>p.slice(0,2).join(',')).join(' ')}" fill="${f.c}" fill-opacity=".58" stroke="#785f49"/>`).join('');
 if($('water').checked||$('cover').checked)svg+=`<polygon points="${water.map(project).map(p=>p.slice(0,2).join(',')).join(' ')}" fill="${$('cover').checked?$('coverColor').value:$('waterColor').value}" fill-opacity=".65" stroke="#17596e"/>`;
 svg+=text(450,435,`Water ${fmt(g.waterVolume,0)} m³ · rim ${fmt(g.L)} × ${fmt(g.B)} m · depth ${fmt(g.H)} m`);
 $('three').innerHTML=svg;
}
function update(){const p={mode:$('mode').value};numeric.forEach(id=>p[id]=$(id).value.trim()===''?NaN:Number($(id).value));
 $('siteInputs').hidden=p.mode!=='site';$('volumeInputs').hidden=p.mode!=='volume';
 try{model=embedded?embedded.model:PTES.calculate(p);inputs=p;$('error').textContent='';const g=model;
 $('metrics').innerHTML=`<div>Water volume<strong>${fmt(g.waterVolume,0)} m³</strong></div><div>Rim dimensions<strong>${fmt(g.L)} × ${fmt(g.B)} m</strong></div><div>Water depth<strong>${fmt(g.h)} m</strong></div>`;
 plan(g);sections(g);three(g);drawCAD();
 schedule=[['Ideal full pit geometry volume','m³',g.pitVolume],['Water volume','m³',g.waterVolume],['Bottom area','m²',g.bottomArea],['Full-height side-wall area','m²',g.sideArea],['Liner geometric area','m²',g.linerArea],['Liner area including entered allowance','m²',g.linerOrderArea],['Liner mass using entered density','kg',g.linerMass],['Water-surface / cover area','m²',g.coverArea],['Cover insulation volume','m³',g.insulationVolume],['Cover insulation mass using entered density','kg',g.insulationMass]];
 $('quantities').innerHTML=schedule.map(r=>`<tr><td>${r[0]}</td><td>${fmt(r[2])} ${r[1]}</td></tr>`).join('');
 }catch(e){model=null;$('error').textContent=e.message;$('metrics').innerHTML='';['plan','sections','three','quantities','cadSheet'].forEach(id=>$(id).innerHTML='');}
 document.querySelectorAll('button').forEach(b=>b.disabled=!model);
}
function save(name,mime,data){const a=document.createElement('a'),u=URL.createObjectURL(new Blob([data],{type:mime}));a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
document.querySelectorAll('aside input,aside select').forEach(e=>e.addEventListener('input',update));
['water','cover','angle','tilt','waterColor','coverColor','groundColor'].forEach(id=>$(id).addEventListener('input',()=>{if(model)three(model);}));
for(const [button,id] of [['downloadPlan','plan'],['downloadSections','sections']])$(button).onclick=()=>{const s=$(id).cloneNode(true);s.setAttribute('xmlns','http://www.w3.org/2000/svg');save('ptes-'+id+'.svg','image/svg+xml',s.outerHTML);};
$('downloadJSON').onclick=()=>save('ptes-design.json','application/json',JSON.stringify({version:1,status:'Preliminary geometry, not construction approved',inputs,materialLabels:{liner:$('linerMaterial').value,cover:$('coverMaterial').value},results:model},null,2));
$('downloadCSV').onclick=()=>save('ptes-quantities.csv','text/csv','Quantity,Unit,Value\r\n'+schedule.map(r=>[r[0],r[1],r[2].toFixed(4)].join(',')).join('\r\n'));
let drag=null;$('three').onpointerdown=e=>{drag=[e.clientX,e.clientY,+$('angle').value,+$('tilt').value];$('three').setPointerCapture(e.pointerId);};$('three').onpointermove=e=>{if(!drag)return;$('angle').value=Math.max(-180,Math.min(180,drag[2]+(e.clientX-drag[0])*.5));$('tilt').value=Math.max(15,Math.min(80,drag[3]+(e.clientY-drag[1])*.25));if(model)three(model);};$('three').onpointerup=$('three').onpointercancel=()=>drag=null;
update();
