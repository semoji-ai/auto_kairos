/* props & small shapes. PROPS.name=(P,ux,uy)=>{} is drawn at the grip point of the hand that holds it (propR/propL in a key) */
/* ---------- small things: beans, cherries, sacks, tools ---------- */
function cherryShape(x,y,r,col){shape(circ(x,y,r),col||'#D63A2F');shape(circ(x-r*0.3,y-r*0.32,r*0.27),'rgba(255,255,255,0.45)')}
function beanShape(x,y,w,col,rot){c.save();c.translate(x,y);c.rotate(rot||0);shape(ell(0,0,w*0.5,w*0.34),col);line(()=>{c.beginPath();c.moveTo(-w*0.36,0);c.bezierCurveTo(-w*0.12,-w*0.15,w*0.12,w*0.15,w*0.36,0)},w*0.075,'rgba(40,15,5,0.32)');c.restore()}
function basketShape(fill){const n=Math.round(cl(fill)*8);for(let i=0;i<n;i++)cherryShape(-0.22+(i%4)*0.147+(i>3?0.07:0),-0.235-(i>3?0.09:0),0.078);
 const b=poly(-0.31,-0.2,0.31,-0.2,0.22,0.24,-0.22,0.24);shape(b,'#D2A96B');c.save();b();c.clip();c.fillStyle='rgba(120,70,20,0.22)';for(let y=-0.12;y<0.24;y+=0.11)c.fillRect(-0.4,y,0.8,0.045);for(let x=-0.28;x<0.3;x+=0.115)c.fillRect(x,-0.2,0.02,0.5);c.restore();shape(rr(-0.345,-0.25,0.69,0.09,0.045),'#B4874C')}
function sackShape(bean){const b=rr(-0.32,-0.34,0.64,0.7,0.14);shape(poly(-0.11,-0.3,0.11,-0.3,0.2,-0.52,-0.2,-0.52),'#D6B57E');shape(b,'#CDAA72');c.save();b();c.clip();F('rgba(70,30,10,0.1)',0.14,-0.4,0.3,0.9);c.fillStyle='rgba(120,80,30,0.2)';for(let y=-0.22;y<0.36;y+=0.14)c.fillRect(-0.4,y,0.8,0.02);c.restore();F('#8A6A3A',-0.13,-0.355,0.26,0.05);beanShape(0,0.03,0.3,bean||'#8DB45A',-0.5)}
function beanbagShape(){const b=rr(-0.22,-0.3,0.44,0.58,0.04);shape(b,'#8B5A3C');c.save();b();c.clip();F('#74492E',-0.3,-0.3,0.6,0.13);F('rgba(0,0,0,0.12)',0.1,-0.3,0.2,0.7);c.restore();shape(circ(0,0.06,0.125),'#F3E7D3');beanShape(0,0.06,0.17,'#5E3620',-0.5)}
const KTIP=[0.9,-0.22];
function kettleShape(){line(()=>{c.beginPath();c.moveTo(0.16,-0.17);c.quadraticCurveTo(-0.1,-0.16,-0.04,0);c.quadraticCurveTo(0,0.14,0.12,0.16)},0.055,'#8A5A3B');
 line(()=>{c.beginPath();c.moveTo(0.5,0.12);c.bezierCurveTo(0.72,0.1,0.66,-0.2,KTIP[0],KTIP[1])},0.05,'#2F343E');
 const b=poly(0.15,-0.2,0.45,-0.2,0.55,0.22,0.07,0.22);shape(b,'#3A3F4A');c.save();b();c.clip();F('rgba(255,255,255,0.14)',0.13,-0.2,0.09,0.5);F('rgba(0,0,0,0.18)',0.07,0.14,0.5,0.1);c.restore();shape(rr(0.17,-0.26,0.26,0.07,0.03),'#2F343E');shape(circ(0.3,-0.29,0.035),'#8A5A3B')}
function rakeShape(){line(()=>{c.beginPath();c.moveTo(-0.28,0);c.lineTo(1.45,0)},0.055,'#B98A56');shape(poly(1.36,-0.03,1.52,-0.03,1.64,0.2,1.24,0.2),'#8A6238');line(()=>{c.beginPath();for(let i=0;i<5;i++){const x=1.28+i*0.08;c.moveTo(x,0.2);c.lineTo(x,0.29)}},0.03,'#74502C')}
function scoopShape(fill,col){line(()=>{c.beginPath();c.moveTo(0.1,0);c.lineTo(-0.1,0)},0.05,'#8A5A3B');if(fill>0.05)for(let i=0;i<4;i++)beanShape(-0.4+i*0.085,-0.1-(i%2)*0.025,0.115,col||'#6B3F26',i);const b=rr(-0.46,-0.1,0.38,0.2,[0.1,0.03,0.03,0.1]);shape(b,'#C9CED6');c.save();b();c.clip();F('rgba(0,0,0,0.12)',-0.5,0.02,0.5,0.1);c.restore()}
PROPS.basket=P=>{c.save();c.translate(0.02,0.08);basketShape(P.fill);c.restore()};
PROPS.cherry=(P,ux,uy)=>cherryShape(ux*0.13,uy*0.13,0.07);
PROPS.rake=P=>{c.save();c.rotate(P.propRot);rakeShape();c.restore()};
PROPS.scoop=P=>{c.save();c.rotate(P.propRot);scoopShape(P.fill);c.restore()};
PROPS.trier=P=>{c.save();c.rotate(P.propRot);c.scale(-1,1);scoopShape(1,'#B58A3E');c.restore()};
PROPS.kettle=P=>{c.save();c.rotate(P.propRot);kettleShape();c.restore()};
PROPS.sack=()=>{c.save();c.translate(0.02,0.3);c.scale(0.85,0.85);sackShape();c.restore()};
PROPS.beanbag=()=>{c.save();c.translate(0.02,0.12);beanbagShape();c.restore()};
