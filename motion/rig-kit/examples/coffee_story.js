/* EXAMPLE STORY — "커피 한 잔이 내 손에 오기까지" (7 scenes, 47 s)
   A scene = closure returning {N, dur, tag, title, cam?, draw(t)}.
   N=nar([...lines]) gives each narration line a time slot; the acting keys are written against N[i].t0 / N[i].t1. */
/* ============ 01 — 아침의 한 잔 ============ */
const A1=(()=>{const N=nar(['매일 아침 손에 쥐는 커피 한 잔.','이 한 잔은 어디에서 왔을까요?']),V=SPEED('walk'),x1=7.5,tw=N[0].t1-0.35,t2=N[1].t0;
 const man={ch:who('직장인'),seed:0.13,kicks:[tw+0.03,t2+0.3],tracks:[
  [{t:0,d:0,x:x1-V*tw,z:0.4},{t:0,d:tw,e:E.lin,x:x1}],
  [{t:0,d:0,yaw:90},{t:tw,d:0.45,yaw:22}],
  [{t:0,d:0,walk:1,swR:0,propR:'cup',steam:1,propL:'case'},{t:tw,d:0.25,walk:0}],
  [{t:0,d:0,armR:{a:0.45,b:1.45}},{t:tw+0.2,d:0.4,e:E.back,armR:{a:0.5,b:1.5,ab:0.5}}],
  [{t:0,d:0,mood:'smile'},{t:tw+0.25,d:0.3,headTurn:-20,nod:0.5,look:[-0.8,0.8]},{t:t2+0.25,d:0.2,brow:1,mood:'o'},{t:t2+1.5,d:0.3,mood:'smile',brow:0.4,nod:0,headTurn:0,look:[0,0]}]]};
 const kid={ch:who('학생'),seed:0.31,gy:-0.24,sc:0.86,tracks:[[{t:0,d:0,x:8.4,yaw:90,walk:1},{t:0,d:8,e:E.lin,x:8.4+V*8}]]};
 const shop=(x,w,wall,awn,sign,door)=>{F(wall,x,-5.05,w,5.05);F(dk(wall,0.9),x,-0.3,w,0.3);F(dk(wall,0.88),x,-5.05,w,0.2);
  shape(rr(x+0.32,-3.4,w-1.72,2.75,0.06),'#FFFFFF');const g=rr(x+0.4,-3.32,w-1.88,2.59,0.04);shape(g,'#BFE3F5');c.save();g();c.clip();shape(poly(x+0.8,-3.4,x+1.3,-3.4,x+0.75,-0.7,x+0.25,-0.7),'rgba(255,255,255,0.35)');F('rgba(70,30,10,0.1)',x,-3.35,w,0.22);c.restore();
  shape(rr(x+w-1.15,-3.05,0.85,3.05,[0.06,0.06,0,0]),door);shape(rr(x+w-1.03,-2.9,0.61,1.35,0.04),'#BFE3F5');shape(circ(x+w-0.44,-1.25,0.045),'#F2D27A');
  const a=poly(x+0.12,-4.2,x+w-0.12,-4.2,x+w+0.06,-3.66,x-0.06,-3.66);shape(a,awn);c.save();a();c.clip();c.fillStyle='rgba(255,255,255,0.82)';for(let xx=x+0.3;xx<x+w;xx+=0.64)c.fillRect(xx,-4.3,0.32,0.7);c.restore();F('rgba(70,30,10,0.14)',x-0.06,-3.66,w+0.12,0.07);
  shape(rr(x+w/2-0.95,-4.93,1.9,0.5,0.08),'#FFFFFF');label(sign,x+w/2,-4.67,0.26,INK)};
 function back(t){F(lin(0,-6.3,0,-2,'#A9D6F2','#D8EEF7','#F6EEDC'),0,-6.3,VW,6.3);glow(9.15,-5.65,3.0,'#FFE7B0',0.9);shape(circ(9.15,-5.65,0.55),'#FFF1C4');cloud(5.0+0.1*t,-5.75,0.75);cloud(11.3+0.07*t,-5.9,0.55);
  for(const[x,w,h,cc]of[[0,1.5,5.7,'#C3DCE8'],[1.7,1.1,6.3,'#B6D2E0'],[3.1,1.7,5.6,'#C3DCE8'],[5.6,1.2,6.3,'#B6D2E0'],[7.0,1.5,5.75,'#C3DCE8'],[9.9,1.0,6.0,'#B6D2E0'],[10.9,1.2,5.6,'#C3DCE8'],[12.0,0.9,6.2,'#B6D2E0']]){F(cc,x,-h,w,h);c.fillStyle='rgba(255,255,255,0.45)';for(let yy=-h+0.25;yy<-5.15;yy+=0.36)for(let xx=x+0.18;xx<x+w-0.25;xx+=0.36)c.fillRect(xx,yy,0.16,0.2)}
  shop(0.25,3.95,'#F4D6B8','#E5484D','BAKERY','#B5553A');shop(4.4,4.2,'#F7E8D2','#2E7D5B','COFFEE','#2E7D5B');shop(8.8,4.0,'#DCE6EE','#3D6BE0','BOOKS','#3A5BA8');
  /* lamp + planters */
  F('#4A4F5A',4.265,-4.75,0.07,4.75);F('#4A4F5A',4.02,-4.78,0.56,0.07);shape(poly(4.0,-4.72,4.6,-4.72,4.5,-4.45,4.1,-4.45),'#3A3F4A');shape(circ(4.3,-4.43,0.07),'#FFF3C4');
  for(const x of[4.85,8.35]){for(const[a,l]of[[-0.5,0.55],[0,0.7],[0.5,0.55]]){c.save();c.translate(x,-0.42);c.rotate(a);shape(ell(0,-l*0.5,0.13,l*0.5),a?'#2E7D5B':'#3E9B6A');c.restore()}shape(poly(x-0.24,-0.45,x+0.24,-0.45,x+0.18,0,x-0.18,0),'#C7694A')}
  F('#DAD3C7',0,0,VW,1.3);F('#C9C1B4',0,0,VW,0.06);c.fillStyle='rgba(70,30,10,0.07)';for(let x=0.4;x<VW;x+=1.6)c.fillRect(x,0.06,0.03,1.3)}
 function fx(t){const k=popK(t,t2+0.3,0.3);if(k>0){for(let i=0;i<2;i++){const kk=popK(t,t2+0.12+i*0.09,0.2);shape(circ(8.2+i*0.2,-3.95-i*0.19,(0.06+i*0.035)*kk),'#FFFFFF')}
   bubble(9.0,-4.7,1.25,1.15,k,0);c.rotate(0.12*Math.sin(t*3));label('?',0,0.03,0.82,'#C8553A');c.restore()}}
 return{N,dur:N.dur,tag:'01',title:'아침의 한 잔',cam:[7.7,-2.7,1,1.045],look:{light:{dir:[0.55,-0.85]},palette:{light:'#FFF0CF',sky:'#D8EEF7'},air:'motes'},draw(t){back(t);drawActor3(kid,t);drawActor3(man,t);fx(t)}}})();

/* ---------- farm backdrop (used by 02 and 03) ---------- */
function farmBack(t,soil,soil2){F(lin(0,-6.3,0,-2,'#9ED3EE','#CBEAF2','#EAF5EC'),0,-6.3,VW,6.3);glow(11.6,-5.6,3.4,'#FFF0C8',0.55);cloud(5.6+0.08*t,-5.45,0.8);cloud(9.0+0.05*t,-5.0,0.6);
 shape(()=>{c.beginPath();c.moveTo(0,-2.4);c.bezierCurveTo(1.5,-4.0,3.2,-4.1,4.6,-3.0);c.bezierCurveTo(6.0,-4.0,7.8,-4.4,9.6,-3.1);c.bezierCurveTo(10.8,-3.8,12,-3.7,12.8,-3.2);c.lineTo(12.8,0);c.lineTo(0,0);c.closePath()},'#A5D6B4');
 shape(()=>{c.beginPath();c.moveTo(0,-2.0);c.bezierCurveTo(3,-3.0,6,-2.3,8,-2.6);c.bezierCurveTo(10,-2.9,12,-2.4,12.8,-2.5);c.lineTo(12.8,0);c.lineTo(0,0);c.closePath()},'#84C48E');
 for(let r=0;r<3;r++){const y=-1.95+r*0.42,sz=0.15+r*0.045;F(['#7FBF89','#78B982','#70B27B'][r],0,y+sz*0.4,VW,0.7);for(let i=0;i<70;i++){const x=i*(0.27+r*0.07)+(r%2)*0.13+hash(i+r*17)*0.06;if(x>VW+0.3)break;shape(circ(x,y,sz),hash(i*3+r)>0.5?'#5FA873':'#68B07B');if(hash(i*7+r)>0.62)shape(circ(x+sz*0.3,y+sz*0.1,sz*0.2),'#D9584C')}}
 F('#93CF92',0,-0.98,VW,0.98);F('#A2D9A0',0,-0.98,VW,0.07);c.fillStyle='#7FC281';for(let i=0;i<22;i++){const x=hash(i*5.3)*VW,y=-0.8+hash(i*2.1)*0.6;c.beginPath();c.moveTo(x-0.08,y);c.lineTo(x-0.03,y-0.13);c.lineTo(x,y);c.lineTo(x+0.04,y-0.16);c.lineTo(x+0.08,y);c.closePath();c.fill()}
 F(soil||'#C68E57',0,0,VW,1.3);F(soil2||'#B47B48',0,0,VW,0.08)}
/* coffee tree: leaves in pairs along the branches, cherries in clusters (red = ripe, green = not yet) */
function coffeeTree(x,gone,t){const BR=[[-1,-2.3,1.3],[-1,-2.7,1.2],[-1,-3.3,0.7],[1,-1.6,1.2],[1,-2.2,1.3],[1,-2.8,1.2],[1,-3.3,0.9],[-1,-3.7,0.5],[1,-3.75,0.5]];
 line(()=>{c.beginPath();c.moveTo(x+0.03,0);c.quadraticCurveTo(x-0.08,-2,x,-3.9)},0.15,'#7A5236');
 for(const[s,y,l]of BR){const sw=0.015*Math.sin(t*1.6+y*3),ex=x+s*l,ey=y-0.22+sw;line(()=>{c.beginPath();c.moveTo(x,y);c.quadraticCurveTo(x+s*l*0.5,y-0.2,ex,ey)},0.055,'#7A5236');
  for(let i=1;i<=4;i++){const u=i/4,px=lerp(x,ex,u),py=lerp(y,ey,u)-0.1*Math.sin(Math.PI*u);for(const d of[-1,1]){c.save();c.translate(px,py+d*0.13);c.rotate(s*(d*0.45-0.15));shape(ell(0,0,0.27,0.115),(i+d)%2?'#2F7D4F':'#3E9B62');line(()=>{c.beginPath();c.moveTo(-0.2,0);c.lineTo(0.2,0)},0.014,'rgba(255,255,255,0.22)');c.restore()}}}
 shape(ell(x,-4.05,0.3,0.14,-0.5),'#3E9B62');shape(ell(x+0.12,-4.12,0.3,0.13,0.6),'#2F7D4F');
 /* cherries that stay on the tree */
 for(const[bx,by,cc]of[[x-0.6,-2.36,0],[x-0.5,-2.76,1],[x-0.28,-3.36,0],[x+0.55,-1.62,0],[x+0.95,-1.72,1],[x+0.5,-2.24,2],[x+1.0,-2.36,0],[x+0.62,-2.86,0],[x+0.9,-2.96,1],[x+0.45,-3.4,0],[x-0.95,-2.42,1]])for(let j=0;j<3;j++)cherryShape(bx+(j-1)*0.12,by+(j%2)*0.1+0.04,0.07,['#D63A2F','#8DBB4E','#E9B44C'][cc]);
 gone.forEach((g,i)=>{if(!g[2])for(let j=0;j<2;j++)cherryShape(g[0]+(j?-0.11:0.0),g[1]+(j?0.09:0),0.075)})}

/* ============ 02 — 농장 · 수확 ============ */
const A2=(()=>{const N=nar(['시작은 적도 근처의 커피 농장입니다.','빨갛게 익은 열매만 골라 손으로 하나하나 땁니다.']),V=SPEED('walk'),xs=7.3,tw=1.55,tp=N[1].t0+0.1,cyc=(N[1].t1-tp)/3,TX=9.3;
 const CH=[[8.02,-2.75],[8.02,-2.36],[8.22,-2.33]],DROP=[7.92,-2.06,0.8],HZ=0.8;   /* hand targets sit at the near shoulder's depth (actor z + ~0.45); screen y = Y + 0.16*Z */
 const arm=[{t:0,d:0,armR:null,armL:{local:[0.12,0.62,0.5]}}],face=[{t:0,d:0,mood:'smile'},{t:tw,d:0.3,nod:-0.45,look:[0.7,-0.7]}],fill=[{t:0,d:0,fill:0.25}],hits=[];
 for(let i=0;i<3;i++){const s=tp+i*cyc;arm.push({t:s,d:0.3,e:E.back,armR:{hand:[CH[i][0],CH[i][1]-0.16*HZ+0.04,HZ]},handR:'open'},{t:s+0.3,d:0,propR:'cherry',handR:'grip'},{t:s+0.42,d:0.32,armR:{hand:DROP}},{t:s+0.76,d:0,propR:null,handR:null});
  face.push({t:s,d:0.25,nod:-0.5,look:[0.6,-0.7]},{t:s+0.42,d:0.3,nod:0.55,look:[0.5,0.8]});fill.push({t:s+0.76,d:0.14,e:E.back,fill:0.25+(i+1)*0.25});hits.push(s+0.76)}
 const te=tp+3*cyc+0.02;arm.push({t:te,d:0.3,armR:null});face.push({t:te,d:0.3,nod:0,look:[0,0],mood:'grin',brow:0.6});
 const farmer={ch:who('농부'),seed:0.52,kicks:[tw+0.03].concat(hits),tracks:[
  [{t:0,d:0,x:xs-V*tw,z:0.35},{t:0,d:tw,e:E.lin,x:xs}],[{t:0,d:0,yaw:90},{t:tw,d:0.35,yaw:72},{t:te,d:0.45,yaw:30}],
  [{t:0,d:0,walk:1,swL:0,propL:'basket'},{t:tw,d:0.25,walk:0,lean:0.1},{t:te,d:0.3,lean:0.03}],arm,face,fill]};
 const picked=t=>CH.map((p,i)=>[p[0],p[1],t>=tp+i*cyc+0.3]);
 function globe(t){const k=popK(t,N[0].t0+0.75,0.35);if(k<=0)return;c.save();c.translate(4.25,-4.85);c.scale(k,k);const R=0.82,g=circ(0,0,R);shape(circ(0.03,0.05,R),'rgba(70,30,10,0.12)');shape(g,'#8FD0EE');c.save();g();c.clip();
  for(const[x,y,rx,ry,r]of[[-0.42,-0.3,0.34,0.28,0.3],[-0.3,0.32,0.2,0.34,-0.2],[0.3,-0.15,0.3,0.42,0.2],[0.62,0.35,0.2,0.16,0],[0.12,-0.62,0.3,0.14,0]])shape(ell(x,y,rx,ry,r),'#8CCB8A');
  F('rgba(242,138,46,0.5)',-1,-0.24,2,0.48);c.strokeStyle='#FFFFFF';c.lineWidth=0.025;c.setLineDash([0.08,0.07]);c.beginPath();c.moveTo(-1,0);c.lineTo(1,0);c.stroke();c.setLineDash([]);c.restore();
  const b=0.06*Math.abs(Math.sin(t*4));shape(poly(-0.2,-0.02-b,-0.11,-0.3-b,-0.29,-0.3-b),'#D63A2F');shape(circ(-0.2,-0.34-b,0.12),'#D63A2F');shape(circ(-0.2,-0.34-b,0.045),'#FFFFFF');
  shape(rr(1.0,-0.27,1.95,0.54,0.27),'#FFFFFF');shape(circ(1.27,0,0.11),'#F28A2E');label('커피 벨트',2.08,0.01,0.25,INK);c.restore()}
 function fx(t){hits.forEach((h,i)=>{const u=(t-h)/0.7;if(u>0&&u<1){c.globalAlpha=1-u*u;const y=-1.7-u*0.5;shape(circ(8.78,y,0.27),'#FFFFFF');label('+1',8.78,y+0.01,0.27,'#D63A2F');c.globalAlpha=1}})}
 return{N,dur:N.dur,tag:'02',title:'농장 · 수확',cam:[8.0,-2.4,1,1.05],look:{light:{dir:[0.6,-0.8]},palette:{light:'#FFF2D0',sky:'#CBEAF2'},air:{preset:'motes',n:22}},draw(t){farmBack(t);coffeeTree(TX,picked(t),t);globe(t);drawActor3(farmer,t);fx(t)}}})();

/* ============ 03 — 건조 ============ */
const A3=(()=>{const N=nar(['열매에서 씨앗을 꺼내 햇볕에 말리면','연둣빛 생두가 됩니다.']),xs=3.25,te=N[1].t0+0.45;
 const arm=[{t:0,d:0,armR:{hand:[3.85,-2.04,0.8]},propR:'rake',propRot:0.33,armL:{a:-0.25,b:0.5}}];for(let i=0,t=0.25;t<te-0.55;i++,t+=0.6)arm.push({t,d:0.55,armR:{hand:[i%2?3.8:4.22,-2.04,0.8]}});arm.push({t:te,d:0.4,armR:{a:0.45,b:0.95},propRot:1.2});   /* stands the rake up like a staff when he turns */
 const farmer={ch:who('농부'),seed:0.2,kicks:[te+0.35],tracks:[[{t:0,d:0,x:xs,z:0.35,yaw:80,lean:0.13,mood:'smile',look:[0.6,0.5]},{t:te,d:0.45,yaw:42,lean:0.03,look:[0,0]},{t:te+0.3,d:0.3,mood:'grin',brow:0.7,nod:-0.35,headTurn:14}],arm,
  [{t:0,d:0,x:xs}].concat(arm.slice(1,-1).map((k,i)=>({t:k.t,d:0.55,x:xs+(i%2?-0.06:0.1)})))]};
 function sun(t,k){glow(11.75,-5.2,3.2+0.8*k,'#FFE4A0',0.6+0.4*k);c.save();c.translate(11.75,-5.2);const p=1+0.05*Math.sin(t*3);c.rotate(t*0.25);c.fillStyle='rgba(255,214,102,'+(0.35+0.4*k)+')';for(let i=0;i<12;i++){c.rotate(TAU/12);c.beginPath();c.moveTo(-0.09,-0.82*p);c.lineTo(0.09,-0.82*p);c.lineTo(0,-(1.12+0.25*k)*p);c.closePath();c.fill()}c.restore();shape(circ(11.75,-5.2,0.95+0.1*k),'rgba(255,236,170,0.4)');shape(circ(11.75,-5.2,0.64),'#FFD666')}
 function bed(t,k){for(const x of[4.6,7.25,9.9,12.4]){F('#8A6238',x,-1.3,0.12,1.3);F('#74502C',x+0.12,-1.3,0.045,1.3)}F('#74502C',4.5,-0.62,8.4,0.07);
  shape(poly(4.55,-1.7,12.8,-1.7,12.8,-1.28,4.28,-1.28),'#A47A48');shape(poly(4.68,-1.65,12.8,-1.65,12.8,-1.34,4.46,-1.34),'#F3E7C9');F('#8A6238',4.28,-1.28,8.6,0.13);
  for(let i=0;i<190;i++){const u=hash(i*3.1),v=hash(i*7.7+1),x=lerp(4.72,12.9,u)-(1-v)*0.14,y=lerp(-1.62,-1.37,v),kk=cl(k*1.7-hash(i*1.3)*0.7);beanShape(x,y,0.15,mix('#E7D29A','#93B863',kk),hash(i*2.3)*3)}
  /* warm air */
  c.globalAlpha=0.25+0.3*k;for(let i=0;i<7;i++){const x=6.2+i*0.95,ph=(t*0.45+i*0.37)%1;line(()=>{c.beginPath();for(let j=0;j<=8;j++){const yy=-1.8-ph*0.5-j*0.07,xx=x+0.05*Math.sin(j*0.9+t*3+i);j?c.lineTo(xx,yy):c.moveTo(xx,yy)}},0.03,'rgba(255,255,255,'+Math.sin(Math.PI*ph)+')')}c.globalAlpha=1}
 function card(t){const k0=popK(t,N[0].t0+0.1,0.35);if(k0<=0)return;c.save();c.translate(7.75,-4.72);c.scale(k0,k0);shape(rr(-2.3,-0.86+0.05,4.6,1.82,0.3),'rgba(70,30,10,0.1)');shape(rr(-2.3,-0.9,4.6,1.8,0.3),'#FFFFFF');
  const ka=popK(t,N[0].t0+0.3,0.3),kb=popK(t,N[0].t0+1.05,0.3),ks=popK(t,N[0].t0+1.95,0.3),kc=popK(t,N[1].t0+0.1,0.35),arrow=(x,k)=>{c.globalAlpha=cl(k);line(()=>{c.beginPath();c.moveTo(x-0.2,-0.12);c.lineTo(x+0.16,-0.12);c.moveTo(x+0.05,-0.23);c.lineTo(x+0.17,-0.12);c.lineTo(x+0.05,-0.01)},0.05,'#C9B9A6');c.globalAlpha=1};
  /* cherry, cut open */
  c.save();c.translate(-1.55,-0.12);c.scale(ka,ka);line(()=>{c.beginPath();c.moveTo(0,-0.3);c.quadraticCurveTo(0.05,-0.5,0.2,-0.55)},0.035,'#7A5236');shape(ell(0.3,-0.52,0.17,0.075,-0.3),'#3E9B62');shape(circ(0,0,0.34),'#D63A2F');
  if(kb>0){c.save();circ(0,0,0.34)();c.clip();c.globalAlpha=cl(kb);shape(ell(0.02,0.02,0.25,0.27),'#F6C7AE');beanShape(-0.085,0.02,0.3,'#EADFAE',Math.PI/2);beanShape(0.12,0.02,0.3,'#EADFAE',Math.PI/2);c.restore()}else shape(circ(-0.1,-0.11,0.09),'rgba(255,255,255,0.45)');c.restore();
  arrow(-0.82,kb);c.save();c.translate(-0.05,-0.12);c.scale(kb,kb);beanShape(-0.16,0,0.5,'#EADFAE',Math.PI/2-0.15);beanShape(0.2,0.02,0.5,'#E3D69F',Math.PI/2+0.15);c.restore();
  arrow(0.8,ks);if(ks>0){c.save();c.translate(0.78,-0.5);c.scale(ks,ks);c.rotate(t*0.8);c.fillStyle='#FFD666';for(let i=0;i<8;i++){c.rotate(TAU/8);c.fillRect(-0.02,-0.22,0.04,0.09)}shape(circ(0,0,0.1),'#FFD666');c.restore()}
  c.save();c.translate(1.55,-0.12);c.scale(kc,kc);shape(circ(0,0,0.46),'#EAF3D8');beanShape(0,0,0.62,'#93B863',-0.5);c.restore();if(kc>0.5){const s=0.5+0.5*Math.sin(t*6);sparkle(2.0,-0.55,0.09+0.04*s,'#FFD666');sparkle(1.12,0.22,0.06+0.03*(1-s),'#FFD666')}
  c.globalAlpha=cl(ka);label('열매',-1.55,0.6,0.22,INK,null,700);c.globalAlpha=cl(kb);label('씨앗',-0.02,0.6,0.22,INK,null,700);c.globalAlpha=cl(kc);label('생두',1.55,0.6,0.25,'#5E8A2E');c.globalAlpha=1;c.restore()}
 return{N,dur:N.dur,tag:'03',title:'건조',cam:[7.4,-2.2,1,1.04],look:{light:{dir:[0.75,-0.65]},palette:{light:'#FFE9B8',sky:'#CBEAF2'},air:{preset:'dust',col:'#FFE6B0',n:30}},draw(t){const k=sm((t-N[0].t0-1.4)/(N[1].t1-N[0].t0-1.6));farmBack(t,'#E6D6B8','#D3C09C');sun(t,k);bed(t,k);card(t);drawActor3(farmer,t)}}})();

/* ============ 04 — 항해 ============ */
const A4=(()=>{const N=nar(['자루에 담긴 생두는 배를 타고 바다를 건너고,'],0.4,0.35);
 const hand={ch:who('등산객'),seed:0.6,sc:0.4,noShadow:1,tracks:[[{t:0,d:0,x:0,yaw:28,mood:'grin',armL:{a:0.25,ab:2.3,b2:0.55},handL:'wave',waveL:1}]]};
 const wave=(y,a,ph,col,t)=>shape(()=>{c.beginPath();c.moveTo(0,1.2);c.lineTo(0,y);for(let x=0;x<=VW+0.2;x+=0.2)c.lineTo(x,y+a*Math.sin(x*2.1+ph+t*2.2));c.lineTo(VW,1.2);c.closePath()},col);
 function ship(t){const bob=0.05*Math.sin(t*1.7);c.save();c.translate(lerp(3.7,6.9,t/N.dur),-1.27+bob);c.rotate(0.012*Math.sin(t*1.7+1));
  /* smoke */for(let i=0;i<5;i++){const ph=((t*0.45+i/5)%1+1)%1;c.globalAlpha=0.5*(1-ph);shape(circ(-2.5-ph*1.9,-3.45-ph*0.9,0.16+ph*0.3),'#FFFFFF')}c.globalAlpha=1;
  /* bridge + funnel */shape(rr(-2.78,-3.35,0.52,0.8,0.05),'#E5484D');F('#2F3140',-2.78,-3.35,0.52,0.16);shape(rr(-3.25,-2.62,1.55,1.7,[0.08,0.08,0,0]),'#F3EFE6');F('rgba(70,30,10,0.1)',-3.25,-1.75,1.55,0.08);c.fillStyle='#3A5BA8';for(let r=0;r<2;r++)for(let i=0;i<4;i++)c.fillRect(-3.1+i*0.34,-2.42+r*0.5,0.22,0.24);F('#C9CED6',-3.35,-2.7,1.75,0.1);
  line(()=>{c.beginPath();c.moveTo(-1.55,-0.95);c.lineTo(-1.55,-3.2)},0.04,'#8E96A3');shape(poly(-1.53,-3.2,-1.05,-3.07,-1.53,-2.94),'#F2B705');
  /* containers */const CC=['#E5484D','#F2B705','#18B7A0','#3D6BE0','#F08A2E','#9B6FD0','#18B7A0','#E5484D'];let n=0;for(let r=0;r<2;r++)for(let i=0;i<4-r;i++){const x=-0.75+i*0.82+r*0.41,y=-0.95-(r+1)*0.56,col=CC[n++];shape(rr(x,y,0.78,0.54,0.03),col);c.fillStyle='rgba(0,0,0,0.12)';for(let k=1;k<6;k++)c.fillRect(x+k*0.13-0.012,y+0.05,0.024,0.44)}
  /* sacks at the bow */for(const[x,y,s]of[[2.72,-1.14,0.5],[3.12,-1.16,0.5],[2.92,-1.46,0.5]]){c.save();c.translate(x,y);c.scale(s,s);sackShape();c.restore()}
  c.save();c.translate(-1.15,-0.95);const P=drawActor3(hand,t);c.restore();
  /* hull */const h=poly(-3.55,-0.95,3.25,-0.95,3.9,-1.22,3.25,0.3,-3.2,0.3,-3.65,-0.5);shape(h,'#27365E');c.save();h();c.clip();F('#D64545',-4,-0.05,8,0.5);F('#FFFFFF',-4,-0.78,8,0.07);F('rgba(0,0,0,0.15)',-4,-0.25,8,0.2);c.restore();
  c.fillStyle='rgba(255,255,255,0.75)';for(let i=0;i<4;i++){const ph=((t*0.9+i/4)%1+1)%1;c.globalAlpha=0.7*(1-ph);c.beginPath();c.ellipse(-3.6-ph*1.4,0.02,0.22+ph*0.3,0.05+ph*0.03,0,0,TAU);c.fill()}c.globalAlpha=1;c.restore()}
 function route(t){const k=popK(t,0.25,0.35);c.save();c.translate(10.3,-5.05);c.scale(k,k);shape(rr(-1.95,-0.67,3.9,1.45,0.26),'rgba(70,30,10,0.1)');shape(rr(-1.95,-0.72,3.9,1.45,0.26),'#FFFFFF');
  c.strokeStyle='#C9B9A6';c.lineWidth=0.04;c.setLineDash([0.1,0.09]);c.beginPath();c.moveTo(-1.3,0.05);c.quadraticCurveTo(0,-0.75,1.3,0.05);c.stroke();c.setLineDash([]);
  shape(circ(-1.3,0.05,0.12),'#5E9B4A');shape(circ(1.3,0.05,0.12),'#8B5A3C');label('농장',-1.3,0.42,0.2,INK,null,700);label('로스터리',1.3,0.42,0.2,INK,null,700);
  const p=sm(lerp(0.08,0.92,t/N.dur)),x=lerp(lerp(-1.3,0,p),lerp(0,1.3,p),p),y=lerp(lerp(0.05,-0.75,p),lerp(-0.75,0.05,p),p);shape(poly(x-0.2,y-0.05,x+0.2,y-0.05,x+0.13,y+0.08,x-0.15,y+0.08),'#27365E');F('#E5484D',x-0.1,y-0.17,0.12,0.12);c.restore()}
 function back(t){F('#CDEBF7',0,-6.3,VW,6.3);F('#E6F5F4',0,-3.4,VW,1.6);glow(6.7,-5.0,3.0,'#FFE9B8',0.8);shape(circ(6.7,-5.0,0.6),'#FFF1C4');cloud(3.6+0.12*t,-5.3,0.8);cloud(8.6+0.09*t,-3.75,0.65);cloud(0.5+0.1*t,-3.3,0.55);
  /* the coast it left behind */shape(()=>{c.beginPath();c.moveTo(0,-1.9);c.bezierCurveTo(0.4,-2.6,1.5,-2.7,2.6,-1.9);c.closePath()},'#8FCB98');for(const[x,h]of[[0.7,0.5],[1.35,0.62]]){line(()=>{c.beginPath();c.moveTo(x,-2.35);c.quadraticCurveTo(x+0.05,-2.35-h*0.6,x+0.1,-2.35-h)},0.04,'#7A5236');for(const a of[-2.4,-1.6,-0.8,0])shape(ell(x+0.1+0.2*Math.cos(a),-2.35-h+0.14*Math.sin(a)+0.04,0.2,0.06,a+Math.PI/2*0.2),'#3F8F5C')}
  F('#58B9DD',0,-1.9,VW,3.2);F('#7CCBE8',0,-1.9,VW,0.2);for(let i=0;i<3;i++){const x=((2+i*4.1+t*0.6)%14)-0.6,y=-4.6+i*0.5+0.1*Math.sin(t*2+i);line(()=>{c.beginPath();c.moveTo(x-0.16,y-0.07-0.05*Math.sin(t*9+i));c.quadraticCurveTo(x-0.07,y-0.1,x,y);c.quadraticCurveTo(x+0.07,y-0.1,x+0.16,y-0.07-0.05*Math.sin(t*9+i))},0.035,'#5B6B78')}}
 return{N,dur:N.dur,tag:'04',title:'항해',look:{light:{dir:[0.1,-1]}},draw(t){back(t);wave(-1.6,0.05,0.5,'#4FB0D6',t);ship(t);wave(-1.2,0.06,0,'#3FA2CC',t);wave(-0.62,0.07,1.7,'#3192BD',t*0.8);wave(-0.02,0.07,3.1,'#2882AB',t*0.65);route(t)}}})();

/* ============ 05 — 로스팅 ============ */
const A5=(()=>{const N=nar(['로스터리에서 뜨거운 불을 만나 갈색 원두로 바뀝니다.'],0.25,0.8),T0=N[0].t0,xs=6.95,tOpen=T0+2.95,TR=[7.62,-2.8,0.8],LV=[7.66,-2.22,0.8];
 const man={ch:who('로스터'),seed:0.3,kicks:[T0+1.0,tOpen+0.08,T0+3.75],tracks:[
  [{t:0,d:0,x:xs,z:0.35,yaw:78,lean:0.06},{t:tOpen+0.35,d:0.45,yaw:24,lean:0.03}],
  [{t:0,d:0,armR:null,armL:{a:-0.2,b:0.6}},{t:T0+0.35,d:0.32,e:E.back,armR:{hand:TR},handR:'grip'},{t:T0+0.7,d:0,propR:'trier'},{t:T0+0.72,d:0.3,armR:{hand:[7.35,-2.7,0.8]}},{t:T0+1.05,d:0.35,armR:{hand:[7.52,-3.0,0.8]},propRot:-0.25},
   {t:T0+1.95,d:0.3,armR:{hand:TR},propRot:0},{t:T0+2.27,d:0,propR:null},{t:T0+2.32,d:0.28,armR:{hand:LV}},{t:tOpen-0.05,d:0.22,e:E.back,armR:{hand:[7.6,-1.8,0.8]}},{t:tOpen+0.4,d:0.4,e:E.back,armR:{a:0.95,b:1.75,ab:0.45}},{t:tOpen+1.1,d:0.35,armR:{a:0.2,b:0.5}}],
  [{t:0,d:0,mood:'smile',look:[0.7,0]},{t:T0+1.1,d:0.25,nod:0.35,blink:1},{t:T0+1.55,d:0.2,blink:0,mood:'grin',brow:0.7},{t:T0+1.75,d:0.15,nod:-0.1},{t:T0+1.95,d:0.2,nod:0,brow:0},{t:tOpen+0.35,d:0.3,look:[0,0],brow:0.4}]]};
 const G='#93B863',Y='#D9B45A',B='#6B3F26',rc=k=>k<0.5?mix(G,Y,k*2):mix(Y,B,(k-0.5)*2);
 function back(t,k,op){F('#F1DFC6',0,-6.3,VW,6.3);c.fillStyle='rgba(180,110,70,0.16)';for(const[x,y]of[[0.5,-3.6],[1.3,-3.6],[0.9,-3.3],[4.9,-5.7],[5.7,-5.7],[5.3,-5.4],[11.5,-5.3],[12.2,-5.0],[4.2,-2.3],[4.9,-2.0],[5.0,-3.9],[11.9,-1.7]])c.fillRect(x,y,0.7,0.24);
  F('#DCC6A6',0,-1.15,VW,1.15);F('#CBB08C',0,-1.2,VW,0.07);F('#B98B62',0,0,VW,1.3);c.fillStyle='rgba(70,30,10,0.09)';for(let x=0.7;x<VW;x+=1.45)c.fillRect(x,0,0.03,1.3);
  /* lamp */F('#5A4636',5.0,-6.3,0.03,1.0);shape(circ(5.015,-4.9,0.6),'rgba(255,222,150,0.22)');shape(poly(4.6,-4.92,5.43,-4.92,5.22,-5.32,4.8,-5.32),'#3A3F4A');shape(circ(5.015,-4.9,0.09),'#FFF3C4');
  /* shelf with green-bean sacks */F('#8A5A3B',0.35,-2.42,3.7,0.1);F('#74492E',0.6,-2.32,0.08,0.5);F('#74492E',3.7,-2.32,0.08,0.5);for(const[x,y,s]of[[0.95,-2.645,0.62],[1.75,-2.645,0.62],[2.55,-2.645,0.62],[3.35,-2.645,0.62],[1.0,-0.285,0.78],[1.9,-0.285,0.78],[1.45,-0.78,0.78],[3.2,-0.285,0.78]]){c.save();c.translate(x,y);c.scale(s,s);sackShape();c.restore()}
  F('#8A6A3A',1.72,-4.25,0.03,0.4);F('#8A6A3A',2.55,-4.25,0.03,0.4);shape(rr(1.5,-3.9,1.3,0.52,0.1),'#FFFFFF');label('생두',2.15,-3.63,0.25,'#5E8A2E');
  /* ---- drum roaster ---- */
  const heat=sm(k*1.3);F('#9AA2AE',9.72,-6.3,0.44,2.2);F('#8891A0',10.02,-6.3,0.14,2.2);shape(rr(9.0,-4.3,1.55,2.6,[0,0.35,0.35,0]),'#343A46');
  shape(rr(7.9,-1.8,2.6,1.8,[0.1,0.1,0,0]),'#3A3F4A');F('rgba(0,0,0,0.18)',7.9,-0.3,2.6,0.3);
  shape(circ(9.0,-3.0,1.42),'rgba(255,140,40,'+(0.16*heat)+')');shape(circ(9.0,-3.0,1.25),'#3F4654');shape(circ(9.0,-3.0,1.08),'#566070');c.fillStyle='#3F4654';for(let i=0;i<8;i++){c.beginPath();c.arc(9.0+0.97*Math.cos(i*TAU/8+0.39),-3.0+0.97*Math.sin(i*TAU/8+0.39),0.035,0,TAU);c.fill()}
  /* hopper */shape(poly(8.4,-4.85,9.6,-4.85,9.28,-4.2,8.72,-4.2),'#C9A45C');F('#B08C46',8.4,-4.9,1.2,0.09);{const hk=cl(1-k*5);if(hk>0)for(let i=0;i<7;i++)beanShape(8.6+i*0.135,-4.93-(i%2)*0.035*hk,0.15,G,i)}
  /* window */shape(circ(9.0,-3.0,0.6),'#C9A45C');const w=circ(9.0,-3.0,0.49);shape(w,'#20242E');c.save();w();c.clip();const nb=Math.round(16*(1-op));for(let i=0;i<nb;i++){const a=i*0.83+t*(3.2+hash(i)),r=0.1+0.3*hash(i*5.1);beanShape(9.0+r*Math.cos(a),-2.92+r*Math.sin(a)*0.9+0.1,0.19,rc(cl(k+(hash(i*9)-0.5)*0.12)),a*2)}shape(poly(8.6,-3.5,8.85,-3.5,8.7,-2.5,8.45,-2.5),'rgba(255,255,255,0.1)');c.restore();
  /* burner */shape(rr(8.25,-1.62,1.3,0.26,0.07),'#20242E');for(let i=0;i<6;i++){const x=8.38+i*0.21,h=(0.12+0.07*Math.sin(t*13+i*2.1))*(0.5+0.5*heat+0.3);shape(()=>{c.beginPath();c.moveTo(x-0.06,-1.39);c.quadraticCurveTo(x-0.07,-1.39-h*0.6,x,-1.39-h);c.quadraticCurveTo(x+0.07,-1.39-h*0.6,x+0.06,-1.39);c.closePath()},i%2?'#FF9A3C':'#FFC94A')}
  /* trier + lever */if(t<T0+0.7||t>T0+2.27){line(()=>{c.beginPath();c.moveTo(8.02,-2.72);c.lineTo(7.66,-2.72)},0.055,'#C9CED6');shape(circ(7.62,-2.72,0.075),'#8A5A3B')}shape(circ(8.0,-2.72,0.07),'#2B303A');
  {const a=lerp(-0.12,0.95,op);c.save();c.translate(8.12,-2.08);c.rotate(-a);line(()=>{c.beginPath();c.moveTo(0,0);c.lineTo(-0.46,-0.02)},0.06,'#C9CED6');shape(circ(-0.48,-0.02,0.08),'#E5484D');c.restore();shape(circ(8.12,-2.08,0.08),'#2B303A')}
  /* chute + cooling tray */shape(poly(9.62,-2.25,9.98,-2.05,10.2,-1.42,9.86,-1.38),'#8E96A3');shape(poly(9.62,-2.25,9.72,-2.3,10.08,-2.1,9.98,-2.05),'#AEB5C0');
  /* gauge */F('#8E96A3',11.42,-2.2,0.12,2.2);shape(rr(10.75,-3.75,1.5,1.95,0.12),'#E9E4DC');shape(circ(11.5,-2.95,0.52),'#FFFFFF');const arc=(a0,a1,col)=>{c.beginPath();c.arc(11.5,-2.95,0.4,a0,a1);c.strokeStyle=col;c.lineWidth=0.1;c.lineCap='butt';c.stroke()};arc(Math.PI*0.85,Math.PI*1.28,G);arc(Math.PI*1.28,Math.PI*1.72,Y);arc(Math.PI*1.72,Math.PI*2.15,'#8B5A3C');
  {const a=lerp(Math.PI*0.88,Math.PI*2.12,k);line(()=>{c.beginPath();c.moveTo(11.5,-2.95);c.lineTo(11.5+0.36*Math.cos(a),-2.95+0.36*Math.sin(a))},0.045,'#2B303A');shape(circ(11.5,-2.95,0.06),'#2B303A')}label('ROAST',11.5,-3.58,0.15,'#6B5A4A');shape(circ(11.05,-2.1,0.07),heat>0.2?'#FF9A3C':'#C9C1B4');shape(circ(11.3,-2.1,0.07),op>0.5?'#6BE38A':'#C9C1B4')}
 function tray(t,op,p){/* p: how much has landed */
  const fall=cl((t-tOpen-0.1)/0.25)*cl((tOpen+1.25-t)/0.2);if(fall>0){c.globalAlpha=fall;for(let i=0;i<9;i++){const ph=((t*2.6+i/9)%1+1)%1;beanShape(10.03+0.06*Math.sin(i*2.4),lerp(-1.4,-0.82,ph),0.15,B,i+t*5)}c.globalAlpha=1}
  for(const x of[8.55,10.4]){F('#6B7380',x,-0.6,0.09,0.6)}shape(ell(9.5,-0.58,1.25,0.21),'#6B7380');shape(rr(8.25,-0.8,2.5,0.22,0),'#8E96A3');shape(ell(9.5,-0.8,1.25,0.2),'#AEB5C0');const in_=ell(9.5,-0.8,1.15,0.16);shape(in_,'#5B6472');c.save();in_();c.clip();const n=Math.round(46*p);for(let i=0;i<n;i++){const a=hash(i*4.3)*TAU+t*0.6,r=Math.sqrt(hash(i*2.9))*1.05;beanShape(9.5+r*Math.cos(a),-0.8+r*Math.sin(a)*0.14,0.16,mix(B,'#7A4A2C',hash(i)),i)}
  line(()=>{c.beginPath();c.moveTo(9.5-1.05*Math.cos(t*2.5),-0.8-0.14*Math.sin(t*2.5));c.lineTo(9.5+1.05*Math.cos(t*2.5),-0.8+0.14*Math.sin(t*2.5))},0.045,'#C9CED6');c.restore();shape(circ(9.5,-0.82,0.06),'#C9CED6');
  if(p>0.15)for(let i=0;i<3;i++){const ph=((t*0.7+i/3)%1+1)%1;c.globalAlpha=0.55*Math.sin(Math.PI*ph)*cl(p*2);line(()=>{c.beginPath();for(let j=0;j<=7;j++){const yy=-1.0-ph*0.6-j*0.06,xx=9.0+i*0.5+0.05*Math.sin(j*1.1+ph*6+i*2);j?c.lineTo(xx,yy):c.moveTo(xx,yy)}},0.035,'#FFFFFF')}c.globalAlpha=1}
 return{N,dur:N.dur,tag:'05',title:'로스팅',cam:[8.4,-2.5,1,1.045],draw(t){const k=sm((t-T0-0.15)/(tOpen-T0-0.3)),op=sm((t-tOpen)/0.25),p=sm((t-tOpen-0.3)/1.0);back(t,k,op);tray(t,op,p);drawActor3(man,t)}}})();

/* ============ 06 — 추출 ============ */
const A6=(()=>{const N=nar(['원두는 바리스타의 손에서 곱게 갈리고,','뜨거운 물이 천천히 지나가면 비로소 커피가 됩니다.']),a0=N[0].t0,b0=N[1].t0,b1=N[1].t1,g0=a0+1.05,g1=N[0].t1+0.1,p0=b0+0.75,p1=b1-0.35,KX=9.16,KY=-2.17,DX=10.22,GX=7.74,PH=[9.25,-2.98,-0.05];
 const pour=[{t:0,d:0,armL:null}];pour.push({t:b0-0.15,d:0.3,armL:{hand:[KX-0.04,KY,-0.05]},handL:'grip'},{t:b0+0.17,d:0,propL:'kettle'},{t:b0+0.2,d:0.4,e:E.out,armL:{hand:PH}});for(let i=0,t=p0;t<p1-0.3;i++,t+=0.42)pour.push({t,d:0.42,armL:{hand:[PH[0]+(i%2?0.06:-0.04),PH[1]+(i%2?0.02:-0.03),PH[2]]}});pour.push({t:p1+0.05,d:0.35,armL:{hand:[KX-0.04,KY,-0.05]}},{t:p1+0.42,d:0,propL:null,handL:null},{t:p1+0.45,d:0.3,armL:null});
 const bar={ch:who('바리스타'),seed:0.4,noShadow:1,kicks:[g0,p1+0.4],tracks:[
  [{t:0,d:0,x:8.6,z:-0.4,yaw:-10},{t:b0-0.2,d:0.4,yaw:8}],
  [{t:0,d:0,armR:{a:0.4,b:1.5},propR:'scoop',fill:1,propRot:0},{t:a0-0.1,d:0.35,e:E.out,armR:{hand:[8.03,-3.03,-0.3]}},{t:a0+0.3,d:0.35,propRot:-0.85},{t:a0+0.95,d:0,fill:0},{t:a0+1.15,d:0.3,propRot:0,armR:{a:0.3,b:1.2}},{t:a0+1.5,d:0,propR:null},{t:a0+1.55,d:0.3,armR:null}],
  pour,[{t:0,d:0,propRot:0},{t:a0+0.3,d:0.35,propRot:-0.85},{t:a0+1.15,d:0.3,propRot:0},{t:p0-0.3,d:0.3,propRot:0.5},{t:p1,d:0.3,propRot:0}],
  [{t:0,d:0,mood:'smile',headTurn:-18,look:[-0.7,0.5]},{t:a0+1.5,d:0.3,headTurn:-24,nod:0.3},{t:b0-0.2,d:0.35,headTurn:18,look:[0.7,0.6]},{t:p1+0.3,d:0.3,headTurn:0,nod:0,look:[0,0],mood:'grin',brow:0.6}]]};
 const man={ch:who('직장인'),seed:0.13,kicks:[p1+0.5],tracks:[[{t:0,d:0,x:6.3,z:0.45,yaw:76,propL:'case',mood:'smile',look:[0.6,0.2]},{t:b0+0.4,d:0.5,lean:0.14,brow:0.6},{t:p1+0.2,d:0.3,lean:0.03,mood:'o',brow:1},{t:p1+0.9,d:0.3,mood:'grin'}]]};
 function back(t){F('#F7E8D2',0,-6.2,VW,6.2);F('#EDD9BC',0,-1.15,VW,1.15);F('#E2C9A3',0,-1.2,VW,0.07);F('#D3B58D',0,0,VW,1.3);c.fillStyle='rgba(70,30,10,0.08)';for(let x=0.6;x<VW;x+=1.7)c.fillRect(x,0,0.03,1.3);
  /* window */
  shape(rr(0.6,-4.8,3.1,3.2,0.12),'#FFFFFF');c.save();rr(0.75,-4.65,2.8,2.9,0.06)();c.clip();F('#BFE3F5',0,-5,5,4);cloud(1.0+0.12*t,-4.1,0.7);F('#A9D3A0',0,-2.6,5,1);for(const[x,h,cc]of[[0.9,1.0,'#E7C9A9'],[1.6,1.5,'#D9B79A'],[2.5,0.9,'#EBD3B4'],[3.0,1.3,'#D9B79A']]){F(cc,x,-2.5-h,0.62,h+0.6);c.fillStyle='rgba(255,255,255,0.6)';for(let k=0;k<2;k++)c.fillRect(x+0.12+k*0.26,-2.3-h,0.13,0.18)}c.restore();
  F('#FFFFFF',2.12,-4.65,0.07,2.9);F('#FFFFFF',0.75,-3.25,2.8,0.07);shape(rr(0.45,-1.72,3.4,0.16,0.05),'#FFFFFF');
  shape(poly(0.45,-4.95,3.85,-4.95,4.05,-4.45,0.25,-4.45),'#2E7D5B');c.fillStyle='rgba(255,255,255,0.85)';for(let x=0.55;x<3.8;x+=0.6){c.beginPath();c.moveTo(x,-4.95);c.lineTo(x+0.3,-4.95);c.lineTo(x+0.34-0.12,-4.45);c.lineTo(x-0.12,-4.45);c.closePath();c.fill()}
  /* plant */
  for(const[a,l]of[[-0.9,1.2],[-0.35,1.5],[0.2,1.55],[0.75,1.2]]){c.save();c.translate(4.75,-0.8);c.rotate(a);shape(()=>{c.beginPath();c.ellipse(0,-l*0.55,0.2,l*0.55,0,0,TAU)},a>0?'#3E9B6A':'#2E7D5B');c.restore()}shape(poly(4.4,-0.85,5.1,-0.85,5.0,0,4.5,0),'#C7694A');F('#B25A3E',4.36,-0.9,0.78,0.13);
  /* lamps */
  for(const x of[4.2,7.3]){F('#5A4636',x-0.015,-6.2,0.03,1.1);shape(circ(x,-4.72,0.55),'rgba(255,222,150,0.22)');shape(poly(x-0.42,-4.72,x+0.42,-4.72,x+0.2,-5.12,x-0.2,-5.12),'#E8B04A');shape(circ(x,-4.7,0.09),'#FFF3C4')}
  /* menu board */
  shape(rr(8.25,-5.6,2.8,1.5,0.06),'#6B4A2E');shape(rr(8.34,-5.51,2.62,1.32,0.04),'#2F4F47');label('MENU',8.95,-5.25,0.2,'#FFFFFF');c.fillStyle='rgba(255,255,255,0.8)';for(let i=0;i<3;i++){c.fillRect(8.55,-4.98+i*0.24,0.95,0.045);c.fillRect(9.7,-4.98+i*0.24,0.3,0.045)}
  shape(rr(10.28,-5.2,0.42,0.5,[0.03,0.03,0.1,0.1]),'#FFFFFF');line(()=>{c.beginPath();c.arc(10.72,-4.98,0.12,-1.2,1.2)},0.04,'#FFFFFF');
  /* shelf */
  F('#8A5A3B',9.6,-3.95,3.3,0.1);for(const[x,cc]of[[9.85,'#FFFFFF'],[10.25,'#F2C6A0'],[10.65,'#FFFFFF'],[11.6,'#9ED3C2'],[12.1,'#F2B6B6']])shape(rr(x,-4.3,0.28,0.35,[0.02,0.02,0.08,0.08]),cc);shape(rr(11.05,-4.55,0.34,0.6,0.06),'#C98B5A');F('#8B5A3C',11.05,-4.6,0.34,0.1);
  /* back counter + espresso machine */
  F('#A9744A',9.45,-2.0,3.5,2.0);F('#7A4E33',9.4,-2.04,3.6,0.1);
  shape(rr(10.0,-3.4,1.6,1.38,0.1),'#C9CED6');c.save();rr(10.0,-3.4,1.6,1.38,0.1)();c.clip();F('#8E96A3',10,-3.4,1.6,0.2);F('rgba(70,30,10,0.1)',10,-2.3,1.6,0.3);c.restore();
  for(const x of[10.2,10.55,10.9])shape(rr(x,-3.62,0.26,0.22,[0.02,0.02,0.06,0.06]),'#FFFFFF');
  shape(rr(10.75,-3.05,0.7,0.36,0.05),'#3A3F4A');shape(circ(10.95,-2.87,0.1),'#E9EDF2');line(()=>{c.beginPath();c.moveTo(10.95,-2.87);c.lineTo(11.0,-2.93)},0.02,'#E5484D');shape(circ(11.25,-2.87,0.05),t>3.95&&t<4.95?'#6BE38A':'#E5484D');
  shape(rr(9.7,-3.08,0.5,0.28,0.06),'#8E96A3');shape(circ(9.87,-3.1,0.06),t>3.95&&t<4.95?'#6BE38A':'#F3EFE6');F('#5E6570',9.86,-2.8,0.12,0.14);line(()=>{c.beginPath();c.moveTo(9.74,-2.76);c.lineTo(9.5,-2.7)},0.06,'#3A3F4A');shape(rr(9.6,-2.14,0.75,0.12,0.03),'#5E6570');
  /* cup under the spout, coffee pouring */
  if(t>4.0&&t<5.15){const k=pop(t,4.0,0.25);if(t>4.15&&t<4.85)F('#6B3F26',9.905,-2.66,0.03,0.4);c.save();c.translate(9.92,-2.14);c.scale(k,k);c.translate(0,-0.18);cupShape(t,t>4.6?1:0);c.restore()}}
 function front(t){shape(rr(7.6,-1.8,5.4,2.0,[0.06,0,0,0]),'#C08A56');for(let i=0;i<4;i++)shape(rr(7.9+i*1.28,-1.5,1.02,1.22,0.05),'#B47D4A');shape(rr(7.42,-1.95,5.6,0.18,0.05),'#7A4E33');
  shape(circ(9.05,-0.9,0.3),'#F7E8D2');shape(rr(8.93,-1.02,0.2,0.24,[0.02,0.02,0.07,0.07]),'#2E7D5B');
  /* register + pastry dome */
  shape(rr(10.75,-2.75,0.75,0.55,0.05),'#3A3F4A');shape(rr(10.82,-2.68,0.61,0.4,0.03),'#9ED3EA');F('#3A3F4A',11.06,-2.2,0.13,0.27);shape(rr(10.85,-2.02,0.55,0.08,0.03),'#3A3F4A');
  shape(rr(11.75,-2.02,0.95,0.08,0.03),'#E9E4DC');for(const[x,y]of[[11.95,-2.1],[12.25,-2.1],[12.1,-2.26]])shape(()=>{c.beginPath();c.ellipse(x,y,0.17,0.09,0,0,TAU)},'#E0A458');c.fillStyle='rgba(255,255,255,0.4)';c.beginPath();c.arc(12.22,-2.02,0.46,Math.PI,TAU);c.fill();shape(circ(12.22,-2.5,0.045),'#E9E4DC')}
 function fx(t){/* order bubble */
  if(t>2.45&&t<3.6){const k=t<3.3?pop(t,2.45,0.3):1-E.in(cl((t-3.3)/0.25));c.save();c.translate(5.7,-4.95);c.scale(k,k);shape(rr(-0.7,-0.6,1.4,1.1,0.3),'#FFFFFF');shape(poly(0.2,0.45,0.62,0.45,0.72,0.86),'#FFFFFF');shape(rr(-0.28,-0.28,0.44,0.5,[0.03,0.03,0.12,0.12]),'#8B5A3C');line(()=>{c.beginPath();c.arc(0.18,-0.05,0.13,-1.2,1.2)},0.05,'#8B5A3C');for(let i=0;i<2;i++)line(()=>{c.beginPath();c.moveTo(-0.14+i*0.16,-0.36);c.quadraticCurveTo(-0.2+i*0.16,-0.44,-0.12+i*0.16,-0.5)},0.03,'#C9A98C');c.restore()}
  /* happy hearts after the first sip */
  for(let i=0;i<3;i++){const u=(t-7.45-i*0.18)/0.9;if(u>0&&u<1){c.globalAlpha=1-u*u;heart(7.3+i*0.32+0.08*Math.sin(u*7+i),-3.9-u*0.9-i*0.2,0.3+0.1*i,'#F26D7D');c.globalAlpha=1}}}
 function gear(t){const gr=t>g0&&t<g1,jx=gr?0.012*Math.sin(t*90):0,lv=cl(1-(t-g0)/(g1-g0)),inH=sm((t-a0-0.5)/0.5);
  /* grinder */c.save();c.translate(jx,0);const hp=poly(GX-0.3,-2.8,GX+0.3,-2.8,GX+0.2,-2.4,GX-0.2,-2.4);shape(hp,'rgba(255,255,255,0.6)');c.save();hp();c.clip();const top=lerp(-2.42,-2.72,inH*lv);for(let i=0;i<22;i++){const x=GX-0.26+hash(i*3.3)*0.52,y=top+hash(i*5.7)*0.32;if(y<-2.4)beanShape(x,y,0.13,'#6B3F26',i)}c.restore();F('#C9CED6',GX-0.33,-2.84,0.66,0.055);
  shape(rr(GX-0.25,-2.4,0.5,0.46,0.06),'#2F3140');shape(circ(GX,-2.17,0.085),gr?'#6BE38A':'#C9CED6');shape(poly(GX+0.23,-2.27,GX+0.42,-2.19,GX+0.42,-2.12,GX+0.23,-2.14),'#3A3F4A');c.restore();
  if(gr){c.globalAlpha=0.8;F('#5E3620',GX+0.375,-2.13,0.035,0.1+0.02*Math.sin(t*40));c.globalAlpha=1;for(const sd of[-1,1])line(()=>{c.beginPath();c.moveTo(GX+sd*0.42,-2.68);c.lineTo(GX+sd*0.5,-2.75);c.moveTo(GX+sd*0.4,-2.35);c.lineTo(GX+sd*0.48,-2.31)},0.025,'rgba(70,30,10,'+(0.25+0.25*Math.sin(t*30))+')')}
  shape(rr(GX+0.27,-2.08,0.24,0.14,[0.02,0.02,0.05,0.05]),'#C9CED6');shape(ell(GX+0.39,-2.08,0.1,0.03),'#5E3620');
  /* dripper + server */const lvl=sm((t-p0-0.5)/(p1-p0)),sv=rr(DX-0.23,-2.28,0.46,0.33,[0.04,0.04,0.11,0.11]);shape(sv,'rgba(255,255,255,0.62)');c.save();sv();c.clip();F('#6B3F26',DX-0.3,-1.95-0.27*lvl,0.6,0.5);F('rgba(255,255,255,0.25)',DX-0.19,-2.3,0.07,0.5);c.restore();
  if(t>p0+0.35&&t<p1+0.5)for(let i=0;i<2;i++){const ph=((t*2.2+i*0.5)%1+1)%1;shape(ell(DX,lerp(-2.28,-1.98-0.27*lvl,ph),0.022,0.04),'#6B3F26')}
  shape(poly(DX-0.34,-2.63,DX+0.34,-2.63,DX+0.11,-2.3,DX-0.11,-2.3),'#FFFFFF');shape(poly(DX-0.3,-2.69,DX+0.3,-2.69,DX+0.27,-2.61,DX-0.27,-2.61),'#F3E7D3');shape(ell(DX,-2.67,0.26,0.035),t>p0?'#4A2A18':'#6B3F26');F('#E9E4DC',DX-0.19,-2.32,0.38,0.05);
  if(t<b0+0.17||t>p1+0.42){c.save();c.translate(KX,KY);kettleShape();c.restore()}}
 function brewFx(t,P){if(t>p0&&t<p1+0.05&&P){const h=handOf(bar,P,1),th=P.propRot,ox=h.x+h.ux*0.12*h.sc,oy=h.y+h.uy*0.12*h.sc,tx=ox+h.sc*(KTIP[0]*Math.cos(th)-KTIP[1]*Math.sin(th)),ty=oy+h.sc*(KTIP[0]*Math.sin(th)+KTIP[1]*Math.cos(th));
   line(()=>{c.beginPath();c.moveTo(tx,ty);c.quadraticCurveTo(tx+0.05,ty+0.04,tx+0.06,-2.67)},0.028,'#BFE9F7')}
  if(t>p0+0.2){const a=cl((t-p0-0.2)/0.6);for(let i=0;i<3;i++){const ph=((t*0.6+i/3)%1+1)%1;c.globalAlpha=0.6*Math.sin(Math.PI*ph)*a;line(()=>{c.beginPath();for(let j=0;j<=7;j++){const yy=-2.8-ph*0.55-j*0.06,xx=DX-0.16+i*0.16+0.05*Math.sin(j*1.1+ph*6+i*2);j?c.lineTo(xx,yy):c.moveTo(xx,yy)}},0.035,'#FFFFFF')}c.globalAlpha=1}
  if(t>p1+0.35){const s=0.5+0.5*Math.sin(t*7),k=popK(t,p1+0.35,0.3);sparkle(DX+0.48,-2.3,(0.1+0.05*s)*k,'#FFD666');sparkle(DX-0.46,-2.08,(0.07+0.04*(1-s))*k,'#FFD666')}}
 return{N,dur:N.dur,tag:'06',title:'추출',cam:[8.8,-2.6,1,1.05],draw(t){back(t*0.3);const P=drawActor3(bar,t);front(0);gear(t);brewFx(t,P);drawActor3(man,t)}}})();

/* ============ 07 — 한 잔의 여정 ============ */
const A7=(()=>{const N=nar(['농장에서 내 손까지,','커피 한 잔에는 수많은 사람의 손길이 담겨 있습니다.'],0.45,2.0),X=[2.3,5.2,8.1,10.0],r1=0.42,c1=0.88,s1=1.08,r2=1.3,c2=1.76,s2=1.96,h0=2.14,h1=2.48,tf=N[1].t0+0.4;
 const far={ch:who('농부'),seed:0.52,kicks:[r1,tf+0.5],tracks:[[{t:0,d:0,x:X[0],z:0.3,yaw:62,propL:'basket',fill:1,armL:{local:[0.12,0.8,0.45]},mood:'grin'},{t:tf,d:0.45,yaw:14}],
  [{t:0,d:0,armR:{a:-0.5,b:0.9},propR:'sack'},{t:r1-0.14,d:0.16,e:E.out,armR:{a:1.75,b:0.25}},{t:r1,d:0,propR:null,handR:'open'},{t:r1+0.3,d:0.35,armR:null,handR:null},{t:tf+0.35,d:0.3,e:E.back,armR:{a:0.25,ab:2.3,b2:0.55},handR:'wave',waveR:1}],[{t:0,d:0,headTurn:0},{t:r1+0.1,d:0.4,headTurn:20},{t:tf,d:0.4,headTurn:0}]]};
 const C1=[X[1]-0.62,-2.67,0.7],C2=[X[2]-0.58,-2.65,0.7];
 const roa={ch:who('로스터'),seed:0.3,kicks:[c1,s1,r2,tf+0.6],tracks:[[{t:0,d:0,x:X[1],z:0.3,yaw:-62,mood:'smile'},{t:c1+0.06,d:0.3,yaw:62},{t:tf+0.05,d:0.45,yaw:-10}],
  [{t:0,d:0,armL:null,armR:null},{t:r1-0.05,d:0.3,e:E.out,armL:{hand:C1},handL:'open'},{t:c1,d:0,propL:'sack',handL:null},{t:c1+0.03,d:0.16,armL:{a:0.3,b:1.3},armR:{a:-0.5,b:0.9}},{t:s1,d:0,propL:null,propR:'beanbag'},{t:s1+0.02,d:0.05,armL:null},{t:r2-0.14,d:0.16,e:E.out,armR:{a:1.75,b:0.25}},{t:r2,d:0,propR:null,handR:'open'},{t:r2+0.3,d:0.35,armR:null,handR:null},{t:tf+0.45,d:0.3,e:E.back,armL:{a:0.25,ab:2.3,b2:0.55},handL:'wave',waveL:1}],
  [{t:0,d:0,headTurn:0},{t:s1,d:0.1,mood:'grin'},{t:r2+0.1,d:0.4,headTurn:18},{t:tf,d:0.4,headTurn:0}]]};
 const HP=[9.03,-2.36,0.75];
 const bar={ch:who('바리스타'),seed:0.4,kicks:[c2,s2,h1,tf+0.7],tracks:[[{t:0,d:0,x:X[2],z:0.3,yaw:-62,mood:'smile'},{t:c2+0.04,d:0.26,yaw:72},{t:tf+0.1,d:0.45,yaw:-8}],[{t:0,d:0,lean:0.03},{t:h0-0.05,d:0.3,lean:0.2},{t:h1+0.12,d:0.3,lean:0.03}],
  [{t:0,d:0,armL:null,armR:null},{t:r2-0.05,d:0.3,e:E.out,armL:{hand:C2},handL:'open'},{t:c2,d:0,propL:'beanbag',handL:null},{t:c2+0.03,d:0.17,armL:{a:0.3,b:1.3},armR:{a:0.45,b:1.45}},{t:s2,d:0,propL:null,propR:'cup',steam:1},{t:s2+0.02,d:0.12,armL:null},{t:h0,d:0.3,e:E.out,armR:{hand:[HP[0]-0.06,HP[1],HP[2]]}},{t:h1,d:0,propR:null,handR:'open'},{t:h1+0.12,d:0.35,armR:null,handR:null},{t:tf+0.55,d:0.3,e:E.back,armR:{a:0.25,ab:2.3,b2:0.55},handR:'wave',waveR:1}],
  [{t:0,d:0,headTurn:0},{t:s2,d:0.1,mood:'grin'},{t:tf,d:0.4,headTurn:0}]]};
 const sip=N[1].t0+2.0;
 const me={ch:who('직장인'),seed:0.13,kicks:[h1,tf+0.9,sip+1.1],tracks:[[{t:0,d:0,x:X[3],z:0.3,yaw:-76,mood:'smile',look:[-0.6,0]},{t:tf+0.15,d:0.45,yaw:-12,look:[0,0]}],[{t:0,d:0,lean:0.03},{t:h0-0.05,d:0.3,lean:0.2},{t:h1+0.12,d:0.3,lean:0.03}],
  [{t:0,d:0,armL:null},{t:h0,d:0.3,e:E.out,armL:{hand:[HP[0]+0.1,HP[1],HP[2]]},handL:'open'},{t:h1,d:0,propL:'cup',steam:1,handL:null},{t:h1+0.1,d:0.35,armL:{a:0.45,b:1.45}},{t:tf+0.5,d:0.35,e:E.back,armL:{a:1.15,b:1.2,ab:0.5}},{t:sip-0.35,d:0.3,armL:{a:0.45,b:1.45}},{t:sip,d:0.3,armL:{local:[0.14,-0.2,0.5]},propRot:-0.3},{t:sip+0.75,d:0.3,armL:{a:0.45,b:1.45},propRot:0}],
  [{t:0,d:0,brow:0},{t:h1,d:0.15,mood:'grin',brow:1},{t:sip,d:0.25,blink:1,mood:'smile'},{t:sip+0.8,d:0.2,blink:0,mood:'grin',brow:1}]]};
 const BAND=[[0,3.75,'#E4F1CB'],[3.75,6.65,'#F8DDBB'],[6.65,9.25,'#CFE9DC'],[9.25,12.8,'#D8E3F4']],STEP=[['수확',0],['로스팅',c1],['추출',c2],['한 잔',h1]];
 const icon=(i,t)=>{if(i===0){cherryShape(-0.08,0.02,0.11);cherryShape(0.1,-0.04,0.11)}else if(i===1)beanShape(0,0,0.34,'#6B3F26',-0.5);else if(i===2){shape(poly(-0.17,-0.12,0.17,-0.12,0.06,0.1,-0.06,0.1),'#8E96A3');shape(ell(0,0.17,0.025,0.04),'#6B3F26')}else{shape(rr(-0.11,-0.12,0.22,0.25,[0.02,0.02,0.07,0.07]),'#8B5A3C');line(()=>{c.beginPath();c.arc(0.13,0,0.07,-1.2,1.2)},0.035,'#8B5A3C')}};
 function back(t){for(const[x0,x1,col]of BAND)F(col,x0,-6.3,x1-x0,6.3);for(let i=0;i<4;i++){const cx=X[i],col=BAND[i][2];shape(circ(cx,-2.2,1.75),dk(col,0.955))}F('#EFE6D6',0,0,VW,1.3);F('#E2D6C2',0,0,VW,0.07);for(let i=0;i<4;i++)shape(ell(X[i],0.2,1.05,0.2),dk(BAND[i][2],0.9));
  /* step chips + dotted link */c.strokeStyle='rgba(59,36,22,0.28)';c.lineWidth=0.04;c.setLineDash([0.1,0.1]);c.beginPath();c.moveTo(X[0],-4.62);c.lineTo(X[3],-4.62);c.stroke();c.setLineDash([]);
  STEP.forEach(([s,t0],i)=>{const k=popK(t,0.1+i*0.08,0.3),on=t>=t0,kk=on?1+0.16*Math.exp(-7*(t-t0))*Math.cos(18*(t-t0)):1;c.save();c.translate(X[i],-4.62);c.scale(k*kk,k*kk);shape(rr(-0.92,-0.33,1.84,0.66,0.33),on?'#FFFFFF':'#F3EFE6');shape(circ(-0.58,0,0.25),on?BAND[i][2]:'#E6E0D4');c.globalAlpha=on?1:0.35;c.save();c.translate(-0.58,0);icon(i,t);c.restore();label(s,0.22,0.01,0.26,INK);c.globalAlpha=1;c.restore()})}
 let pA=null,pB=null;
 function fx(t){const fly=(r,cc,A,B,fn,sp)=>{const u=(t-r)/(cc-r);if(u<=0||u>=1||!A)return;const x=lerp(A[0],B[0],u),y=lerp(A[1],B[1],u)-1.15*4*u*(1-u);c.save();c.translate(x,y);c.rotate(sp*u);c.scale(0.85,0.85);fn();c.restore()};
  if(!pA){const h=handOf(far,poseOfK(far,r1),0);pA=[h.x,h.y+0.2]}if(!pB){const h=handOf(roa,poseOfK(roa,r2),0);pB=[h.x,h.y+0.1]}
  fly(r1,c1,pA,[C1[0],C1[1]+0.25],()=>sackShape(),TAU);fly(r2,c2,pB,[C2[0],C2[1]+0.1],beanbagShape,TAU);
  for(const[ts,x,col]of[[s1,X[1],'#FF9A3C'],[s2,X[2],'#FFFFFF']]){const u=(t-ts)/0.5;if(u>0&&u<1){c.globalAlpha=1-u;for(let i=0;i<6;i++){const a=i*TAU/6+0.4;sparkle(x+0.55+Math.cos(a)*(0.2+0.5*u),-2.25+Math.sin(a)*(0.2+0.5*u),0.11*(1-u*0.5),col)}c.globalAlpha=1}}
  for(let i=0;i<4;i++){const u=(t-sip-1.05-i*0.16)/1.0;if(u>0&&u<1){c.globalAlpha=1-u*u;heart(X[3]-0.75+i*0.36+0.08*Math.sin(u*7+i),-3.95-u*0.8-(i%2)*0.2,0.3+0.08*(i%2),'#F26D7D');c.globalAlpha=1}}
  const k=popK(t,tf+0.55,0.4);if(k>0){c.save();c.translate(VW/2,-5.52);c.scale(k,k);label('커피 한 잔이 내 손에 오기까지',0,0,0.5,INK);c.restore()}}
 return{N,dur:N.dur,tag:'07',title:'한 잔의 여정',noTag:tf+0.3,draw(t){back(t);for(const a of[far,roa,bar,me])drawActor3(a,t);fx(t)}}})();

const SCENES=[A1,A2,A3,A4,A5,A6,A7];
