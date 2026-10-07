/* TEMPLATE — copy this file, rename, and replace the scene.
   Build:  python3 tools/build.py my_story.js my_story.html
   Look:   node tools/shot.js my_story.html '[[1.5,"f1.png"],[4.0,"f2.png"]]'   (then actually open the PNGs)
   Render: node tools/render.js my_story.html my_story.mp4 */

const S1=(()=>{
 /* 1) narration first. One line = one subtitle = one beat of action. */
 const N=nar(['우산을 들고 걸어오던 사람이 멈춰 섭니다.','그리고 하늘을 올려다봅니다.']);
 const V=SPEED('walk'),stopX=6.4,tw=N[0].t1-0.3;          /* arrive just before line 1 ends */

 /* 2) actors. Each track is an independent channel; a key eases from the state before it.
       Keep t+d of a key <= t of the next key in the same track, or the pose jumps. */
 const kid={ch:who('비 오는 날'),seed:0.2,kicks:[tw+0.03],tracks:[
  [{t:0,d:0,x:stopX-V*tw,z:0.35},{t:0,d:tw,e:E.lin,x:stopX}],          /* where */
  [{t:0,d:0,yaw:90},{t:tw,d:0.4,yaw:20}],                               /* facing: 90 = screen-right, 0 = camera */
  [{t:0,d:0,walk:1},{t:tw,d:0.25,walk:0}],                              /* gait */
  [{t:0,d:0,armR:null},{t:N[1].t0+0.2,d:0.35,e:E.back,armR:{a:0.25,ab:2.55,b2:0.25},handR:'point'}],   /* raised sideways: reads from the front (a forward point would foreshorten) */
  [{t:0,d:0,mood:'smile'},{t:N[1].t0,d:0.3,nod:-0.5,look:[0.3,-0.8],brow:1,mood:'o'}]]};       /* face */

 /* 3) the set: flat fills, no outlines, back to front. World units: x 0..12.8, ground y=0, up is negative. */
 function back(t){F('#CFE9F7',0,-6.3,VW,6.3);cloud(3+0.1*t,-5.0,0.9);cloud(8.5+0.07*t,-4.4,0.7);
  shape(circ(10.6,-4.8,0.65),'#FFE9A8');tree(2.2,0,1.0,'#6DB56D');tree(11.2,0,0.85,'#7CC07C');
  F('#B9DDA6',0,-0.9,VW,0.9);F('#DAD3C7',0,0,VW,1.3);F('#C9C1B4',0,0,VW,0.06)}
 function fx(t){const k=popK(t,N[1].t0+0.5,0.3);if(k>0){bubble(8.0,-4.6,1.2,1.1,k,0);label('!',0,0.03,0.8,'#C8553A');c.restore()}}

 return{N,dur:N.dur,tag:'01',title:'템플릿',cam:[6.4,-2.4,1,1.04],draw(t){back(t);drawActor3(kid,t);fx(t)}}})();

const SCENES=[S1];
