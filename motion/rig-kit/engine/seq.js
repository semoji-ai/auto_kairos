/* ---------- sequencing: scenes back to back, narration as subtitles ---------- */
const SCN=SCENES,NARR=[];let DUR=0;for(const s of SCN){s.t0=DUR;for(const n of s.N)NARR.push({t0:DUR+n.t0,t1:DUR+n.t1,text:n.text,scene:s.tag+' '+s.title});DUR+=s.dur}window.NARR=NARR;
function caption(t){if(Q.get('nosub'))return;const n=NARR.find(n=>t>=n.t0-0.1&&t<=n.t1+0.25);if(!n)return;const a=cl((t-n.t0+0.1)/0.14)*cl((n.t1+0.25-t)/0.14);c.save();c.setTransform(1,0,0,1,0,0);c.globalAlpha=a;c.font=`700 44px ${FONT}`;const w=c.measureText(n.text).width+76;c.beginPath();c.roundRect(W/2-w/2,966,w,78,22);c.fillStyle='rgba(43,26,16,0.88)';c.fill();c.fillStyle='#FFFFFF';c.textAlign='center';c.textBaseline='middle';c.fillText(n.text,W/2,1007);c.restore()}
function render(t){c.setTransform(1,0,0,1,0,0);c.fillStyle=BG;c.fillRect(0,0,W,H);const tt=Math.max(0,Math.min(t,DUR-1e-3));let i=0;while(i<SCN.length-1&&tt>=SCN[i].t0+SCN[i].dur)i++;const sc=SCN[i],lt=tt-sc.t0;
 useLook(resolveLook(sc));
 world();c.save();c.beginPath();c.rect(0,-GY/U,VW,H/U);c.clip();CAM={fx:0,fy:0,z:1,cx:0,cy:0};
 /* cam:[fx,fy,z0,z1,panX,panY]: zoom z0→z1 about (fx,fy); the optional pan slides the view centre by (panX,panY) over the scene */
 if(sc.cam){const[fx,fy,z0,z1,px,py]=sc.cam,u=sm(lt/sc.dur),z=lerp(z0,z1,u),cx=fx+(px||0)*u,cy=fy+(py||0)*u;CAM={fx,fy,z,cx,cy};c.translate(fx,fy);c.scale(z,z);c.translate(-cx,-cy)}
 sc.draw(lt);if(LK.on&&LK.air)for(const a of[].concat(LK.air))air(lt,a);c.restore();c.setTransform(1,0,0,1,0,0);finish(tt);
 {const k=popK(lt,0.15,0.35)*(sc.noTag?cl((sc.noTag-lt)/0.2):1);if(k>0.01){c.font=`900 30px ${FONT}`;const w1=c.measureText(sc.tag).width+44;c.font=`900 34px ${FONT}`;const w2=c.measureText(sc.title).width+56;c.save();c.translate(56,56);c.scale(k,k);c.beginPath();c.roundRect(0,0,w1+w2,64,32);c.fillStyle='#FFFFFF';c.fill();c.beginPath();c.roundRect(0,0,w1,64,32);c.fillStyle=INK;c.fill();
  c.textBaseline='middle';c.textAlign='center';c.font=`900 30px ${FONT}`;c.fillStyle='#FFFFFF';c.fillText(sc.tag,w1/2,34);c.font=`900 34px ${FONT}`;c.fillStyle=INK;c.fillText(sc.title,w1+w2/2-4,34);c.restore()}}
 caption(tt);const a=Math.max(1-lt/0.22,(lt-(sc.dur-0.18))/0.18);if(a>0){c.globalAlpha=cl(a);c.fillStyle=BG;c.fillRect(0,0,W,H);c.globalAlpha=1}}
let time=0,done=false;
function step(dt){render(time);time+=dt;if(time>=DUR-1e-6)done=true;return done}
window.step=step;window.renderAt=t=>render(t);window.DUR=DUR;
if(Q.get('live')){let last=performance.now();(function loop(n){const dt=(n-last)/1000;last=n;time=(time+dt)%DUR;render(time);requestAnimationFrame(loop)})(last)}
