/* stage: world units (U px per unit, ground line at GY), narration timing, small helpers
   world(): x 0..VW (12.8) left→right, y 0 = ground, up is negative (a 3.4-unit-tall character reaches y=-3.4) */
/* ---------- stage ---------- */
const U=150,GY=935,VW=W/U;
function world(){c.setTransform(U,0,0,U,0,GY)}
const pop=(t,t0,d)=>t<t0?0:E.back(cl((t-t0)/(d||0.3)));
function cloud(x,y,s){c.fillStyle='#FFFFFF';for(const[dx,dy,r]of[[0,0,0.32],[0.36,-0.1,0.4],[0.78,0,0.3],[0.4,0.1,0.34]]){c.beginPath();c.arc(x+dx*s,y+dy*s,r*s,0,TAU);c.fill()}c.fillRect(x,y,0.78*s,0.3*s)}
function tree(x,y,s,col){F('#8A5A3B',x-0.09*s,y-1.3*s,0.18*s,1.3*s);for(const[dx,dy,r]of[[0,-1.9,0.7],[-0.5,-1.5,0.5],[0.5,-1.5,0.52],[0,-2.5,0.5]])shape(circ(x+dx*s,y+dy*s,r*s),col)}
function heart(x,y,s,col){c.fillStyle=col;c.beginPath();c.moveTo(x,y+0.3*s);c.bezierCurveTo(x-0.6*s,y-0.1*s,x-0.25*s,y-0.5*s,x,y-0.15*s);c.bezierCurveTo(x+0.25*s,y-0.5*s,x+0.6*s,y-0.1*s,x,y+0.3*s);c.fill()}
/* ---------- narration → time slots ---------- */
const SYL=Number(Q.get('syl'))||5.2,GAP=0.38;
/* nar(['문장', ['녹음 길이를 아는 문장', 3.2], ...], lead, tail): a line is text, or [text, seconds] once the real voice-over length is known */
function nar(lines,lead,tail){let t=lead===undefined?0.45:lead;const out=[];for(const l of lines){const s=Array.isArray(l)?l[0]:l,n=(s.match(/[가-힣A-Za-z0-9]/g)||[]).length,d=Array.isArray(l)?l[1]:Math.max(1.2,n/SYL);out.push({t0:t,t1:t+d,text:s});t+=d+GAP}out.dur=t-GAP+(tail===undefined?0.75:tail);return out}
/* text in world units that follows the current transform (replaces the stage helper) */
function label(str,x,y,size,col,align,weight){c.save();c.translate(x,y);c.scale(0.01,0.01);c.font=`${weight||900} ${size*100}px ${FONT}`;c.fillStyle=col;c.textAlign=align||'center';c.textBaseline='middle';c.fillText(str,0,0);c.restore()}
const ell=(x,y,rx,ry,rot)=>()=>{c.beginPath();c.ellipse(x,y,rx,ry,rot||0,0,TAU)};
const popK=(t,t0,d)=>t<t0?0:E.back(cl((t-t0)/(d||0.3)));
function handOf(ac,P,i){const sc=(ac.sc||1)*(ac.ch.h||1),A=P.arms[i],gy=(ac.gy||0)+P.z*PITCH,dx=A.wr[0]-A.el[0],dy=A.wr[1]-A.el[1],l=Math.hypot(dx,dy)||1;return{x:P.x+sc*A.wr[0],y:gy+sc*(A.wr[1]-P.y),ux:dx/l,uy:dy/l,sc}}
function sparkle(x,y,s,col){c.save();c.translate(x,y);c.fillStyle=col||'#FFFFFF';c.beginPath();for(let i=0;i<8;i++){const a=i*TAU/8,r=i%2?s*0.3:s;c.lineTo(Math.cos(a)*r,Math.sin(a)*r)}c.closePath();c.fill();c.restore()}
/* white info card with a soft shadow, centred on (x,y), scaled by k (use popK). Leaves a save open like bubble(): draw inside in card-local units, then c.restore() */
function card(x,y,w,h,k){c.save();c.translate(x,y);c.scale(k,k);const r=Math.min(w,h)*0.17;shape(rr(-w/2,-h/2+0.05,w,h,r),'rgba(70,30,10,0.1)');shape(rr(-w/2,-h/2,w,h,r),'#FFFFFF')}
function bubble(x,y,w,h,k,tail){c.save();c.translate(x,y);c.scale(k,k);shape(rr(-w/2,-h/2,w,h,Math.min(w,h)*0.3),'#FFFFFF');if(tail)shape(poly(tail*0.15*w,h/2-0.02,tail*0.38*w,h/2-0.02,tail*0.5*w,h/2+0.34),'#FFFFFF')}
/* one character in pixel space (turnarounds, sheets, probes) */
function actor(ch,q,t,x,gy,Upx){const hh=ch.h||1,P=pose360(Object.assign({sc:hh},q),t);c.save();c.translate(x,gy);c.scale(Upx*hh,Upx*hh);footShadows(P);drawChar3(ch,P);c.restore();return P}
