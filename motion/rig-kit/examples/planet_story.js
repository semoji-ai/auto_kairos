/* EXAMPLE — look preset 'cinematic': 작은 행성 위에서 커다란 지구를 가리키는 학생 (어두운 남보라, 빛나는 초점 하나, 여러 겹의 layer(), stars(), air()) */
const SP1=(()=>{
 const N=nar(['밤하늘 너머, 푸른 지구가 떠 있습니다.','우리가 아는 모든 이야기가 저 작은 별 위에서 일어났죠.']);
 const T2=N[1].t0,EX=10.1,EY=-4.05,ER=2.35;      /* Earth: the focal light of the shot */
 const kid={ch:who('학생'),seed:0.3,gy:-0.9,kicks:[T2+0.45],tracks:[
  [{t:0,d:0,x:4.2,z:0.35,yaw:90},{t:0,d:1.1,e:E.lin,x:4.2+SPEED('walk')*0.55*1.1}],
  [{t:0,d:0,walk:0.55},{t:1.1,d:0.3,walk:0,yaw:48}],
  [{t:0,d:0,mood:'smile',nod:0,look:[0.3,0]},{t:1.3,d:0.6,headTurn:14,nod:-0.4,look:[0.8,-0.9]},{t:T2+0.2,d:0.3,mood:'grin',brow:0.6}],
  [{t:0,d:0,armR:null,armL:null},{t:T2+0.25,d:0.45,e:E.back,armR:{hand:[6.47,-2.33,0.72]},handR:'point'},{t:N[1].t1-0.2,d:0.5,armR:{a:0.3,b:0.4}}]]};

 function space(t){F(lin(0,-6.3,0,1,'#06051A','#0F0C33','#1E1650','#2C1E5E'),0,-6.3,VW,7.6);
  glow(3.2,-4.6,3.6,'#7A4FD8',0.45);glow(1.2,-2.4,2.6,'#2F8FB8',0.3);glow(12.2,-1.6,3.2,'#C05A9A',0.28);           /* nebula haze */
  stars(t,{n:220,y0:-6.4,y1:0.4,seed:1});
  {const u=((t*0.35)%3)/3;if(u<0.25){const k=u/0.25,x=lerp(1.0,4.5,k),y=lerp(-5.9,-4.8,k);c.save();c.globalAlpha=Math.sin(Math.PI*k);line(()=>{c.beginPath();c.moveTo(x,y);c.lineTo(x-0.9,y-0.28)},0.025,'#FFFFFF');c.restore()}}}  /* shooting star */
 function ringed(t){const x=2.2,y=-3.5;c.save();c.translate(x,y);c.rotate(-0.25);
  line(()=>{c.beginPath();c.ellipse(0,0,0.95,0.2,0,Math.PI,TAU)},0.06,'#C9A6E8');shape(circ(0,0,0.5),lin(-0.5,-0.5,0.5,0.5,'#E2B6D8','#6E4A9E'));line(()=>{c.beginPath();c.ellipse(0,0,0.95,0.2,0,0,Math.PI)},0.06,'#E8CFF6');c.restore();glow(x,y,1.2,'#C9A6E8',0.25)}
 function moon(){shape(circ(6.4,-5.4,0.28),lin(6.2,-5.6,6.6,-5.2,'#F2EEFF','#8D86B8'));glow(6.4,-5.4,0.8,'#CFC8FF',0.35)}
 function earth(t){glow(EX,EY,ER*2.1,'#4FB8FF',0.75);glow(EX,EY,ER*1.25,'#9EE3FF',0.55);                  /* atmosphere */
  const e=circ(EX,EY,ER);shape(e,rad(EX+ER*0.35,EY-ER*0.35,ER*1.5,'#5FD0FF','#1E7FD0','#123A86'));c.save();e();c.clip();
  c.save();c.translate(EX,EY);c.rotate(t*0.025);const L=[[-0.9,-1.0,0.75,0.5,0.4],[-0.55,0.1,0.45,0.85,-0.3],[0.75,-0.6,0.6,0.42,0.2],[0.95,0.55,0.38,0.62,0.5],[0.1,1.6,0.9,0.3,0],[-1.6,0.7,0.3,0.45,0.3]];
   for(const[x,y,rx,ry,r]of L)shape(ell(x,y,rx,ry,r),lin(x-rx,y-ry,x+rx,y+ry,'#8FE08A','#3E9C62'));
   c.restore();
   /* cloud bands: soft partial latitude rings that wrap round the sphere and drift */
   c.save();c.lineCap='round';for(const[ph,a0,len,w]of[[-0.62,0.3,1.6,0.16],[-0.25,1.4,1.3,0.12],[0.12,0.2,1.9,0.18],[0.45,1.1,1.4,0.13],[0.75,0.5,1.2,0.1]]){const cyy=EY+ER*Math.sin(ph)*0.92,rx=ER*Math.cos(ph),ry=rx*0.3,s0=a0+t*0.05;
    for(const[k,al]of[[1.9,0.16],[1,0.42]])line(()=>{c.beginPath();c.ellipse(EX,cyy,rx,ry,-0.18,s0,s0+len)},w*k,`rgba(255,255,255,${al})`)}c.restore();
  /* night side toward the lower left */
  shape(e,rad(EX-ER*0.75,EY+ER*0.7,ER*1.55,'rgba(8,6,40,0.95)',[0.45,'rgba(8,6,40,0.75)'],'rgba(8,6,40,0)'));c.restore();
  line(()=>{c.beginPath();c.arc(EX,EY,ER-0.03,-2.6,0.9)},0.06,'rgba(200,245,255,0.8)')}           /* lit limb */
 function farHills(){shape(()=>{c.beginPath();c.moveTo(-0.5,-0.8);c.bezierCurveTo(2,-1.6,4,-1.2,6,-1.0);c.bezierCurveTo(8.5,-0.7,10.5,-1.5,13.4,-1.1);c.lineTo(13.4,1);c.lineTo(-0.5,1);c.closePath()},lin(0,-1.6,0,0,'#3A2C78','#241A55'));
  line(()=>{c.beginPath();c.moveTo(-0.5,-0.8);c.bezierCurveTo(2,-1.6,4,-1.2,6,-1.0);c.bezierCurveTo(8.5,-0.7,10.5,-1.5,13.4,-1.1)},0.03,'rgba(140,210,255,0.45)')}
 function farPlanet(){shape(circ(11.8,1.9,3.2),lin(9,-1.3,13,3,'#5A3E9E','#21184E'));line(()=>{c.beginPath();c.arc(11.8,1.9,3.18,-2.6,-1.2)},0.04,'rgba(190,150,255,0.6)');shape(circ(0.4,1.6,1.9),lin(-1,-0.3,1.5,2,'#2E4E8E','#151A48'));line(()=>{c.beginPath();c.arc(0.4,1.6,1.88,-1.9,-0.6)},0.035,'rgba(140,210,255,0.55)')}
 function planet(){const R=6,cx=5.9,cy=R-0.85;shape(circ(cx,cy,R),lin(0,-0.2,0,2,'#3B3486','#1C1648'));
  line(()=>{c.beginPath();c.arc(cx,cy,R-0.02,-2.3,-0.7)},0.05,'rgba(150,220,255,0.7)');                          /* earthshine on the horizon */
  c.save();circ(cx,cy,R)();c.clip();for(const[x,y,r]of[[3.6,-0.1,0.42],[8.3,-0.25,0.3],[7.2,0.3,0.5],[4.7,-0.6,0.22]]){shape(ell(x,y,r,r*0.32),'#251E5C');shape(ell(x+r*0.12,y-r*0.06,r*0.82,r*0.22),'#17123E');line(()=>{c.beginPath();c.ellipse(x,y,r,r*0.32,0,-0.2,1.9)},0.025,'rgba(150,220,255,0.35)')}c.restore()}

 return{N,dur:N.dur,tag:'∞',title:'창백한 푸른 점',cam:[7.4,-2.8,1,1.07,0.35,-0.1],board:[1.6,T2+1.2],
  look:{preset:'cinematic',light:{dir:[0.85,-0.5]},palette:{light:'#BFE9FF',shadow:'#0E0B30'},air:{preset:'motes',col:'#BFE9FF',n:34,alpha:0.45}},
  draw(t){space(t);layer(0.95,()=>{ringed(t);moon()},0.15);layer(0.85,()=>earth(t),0);layer(0.6,farPlanet,0);planet();drawActor3(kid,t)}}})();

const SCENES=[SP1];
