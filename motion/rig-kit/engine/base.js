/* base: canvas, constants, 2-bone IK, lineless drawing primitives */
const Q=new URLSearchParams(location.search);const W=1920,H=1080;
const cv=document.getElementById('cv');cv.width=W;cv.height=H;let c=cv.getContext('2d',{willReadFrequently:true});/* CPU-backed: renders read every frame back and canvas→canvas copies stay cheap; `c` is swapped while a layer is drawn off-screen (look.js withCtx) */
const TAU=Math.PI*2,INK='#3B2416',BG='#F3EFE6';
const lerp=(a,b,u)=>a+(b-a)*u,cl=x=>Math.max(0,Math.min(1,x)),sm=x=>{x=cl(x);return x*x*(3-2*x)},cl2=x=>Math.max(-1,Math.min(1,x));
const ANK=0.17,L1=0.67,L2=0.67,TL0=0.88,UA=0.5,FA=0.46;
function ik(a,t,l1,l2,s,st){let dx=t[0]-a[0],dy=t[1]-a[1],dd=Math.hypot(dx,dy);if(dd>l1+l2){const k=Math.min(st||1,dd/(l1+l2));l1*=k;l2*=k}const D=Math.min(l1+l2-1e-3,Math.max(Math.abs(l1-l2)+1e-3,dd)),th=Math.atan2(dy,dx),al=Math.acos(cl2((l1*l1+D*D-l2*l2)/(2*l1*D)));
 return[[a[0]+Math.cos(th+s*al)*l1,a[1]+Math.sin(th+s*al)*l1],[a[0]+Math.cos(th)*D,a[1]+Math.sin(th)*D]]}
const FONT='"Noto Sans CJK KR","Noto Sans KR","Apple SD Gothic Neo",sans-serif';
const hash=n=>{const x=Math.sin(n*127.1+311.7)*43758.5453;return x-Math.floor(x)};
/* ---------- drawing primitives: LINELESS. flat fills, shapes separated by colour and cast shadows ---------- */
const TONE='rgba(70,30,10,0.26)',SHC='rgba(70,30,10,0.2)',GLOSS='rgba(255,255,255,0.14)';
function polyPath(pts){c.beginPath();pts.forEach((q,i)=>i?c.lineTo(q[0],q[1]):c.moveTo(q[0],q[1]))}
function tube(pts,w,col,cap){c.lineJoin='round';c.lineCap=cap||'round';polyPath(pts);c.strokeStyle=col;c.lineWidth=w;c.stroke()}
/* tapered limb: one path (quads + joint discs, same winding) so it also works with translucent fills */
function part(pts,ws,f0,f1){const seg=[];let tot=0;for(let i=1;i<pts.length;i++){const l=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);seg.push(l);tot+=l}
 const at=f=>{let d=cl(f)*tot;for(let i=0;i<seg.length;i++){if(d<=seg[i]||i===seg.length-1){const u=seg[i]?cl(d/seg[i]):0;return{i,pt:[lerp(pts[i][0],pts[i+1][0],u),lerp(pts[i][1],pts[i+1][1],u)],w:lerp(ws[i],ws[i+1],u)}}d-=seg[i]}};
 const a=at(f0),b=at(f1),P=[a.pt],W=[a.w];for(let i=a.i+1;i<=b.i;i++){P.push(pts[i]);W.push(ws[i])}P.push(b.pt);W.push(b.w);return[P,W]}
function limbPath(pts,ws,capA,capB,k){k=k||1;c.beginPath();const n=pts.length;
 for(let i=0;i<n-1;i++){const a=pts[i],b=pts[i+1],dx=b[0]-a[0],dy=b[1]-a[1],l=Math.hypot(dx,dy);if(l<1e-4)continue;const nx=-dy/l,ny=dx/l,wa=ws[i]*k/2,wb=ws[i+1]*k/2;
  c.moveTo(a[0]-nx*wa,a[1]-ny*wa);c.lineTo(b[0]-nx*wb,b[1]-ny*wb);c.lineTo(b[0]+nx*wb,b[1]+ny*wb);c.lineTo(a[0]+nx*wa,a[1]+ny*wa);c.closePath()}
 for(let i=0;i<n;i++){if((i===0&&!capA)||(i===n-1&&!capB))continue;const r=ws[i]*k/2;c.moveTo(pts[i][0]+r,pts[i][1]);c.arc(pts[i][0],pts[i][1],r,0,TAU)}}
function limb(pts,ws,col,capA,capB,k){limbPath(pts,ws,capA,capB,k);c.fillStyle=col;c.fill()}
function bandOf(pts,ws,f0,f1,col,k){const[P,W]=part(pts,ws,f0,f1);limb(P,W,col,false,false,k)}
function shape(pathFn,col){pathFn();c.fillStyle=col;c.fill()}
/* a shape lifted off whatever is under it by a small cast shadow (replaces the outline) */
function lifted(pathFn,col,dx,dy){c.save();c.translate(dx||0,dy===undefined?0.025:dy);pathFn();c.fillStyle=SHC;c.fill();c.restore();pathFn();c.fillStyle=col;c.fill()}
function line(pathFn,w,col){pathFn();c.strokeStyle=col||TONE;c.lineWidth=w||0.02;c.lineCap='round';c.lineJoin='round';c.stroke()}
const F=(col,x,y,w,h)=>{c.fillStyle=col;c.fillRect(x,y,w,h)};
const rr=(x,y,w,h,r)=>()=>{c.beginPath();c.roundRect(x,y,w,h,r)};
const circ=(x,y,r)=>()=>{c.beginPath();c.arc(x,y,r,0,TAU)};
const poly=(...p)=>()=>{c.beginPath();for(let i=0;i<p.length;i+=2)i?c.lineTo(p[i],p[i+1]):c.moveTo(p[i],p[i+1]);c.closePath()};
const rgb=hex=>{const n=parseInt(hex.slice(1),16);return[n>>16&255,n>>8&255,n&255]};
const dk=(hex,f)=>{const[r,g,b]=rgb(hex);return`rgb(${Math.min(255,r*f)|0},${Math.min(255,g*f)|0},${Math.min(255,b*f)|0})`};
const mix=(h1,h2,k)=>{const a=rgb(h1),b=rgb(h2);return`rgb(${a.map((v,i)=>lerp(v,b[i],k)|0).join(',')})`};
const lum=hex=>{const[r,g,b]=rgb(hex);return 0.3*r+0.59*g+0.11*b};
