/* =====================================================================
   POSE KEYS on the 360° rig
   a track = list of keys {t,d,e,...fields}; keys accumulate and ease from the pose before them.
   angles in the scripts are degrees (yaw 0 = facing camera, 90 = facing screen-right, 180 = back).
   ===================================================================== */
const REST3={x:0,z:0,y:0,yaw:0,headTurn:0,walk:0,gait:'walk',hipY:1.49,lean:0.03,tl:1,nod:0,swR:1,swL:1,waveR:0,waveL:0,cheer:0,clap:0,look:[0,0],brow:0,talk:0,blink:0,propRot:0,steam:0,mood:null,handR:null,handL:null,propR:null,propL:null,armR:null,armL:null};
function blendF(f,a,b,k){if(f==='armR'||f==='armL')return{A:a,B:b,k};if(typeof b==='number')return typeof a==='number'?lerp(a,b,k):b;if(Array.isArray(b))return Array.isArray(a)?b.map((v,i)=>lerp(a[i],v,k)):b;return b}
function evalTrack(keys,t){let prev=null,cur={},k=1;
 for(const key of keys){if(key.t>t)break;prev=cur;cur=Object.assign({},cur,key);const d=key.d||0;k=(key.e||E.io)(d>0?cl((t-key.t)/d):1)}
 const out={};for(const f in cur){if(f==='t'||f==='d'||f==='e')continue;const b=cur[f],a=prev&&f in prev?prev[f]:b;out[f]=blendF(f,a,b,k)}return out}
function poseOfK(ac,t){const q=Object.assign({},REST3);for(const tr of ac.tracks)Object.assign(q,evalTrack(tr,t));q.seed=ac.seed||0;q.sc=(ac.sc||1)*(ac.ch.h||1);
 let w=0;for(const t0 of ac.kicks||[]){const u=t-t0;if(u>0&&u<1.6)w+=Math.exp(-6*u)*Math.sin(17*u)}q.kick=w;q.yaw*=D2R;q.headTurn*=D2R;
 q.face={mood:q.mood,talk:q.talk,look:q.look,brow:q.brow,blink:q.blink};if(ac.live)ac.live(q,t);return pose360(q,t+q.seed)}
function drawActor3(ac,t){const P=poseOfK(ac,t),sc=(ac.sc||1)*(ac.ch.h||1);c.save();c.translate(P.x,(ac.gy||0)+P.z*PITCH);c.scale(sc,sc);
 if(!ac.noShadow)for(const L of P.legs){const h=cl((L.lift+P.y)/0.3);c.beginPath();c.ellipse(L.a[0]+0.14*P.sy,ANK+L.a[1]+L.lift+0.02,0.4*(1-0.35*h),0.07*(1-0.35*h),0,0,TAU);c.fillStyle=`rgba(60,30,10,${0.18*(1-0.6*h)})`;c.fill()}
 c.translate(0,-P.y);drawChar3(ac.ch,P);
 /* a hand target the arm cannot reach is logged (tools/reach.js) and, with ?debug=1, marked in red */
 for(const A of P.arms)if(A.miss>0.03){(window.MISS=window.MISS||[]).push([ac.ch.name,A.side<0?'armR':'armL',+A.miss.toFixed(2),A.shw.map(v=>+v.toFixed(2)),+A.reach.toFixed(2)]);if(Q.get('debug')){c.beginPath();c.arc(A.wr[0],A.wr[1],0.16,0,TAU);c.strokeStyle='#FF2D2D';c.lineWidth=0.05;c.stroke()}}
 c.restore();return P}
REST3.fill=0;
