/* look: light, depth and finish over the flat style — 조명 레이어, 깊이감, 공기 입자, 마감(비네트·그레인).
   On by default. LOOK holds the defaults; a scene overrides any of them with look:{...} (look:false = the plain flat look).
   Conventions
   · light.dir = screen direction TOWARD the light ([-0.55,-0.8] = upper left). Set code shades with it: lit(col) on the faces turned
     toward it, shd(col) on the faces turned away; the wash comes in from that side and contact shadows fall away from it.
   · palette.shadow is the colour every shadow is tinted with (deep blue/purple, never black); palette.light tints glows and motes.
   · Characters stay the clean flat rig: the look only adds a soft contact shadow under them. Grain never goes over characters (grain() is a set helper). */
const LOOK={on:1,
 light:{dir:[-0.55,-0.8],col:null},
 palette:{base:'#F3EFE6',accent:'#FFB54A',shadow:'#40366E',light:'#FFF2D6',sky:'#CFE3F0'},
 charShade:0,  /* optional soft far-side shadow on head + torso (0 = the clean flat characters) */
 shadow:1,     /* soft, blurred contact shadows under feet            */
 vignette:0.14,/* edge darkening toward palette.shadow                */
 wash:0.07,    /* soft light falling in from the light's side        */
 aerial:0.55,  /* how strongly layer(d,..) hazes far layers toward palette.sky */
 air:null};    /* ambient particles drawn over the scene: 'dust' 'motes' 'snow' 'embers' 'smoke' or {preset,n,col,...} */
/* presets: look:{preset:'cinematic', ...overrides}. 'cinematic' = deep indigo darks, strong luminous glows, a dark colour grade at the
   frame edges so the lit focal point carries the shot. Characters are untouched either way. */
const LOOKS={cinematic:{palette:{base:'#16143C',accent:'#FFB45A',shadow:'#14113A',light:'#FFD7A2',sky:'#2C2D68'},
 vignette:0.55,wash:0.05,glow:1.35,aerial:0.7,grade:{top:'#0B0926',bottom:'#0B0926',a:0.42}}};
let LK=null,CAM={fx:0,fy:0,z:1,cx:0,cy:0};
const hexA=(hex,a)=>{const[r,g,b]=rgb(hex);return`rgba(${r},${g},${b},${a})`};
function resolveLook(sc){let o=sc&&sc.look;const off=o===false||LOOK.on===0;if(off)o=null;   /* off: same fields (helpers keep working), every effect skipped */
 const pr=(o&&o.preset&&LOOKS[o.preset])||{},L=Object.assign({},LOOK,pr,o||{});L.light=Object.assign({},LOOK.light,pr.light,o&&o.light);L.palette=Object.assign({},LOOK.palette,pr.palette,o&&o.palette);L.on=off?0:L.on===undefined?1:L.on;
 const p=L.palette,d=L.light.dir,dl=Math.hypot(d[0],d[1])||1;L.lx=d[0]/dl;L.ly=d[1]/dl;L.lcol=L.light.col||p.light;
 L.sh=a=>hexA(p.shadow,a);return L}
function useLook(L){LK=L}
useLook(resolveLook(null));

/* ---------- colour & gradient helpers for set code ---------- */
/* stops: colours spread evenly, or [pos,colour] pairs */
function grad(g,stops){stops.forEach((s,i)=>Array.isArray(s)?g.addColorStop(s[0],s[1]):g.addColorStop(stops.length>1?i/(stops.length-1):0,s));return g}
const lin=(x0,y0,x1,y1,...st)=>grad(c.createLinearGradient(x0,y0,x1,y1),st);   /* shape(path, lin(0,-6,0,0,'#9CC8EA','#E8F1F4')) */
const rad=(x,y,r,...st)=>grad(c.createRadialGradient(x,y,0,x,y,r),st);
/* palette-aware tones: shd('#8E9399') = the shadow side of that colour, lit('#8E9399') = its lit side, haze(col,k) = toward the sky */
const shd=(hex,k)=>mix(hex,LK.on?LK.palette.shadow:'#000000',k===undefined?0.32:k);
const lit=(hex,k)=>mix(hex,LK.on?LK.lcol:'#FFFFFF',k===undefined?0.3:k);
const haze=(hex,k)=>mix(hex,(LK.on&&LK.palette.sky)||'#CFE3F0',k===undefined?0.4:k);
/* soft light glow (sun, fire, lamps, screens, explosions): additive-looking, fades to nothing at r */
function glow(x,y,r,col,k){if(k===undefined)k=1;k*=(LK.on&&LK.glow)||1;if(k<=0||r<=0)return;col=col||(LK.on?LK.lcol:'#FFF2D6');c.save();c.globalCompositeOperation='screen';c.globalAlpha*=Math.min(1,k);
 c.fillStyle=rad(x,y,r,hexA(col,0.85),[0.25,hexA(col,0.45)],[0.6,hexA(col,0.12)],hexA(col,0));c.beginPath();c.arc(x,y,r,0,TAU);c.fill();c.restore()}
/* micro-sway for background things (trees, signs, smoke): rotates what fn draws about the pivot (px,py) */
function sway(px,py,t,amp,fn,seed,freq){seed=seed||0;freq=freq||0.45;const a=amp*(Math.sin(t*freq*TAU+seed*7.3)+0.35*Math.sin(t*freq*2.37*TAU+seed*3.1));c.save();c.translate(px,py);c.rotate(a);c.translate(-px,-py);fn();c.restore()}

/* ---------- off-screen drawing ---------- */
const _OFF={};
function offCanvas(name){let o=_OFF[name];if(!o||o.width!==cv.width||o.height!==cv.height){o=_OFF[name]=document.createElement('canvas');o.width=cv.width;o.height=cv.height;o.ctx=o.getContext('2d',{willReadFrequently:true})}return o}
/* draw fn with the global `c` pointing at ctx (same transform) */
function withCtx(ctx,fn){const old=c,m=old.getTransform();c=ctx;c.setTransform(m);try{fn()}finally{c=old}}

/* ---------- depth: parallax layers + aerial perspective ---------- */
/* layer(d, fn, hz): d = depth 0 (stage) .. 1 (far away). Far layers zoom/pan less with the scene camera and are hazed toward palette.sky
   (hz overrides the haze amount, 0 = none). Draw far → near. */
function layer(d,fn,hz){const z=CAM.z||1,zd=lerp(z,1,d),s=zd/z,cxd=lerp(CAM.cx,CAM.fx,d),cyd=lerp(CAM.cy,CAM.fy,d);c.save();c.translate(CAM.cx-s*cxd,CAM.cy-s*cyd);c.scale(s,s);
 const k=hz===undefined?d*(LK.on?LK.aerial:0):hz;
 if(k>0.01&&LK.on){const o=offCanvas('layer'),x=o.ctx;x.setTransform(1,0,0,1,0,0);x.clearRect(0,0,o.width,o.height);withCtx(x,fn);
  x.setTransform(1,0,0,1,0,0);x.globalCompositeOperation='source-atop';x.fillStyle=hexA(LK.palette.sky||'#CFE3F0',Math.min(0.85,k));x.fillRect(0,0,o.width,o.height);x.globalCompositeOperation='source-over';
  c.setTransform(1,0,0,1,0,0);c.drawImage(o,0,0)}else fn();
 c.restore()}

/* ---------- ambient particles ---------- */
const AIR={dust:{n:40,col:null,size:0.011,alpha:0.55,vx:0.1,vy:-0.04,wob:0.12,soft:0.35,y0:-5.8,y1:0.6},
 motes:{n:26,col:null,size:0.035,alpha:0.42,vx:0.05,vy:-0.06,wob:0.18,soft:1,twinkle:1,y0:-6,y1:0.4},
 snow:{n:70,col:'#FFFFFF',size:0.025,alpha:0.85,vx:0.12,vy:0.55,wob:0.25,soft:0.5,y0:-6.4,y1:1},
 embers:{n:34,col:'#FFB054',size:0.014,alpha:0.9,vx:0.08,vy:-0.55,wob:0.3,soft:0.3,twinkle:1,glow:1,y0:-6,y1:0.8},
 smoke:{n:12,col:'#D9D2C4',size:0.6,alpha:0.16,vx:0.16,vy:-0.05,wob:0.1,soft:1,y0:-5.5,y1:0.5}};
const _SPR={};
function sprite(col,soft){const key=col+soft;let s=_SPR[key];if(s)return s;s=_SPR[key]=document.createElement('canvas');s.width=s.height=64;const x=s.getContext('2d',{willReadFrequently:true}),g=x.createRadialGradient(32,32,0,32,32,32);
 g.addColorStop(0,hexA(col,1));g.addColorStop(cl(1-soft*0.75),hexA(col,soft>0.9?0.55:0.95));g.addColorStop(1,hexA(col,0));x.fillStyle=g;x.fillRect(0,0,64,64);return s}
/* air(t, 'dust' | {preset:'dust', n, col, alpha, x0, x1, y0, y1, seed}) — depth-scaled drifting particles in world units. Deterministic in t. */
function air(t,o){if(typeof o==='string')o={preset:o};const P=Object.assign({},AIR[o.preset||'dust'],o),col=P.col||(LK.on?LK.lcol:'#FFF2D6'),spr=sprite(col,P.soft),x0=P.x0===undefined?-0.5:P.x0,x1=P.x1===undefined?VW+0.5:P.x1,w=x1-x0,h=P.y1-P.y0,sd=P.seed||0;
 c.save();if(P.glow)c.globalCompositeOperation='screen';const ga=c.globalAlpha;
 for(let i=0;i<P.n;i++){const r1=hash(i*1.37+sd),r2=hash(i*2.71+sd+5),r3=hash(i*4.13+sd+9),dep=0.35+0.65*hash(i*7.7+sd+3),sp=0.4+0.6*dep;
  let x=x0+((r1*w+P.vx*sp*t+P.wob*Math.sin(t*(0.6+r3)+i))%w+w)%w,y=P.y0+((r2*h+P.vy*sp*t+P.wob*0.6*Math.cos(t*(0.5+r1)+i*1.7))%h+h)%h;
  let a=P.alpha*(0.45+0.55*dep);if(P.twinkle)a*=0.55+0.45*Math.sin(t*(1.3+r3*2)+i*2.1);const edge=cl(Math.min(y-P.y0,P.y1-y)/(0.12*h));a*=edge;if(a<=0.01)continue;
  const s=P.size*(0.5+1.1*dep)*(0.7+0.6*r3)*2.2;c.globalAlpha=ga*a;c.drawImage(spr,x-s,y-s,s*2,s*2)}
 c.restore()}

/* night sky: twinkling stars (deterministic). stars(t,{n,y0,y1,seed,col}) */
function stars(t,o){o=o||{};const n=o.n||120,y0=o.y0===undefined?-6.4:o.y0,y1=o.y1===undefined?-1.5:o.y1,sd=o.seed||0,col=o.col||'#FFFFFF',spr=sprite(col,0.6);c.save();const ga=c.globalAlpha;
 for(let i=0;i<n;i++){const x=hash(i*3.17+sd)*VW,y=lerp(y0,y1,Math.pow(hash(i*5.31+sd),1.3)),b=hash(i*7.9+sd),tw=0.55+0.45*Math.sin(t*(0.8+b*2.4)+i*1.9),r=0.008+0.03*b*b;
  c.globalAlpha=ga*tw*(0.35+0.65*b);c.drawImage(spr,x-r*2.2,y-r*2.2,r*4.4,r*4.4);
  if(b>0.93){c.globalAlpha=ga*tw*0.8;sparkle(x,y,0.09+0.05*b,col)}}c.restore()}
/* where a helmet lamp (hat.lamp) is in world units for an actor drawn with drawActor3 → {x,y,dir,k}: dir = ±1 facing side, k = how much the lamp faces the camera */
function lampOf(ac,P){const sc=(ac.sc||1)*(ac.ch.h||1),hd=(ac.ch.hd||1)*HS,sy=Math.sin(P.headYaw),ex=Math.max(-0.56,Math.min(0.56,0.6*sy))*0.84,ly=P.hat-0.897-0.5*0.84,ca=Math.cos(P.hrot),sa=Math.sin(P.hrot),lx=ex*hd,lyy=ly*hd;
 return{x:P.x+sc*(P.head[0]+lx*ca-lyy*sa),y:(ac.gy||0)+P.z*PITCH+sc*(P.head[1]-P.y+lx*sa+lyy*ca),dir:sy>=0?1:-1,side:Math.abs(sy),k:Math.cos(P.headYaw),sc}}
/* a glowing head-lamp: halo + a soft beam toward the side the head faces (tilted by nod) */
/* aim (optional, radians on screen, 0 = right, +π/2 = down) overrides the beam direction, e.g. Math.atan2(ty-L.y, tx-L.x) toward a target */
function headlamp(ac,P,len,col,aim){const L=lampOf(ac,P);col=col||'#FFF1C2';len=len||3.2;
 if(L.side>0.25||aim!==undefined){const a=aim!==undefined?aim:(L.dir>0?0:Math.PI)+L.dir*0.12+P.hrot*1.6,sp=0.26;c.save();c.globalCompositeOperation='screen';c.globalAlpha*=(aim!==undefined?1:cl((L.side-0.25)*2))*((LK.on&&LK.glow)||1)*0.7;
  c.fillStyle=rad(L.x,L.y,len*L.sc,hexA(col,0.55),[0.4,hexA(col,0.18)],hexA(col,0));c.beginPath();c.moveTo(L.x,L.y);c.arc(L.x,L.y,len*L.sc,a-sp,a+sp);c.closePath();c.fill();c.restore()}
 glow(L.x,L.y,0.55*L.sc,col,0.55+0.45*cl(L.k+0.4));return L}
/* ---------- characters: soft contact shadow (called by drawActor3 / actor) ---------- */
function footShadows(P){if(!(LK.on&&LK.shadow)){for(const L of P.legs){const h=cl((L.lift+P.y)/0.3);c.beginPath();c.ellipse(L.a[0]+0.14*P.sy,ANK+L.a[1]+L.lift+0.02,0.4*(1-0.35*h),0.07*(1-0.35*h),0,0,TAU);c.fillStyle=`rgba(60,30,10,${0.18*(1-0.6*h)})`;c.fill()}return}
 const sh=LK.palette.shadow,ox=-LK.lx*0.22,el=(x,y,rx,ry,a)=>{c.save();c.translate(x,y);c.scale(rx,ry);c.fillStyle=rad(0,0,1,hexA(sh,a),[0.55,hexA(sh,a*0.55)],hexA(sh,0));c.beginPath();c.arc(0,0,1,0,TAU);c.fill();c.restore()};
 const fx=P.legs.map(L=>L.a[0]+0.14*P.sy),cx=(fx[0]+fx[1])/2,hy=cl(P.y/0.4),sp=Math.abs(fx[0]-fx[1]);
 el(cx+ox,ANK+0.04+Math.max(P.legs[0].a[1],P.legs[1].a[1]),(0.62+sp*0.5)*(1-0.3*hy),0.13*(1-0.3*hy),0.2*(1-0.6*hy));
 for(const L of P.legs){const h=cl((L.lift+P.y)/0.3);el(L.a[0]+0.14*P.sy+ox*0.4,ANK+L.a[1]+L.lift+0.03,0.36*(1-0.35*h),0.065*(1-0.35*h),0.34*(1-0.7*h))}}
/* optional, OFF by default (look.charShade, 0..1): one soft, low-contrast shadow on the far side of the head and torso. No hard bands. */
function charShade(R){if(!(LK.on&&LK.charShade>0))return;const sg=LK.lx<0?1:-1;c.save();c.fillStyle=lin(sg*R*1.02,0,sg*R*0.15,0,LK.sh(0.17*LK.charShade),LK.sh(0));c.fillRect(-3,-4,6,8);c.restore()}

/* paper grain for the SET only: call grain(t) in draw() after the background and before the actors (k ≈ 0.03–0.06). Deterministic per frame. */
function grain(t,k){k=k===undefined?0.04:k;if(k<=0)return;const T=grainTiles(),f=Math.floor(t*24+1e-6);c.save();c.setTransform(1,0,0,1,0,0);c.globalAlpha*=Math.min(1,k*1.6);c.translate(-hash(f*1.7)*256,-hash(f*2.9)*256);c.fillStyle=c.createPattern(T[f%4],'repeat');c.fillRect(0,0,W+256,H+256);c.restore()}
/* ---------- finish: light wash + colour grade + vignette (device space, after the scene, before tag and captions) ---------- */
const _VIG={},_GR=[];
function vignetteCanvas(col,k){const key=col+k;if(_VIG[key])return _VIG[key];const o=document.createElement('canvas');o.width=W;o.height=H;const x=o.getContext('2d',{willReadFrequently:true});
 x.translate(W/2,H*0.47);x.scale(1,H/W*1.25);const g=x.createRadialGradient(0,0,W*0.28,0,0,W*0.66);g.addColorStop(0,hexA(col,0));g.addColorStop(0.55,hexA(col,k*0.35));g.addColorStop(1,hexA(col,k));x.fillStyle=g;x.fillRect(-W,-W,2*W,2*W);return _VIG[key]=o}
function grainTiles(){if(_GR.length)return _GR;for(let n=0;n<4;n++){const o=document.createElement('canvas');o.width=o.height=256;const x=o.getContext('2d',{willReadFrequently:true}),im=x.createImageData(256,256);
 for(let i=0;i<256*256;i++){const v=hash(i*0.731+n*91.7),w=hash(i*1.913+n*37.1)>0.5?255:0;im.data[i*4]=im.data[i*4+1]=im.data[i*4+2]=w;im.data[i*4+3]=Math.pow(v,3)*255|0}x.putImageData(im,0,0);_GR.push(o)}return _GR}
function finish(t){if(!LK.on)return;c.save();c.setTransform(1,0,0,1,0,0);
 if(LK.wash>0){const cx=W/2,cy=H/2,g=c.createLinearGradient(cx+LK.lx*W*0.62,cy+LK.ly*H*0.75,cx-LK.lx*W*0.1,cy-LK.ly*H*0.15);g.addColorStop(0,hexA(LK.lcol,Math.min(0.6,LK.wash)));g.addColorStop(1,hexA(LK.lcol,0));c.globalCompositeOperation='screen';c.fillStyle=g;c.fillRect(0,0,W,H);c.globalCompositeOperation='source-over'}
 if(LK.grade){const g=LK.grade,gr=c.createLinearGradient(0,0,0,H);gr.addColorStop(0,hexA(g.top,g.a));gr.addColorStop(0.38,hexA(g.top,0));gr.addColorStop(0.72,hexA(g.bottom,0));gr.addColorStop(1,hexA(g.bottom,g.a*0.8));c.fillStyle=gr;c.fillRect(0,0,W,H)}
 if(LK.vignette>0)c.drawImage(vignetteCanvas(LK.palette.shadow,Math.min(0.9,LK.vignette)),0,0);
 c.restore()}
