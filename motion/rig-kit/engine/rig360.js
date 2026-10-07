/* =====================================================================
   360° 2D RIG
   · skeleton lives in 3D (x: character's left, y: down, z: forward) and is projected with a yaw angle
   · flat parts stay 2D, but everything that sits ON the head / torso is stored by azimuth (degrees
     around the body, 0 = front) and slides, squashes and hides as the yaw changes
   · layer order (arms, legs, pack, back hair) is decided by depth after projection
   ===================================================================== */
const E={lin:k=>k,io:k=>k*k*(3-2*k),out:k=>1-Math.pow(1-k,3),in:k=>k*k,back:k=>{const s=2.2;k-=1;return k*k*((s+1)*k+s)+1}};
const frac=x=>x-Math.floor(x);
function Jg(t,CTg,dl,a,w,sin){const t0=frac((t-dl)/CTg)*CTg;let s=0;for(let j=0;j<4;j++){const u=t0+j*CTg;s+=Math.exp(-a*u)*(sin?Math.sin(w*u):Math.cos(w*u))}return s}
const GAIT={walk:{cy:0.8,str:1.12,lift:0.26,hip:1.46,lean:0.15,sw:0.62,bend:0.28,bsw:0.85,bounce:0.055},
            run:{cy:0.48,str:1.5,lift:0.46,hip:1.4,lean:0.36,sw:0.95,bend:1.25,bsw:0.5,bounce:0.1}};
const SPEED=g=>GAIT[g].str/(GAIT[g].cy/2);
function footG(q,g){q=frac(q);let x,y=0,ang;
 if(q<0.5){const u=q/0.5;x=g.str/2-g.str*u;ang=u<0.16?0.42*(1-sm(u/0.16)):u>0.66?-0.85*sm((u-0.66)/0.34):0}
 else{const u=(q-0.5)/0.5,e=u*u*(3-2*u);x=-g.str/2+g.str*e;y=g.lift*Math.sin(Math.PI*Math.pow(u,0.8));ang=lerp(-0.85,0.42,sm((u-0.2)/0.8))-0.3*Math.sin(Math.PI*cl(u/0.4))}
 const heel=Math.max(0,-ang)*0.3;return{x:x+Math.max(0,-ang)*0.1,y:y+heel,ang}}
function gaitPose(t,g){const CTg=g.cy/2,p=frac(t/g.cy),c4=Math.cos(4*Math.PI*p),j=(dl,a,w,s)=>Jg(t,CTg,dl,a,w,s);
 const lean=g.lean+0.05*Math.cos(4*Math.PI*p+0.6)+0.04*j(0.03,6,17,true);
 const arm=sg=>{const a=sg*g.sw*Math.cos(TAU*(p-0.05)),f=0.5+sg*0.5*Math.cos(TAU*(p-0.15));return{a,b:g.bend+g.bsw*f+0.12*j(0.1,6,18)}};
 return{p,hipY:g.hip-g.bounce*c4-0.05*j(0,7,20),hipDx:0.03*Math.sin(4*Math.PI*p),lean,fN:footG(p,g),fF:footG(p+0.5,g),aN:arm(-1),aF:arm(1),
  tl:1-0.06*j(0.02,7,20),headDy:0.05*j(0.05,6,18),hrot:lean*0.3+0.08*j(0.07,5,15,true),hsq:1-0.07*j(0.07,7,20),hat:-0.08*Math.max(0,j(0.13,5,16)),bob:0.07*j(0.11,5,16),sway:0.5*j(0.14,4,13,true)}}

/* ---------- 3D pose → projected joints ---------- */
const D2R=Math.PI/180,PITCH=0.16,HXS=0.14,SHX=0.47;
/* arm IK in 3D (character space): the elbow is pulled down, back and outward */
function ik3(S,T,side){const d=[T[0]-S[0],T[1]-S[1],T[2]-S[2]],L=Math.hypot(d[0],d[1],d[2])||1e-6,D=Math.max(Math.abs(UA-FA)+1e-3,Math.min(UA+FA-1e-3,L)),n=d.map(v=>v/L);
 const a1=(UA*UA-FA*FA+D*D)/(2*D),h=Math.sqrt(Math.max(0,UA*UA-a1*a1)),p=[side*0.35,0.55,-0.75],dot=p[0]*n[0]+p[1]*n[1]+p[2]*n[2];let q=[p[0]-n[0]*dot,p[1]-n[1]*dot,p[2]-n[2]*dot];const ql=Math.hypot(q[0],q[1],q[2])||1;q=q.map(v=>v/ql);
 return{el:[S[0]+n[0]*a1+q[0]*h,S[1]+n[1]*a1+q[1]*h,S[2]+n[2]*a1+q[2]*h],wr:[S[0]+n[0]*D,S[1]+n[1]*D,S[2]+n[2]*D]}}
/* q: yaw, headTurn, walk(0..1)+gait, hipY, lean, tl, y(jump), x/z(root on the ground)
      armR/armL = {a,b,ab,b2} angles | {hand:[X,Y,Z]} world target | {local:[x,y,z]} | {A,B,k} blend of two of those
      swR/swL walk-swing weight · waveR/waveL · cheer · clap · handR/handL · propR/propL · face · kick(wobble) */
function pose360(q,t){const sc=q.sc||1,g=GAIT[q.gait||'walk'],W=cl(q.walk===undefined?1:q.walk),wp=gaitPose(t/sc,g),cy=Math.cos(q.yaw),sy=Math.sin(q.yaw),sd=q.seed||0;
 const pr=p=>{const X=p[0]*cy+p[2]*sy,Z=-p[0]*sy+p[2]*cy;return[X,p[1]+Z*PITCH,Z]};
 const kw=q.kick||0,chr=q.cheer||0,ph=t*6.2+sd*9,hop=Math.abs(Math.sin(ph)),yj=(q.y||0)+chr*0.34*hop,br=Math.sin(t*2.3+sd*7)*(1-W),nod=q.nod||0;
 const hipY=lerp(q.hipY===undefined?1.49:q.hipY,wp.hipY,W)-chr*0.07*(1-hop),lean=lerp(q.lean===undefined?0.03:q.lean,wp.lean,W)+0.05*kw,TL=TL0*(q.tl||1)*lerp(1+0.012*br,wp.tl,W)*(1-0.045*kw)*(1-chr*0.04*Math.cos(2*ph));
 const hip=[0,-hipY,W*wp.hipDx],u=[0,-Math.cos(lean),Math.sin(lean)],sh=[0,hip[1]+u[1]*TL,hip[2]+u[2]*TL],hb=[0,sh[1]+u[1]*0.2+W*wp.headDy+0.03*kw+0.05*nod,sh[2]+u[2]*0.2+0.04];
 const leg=(sx,f,rz)=>{const fz=lerp(rz,f.x,W),fy=f.y*W,[k,e]=ik([hip[2],hip[1]],[fz,-(ANK+fy)],L1,L2,-1,1.12);return{h:pr([sx*HXS,hip[1],hip[2]]),k:pr([sx*HXS,k[1],k[0]]),a:pr([sx*HXS,e[1],e[0]]),ang:f.ang*W,lift:fy}};
 const L3=(a,b,k)=>[lerp(a[0],b[0],k),lerp(a[1],b[1],k),lerp(a[2],b[2],k)],mixJ=(A,B,k)=>({el:L3(A.el,B.el,k),wr:L3(A.wr,B.wr,k)});
 const arm=(side,wa,spec,sw,wave,hand,prop)=>{const s0=[side*SHX,sh[1]-u[1]*0.15,sh[2]-u[2]*0.15],d=(a,ab)=>[side*Math.sin(ab)*Math.cos(a),Math.cos(ab)*Math.cos(a),Math.sin(a)];
  const fk=(a,b,ab,b2)=>{const d1=d(a,ab),d2=d(a+b,ab+b2),el=[s0[0]+UA*d1[0],s0[1]+UA*d1[1],s0[2]+UA*d1[2]];return{el,wr:[el[0]+FA*d2[0],el[1]+FA*d2[1],el[2]+FA*d2[2]]}};
  const res=sp=>{if(!sp)return fk(0.02,0.2,0.1,0);if(sp.hand){const dX=sp.hand[0]-(q.x||0),dZ=sp.hand[2]-(q.z||0);return ik3(s0,[(dX*cy-dZ*sy)/sc,sp.hand[1]/sc+yj,(dX*sy+dZ*cy)/sc],side)}
   if(sp.local)return ik3(s0,[side*sp.local[0],s0[1]+sp.local[1],sp.local[2]],side);
   const ab=sp.ab===undefined?0.1:sp.ab,wv=wave*0.3*Math.sin(13*t);return Math.abs(ab)>0.8?fk(sp.a,sp.b||0,ab,(sp.b2||0)+wv):fk(sp.a,(sp.b||0)+wv,ab,sp.b2||0)};
  let J=spec&&spec.A!==undefined?mixJ(res(spec.A),res(spec.B),spec.k):res(spec);
  const mOf=sp=>{if(!sp||!sp.hand)return -1;const dX=sp.hand[0]-(q.x||0),dZ=sp.hand[2]-(q.z||0);return Math.hypot((dX*cy-dZ*sy)/sc-s0[0],sp.hand[1]/sc+yj-s0[1],(dX*sy+dZ*cy)/sc-s0[2])-(UA+FA)},miss=spec&&spec.A!==undefined?(spec.k>0.98?mOf(spec.B):-1):mOf(spec);
  if(chr>0)J=mixJ(J,fk(0.35,0.05,2.45+0.18*Math.sin(ph+(side>0?1.3:0)),0.2+0.25*Math.sin(2*ph+(side>0?1:0))),chr);
  if(q.clap>0)J=mixJ(J,ik3(s0,[side*(0.05+0.1*(0.5+0.5*Math.sin(15*t))),s0[1]+0.22,0.42],side),q.clap);
  if(W*sw>0)J=mixJ(J,fk(wa.a,wa.b,0.1,0),W*sw);
  const S=pr(s0),EL=pr(J.el),WR=pr(J.wr);return{s0:S,el:EL,wr:WR,side,Zm:(S[2]+EL[2]+WR[2])/3,hand:hand||(prop?'grip':'open'),prop,miss,shw:[(q.x||0)+sc*(s0[0]*cy+s0[2]*sy),sc*(s0[1]-yj),(q.z||0)+sc*(-s0[0]*sy+s0[2]*cy)],reach:sc*(UA+FA)}};
 const H=pr(hip),S=pr(sh),HB=pr(hb),dflt=(v,d)=>v===undefined?d:v;
 return{t:t,yaw:q.yaw,cy,sy,x:q.x||0,z:q.z||0,y:yj,hip:H,sh:S,head:HB,TL:Math.hypot(S[0]-H[0],S[1]-H[1]),trot:Math.atan2(S[0]-H[0],-(S[1]-H[1])),Wt:Math.hypot(0.43*cy,0.385*sy),
  legs:[leg(-1,wp.fN,0.03),leg(1,wp.fF,-0.03)],arms:[arm(-1,wp.aN,q.armR,dflt(q.swR,1),q.waveR||0,q.handR,q.propR),arm(1,wp.aF,q.armL,dflt(q.swL,1),q.waveL||0,q.handL,q.propL)],
  hrot:(W*wp.hrot+0.3*nod)*sy,hsq:lerp(1,wp.hsq,W)*(1-0.05*kw),headYaw:q.yaw+Math.max(-1.3,Math.min(1.3,q.headTurn||0)),hat:W*wp.hat-0.05*Math.max(0,kw),bob2:W*wp.bob+0.12*kw,sway:W*wp.sway+0.7*kw,face:q.face||{},propRot:q.propRot||0,steam:q.steam||0,fill:q.fill||0,W}}

/* ---------- azimuth helpers: where does something at angle f (deg) around a cylinder of radius R land? ---------- */
let _PS=0,_R=0.4;
const nrm=a=>{a=(a+Math.PI)%TAU;if(a<0)a+=TAU;return a-Math.PI};
function at(f,R,psi){const a=nrm(f*D2R+(psi===undefined?_PS:psi)),k=Math.cos(a);return k>0.03?{x:(R||_R)*Math.sin(a),k,a}:null}
function px(f,R,psi){const a=nrm(f*D2R+(psi===undefined?_PS:psi));return(R||_R)*Math.sin(Math.max(-Math.PI/2,Math.min(Math.PI/2,a)))}
function vis(f0,f1,R,psi){const p=psi===undefined?_PS:psi,m=nrm((f0+f1)/2*D2R+p),h=(f1-f0)/2*D2R,lo=Math.max(m-h,-Math.PI/2),hi=Math.min(m+h,Math.PI/2);return hi>lo?[(R||_R)*Math.sin(lo),(R||_R)*Math.sin(hi)]:null}
function panel(f0,f1,col,y,h){const v=vis(f0,f1);if(v)F(col,v[0],y,v[1]-v[0],h)}
function spot(f,y,r,col){const p=at(f);if(p){c.beginPath();c.ellipse(p.x,y,r*Math.max(0.3,p.k),r,0,0,TAU);c.fillStyle=col;c.fill()}}
function vline(f,y0,y1,w,col){const p=at(f);if(p)F(col||TONE,p.x-w*Math.max(0.35,p.k)/2,y0,w*Math.max(0.35,p.k),y1-y0)}

/* ---------- legs & shoes ---------- */
/* shoe: ONE outline that morphs continuously between the side shape (|sin ψ|→1) and the short front/back shape (sin ψ→0) */
function drawShoe3(a,ang,ch,fz,P){const s=ch.shoe,ty=s.type||'sneaker',col=dk(s.col,lerp(1,0.82,fz)),sole=dk(s.sole||'#FFFFFF',lerp(1,0.86,fz)),light=lum(s.col)>190,k=P.sy,ak=Math.abs(k),sg=k>=0?1:-1,top=ty==='boot'?-0.3:ty==='dress'?-0.09:-0.13;
 const S=ty==='dress'?[[-0.2,top],[-0.25,0.05],[-0.21,0.13],[0.5,0.13],[0.61,0.07],[0.27,-0.06],[0.15,top]]:[[-0.2,top],[-0.25,0.05],[-0.21,0.13],[0.46,0.13],[0.575,0.03],[0.31,-0.075],[0.15,top]],
  Fp=[[-0.165,top],[-0.185,0.03],[-0.16,0.13],[0.16,0.13],[0.185,0.03],[0.165,top],[0,top]],m=Math.max(ak,0.45),u=cl(ak/0.45),pts=S.map((q,i)=>[sg*lerp(Fp[i][0],q[0]*m,u),lerp(Fp[i][1],q[1],u)]),X=x=>sg*x*m,tS=cl((ak-0.3)/0.15),fr=P.cy>0;
 c.save();c.translate(a[0],a[1]);c.rotate(-ang*k);
 const out=()=>{c.beginPath();pts.forEach((q,i)=>i?c.lineTo(q[0],q[1]):c.moveTo(q[0],q[1]));c.closePath()};
 out();c.fillStyle=col;c.fill();c.strokeStyle=col;c.lineWidth=0.04;c.lineJoin='round';c.stroke();
 c.save();out();c.clip();const rct=(cc,x0,x1,y,h)=>F(cc,Math.min(X(x0),X(x1)),y,Math.abs(X(x1)-X(x0)),h),toeC=s.toe?dk(s.toe,lerp(1,0.86,fz)):'rgba(255,255,255,0.16)',heelC='rgba(70,30,10,0.14)';
 if(ty!=='dress'){c.globalAlpha=tS;rct(toeC,0.4,0.75,-0.2,0.4);rct(heelC,-0.4,-0.185,-0.4,0.6);c.globalAlpha=1-tS;F(fr?toeC:heelC,-0.3,-0.005,0.6,0.2);c.globalAlpha=1}
 if(ty==='sneaker'&&s.stripe){c.globalAlpha=tS;c.fillStyle=dk(s.stripe,lerp(1,0.86,fz));poly(X(-0.04),-0.05,X(0.05),-0.05,X(0.15),0.13,X(0.06),0.13)();c.fill();c.globalAlpha=1}
 if(ty==='boot'){F('rgba(255,255,255,0.18)',-0.6,-0.3,1.2,0.07);c.globalAlpha=tS;c.fillStyle=light?TONE:'rgba(255,255,255,0.55)';for(const[x,y]of[[0.13,-0.2],[0.17,-0.13],[0.22,-0.075]]){c.beginPath();c.arc(X(x),y,0.017,0,TAU);c.fill()}c.globalAlpha=1}
 if(ty==='dress'){c.fillStyle='rgba(255,255,255,0.2)';c.globalAlpha=tS;c.beginPath();c.ellipse(X(0.43),0.03,0.11*m,0.03,0.2*sg,0,TAU);c.fill();c.globalAlpha=(1-tS)*(fr?1:0);c.beginPath();c.ellipse(0,0.03,0.08,0.03,0,0,TAU);c.fill();c.globalAlpha=1}
 c.restore();
 if(ty==='sneaker'){const lc=light?TONE:'rgba(255,255,255,0.8)';c.globalAlpha=tS;line(()=>{c.beginPath();c.moveTo(X(0.165),-0.085);c.lineTo(X(0.205),-0.128);c.moveTo(X(0.225),-0.07);c.lineTo(X(0.262),-0.11)},0.022,lc);
  c.globalAlpha=(1-tS)*(fr?1:0);line(()=>{c.beginPath();c.moveTo(-0.05,-0.09);c.lineTo(0.05,-0.09);c.moveTo(-0.05,-0.05);c.lineTo(0.05,-0.05)},0.02,lc);c.globalAlpha=1}
 const xs=pts.map(q=>q[0]),x0=Math.min(...xs)-0.035,x1=Math.max(...xs)+0.035;
 if(ty==='dress'){shape(rr(x0,0.125,x1-x0,0.045,0.02),sole);c.globalAlpha=tS;const hx=Math.min(X(-0.26),X(-0.06));shape(rr(hx,0.09,Math.abs(X(-0.06)-X(-0.26)),0.08,0.02),sole);c.globalAlpha=1}
 else shape(rr(x0,ty==='boot'?0.075:0.09,x1-x0,ty==='boot'?0.095:0.08,0.035),sole);
 c.restore()}
const mid2=(a,b)=>[(a[0]+b[0])/2,(a[1]+b[1])/2],five=p=>[p[0],mid2(p[0],p[1]),p[1],mid2(p[1],p[2]),p[2]];
/* small fold marks on the inside of a bent joint (they grow with the bend) */
function crease(a,j,b,w,col){const d1=[a[0]-j[0],a[1]-j[1]],d2=[b[0]-j[0],b[1]-j[1]],l1=Math.hypot(d1[0],d1[1])||1,l2=Math.hypot(d2[0],d2[1])||1,ux=d1[0]/l1+d2[0]/l2,uy=d1[1]/l1+d2[1]/l2,ul=Math.hypot(ux,uy),al=cl((ul-0.3)/0.55)*cl(Math.min(l1,l2)/0.25);if(al<0.02)return;
 const an=Math.atan2(uy,ux),g=c.globalAlpha;c.globalAlpha=g*al;line(()=>{c.beginPath();for(const da of[-0.5,0.5]){const cx=Math.cos(an+da),sx=Math.sin(an+da);c.moveTo(j[0]+cx*w*0.5,j[1]+sx*w*0.5);c.lineTo(j[0]+cx*w*0.14,j[1]+sx*w*0.14)}},0.02,col||'rgba(70,30,10,0.2)');c.globalAlpha=g}
const PANTW={std:[0.36,0.34,0.3,0.275,0.25],wide:[0.37,0.355,0.33,0.315,0.3],slim:[0.35,0.32,0.275,0.24,0.215]};
function drawLeg3(P,L,ch){const p3=[L.h,L.k,L.a],pts=five(p3),fz=cl(-L.h[2]/0.13),f=lerp(1,0.82,fz),fs=lerp(1,0.86,fz),pn=ch.pants,pc=dk(pn.col,f);
 if(pn.type==='shorts'){const ws=[0.29,0.275,0.215,0.228,0.158],wp=[0.38,0.37,0.3];limb(pts,ws,dk(ch.skin,fs),true,false);
  if(ch.sock){bandOf(pts,ws,0.78,1,dk(ch.sock,fs),1.12);if(ch.sockStripe)bandOf(pts,ws,0.82,0.86,dk(ch.sockStripe,fs),1.12)}
  {const[Q,Wd]=part(p3,wp,0,0.4);limb(Q,Wd,pc,true,false)}bandOf(p3,wp,0.35,0.4,dk(pn.col,f*0.86));bandOf(p3,wp,0,0.19,SHC)}
 else{const ws=PANTW[pn.fit||'std'];limb(pts,ws,pc,true,false);crease(L.h,L.k,L.a,ws[2]);if(pn.cuff)bandOf(pts,ws,0.86,1,dk(pn.cuff,f),1.09);else bandOf(pts,ws,0.955,1,'rgba(70,30,10,0.13)');bandOf(pts,ws,0,0.19,SHC)}
 drawShoe3(L.a,L.ang,ch,fz,P)}

/* ---------- arms & hands ---------- */
const HANDS={open:[0.125,0.15,0.14,0.105],grip:[0.07,0.085,0.08,0.065],point:[0.21,0.075,0.07,0.06],wave:[0.16,0.19,0.18,0.14]};
function hand3(A,col,lc,st,sy){const dx=A.wr[0]-A.el[0],dy=A.wr[1]-A.el[1],l=Math.hypot(dx,dy)||1;c.save();c.translate(A.wr[0]+dx/l*0.02,A.wr[1]+dy/l*0.02);c.rotate(Math.atan2(dy,dx));
 const L0=HANDS[st]||HANDS.open,mm=cl(0.5+sy*2.5),L=L0.map((v,i)=>lerp(L0[3-i],v,mm)),th=cl(Math.abs(sy)*2.5),sg=sy>=0?1:-1,Y=[-0.074,-0.025,0.024,0.073];c.fillStyle=col;c.beginPath();c.roundRect(-0.05,-0.1,0.21,0.2,[0.05,0.07,0.07,0.05]);c.fill();
 for(let i=0;i<4;i++){c.beginPath();c.roundRect(0.08,Y[i]-0.027,L[i]+0.03,0.054,0.027);c.fill()}c.beginPath();c.ellipse(0.075,-sg*lerp(0.03,0.105,th),0.088*lerp(0.5,1,th),0.046,-0.5*sg,0,TAU);c.fill();
 line(()=>{c.beginPath();for(let i=0;i<3;i++){const y=(Y[i]+Y[i+1])/2;c.moveTo(0.13,y);c.lineTo(0.08+Math.min(L[i],L[i+1])+0.012,y)}},0.012,lc);c.restore()}
/* build = [half-width, half-depth, forward offset] at chest, waist and hem */
const BUILD={std:[[0.43,0.385,0],[0.4,0.355,0],[0.385,0.34,0]],slim:[[0.415,0.37,0.012],[0.355,0.31,0],[0.39,0.345,-0.004]],broad:[[0.452,0.39,0.012],[0.408,0.36,0],[0.385,0.34,0]],round:[[0.43,0.39,0.012],[0.435,0.425,0.05],[0.405,0.39,0.032]]};
const WAISTF=0.64,SOFT={tee:1,stripe:1,hoodie:1,cardigan:1,chef:1,apron:1};
const bodyP=(P,ch)=>{const B=BUILD[ch.build||'std'],y0=-P.TL-0.03,y1=0.13,E=B.map(([a,b,z])=>{const e=Math.hypot(a*P.cy,b*P.sy),m=z*P.sy;return[m-e,m+e]}),C=E[0],Wa=E[1],He=E[2],yC=y0+0.34,yW=y0+(y1-y0)*WAISTF,yH=y1-0.06,mC=(C[0]+C[1])/2,eC=(C[1]-C[0])/2,mH=(He[0]+He[1])/2,eH=(He[1]-He[0])/2;
 return sub=>{if(!sub)c.beginPath();c.moveTo(He[0],yH);c.lineTo((He[0]+Wa[0])/2,(yH+yW)/2);c.quadraticCurveTo(Wa[0],yW,(Wa[0]+C[0])/2,(yW+yC)/2);c.lineTo(C[0],yC);c.bezierCurveTo(C[0],y0+0.1,mC-eC*0.78,y0,mC-eC*0.36,y0);c.lineTo(mC+eC*0.36,y0);c.bezierCurveTo(mC+eC*0.78,y0,C[1],y0+0.1,C[1],yC);c.lineTo((Wa[1]+C[1])/2,(yW+yC)/2);c.quadraticCurveTo(Wa[1],yW,(He[1]+Wa[1])/2,(yH+yW)/2);c.lineTo(He[1],yH);c.quadraticCurveTo(He[1],y1,mH+eH*0.82,y1);c.lineTo(mH-eH*0.82,y1);c.quadraticCurveTo(He[0],y1,He[0],yH);c.closePath()}};
function drawArm3(P,A,ch,inFront){const p3=[A.s0,A.el,A.wr],pts=five(p3),T=ch.top,fz=cl(-A.s0[2]/0.3),f=lerp(1,0.82,fz),sk=dk(ch.skin,lerp(1,0.86,fz)),tc=dk(T.sleeve||T.col,f),hc=ch.glove?dk(ch.glove,f):sk,lc=ch.glove?'rgba(255,255,255,0.25)':ch.nc;
 const long=T.arms==='long',ws=long?[0.25,0.238,0.205,0.2,0.182]:[0.2,0.196,0.165,0.168,0.138];
 {const shk=cl((A.s0[2]-0.03)/0.2);if(inFront&&shk>0.02){/* arms in front of the body drop a shadow on it */
  c.globalAlpha*=shk;const m=c.getTransform();c.save();c.translate(P.hip[0],P.hip[1]);c.rotate(P.trot);bodyP(P,ch)();c.clip();c.setTransform(m);limb(pts.map(q=>[q[0]-0.05*Math.sign(P.sy||1),q[1]+0.035]),ws,SHC,true,true);c.restore();c.globalAlpha/=shk}}
 if(long){limb(pts,ws,tc,true,false);crease(A.s0,A.el,A.wr,ws[2]);if(T.sleeveStripe)bandOf(pts,ws,0.2,0.26,dk(T.sleeveStripe,f));bandOf(pts,ws,0.88,1,T.cuff?dk(T.cuff,f):dk(T.sleeve||T.col,f*0.88),1.08)}
 else{limb(pts,ws,sk,true,true);if(T.arms==='short'){const w2=[0.27,0.255,0.2],[Q,Wd]=part(p3,w2,0,0.4);limb(Q,Wd,tc,true,false);bandOf(p3,w2,0.35,0.4,dk(T.sleeve||T.col,f*0.86))}if(ch.watch&&A.side<0)bandOf(pts,ws,0.88,0.95,dk(ch.watch,f),1.12)}
 drawProp3(P,A);hand3(A,hc,lc,A.hand,P.sy)}
function cupShape(t,steam){if(steam)for(let i=0;i<2;i++){const ph=((t*0.9+i*0.5)%1+1)%1,x0=-0.05+i*0.1;c.globalAlpha=0.6*Math.sin(Math.PI*ph);line(()=>{c.beginPath();for(let k=0;k<=6;k++){const yy=-0.3-ph*0.22-k*0.04,xx=x0+0.035*Math.sin(k*1.1+ph*6+i*2);k?c.lineTo(xx,yy):c.moveTo(xx,yy)}},0.028,'#FFFFFF');c.globalAlpha=1}
   shape(poly(-0.13,-0.2,0.13,-0.2,0.1,0.18,-0.1,0.18),'#FFFFFF');c.save();poly(-0.13,-0.2,0.13,-0.2,0.1,0.18,-0.1,0.18)();c.clip();F('#C98B5A',-0.2,-0.09,0.4,0.15);F('rgba(70,30,10,0.12)',-0.2,-0.3,0.08,0.6);c.restore();shape(circ(0.005,-0.015,0.04),'#FFFFFF');shape(rr(-0.16,-0.275,0.32,0.085,0.03),'#8B5A3C');shape(rr(-0.1,-0.31,0.2,0.05,0.02),'#8B5A3C')}
/* base prop shapes, drawn around their own centre (use them for things lying around, too) */
function caseShape(w){w=w||0.8;line(()=>{c.beginPath();c.moveTo(-0.11,-0.2);c.lineTo(-0.11,-0.31);c.lineTo(0.11,-0.31);c.lineTo(0.11,-0.2)},0.05,'#5E3B25');const b=rr(-w/2,-0.22,w,0.5,0.07);shape(b,'#8A5A3B');c.save();b();c.clip();F('#74492E',-0.4,-0.22,0.8,0.16);F('rgba(70,30,10,0.16)',-0.4,0.2,0.8,0.1);c.restore();if(w>0.6){shape(rr(-w*0.31,-0.1,0.07,0.09,0.015),'#E8C25A');shape(rr(w*0.225,-0.1,0.07,0.09,0.015),'#E8C25A')}}
function parcelShape(){const b=rr(-0.36,-0.3,0.72,0.54,0.04);shape(b,'#D9A066');c.save();b();c.clip();F('#C48B4F',-0.4,-0.3,0.8,0.12);F('#F1E4C8',-0.07,-0.3,0.14,0.6);c.restore();shape(rr(0.1,0.0,0.2,0.14,0.02),'#FFFFFF');F('rgba(40,30,30,0.6)',0.13,0.04,0.14,0.02);F('rgba(40,30,30,0.6)',0.13,0.08,0.09,0.02)}
function bagShape(){line(()=>{c.beginPath();c.moveTo(-0.13,-0.1);c.quadraticCurveTo(0,-0.42,0.13,-0.1)},0.04,'#8A4F6A');const b=rr(-0.26,-0.14,0.52,0.4,[0.06,0.06,0.14,0.14]);shape(b,'#C76D94');c.save();b();c.clip();F('#A9567B',-0.3,-0.14,0.6,0.13);c.restore();shape(circ(0,-0.01,0.035),'#F2D27A')}
const PROPS={};/* extra props register here: PROPS.name=(P,ux,uy)=>{...} drawn at the grip point */
function drawProp3(P,A){const pr=A.prop;if(!pr)return;const dx=A.wr[0]-A.el[0],dy=A.wr[1]-A.el[1],l=Math.hypot(dx,dy)||1;c.save();c.translate(A.wr[0]+dx/l*0.12,A.wr[1]+dy/l*0.12);
 if(PROPS[pr])PROPS[pr](P,dx/l,dy/l,A);
 if(pr==='cup'){c.rotate(P.propRot);c.translate(0,-0.1);cupShape(P.t,P.steam)}
 if(pr==='case'){c.translate(0,0.3);caseShape(lerp(0.3,0.8,Math.abs(P.sy)))}
 if(pr==='parcel'){c.translate(0,-0.06);parcelShape()}
 if(pr==='bag'){c.rotate(P.sway*0.25);c.translate(0,0.26);bagShape()}
 c.restore()}

/* ---------- torso: clothing is stored by azimuth and re-projected for every yaw ---------- */
function drawNeck3(P,ch){const a=[P.sh[0],P.sh[1]+0.12],b=[P.head[0],P.head[1]-0.14];tube([a,b],0.5,ch.skin,'butt');
 {const na=cl((Math.cos(P.headYaw)+0.5)/0.35);if(na>0){const dx=b[0]-a[0],dy=b[1]-a[1],l=Math.hypot(dx,dy)||1,nx=-dy/l*0.25,ny=dx/l*0.25;c.save();polyPath([[a[0]+nx,a[1]+ny],[b[0]+nx,b[1]+ny],[b[0]-nx,b[1]-ny],[a[0]-nx,a[1]-ny]]);c.closePath();c.clip();headXf3(P,ch);c.translate(0,0.09);headPath();c.globalAlpha*=na;c.fillStyle=SHC;c.fill();c.restore()}}}
function drawTorso3(P,ch){c.save();c.translate(P.hip[0],P.hip[1]);c.rotate(P.trot);const TL=P.TL,T=ch.top,y0=-TL-0.03,w=P.Wt,body=bodyP(P,ch),yW=y0+(0.13-y0)*WAISTF,D=k=>dk(T.col,k),D2=k=>dk(T.col2||T.col,k);_PS=P.yaw;_R=w;
 shape(body,T.type==='vest'?T.col2:T.col);c.save();body();c.clip();
 switch(T.type){
 case'apron':panel(-58,58,T.col2,-TL*0.66,TL+0.4);F(T.col2,-1,-0.3,2,0.05);vline(-15,y0,-TL*0.66,0.055,T.col2);vline(15,y0,-TL*0.66,0.055,T.col2);panel(8,46,D2(0.86),-0.3,0.2);spot(-26,-TL*0.5,0.05,'#FFFFFF');
  {const p=at(180);if(p){shape(circ(p.x,-0.275,0.055),T.col2);shape(poly(p.x-0.02,-0.26,p.x-0.12*p.k,-0.08,p.x-0.05*p.k,-0.07),T.col2);shape(poly(p.x+0.02,-0.26,p.x+0.12*p.k,-0.08,p.x+0.05*p.k,-0.07),T.col2)}}break;
 case'jacket':if(T.band)F(T.band,-1,-TL*0.6,2,0.07);panel(-13,13,T.col2,y0-0.1,TL+0.5);vline(-13,y0,0.2,0.022);vline(13,y0,0.2,0.022);for(const s of[1,-1]){const v=vis(s*42-13,s*42+13);if(v)shape(rr(v[0],-0.3,v[1]-v[0],0.04,0.02),TONE)}if(T.hem)F(T.hem,-1,0.02,2,0.2);break;
 case'cardigan':panel(-15,15,T.col2,y0-0.1,TL+0.5);panel(-22,-15,D(0.86),y0-0.1,TL+0.5);panel(15,22,D(0.86),y0-0.1,TL+0.5);panel(30,58,D(0.88),-0.32,0.24);panel(-58,-30,D(0.88),-0.32,0.24);for(const y of[-TL*0.7,-TL*0.46,-TL*0.22])spot(-18.5,y,0.022,'rgba(70,30,10,0.4)');
  {const p=at(42);if(p){for(let i=0;i<5;i++){c.beginPath();c.ellipse(p.x+0.045*p.k*Math.cos(i*TAU/5),y0+0.3+0.045*Math.sin(i*TAU/5),0.03*Math.max(0.4,p.k),0.03,0,0,TAU);c.fillStyle='#F7A8C4';c.fill()}spot(42,y0+0.3,0.025,'#F2D27A')}}break;
 case'raincoat':vline(0,y0,0.2,0.022);for(const y of[-TL*0.72,-TL*0.48,-TL*0.24])spot(9,y,0.026,'rgba(70,30,10,0.4)');panel(30,60,D(0.86),-0.32,0.07);panel(-60,-30,D(0.86),-0.32,0.07);F(D(0.9),-1,0.04,2,0.2);break;
 case'vest':F(D2(0.8),-1,0.03,2,0.2);panel(28,60,D2(0.88),-0.34,0.22);panel(-60,-28,D2(0.88),-0.34,0.22);panel(28,60,D2(0.78),-0.34,0.06);panel(-60,-28,D2(0.78),-0.34,0.06);panel(-17,17,T.col,y0-0.1,TL+0.5);vline(-17,y0,0.2,0.02);vline(17,y0,0.2,0.02);break;
 case'chef':panel(-78,78,'#EEE9E1',-0.3,0.6);F('rgba(70,30,10,0.14)',-1,-0.3,2,0.03);vline(-9,y0+0.1,-0.3,0.018);for(const f of[-18,18])for(const y of[-TL*0.78,-TL*0.58])spot(f,y,0.024,'rgba(70,30,10,0.4)');break;
 case'hoodie':{const v=vis(-44,44);if(v)shape(rr(v[0],-0.36,v[1]-v[0],0.27,0.08),D(lum(T.col)>90?0.9:1.25));if(T.hem)F(T.hem,-1,-0.02,2,0.2);vline(-9,y0+0.06,y0+0.3,0.024,'#FFFFFF');vline(9,y0+0.08,y0+0.28,0.024,'#FFFFFF')}break;
 case'stripe':c.fillStyle=T.col2;for(let y=-TL+0.12;y<0.1;y+=0.2)c.fillRect(-1,y,2,0.09);spot(24,-0.2,0.04,'#F2B705');spot(-34,-0.3,0.028,'#E5484D');spot(50,-0.36,0.025,'#18B7A0');break;
 case'tee':panel(68,112,D(0.86),y0-0.1,TL+0.5);panel(-112,-68,D(0.86),y0-0.1,TL+0.5);{const v=vis(-30,30),p=at(0);if(v){shape(rr(v[0],-TL*0.66,v[1]-v[0],0.24,0.03),'#FFFFFF');if(p){const k=Math.max(0.35,p.k),y=-TL*0.66+0.07;F('rgba(40,30,30,0.75)',p.x-0.075*k,y,0.035*k,0.11);F('rgba(40,30,30,0.75)',p.x-0.01*k,y,0.085*k,0.035);F('rgba(40,30,30,0.75)',p.x+0.045*k,y,0.035*k,0.11)}}}F(D(0.86),-1,0.06,2,0.1);break;
 case'suit':if(Math.cos(P.yaw)>-0.3){const xl=px(-15),xr=px(15),x0=px(0),p0=at(0),k0=p0?Math.max(0.3,p0.k):0.3;shape(poly(xl,y0-0.02,xr,y0-0.02,x0,y0+0.66),T.col2);
   if(p0){shape(poly(x0-0.05*k0,y0+0.04,x0+0.05*k0,y0+0.04,x0+0.06*k0,y0+0.5,x0,y0+0.6,x0-0.06*k0,y0+0.5),T.tie||'#D64545');shape(poly(x0-0.07*k0,y0+0.03,x0+0.07*k0,y0+0.03,x0+0.045*k0,y0+0.14,x0-0.045*k0,y0+0.14),dk(T.tie||'#D64545',0.82))}
   for(const s of[1,-1])if(at(s*17))shape(poly(px(s*15),y0-0.02,x0,y0+0.66,(x0+px(s*8))/2,y0+0.56,px(s*30),y0+0.14),D(1.22));
   vline(0,y0+0.66,0.2,0.02);spot(-4,y0+0.75,0.024,'rgba(0,0,0,0.35)');spot(-4,y0+0.93,0.024,'rgba(0,0,0,0.35)');{const v=vis(24,42);if(v&&v[1]-v[0]>0.01)shape(poly(v[0],y0+0.335,v[0]+(v[1]-v[0])*0.45,y0+0.3,v[1],y0+0.33,v[1],y0+0.375,v[0],y0+0.375),'#FFFFFF')}}
  for(const s of[1,-1]){const v=vis(s*48-12,s*48+12);if(v)shape(rr(v[0],-0.26,v[1]-v[0],0.035,0.015),TONE)}vline(180,-0.22,0.2,0.02);break;
 case'overall':F(T.col2,-1,-TL*0.42,2,TL);panel(-33,33,T.col2,-TL*0.8,TL);panel(-13,13,D2(0.86),-TL*0.66,0.17);
  for(const s of[1,-1]){const a=at(s*25),b=at(s*33);if(a&&b){line(()=>{c.beginPath();c.moveTo(a.x,-TL*0.78);c.lineTo(b.x,y0)},0.1*Math.max(0.4,a.k),T.col2);spot(s*25,-TL*0.75,0.036,'#F4D35E')}
   const e=at(180+s*22),g=at(180+s*33);if(e&&g)line(()=>{c.beginPath();c.moveTo(e.x,-TL*0.42);c.lineTo(g.x,y0)},0.1*Math.max(0.4,e.k),T.col2);const v=vis(s*55-13,s*55+13);if(v)shape(rr(v[0],-0.28,v[1]-v[0],0.2,0.03),D2(0.88))}break;}
 /* cloth folds at the waist (they travel round with the body) */
 if(SOFT[T.type])for(const s of[1,-1]){const p=at(s*68);if(p){c.globalAlpha=cl(p.k*1.8);line(()=>{c.beginPath();c.moveTo(p.x+s*0.03,yW-0.075);c.quadraticCurveTo(p.x-s*0.03*p.k,yW-0.03,p.x-s*0.1*p.k,yW-0.02);c.moveTo(p.x+s*0.03,yW+0.04);c.quadraticCurveTo(p.x-s*0.02*p.k,yW+0.075,p.x-s*0.065*p.k,yW+0.08)},0.02,'rgba(70,30,10,0.15)');c.globalAlpha=1}}
 if(ch.pack)for(const s of[1,-1]){const a=at(s*33),b=at(s*62);if(a)line(()=>{c.beginPath();c.moveTo(a.x,y0+0.03);c.quadraticCurveTo(a.x+(b?(b.x-a.x)*0.2:0),-TL*0.6,b?b.x:px(s*62),-TL*0.3)},0.08*Math.max(0.5,a.k),dk(ch.pack.col,0.8))}
 /* one-step form shade: light comes from the top-left */
 c.save();c.beginPath();c.rect(-2,-3,4,5);c.translate(-0.035,-0.045);body(true);c.fillStyle='rgba(70,30,10,0.085)';c.fill('evenodd');c.restore();
 c.restore();
 /* open neckline with a rib band for tops without a collar */
 if(!T.collar&&!ch.scarf&&!ch.towel&&T.type!=='chef'){const fr=cl(0.5+0.62*P.cy),ry=lerp(0.03,0.105,fr),nk=()=>{c.beginPath();c.ellipse(0,y0-0.006,0.262,ry,0,0,Math.PI)};shape(nk,ch.skin);c.save();nk();c.clip();F(SHC,-0.3,y0-0.02,0.6,0.035+0.03*fr);c.restore();line(nk,0.036,T.neck||D(lum(T.col)>90?0.84:1.35))}
 /* collar wings sit at ±24°, the back of the collar shows from behind */
 if(T.collar){for(const s of[1,-1]){const p=at(s*24,0.33);if(p){const k=Math.max(0.3,p.k);lifted(poly(p.x+s*0.13*k,y0-0.07,p.x-s*0.1*k,y0-0.01,p.x-s*0.03*k,y0+0.15,p.x+s*0.14*k,y0+0.03),T.collar)}}const v=vis(125,235,0.3);if(v)lifted(rr(v[0],y0-0.07,v[1]-v[0],0.1,0.03),T.collar)}
 if(ch.scarf){lifted(rr(-0.25,y0-0.1,0.5,0.15,0.07),ch.scarf);const p=at(0);if(p){const k=Math.max(0.35,p.k),x=p.x*0.6;lifted(poly(x,y0,x+0.18*k,y0+0.2+P.sway*0.04,x+0.05*k,y0+0.24,x-0.04*k,y0+0.05),ch.scarf);shape(poly(x,y0,x-0.05*k,y0+0.24,x-0.13*k,y0+0.19,x-0.07*k,y0+0.02),dk(ch.scarf,0.88))}}
 if(ch.towel){lifted(rr(-0.26,y0-0.1,0.52,0.16,0.08),ch.towel);const p=at(26);if(p){c.save();c.translate(p.x*0.62,y0);c.rotate(P.sway*0.12);const k=Math.max(0.4,p.k);lifted(rr(-0.065*k,0,0.13*k,0.34,0.04),ch.towel);F('#7EC8E3',-0.065*k,0.25,0.13*k,0.035);c.restore()}}
 c.restore()}
function drawPack3(P,ch,front){const k=ch.pack;if(!k)return;c.save();c.translate(P.hip[0],P.hip[1]);c.rotate(P.trot);if(front){const v=vis(118,242,P.Wt+0.55,P.yaw);if(!v){c.restore();return}c.beginPath();c.rect(v[0],-3,v[1]-v[0],4);c.clip()}
 c.translate(0,P.bob2);const TL=P.TL,ac=Math.abs(P.cy),box=k.type==='box',wd=box?lerp(0.66,0.82,ac):lerp(0.5,0.68,ac),cx=-(P.Wt+wd/2)*P.sy*(1-0.25*ac);
 if(box){const b=rr(cx-wd/2,-TL-0.04,wd,0.76,0.08);shape(b,k.col);c.save();b();c.clip();F(dk(k.col,0.84),cx-1,-TL-0.04,2,0.2);F('#FFFFFF',cx-1,-TL+0.42,2,0.07);c.restore();if(P.cy<0.5){shape(circ(cx,-TL+0.3,0.1),'#FFFFFF');shape(poly(cx-0.04,-TL+0.25,cx+0.05,-TL+0.3,cx-0.04,-TL+0.35),k.col)}}
 else{if(k.mat){shape(rr(cx-wd*0.6,-TL-0.12,wd*1.2,0.2,0.1),k.mat);for(const s of[1,-1])F(dk(k.col,0.7),cx+s*wd*0.3-0.018,-TL-0.12,0.035,0.2)}
  const b=rr(cx-wd/2,-TL+0.06,wd,0.7,0.18);shape(b,k.col);c.save();b();c.clip();line(()=>{c.beginPath();c.moveTo(cx-wd/2,-TL+0.3);c.quadraticCurveTo(cx,-TL+0.22,cx+wd/2,-TL+0.3)},0.02);c.restore();
  const pw=lerp(0.2,0.4,ac),pxo=cx-(P.sy*(1-ac))*(wd/2+0.02);shape(rr(pxo-pw/2,-TL+0.42,pw,0.27,0.07),k.col2||dk(k.col,0.82));F('rgba(70,30,10,0.2)',pxo-pw/2,-TL+0.5,pw,0.02);
  if(k.charm){c.save();c.translate(cx-wd*0.3*(P.sy>=0?1:-1),-TL+0.72);c.rotate(P.sway*0.5);line(()=>{c.beginPath();c.moveTo(0,0);c.lineTo(0,0.1)},0.015,'#888888');shape(circ(0,0.14,0.05),k.charm);c.restore()}}
 c.restore()}

/* ---------- head: features live on a cylinder (azimuth 0 = nose) ---------- */
const HW=0.42,EY=-0.67,HS=1.1,RH=0.475;
/* the head outline follows the yaw: the chin moves toward the face side, the jaw on the back side cuts in toward the nape */
let _hs=0,_hj=0.24;
function headSub(){const s=_hs,cx=0.055*s,J=sd=>{const fs=sd*s,bk=Math.max(0,-fs),fr=Math.max(0,fs),y=-0.36-0.09*bk+0.02*fr;return{y,c1:y+lerp(0.23,0.11,bk)+0.02*fr,c2:cx+sd*(_hj-0.07*bk+0.035*fr)}},L=J(-1),R=J(1);
 c.moveTo(-HW,L.y);c.lineTo(-HW,-0.98);c.bezierCurveTo(-HW,-1.18,-0.3,-1.3,-0.1,-1.3);c.lineTo(0.1,-1.3);c.bezierCurveTo(0.3,-1.3,HW,-1.18,HW,-0.98);c.lineTo(HW,R.y);c.bezierCurveTo(HW,R.c1,R.c2,0,cx,0);c.bezierCurveTo(L.c2,0,-HW,L.c1,-HW,L.y);c.closePath()}
const headPath=()=>{c.beginPath();headSub()};
function headXf3(P,ch){_hs=Math.sin(P.headYaw);_hj=ch.jaw||0.24;const hd=ch.hd||1;c.translate(P.head[0],P.head[1]);c.rotate(P.hrot);c.scale(HS*hd/Math.sqrt(P.hsq),HS*hd*P.hsq)}
const pw=pts=>f=>{for(let i=1;i<pts.length;i++)if(f<=pts[i][0]){const a=pts[i-1],b=pts[i];return lerp(a[1],b[1],(f-a[0])/((b[0]-a[0])||1))}return pts[pts.length-1][1]};
/* hairline: height of the lower edge of the hair for every azimuth around the head */
const HL={
 part:pw([[-180,-0.13],[-128,-0.16],[-100,-0.46],[-82,-0.7],[-62,-0.73],[-48,-0.93],[-34,-0.81],[-22,-0.97],[-6,-0.83],[6,-1.0],[20,-0.87],[26,-1.06],[46,-1.02],[52,-0.93],[62,-0.73],[82,-0.7],[100,-0.46],[128,-0.16],[180,-0.13]]),
 bang:pw([[-180,-0.13],[-128,-0.16],[-100,-0.46],[-82,-0.7],[-66,-0.72],[-60,-0.93],[0,-0.89],[60,-0.93],[66,-0.72],[82,-0.7],[100,-0.46],[128,-0.16],[180,-0.13]]),
 sweep:pw([[-180,-0.13],[-128,-0.16],[-100,-0.46],[-82,-0.7],[-64,-0.74],[-58,-0.86],[-20,-0.98],[20,-1.04],[45,-1.02],[58,-0.93],[64,-0.74],[82,-0.7],[100,-0.46],[128,-0.16],[180,-0.13]]),
 arch:pw([[-180,-0.13],[-128,-0.16],[-95,-0.5],[-62,-0.56],[-55,-0.62],[-40,-0.9],[-20,-1.04],[0,-1.09],[20,-1.04],[40,-0.9],[55,-0.62],[62,-0.56],[95,-0.5],[128,-0.16],[180,-0.13]]),
 long:pw([[-180,0.3],[-100,0.3],[-92,-0.5],[-62,-0.56],[-55,-0.62],[-40,-0.9],[-20,-1.04],[0,-1.09],[20,-1.04],[40,-0.9],[55,-0.62],[62,-0.56],[92,-0.5],[100,0.3],[180,0.3]]),
 perm:pw([[-180,-0.15],[-128,-0.18],[-100,-0.48],[-82,-0.74],[-62,-0.78],[-56,-1.0],[56,-1.0],[62,-0.78],[82,-0.74],[100,-0.48],[128,-0.18],[180,-0.15]])};
function hairSub(style,psi){const h=HL[style]||HL.part,N=60;for(let i=0;i<=N;i++){const a=-Math.PI/2+Math.PI*i/N,f=nrm(a-psi)/D2R,y=h(f),x=Math.max(-HW-0.012,Math.min(HW+0.012,RH*Math.sin(a)));i?c.lineTo(x,y):c.moveTo(x,y)}
 c.lineTo(RH,-0.98);c.bezierCurveTo(0.5,-1.26,0.3,-1.4,0,-1.4);c.bezierCurveTo(-0.3,-1.4,-0.5,-1.26,-RH,-0.98);c.closePath()}
function beardSub(psi){const N=40;for(let i=0;i<=N;i++){const a=-Math.PI/2+Math.PI*i/N,f=Math.abs(nrm(a-psi)/D2R),x=0.47*Math.sin(a),y=f>108?0.2:lerp(-0.365,-0.6,Math.pow(cl(f/88),1.5));i?c.lineTo(x,y):c.moveTo(x,y)}c.lineTo(0.6,0.3);c.lineTo(-0.6,0.3);c.closePath()}
const dome=(ry,y0)=>()=>{c.beginPath();c.moveTo(-0.6,y0);c.bezierCurveTo(-0.62,y0-ry*1.3,0.62,y0-ry*1.3,0.6,y0);c.closePath()};
const HATSH={beanie:rr(-0.63,-0.36,1.26,0.2,0.07),cap:rr(-0.6,-0.5,1.2,0.3,0),capBack:rr(-0.6,-0.5,1.2,0.3,0),bucket:poly(-0.62,-0.3,0.62,-0.3,0.9,-0.1,-0.9,-0.1),straw:rr(-1.02,-0.3,2.04,0.13,0.06),toque:rr(-0.46,-0.52,0.92,0.26,0.05),
 beret:()=>{c.beginPath();c.ellipse(0,-0.44,0.66,0.24,0,0,TAU)},helmet:rr(-0.64,-0.6,1.28,0.5,0),headband:rr(-0.6,-0.36,1.2,0.15,0.04)};
function drawHead3(P,ch){const psi=P.headYaw,cyh=Math.cos(psi),syh=Math.sin(psi);c.save();headXf3(P,ch);
 const H=ch.hair||{},hc=H.col||'#2B2320',hat=ch.hat||{},dark=lum(ch.skin)<150,hasHair=H.type&&H.type!=='bald',Fc=P.face||{},mood=Fc.mood||ch.mood,st=H.type==='long'?'long':(H.style||'part'),b=P.bob2;
 const on=(f,R)=>{const a=nrm(f*D2R+psi),k=Math.cos(a);return{x:(R||HW)*Math.sin(a),k,vis:k>0.03}};
 /* things attached to the back / top of the head: drawn behind when they point away from the camera */
 const blobs=[];
 if(H.type==='bun'){const p=on(180,0.2);blobs.push([p.x,-1.44+b*0.6,0.18,p.k,1])}
 if(H.type==='curly'){for(let i=0;i<5;i++){const p=on(i*72+20,0.27);blobs.push([p.x,-1.33+b*0.25,0.2,p.k-0.6,0])}for(let i=0;i<9;i++){const f=60+i*30;if(f>300)break;const p=on(f,0.47);blobs.push([p.x,-1.06+b*0.2,0.19,p.k,0])}for(let i=0;i<7;i++){const p=on(78+i*34,0.5);blobs.push([p.x,-0.84,0.16,p.k,0])}}
 const pony=H.type==='pony'?on(180,0.44):null,drawPony=()=>{c.save();c.translate(pony.x,-1.12);c.rotate((0.5+b*3)*syh);shape(()=>{c.beginPath();c.ellipse(-0.22*syh,0.22,0.15,0.38,0.5*syh,0,TAU)},hc);shape(circ(0,0,0.07),hat.col||'#FF5FA2');c.restore()};
 for(const q of blobs)if(q[3]<0){shape(circ(q[0],q[1],q[2]),hc);if(q[4])shape(circ(q[0]+0.05,q[1]-0.04,0.07),GLOSS)}
 if(pony&&pony.k<0)drawPony();
 /* ears: at ±90°. on the silhouette they peek out from behind, turned toward camera they sit on the head */
 const ears=[1,-1].map(s=>on(90*s,HW+0.015)),ear=e=>{shape(()=>{c.beginPath();c.ellipse(e.x,EY+0.05,0.085,0.1,0,0,TAU)},ch.skin);shape(()=>{c.beginPath();c.ellipse(e.x-0.02*Math.sign(e.x||1)*(1-e.k),EY+0.05,0.038,0.056,0,0,TAU)},ch.nc);if(ch.earring&&e===ears[1])shape(circ(e.x,EY+0.18,0.03),ch.earring)};
 const earHidden=st==='arch'||st==='long';
 if(!earHidden)for(const e of ears)if(e.k<0.3)ear(e);
 shape(headPath,ch.skin);
 /* nose: a small bump that only shows on the silhouette */
 {const pk=cl((cyh+0.32)/0.3),nb=ch.nose==='round'?1.18:ch.nose==='short'?0.86:1,xb=HW*0.88*syh,xt=(HW+0.1*pk*nb)*syh;if(pk>0)shape(()=>{c.beginPath();c.moveTo(xb,EY-0.05);c.quadraticCurveTo(xb+0.07*syh,EY+0.11,xt,EY+0.2);c.quadraticCurveTo(xt+0.014*syh,EY+0.275,xt-0.065*syh,EY+0.285);c.lineTo(xb,EY+0.34);c.closePath()},ch.skin)}
 c.save();headPath();c.clip();
 /* form shade under the jaw (top-left light) */
 c.save();c.beginPath();c.rect(-1,-2,2,3);c.translate(-0.022,-0.05);headSub();c.fillStyle='rgba(70,30,10,0.075)';c.fill('evenodd');c.restore();
 if(ch.blush!==0)for(const s of[1,-1]){const p=on(36*s);if(p.vis){c.fillStyle=dark?'rgba(255,95,85,.3)':'rgba(255,120,125,.36)';c.beginPath();c.ellipse(p.x,EY+0.15,0.105*Math.max(0.35,p.k),0.105,0,0,TAU);c.fill()}}
 if(ch.freckle)for(const s of[1,-1])for(const[df,y]of[[-4,0.11],[4,0.15],[0,0.19]]){const p=on(36*s+df);if(p.vis){c.fillStyle=ch.nc;c.beginPath();c.arc(p.x,EY+y,0.013,0,TAU);c.fill()}}
 if(ch.beard){c.beginPath();beardSub(psi);c.fillStyle=ch.beard;c.fill()}
 if(hasHair){c.save();c.translate(0,0.04);c.beginPath();hairSub(st,psi);c.fillStyle=SHC;c.fill();c.restore()}
 c.restore();
 /* hair cap */
 if(hasHair){c.save();c.translate(0,-0.6);c.scale(1,1+b*0.35);c.translate(0,0.6);c.beginPath();hairSub(st,psi);c.fillStyle=hc;c.fill();
  c.save();c.beginPath();hairSub(st,psi);c.clip();
  {const dh=lum(hc)<70,hl=HL[st]||HL.part,SC=dh?'rgba(255,255,255,0.11)':'rgba(40,15,5,0.17)';
   /* two tones: the underside along the hairline is a step darker (dark hair: the top is a step lighter) */
   c.save();c.beginPath();if(!dh)c.rect(-1,-2,2,3);c.translate(0,-0.07);hairSub(st,psi);c.fillStyle=dh?'rgba(255,255,255,0.065)':'rgba(40,15,5,0.14)';c.fill(dh?'nonzero':'evenodd');c.restore();
   /* strands sit at fixed azimuths, so they travel round the head */
   if(H.type!=='curly'){for(let f=-168;f<=180;f+=24){const p=on(f,RH);if(p.k<0.1)continue;const y=hl(f),x=Math.max(-HW,Math.min(HW,p.x)),ln=Math.max(0.1,Math.min(0.3,(y+1.28)*0.42));c.globalAlpha=cl(p.k*1.5);line(()=>{c.beginPath();c.moveTo(x,y-0.035);c.quadraticCurveTo(x*0.97,y-0.035-ln*0.5,x*0.88,y-0.035-ln)},0.02*Math.max(0.45,p.k),SC)}c.globalAlpha=1;
    const w0=on(180,RH*0.42);if(w0.k>0.1){c.globalAlpha=cl(w0.k*1.4);line(()=>{c.beginPath();c.arc(w0.x,-1.13,0.075,0.5,4.3)},0.02,SC);c.globalAlpha=1}}}
  line(()=>{c.beginPath();c.arc(0.02*cyh,-0.86,0.41,-2.25,-1.0)},0.06,GLOSS);
  if(st==='arch'||st==='long'){const p=on(0,RH);if(p.vis)line(()=>{c.beginPath();c.moveTo(p.x,-1.09);c.quadraticCurveTo(p.x*0.9,-1.25,p.x*0.75,-1.42)},0.018)}c.restore();
  if(st==='perm')for(const f of[-42,-14,14,42]){const p=on(f,0.45);if(p.vis)shape(()=>{c.beginPath();c.ellipse(p.x,-1.0,0.13*Math.max(0.5,p.k),0.13,0,0,TAU)},hc)}
  c.restore()}
 if(!earHidden)for(const e of ears)if(e.k>=0.3)ear(e);
 for(const q of blobs)if(q[3]>=0){shape(circ(q[0],q[1],q[2]),hc);if(q[4])shape(circ(q[0]+0.05,q[1]-0.04,0.07),GLOSS);else{c.globalAlpha=cl(q[3]*2);line(()=>{c.beginPath();c.arc(q[0],q[1],q[2]*0.6,-2.5,-1.25)},0.03,lum(hc)<70?'rgba(255,255,255,0.12)':'rgba(255,255,255,0.3)');c.globalAlpha=1}}
 if(pony&&pony.k>=0)drawPony();
 /* face */
 const eyes=[1,-1].map(s=>on(18.7*s)),bt=((P.t+1.15+(ch.seed||0))%2.3+2.3)%2.3,bk=Math.min(bt<0.14?Math.max(0.12,1-Math.sin(Math.PI*bt/0.14)):1,1-0.9*(Fc.blink||0)),EC='#1E1512',lk=Fc.look||[0,0],sq=p=>Math.max(0.35,p.k),inX=(x,half)=>Math.sign(x)*Math.min(Math.abs(x),HW-half+0.012);for(const p of eyes)p.x=inX(p.x,(ch.eyes==='shades'?0.115:ch.eyes==='glasses'?0.105:0.085)*sq(p));
 if(ch.eyes==='shades'){for(const p of eyes)if(p.vis)shape(rr(p.x-0.115*sq(p),EY-0.08,0.23*sq(p),0.17,[0.04,0.04,0.09,0.09]),'#1B1B24');if(eyes[0].vis&&eyes[1].vis)line(()=>{c.beginPath();c.moveTo(eyes[0].x,EY-0.05);c.lineTo(eyes[1].x,EY-0.05)},0.035,'#1B1B24');
  for(let i=0;i<2;i++){const p=eyes[i],e=ears[i],ta=cl((e.k+0.22)/0.2);if(p.vis&&ta>0){c.globalAlpha=ta;line(()=>{c.beginPath();c.moveTo(p.x+(i?-1:1)*0.1*sq(p),EY-0.04);c.lineTo(e.x,EY-0.02)},0.035,'#1B1B24');c.globalAlpha=1}}
  c.fillStyle='rgba(255,255,255,.7)';for(const p of eyes)if(p.vis){c.beginPath();c.ellipse(p.x-0.04*sq(p),EY-0.03,0.035*sq(p),0.016,-0.5,0,TAU);c.fill()}}
 else{const gl=ch.eyes==='glasses';
  if(gl){c.fillStyle='rgba(255,255,255,.32)';for(const p of eyes)if(p.vis){c.beginPath();c.ellipse(p.x,EY,0.105*sq(p),0.105,0,0,TAU);c.fill()}}
  {const er=ch.eyeR||1,grn=mood==='grin';for(let i=0;i<2;i++){const p=eyes[i];if(!p.vis)continue;const s=i?-1:1,kx=Math.max(0.45,p.k),ex=p.x+lk[0]*0.028*p.k,ey=EY+lk[1]*0.025,rx=0.044*er*kx,ry=Math.max(0.009,0.051*er*bk);
    c.save();if(grn){c.beginPath();c.moveTo(ex-0.2,ey-0.2);c.lineTo(ex+0.2,ey-0.2);c.lineTo(ex+rx*1.5,ey+0.06*er);c.quadraticCurveTo(ex,ey-0.006*er,ex-rx*1.5,ey+0.06*er);c.closePath();c.clip()}c.fillStyle=EC;c.beginPath();c.ellipse(ex,ey,rx,ry,0,0,TAU);c.fill();c.restore();
    /* catch-light */
    {const hl=cl((bk-0.5)/0.3);if(hl>0){c.globalAlpha=hl;c.fillStyle='#FFFFFF';c.beginPath();c.ellipse(ex-0.015*kx*er,ey-0.02*er,0.0145*er*kx,0.0145*er,0,0,TAU);c.fill();c.globalAlpha=1}}
    /* closing lid */
    {const cz=cl((0.5-bk)/0.3);if(cz>0){c.globalAlpha=cz;line(()=>{c.beginPath();c.moveTo(ex-rx*1.25,ey-0.004);c.quadraticCurveTo(ex,ey+0.024,ex+rx*1.25,ey-0.004)},0.022,EC);c.globalAlpha=1}}
    if(ch.lash&&p.k>0.04){c.globalAlpha=cl((p.k-0.04)/0.22);line(()=>{c.beginPath();c.moveTo(ex-s*rx*0.75,ey-ry*0.92);c.quadraticCurveTo(ex+s*rx*0.5,ey-ry*1.22,ex+s*rx*1.18,ey-ry*0.45);c.lineTo(ex+s*(rx*1.18+0.028*kx),ey-ry*0.45-0.024)},0.017,EC);c.globalAlpha=1}
    if(ch.wrinkle){c.globalAlpha=0.55;line(()=>{c.beginPath();c.moveTo(ex-rx*1.1,ey+0.082);c.quadraticCurveTo(ex,ey+0.102,ex+rx*1.1,ey+0.082)},0.012,ch.nc);c.globalAlpha=1}}}
  if(gl){line(()=>{c.beginPath();for(const p of eyes)if(p.vis){c.moveTo(p.x+0.105*sq(p),EY);c.ellipse(p.x,EY,0.105*sq(p),0.105,0,0,TAU)}if(eyes[0].vis&&eyes[1].vis){c.moveTo(eyes[1].x+0.105*sq(eyes[1]),EY-0.01);c.lineTo(eyes[0].x-0.105*sq(eyes[0]),EY-0.01)}
    },0.024,ch.frame||'#4A2E22');
   for(let i=0;i<2;i++){const p=eyes[i],e=ears[i],ta=cl((e.k+0.22)/0.2);if(p.vis&&ta>0){c.globalAlpha=ta;line(()=>{c.beginPath();c.moveTo(p.x+(i?-1:1)*0.105*sq(p),EY-0.01);c.lineTo(e.x,EY)},0.024,ch.frame||'#4A2E22');c.globalAlpha=1}}
   for(const p of eyes)if(p.vis)line(()=>{c.beginPath();c.moveTo(p.x-0.07*sq(p),EY-0.02);c.lineTo(p.x-0.035*sq(p),EY-0.066)},0.018,'rgba(255,255,255,0.8)')}
  const bc=hasHair?dk(hc,lum(hc)>150?0.62:0.85):'#3B2416',m=(mood==='grin'?-0.025:0)-(Fc.brow||0)*0.04,by=EY-0.147+m;
  {const bw0=(ch.brow||1)*0.044;c.save();headPath();c.clip();c.fillStyle=bc;for(let i=0;i<2;i++){const p=eyes[i],s=i?-1:1;if(!p.vis)continue;c.globalAlpha=cl((p.k-0.04)/0.22);const k=sq(p),bw=bw0*lerp(0.7,1,cl((p.k-0.3)/0.5)),xi=p.x-s*0.086*k,xo=p.x+s*0.105*k,N=8,Q=[];
    for(let j=0;j<=N;j++){const u=j/N;Q.push([lerp(xi,xo,u),by-0.026*Math.sin(Math.PI*Math.pow(u,0.85))+0.015*u*u,bw*(1-0.66*Math.pow(u,1.6))*0.5])}
    const Tp=[],Bt=[];for(let j=0;j<=N;j++){const a=Q[Math.max(j-1,0)],b=Q[Math.min(j+1,N)],dx=b[0]-a[0],dy=b[1]-a[1],l=Math.hypot(dx,dy)||1;let nx=-dy/l,ny=dx/l;if(ny>0){nx=-nx;ny=-ny}Tp.push([Q[j][0]+nx*Q[j][2],Q[j][1]+ny*Q[j][2]]);Bt.push([Q[j][0]-nx*Q[j][2],Q[j][1]-ny*Q[j][2]])}
    c.beginPath();Tp.forEach((q,j)=>j?c.lineTo(q[0],q[1]):c.moveTo(q[0],q[1]));for(let j=N;j>=0;j--)c.lineTo(Bt[j][0],Bt[j][1]);c.closePath();c.fill();c.beginPath();c.arc(Q[0][0],Q[0][1],Q[0][2],0,TAU);c.fill();c.beginPath();c.arc(Q[N][0],Q[N][1],Q[N][2],0,TAU);c.fill()}c.restore()}}
 /* nose line + mouth at azimuth 0 (they fade only once the face has turned past the profile) */
 if(cyh>-0.12){const al=cl((cyh+0.05)*4),am=cl((cyh+0.12)*6),hk=-0.057*cl2((nrm(psi)+0.15)/0.15)*Math.max(0.3,cyh),xb=HW*0.9*syh,xt=(HW+0.03)*syh,k=Math.max(0.35,cyh),mx=inX(HW*0.94*syh,0.13*k),tk=Fc.talk||0;c.globalAlpha=al;
  if(ch.nose==='round'){shape(()=>{c.beginPath();c.ellipse(xt+hk*0.55,EY+0.215,0.07*Math.max(0.55,k),0.062,0,0,TAU)},ch.n2);c.fillStyle='rgba(255,255,255,0.22)';c.beginPath();c.ellipse(xt+hk*0.55-0.02*k,EY+0.195,0.022*k,0.016,0,0,TAU);c.fill()}
  else{const sh=ch.nose==='short',u0=sh?0.62:0,ra=cl((cyh-0.6)/0.3);
   /* bridge line reads as volume from the front and 3/4; it fades out as the head turns to the side (the silhouette bump takes over) */
   if(ra>0&&ch.eyes!=='shades'){c.globalAlpha=al*ra;line(()=>{c.beginPath();c.moveTo(lerp(xb,xt,u0),lerp(EY-0.14,EY+0.215,u0));c.lineTo(xt,EY+0.165)},0.022,ch.nc);c.globalAlpha=al}
   /* the tip hook also fades once the nose starts to stick out of the silhouette, so the two never show together */
   const ha=cl((0.89-Math.abs(syh))/0.05);if(ha>0){c.globalAlpha=al*ha;
   line(()=>{c.beginPath();if(ch.eyes==='shades')c.moveTo(xb,EY+0.1);else c.moveTo(xt,EY+0.165);c.lineTo(xt,EY+0.215);c.quadraticCurveTo(xt,EY+0.262,xt+hk,EY+0.262)},0.022,ch.nc);c.globalAlpha=al}
   c.globalAlpha=al*0.4;c.fillStyle=ch.nc;c.beginPath();c.ellipse(xt+hk*0.5,EY+0.296,0.05*k,0.013,0,0,TAU);c.fill()}c.globalAlpha=am;c.save();headPath();c.clip();
  if(ch.wrinkle)line(()=>{c.beginPath();for(const s of[1,-1]){c.moveTo(mx+s*0.15*k,EY+0.29);c.quadraticCurveTo(mx+s*0.2*k,EY+0.37,mx+s*0.185*k,EY+0.45)}},0.016,ch.nc);
  if(ch.stache)shape(()=>{c.beginPath();c.moveTo(mx-0.17*k,EY+0.37);c.quadraticCurveTo(mx-0.09*k,EY+0.27,mx,EY+0.31);c.quadraticCurveTo(mx+0.09*k,EY+0.27,mx+0.17*k,EY+0.37);c.quadraticCurveTo(mx+0.07*k,EY+0.38,mx,EY+0.355);c.quadraticCurveTo(mx-0.07*k,EY+0.38,mx-0.17*k,EY+0.37);c.closePath()},ch.stache);
  if(tk>0.02||mood==='o'){const o=mood==='o'&&tk<=0.02,my=EY+(ch.stache?0.46:0.43),rx=(o?0.062:0.085)*k,ry=o?0.078:0.02+0.065*tk*Math.abs(Math.sin(P.t*13+(ch.seed||0)*5)),Mo=()=>{c.beginPath();c.ellipse(mx,my,rx,ry,0,0,TAU)};shape(Mo,dark?'#5E1F1A':'#9C352E');c.save();Mo();c.clip();c.fillStyle='#F2817F';c.beginPath();c.ellipse(mx,my+ry*0.9,rx*0.8,ry*0.7,0,0,TAU);c.fill();c.restore()}
  else if(ch.stache){if(mood==='grin')line(()=>{c.beginPath();c.moveTo(mx-0.09*k,EY+0.42);c.quadraticCurveTo(mx,EY+0.52,mx+0.09*k,EY+0.42)},0.028,ch.mc)}
  else if(mood==='grin'){const M=()=>{c.beginPath();c.moveTo(mx-0.14*k,EY+0.37);c.lineTo(mx+0.14*k,EY+0.37);c.quadraticCurveTo(mx+0.13*k,EY+0.51,mx,EY+0.51);c.quadraticCurveTo(mx-0.13*k,EY+0.51,mx-0.14*k,EY+0.37);c.closePath()};shape(M,dark?'#5E1F1A':'#9C352E');c.save();M();c.clip();F('#FFFFFF',mx-0.2,EY+0.36,0.4,0.05);c.fillStyle='#F2817F';c.beginPath();c.ellipse(mx,EY+0.52,0.09*k,0.05,0,0,TAU);c.fill();c.restore()}
  else if(ch.lip){const y=EY+0.4,Lp=()=>{c.beginPath();c.moveTo(mx-0.115*k,y);c.quadraticCurveTo(mx-0.06*k,y-0.045,mx-0.022*k,y-0.03);c.quadraticCurveTo(mx,y-0.018,mx+0.022*k,y-0.03);c.quadraticCurveTo(mx+0.06*k,y-0.045,mx+0.115*k,y);c.quadraticCurveTo(mx,y+0.125,mx-0.115*k,y);c.closePath()};shape(Lp,ch.lip);c.save();Lp();c.clip();c.fillStyle='rgba(255,255,255,0.2)';c.beginPath();c.ellipse(mx-0.02*k,y+0.052,0.04*k,0.012,0,0,TAU);c.fill();c.restore();
   line(()=>{c.beginPath();c.moveTo(mx-0.13*k,y-0.008);c.quadraticCurveTo(mx,y+0.05,mx+0.13*k,y-0.008)},0.018,'rgba(90,20,25,0.75)')}
  else{const y=EY+0.385,mc=ch.beard?'#EBA892':ch.mc;line(()=>{c.beginPath();c.moveTo(mx-0.13*k,y);c.quadraticCurveTo(mx,EY+0.5,mx+0.13*k,y)},0.03,mc);
   if(!ch.beard){c.globalAlpha=am*0.32;c.fillStyle=ch.nc;c.beginPath();c.ellipse(mx,EY+0.528,0.058*k,0.015,0,0,TAU);c.fill()}}c.restore();c.globalAlpha=1}
 /* hats */
 if(hat.type==='headphones'){const far=ears.filter(e=>e.k<=0),near=ears.filter(e=>e.k>0);line(()=>{c.beginPath();c.ellipse(0,-0.76,Math.max(0.02,0.64*Math.abs(cyh)),0.64,0,Math.PI+0.2,TAU-0.2)},0.09,hat.col);
  for(const e of ears){const kk=0.55+0.45*Math.abs(e.k),x=e.x*1.12;if(e.k>-0.3){lifted(rr(x-0.11*kk,-0.82,0.22*kk,0.4,0.1*kk),e.k>0.3?hat.col:dk(hat.col,0.92),0.02,0.02);if(e.k>0.3)shape(rr(x-0.06*kk,-0.76,0.12*kk,0.28,0.05),hat.col2)}}}
 const HX=()=>{c.translate(0,P.hat-0.897);c.scale(0.84,0.84)},hasHat=HATSH[hat.type];
 if(hasHat&&cyh>-0.4){c.save();c.beginPath();headSub();if(hasHair)hairSub(st,psi);c.clip();HX();c.translate(0,0.075);HATSH[hat.type]();c.fillStyle=SHC;c.fill();c.restore()}
 HX();const hcol=hat.col,h2=hat.col2||dk(hcol||'#888888',0.8),bob=b/0.84,inDome=(d,fn)=>{c.save();d();c.clip();fn();c.restore()};
 const brim=(ps,y,rx0,rx1,ry0,ry1,col)=>{const cz=Math.cos(ps),sz=Math.sin(ps);if(cz<-0.35)return;shape(()=>{c.beginPath();c.ellipse(0.52*sz,y+0.05*Math.max(0,cz),rx0+rx1*Math.abs(cz),ry0+ry1*Math.max(0,cz),0,0,TAU)},col)};
 if(hat.type==='beanie'){if(hat.pom)shape(circ(0,-0.86+bob*0.8,0.15),hat.pom);shape(dome(0.5,-0.2),hcol);shape(rr(-0.63,-0.36,1.26,0.2,0.07),h2);c.fillStyle=TONE;for(let i=0;i<12;i++){const p=on(i*30,0.6);if(p.vis)c.fillRect(p.x-0.01,-0.36,0.02,0.2)}}
 if(hat.type==='cap'||hat.type==='capBack'){const ps=psi+(hat.type==='cap'?0:Math.PI),cz=Math.cos(ps),d=dome(0.44,-0.2);if(cz<0.25)brim(ps,-0.26,0.36,0.24,0.065,0.07,h2);shape(d,hcol);
  inDome(d,()=>{F(h2,-0.7,-0.27,1.4,0.1);for(const f of[0,60,120,180,240,300]){const p=on(f+(hat.type==='cap'?0:180),0.6);if(p.vis)line(()=>{c.beginPath();c.moveTo(p.x,-0.2);c.quadraticCurveTo(p.x,-0.48,p.x*0.15,-0.63)},0.02)}});shape(circ(0,-0.635,0.04),h2);if(cz>=0.25)brim(ps,-0.26,0.36,0.24,0.065,0.07,h2);
  {const p=on(hat.type==='cap'?0:180,0.56);if(p.vis&&hat.type==='capBack')shape(rr(p.x-0.11*sq(p),-0.5,0.22*sq(p),0.16,0.05),'#FFFFFF')}}
 if(hat.type==='bucket'){const tp=poly(-0.48,-0.66,0.48,-0.66,0.6,-0.24,-0.6,-0.24);shape(tp,hcol);inDome(tp,()=>{F(h2,-0.7,-0.38,1.4,0.09)});shape(poly(-0.62,-0.3,0.62,-0.3,0.9,-0.1,-0.9,-0.1),h2);F('rgba(255,255,255,0.14)',-0.6,-0.3,1.2,0.035)}
 if(hat.type==='straw'){shape(rr(-1.02,-0.3,2.04,0.13,0.06),dk(hcol,0.88));const d=dome(0.4,-0.26);shape(d,hcol);inDome(d,()=>{line(()=>{c.beginPath();for(let i=0;i<14;i++){const p=on(i*360/14,0.6);if(p.vis){c.moveTo(p.x,-0.26);c.lineTo(p.x*0.6,-0.7)}}},0.014);F(h2,-0.7,-0.42,1.4,0.11)});line(()=>{c.beginPath();for(let i=0;i<18;i++){const p=on(i*20,1.0);if(p.vis){c.moveTo(p.x,-0.28);c.lineTo(p.x+0.05,-0.19)}}},0.014)}
 if(hat.type==='toque'){const tq=()=>{c.beginPath();c.moveTo(-0.42,-0.4);c.bezierCurveTo(-0.8,-0.7,-0.56,-1.2,-0.16,-1.02);c.bezierCurveTo(0,-1.24,0.36,-1.18,0.36,-0.98);c.bezierCurveTo(0.78,-1.0,0.7,-0.56,0.42,-0.4);c.closePath()};shape(tq,'#FFFFFF');inDome(tq,()=>{line(()=>{c.beginPath();for(const f of[0,72,144,216,288]){const p=on(f,0.5);if(p.vis){c.moveTo(p.x*0.6,-0.5);c.quadraticCurveTo(p.x*0.9,-0.8,p.x*0.75,-1.0)}}},0.02,'rgba(70,30,10,0.14)')});lifted(rr(-0.46,-0.52,0.92,0.26,0.05),'#FFFFFF',0,-0.03)}
 if(hat.type==='beret'){line(()=>{c.beginPath();c.moveTo(0,-0.66);c.lineTo(0.03,-0.8)},0.06,dk(hcol,0.8));const br=()=>{c.beginPath();c.ellipse(-0.1*syh,-0.44,0.66,0.24,-0.1*syh,0,TAU)};shape(br,hcol);inDome(br,()=>{c.fillStyle=GLOSS;c.beginPath();c.ellipse(0.06,-0.52,0.4,0.1,0,0,TAU);c.fill();F(dk(hcol,0.82),-0.9,-0.28,1.8,0.2)})}
 if(hat.type==='helmet'){const hm=()=>{c.beginPath();c.moveTo(-0.64,-0.1);c.bezierCurveTo(-0.7,-0.92,0.7,-0.92,0.64,-0.1);c.closePath()};if(cyh<0.25)brim(psi,-0.14,0.2,0.3,0.05,0.05,h2);shape(hm,hcol);
  inDome(hm,()=>{F(h2,-0.7,-0.2,1.4,0.1);const xs=0.6*syh*(cyh>=0?1:-1),wk=0.14*Math.max(0.25,Math.abs(cyh));F('#FFFFFF',xs-wk/2,-1,wk,0.8);c.fillStyle=GLOSS;c.beginPath();c.ellipse(0.3,-0.56,0.2,0.07,0.5,0,TAU);c.fill()});if(cyh>=0.25)brim(psi,-0.14,0.2,0.3,0.05,0.05,h2)}
 if(hat.type==='headband'){shape(rr(-0.6,-0.36,1.2,0.15,0.04),hcol);F('rgba(255,255,255,0.3)',-0.6,-0.3,1.2,0.03)}
 c.restore()}
/* things that wrap around the back of the body (long hair, hood, pack) are split by azimuth:
   the part turned toward the camera is drawn in front of the torso, the rest behind it, so nothing flips at once */
function drawLongHair3(P,ch,front){const H=ch.hair||{};if(H.type!=='long')return;const R=0.52;let v=vis(100,260,R,P.headYaw+(front?0:Math.PI));if(!v)return;if(!front)v=[-v[1],-v[0]];const w=v[1]-v[0];if(w<0.04)return;
 c.save();headXf3(P,ch);c.translate(0,-1.2);c.rotate(P.sway*0.05);const r=Math.min(0.16,w/2);c.beginPath();c.roundRect(v[0],0,w,1.8,[Math.min(0.3,w/2),Math.min(0.3,w/2),r,r]);c.fillStyle=H.col;c.fill();c.fillStyle=dk(H.col,0.88);c.beginPath();c.roundRect(v[0],1.25,w,0.55,[0,0,r,r]);c.fill();
 if(front){c.save();c.beginPath();c.rect(v[0],0,w,1.8);c.clip();for(let f=112;f<=248;f+=17){const a=nrm(f*D2R+P.headYaw),k=Math.cos(a);if(k<0.1)continue;c.globalAlpha=cl(k*1.5);const x=R*Math.sin(a);line(()=>{c.beginPath();c.moveTo(x,0.45);c.quadraticCurveTo(x*1.02,1.1,x*0.98,1.72)},0.02*Math.max(0.45,k),'rgba(40,15,5,0.15)')}c.restore()}c.restore()}
function drawHood3(P,ch,front){if(ch.top.type!=='hoodie')return;c.save();headXf3(P,ch);if(front){const v=vis(105,255,0.66,P.yaw);if(!v){c.restore();return}c.beginPath();c.rect(v[0],-1,v[1]-v[0],2);c.clip()}
 const ac=Math.abs(P.cy),x=-0.3*P.sy*(1-0.3*ac),wd=lerp(0.4,0.52,ac),col=ch.top.col;shape(()=>{c.beginPath();c.ellipse(x,0.1,wd,0.24,-0.25*P.sy,0,TAU)},col);
 const al=cl((0.2-P.cy)/0.3);if(al>0.02){c.globalAlpha*=al;shape(()=>{c.beginPath();c.ellipse(x*0.8,0.06,wd*0.65,0.13,-0.25*P.sy,0,TAU)},dk(col,lum(col)>90?0.84:1.4));c.globalAlpha/=al}c.restore()}
function prep(ch){if(!ch.nc){const d=lum(ch.skin)<150;ch.nc=mix(ch.skin,'#8E2F1E',d?0.62:0.42);ch.mc=d?mix(ch.skin,'#4A140E',0.62):mix(ch.skin,'#B02E22',0.6);ch.n2=mix(ch.skin,'#C2452F',d?0.4:0.3)}}
/* layer order comes from depth */
function drawChar3(ch,P){prep(ch);const beh=a=>(a.s0[2]<-0.02&&a.wr[2]<0.12)||a.Zm<-0.1,back=P.arms.filter(beh),front=P.arms.filter(a=>!beh(a)).sort((a,b)=>a.Zm-b.Zm),legs=P.legs.slice().sort((a,b)=>a.h[2]-b.h[2]);
 drawLongHair3(P,ch,false);for(const a of back)drawArm3(P,a,ch,false);drawPack3(P,ch,false);drawHood3(P,ch,false);
 for(const l of legs)drawLeg3(P,l,ch);drawNeck3(P,ch);drawTorso3(P,ch);drawPack3(P,ch,true);drawLongHair3(P,ch,true);drawHood3(P,ch,true);drawHead3(P,ch);for(const a of front)drawArm3(P,a,ch,true)}

/* ---------- cast ---------- */
const SK=['#F9C6AA','#F2B896','#D59A6E','#99643F','#FBD3BC','#C4855A'];
const CAST=[
 {name:'바리스타',build:'slim',h:0.98,lash:1,nose:'short',brow:0.85,jaw:0.22,disc:'#BFE3D0',skin:SK[1],hair:{type:'bun',col:'#5A3A2A',style:'arch'},eyes:'glasses',earring:'#F2C14E',top:{type:'apron',col:'#FFFFFF',col2:'#2E7D5B',arms:'long',cuff:'#E9E4DC',collar:'#FFFFFF'},pants:{type:'long',col:'#2F3140',cuff:'#474A60',fit:'slim'},shoe:{col:'#F3EFE6',sole:'#FFFFFF',stripe:'#2E7D5B'}},
 {name:'라이더',build:'std',h:1.01,brow:1.15,jaw:0.28,disc:'#FFE08A',skin:SK[2],hair:{type:'short',col:'#2B2320'},hat:{type:'helmet',col:'#FFC83A',col2:'#E2A51F'},eyes:'dot',mood:'grin',seed:0.5,glove:'#2F3140',top:{type:'jacket',col:'#E5484D',col2:'#FFFFFF',band:'#FFF1A8',hem:'#2F3140',arms:'long',cuff:'#2F3140',sleeveStripe:'#FFF1A8',collar:'#C93A40'},pants:{type:'long',col:'#5C6370'},shoe:{col:'#2F3140',sole:'#FFFFFF',stripe:'#E5484D'},pack:{type:'box',col:'#5CC9B5'}},
 {name:'등산객',build:'broad',jaw:0.27,disc:'#CFE3A8',skin:SK[0],hair:{type:'short',col:'#6B4A2E'},hat:{type:'bucket',col:'#7A8F4A',col2:'#64773A'},eyes:'shades',top:{type:'vest',col:'#C3CAD2',col2:'#F08A2E',arms:'long',collar:'#F08A2E'},pants:{type:'shorts',col:'#C9B38A'},sock:'#FFFFFF',sockStripe:'#E5484D',shoe:{type:'boot',col:'#8A5A3B',sole:'#3A2A22',toe:'#74492E'},pack:{col:'#3F7CC9',col2:'#2E5F9E',mat:'#E9C46A'}},
 {name:'요리사',build:'round',nose:'round',brow:1.3,jaw:0.27,disc:'#F9C9C2',skin:SK[4],hair:{type:'short',col:'#2B2320',style:'sweep'},hat:{type:'toque'},eyes:'dot',seed:1.1,stache:'#2B2320',scarf:'#D64545',top:{type:'chef',col:'#FFFFFF',arms:'long',cuff:'#E9E4DC'},pants:{type:'long',col:'#3B4A6B'},shoe:{type:'dress',col:'#2F3140',sole:'#1E1F2A'}},
 {name:'학생',h:0.96,hd:1.04,nose:'short',disc:'#BFD7FF',skin:SK[1],hair:{type:'short',col:'#1F1B24',style:'bang'},hat:{type:'capBack',col:'#3D6BE0',col2:'#2F56B8'},eyes:'dot',mood:'grin',seed:0.3,top:{type:'hoodie',col:'#FFD23F',arms:'long',cuff:'#F2B705',hem:'#F2B705'},pants:{type:'long',col:'#5B8FD9',cuff:'#BBD6F7'},shoe:{col:'#FFFFFF',sole:'#E5484D',toe:'#E5484D'},pack:{col:'#E5484D',charm:'#FFD23F'}},
 {name:'할머니',build:'round',h:0.92,hd:1.02,nose:'short',brow:0.75,disc:'#E3D0F5',skin:SK[4],hair:{type:'curly',col:'#C2C2CC',style:'perm'},eyes:'glasses',frame:'#B0496F',wrinkle:1,seed:1.6,top:{type:'cardigan',col:'#9B6FD0',col2:'#F6E7C8',arms:'long',collar:'#F6E7C8'},pants:{type:'long',col:'#B9A892',fit:'wide'},shoe:{type:'dress',col:'#8A5A3B',sole:'#5C3B26'}},
 {name:'화가',build:'slim',h:0.98,lash:1,nose:'short',brow:0.8,jaw:0.2,lip:'#D9596A',disc:'#FFD3A8',skin:SK[0],hair:{type:'long',col:'#B5532E',style:'arch'},hat:{type:'beret',col:'#D64545'},eyes:'dot',freckle:1,seed:0.8,top:{type:'stripe',col:'#FFFFFF',col2:'#27365E',neck:'#27365E',arms:'long',sleeve:'#27365E',cuff:'#FFFFFF'},pants:{type:'long',col:'#7A8F4A',cuff:'#96AA66'},shoe:{col:'#8A5A3B',sole:'#F3EFE6'}},
 {name:'러너',build:'slim',lash:1,brow:0.9,jaw:0.21,disc:'#FFC2DD',skin:SK[3],hair:{type:'pony',col:'#1F1B24',style:'arch'},hat:{type:'headband',col:'#FF5FA2'},eyes:'dot',mood:'grin',seed:0.2,watch:'#1F1B24',top:{type:'tee',col:'#18B7A0',arms:'none'},pants:{type:'shorts',col:'#2F3140'},sock:'#FFFFFF',shoe:{col:'#C6F432',sole:'#FFFFFF',toe:'#FF5FA2',stripe:'#FF5FA2'}},
 {name:'직장인',build:'broad',h:1.03,brow:1.15,jaw:0.27,disc:'#C9D3E0',skin:SK[1],hair:{type:'short',col:'#2B2320',style:'sweep'},eyes:'glasses',seed:1.3,top:{type:'suit',col:'#2F3E63',col2:'#FFFFFF',arms:'long',tie:'#D64545',cuff:'#FFFFFF',collar:'#FFFFFF'},pants:{type:'long',col:'#27345A'},shoe:{type:'dress',col:'#5A3620',sole:'#3A2416'}},
 {name:'농부',build:'broad',h:1.02,nose:'round',brow:1.35,jaw:0.29,disc:'#F4E3A1',skin:SK[5],hair:{type:'short',col:'#3A2A22'},hat:{type:'straw',col:'#F2D27A',col2:'#D64545'},eyes:'dot',wrinkle:1,seed:0.6,beard:'#3A2A22',towel:'#FFFFFF',top:{type:'overall',col:'#E5484D',col2:'#4F86D9',arms:'short'},pants:{type:'long',col:'#4F86D9',fit:'wide'},shoe:{type:'boot',col:'#4A9B62',sole:'#2F6B41'}},
 {name:'디제이',h:1.02,jaw:0.26,disc:'#D4C4FF',skin:SK[2],hair:{type:'curly',col:'#1F1B24',style:'perm'},hat:{type:'headphones',col:'#F3EFE6',col2:'#7A5AF5'},eyes:'shades',top:{type:'hoodie',col:'#2F3140',arms:'long',cuff:'#7A5AF5',hem:'#7A5AF5',sleeveStripe:'#7A5AF5'},pants:{type:'long',col:'#8C93A1',cuff:'#B5BAC6',fit:'slim'},shoe:{col:'#FFFFFF',sole:'#7A5AF5',stripe:'#7A5AF5'}},
 {name:'비 오는 날',h:0.9,hd:1.07,nose:'short',eyeR:1.08,disc:'#BDE6F2',skin:SK[0],hair:{type:'short',col:'#5A3A2A',style:'bang'},hat:{type:'bucket',col:'#FFD23F',col2:'#F2B705'},eyes:'dot',seed:1.9,top:{type:'raincoat',col:'#FFD23F',arms:'long',collar:'#F2B705'},pants:{type:'shorts',col:'#3D6BE0'},shoe:{type:'boot',col:'#E5484D',sole:'#B8363B'}},
 {name:'로스터',disc:'#F2C9A0',build:'broad',h:1.02,brow:1.2,jaw:0.28,skin:SK[5],hair:{type:'short',col:'#3A2A22'},hat:{type:'beanie',col:'#2F8F83',col2:'#257368'},eyes:'dot',seed:1.45,stache:'#3A2A22',watch:'#2F3140',top:{type:'apron',col:'#E9B44C',col2:'#5A3A2A',arms:'short'},pants:{type:'long',col:'#3B4252'},shoe:{type:'boot',col:'#6B4A2E',sole:'#3A2A22'}}
];
const who=n=>CAST.find(k=>k.name===n);
