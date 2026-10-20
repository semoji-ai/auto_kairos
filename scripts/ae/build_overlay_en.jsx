// 영상 에셋 영어판(인트로 타이틀·아웃트로): 원본 영상 위에 판(단색)과 텍스트를 얹는다.
// groups[]: keys가 없으면 메인 컴프에 바로, keys가 있으면 프리컴프(still + 판 + 텍스트)를 만들어 프레임별 위치·크기로 움직임.
// job: build_overlay_en_job.json {src, w, h, fps, dur, groups, save_as, render_to, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={plates:0, texts:0, keys:0, errors:[]};
function rgb(c){ return [c[0]/255, c[1]/255, c[2]/255]; }
function addPlate(comp, p){
  var L=comp.layers.addSolid(rgb(p.color), "plate", Math.max(1,Math.round(p.box[2])), Math.max(1,Math.round(p.box[3])), 1, C.dur);
  L.property("ADBE Transform Group").property("ADBE Position").setValue([p.box[0]+p.box[2]/2, p.box[1]+p.box[3]/2]);
  if(p.from>0) L.inPoint=p.from;
  LOG.plates++;
}
function addText(comp, T){
  var L=comp.layers.addText(T.text);
  var sp=L.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value;
  td.resetCharStyle(); td.resetParagraphStyle();
  td.font=T.font; td.fontSize=100; td.applyFill=true; td.fillColor=rgb(T.color); td.applyStroke=false;
  td.justification=(T.just==="left")?ParagraphJustification.LEFT_JUSTIFY:ParagraphJustification.CENTER_JUSTIFY;
  sp.setValue(td);
  if(sp.value.font!==T.font) LOG.errors.push(T.text+": 폰트 대체됨 "+T.font+" → "+sp.value.font);
  var r=L.sourceRectAtTime(0,false);
  var size=100*T.h/r.height;
  if(r.width*size/100>T.wmax) size=100*T.wmax/r.width;
  td=sp.value; td.fontSize=size; sp.setValue(td);
  r=L.sourceRectAtTime(0,false);
  var ax=(T.just==="left")?r.left:(r.left+r.width/2);
  var tr=L.property("ADBE Transform Group");
  tr.property("ADBE Anchor Point").setValue([ax, r.top+r.height/2]);
  tr.property("ADBE Position").setValue([T.x, T.y]);
  if(T.from>0) L.inPoint=T.from;
  L.outPoint=C.dur; LOG.texts++;
}
app.beginSuppressDialogs();
try{
  try{ if(app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}
  var P=app.newProject();
  var main=P.items.addComp("overlay_en", C.w, C.h, 1, C.dur, C.fps);
  var srcItem=P.importFile(new ImportOptions(new File(C.src)));
  var base=main.layers.add(srcItem); base.startTime=0;
  for(var g=0;g<C.groups.length;g++){
    var G=C.groups[g];
    if(!G.keys){
      var ims=G.images||[];
      for(var m=0;m<ims.length;m++){
        var IL=main.layers.add(P.importFile(new ImportOptions(new File(ims[m].png))));
        IL.outPoint=C.dur; if(ims[m].from>0) IL.inPoint=ims[m].from;
      }
      for(var i=0;i<G.plates.length;i++) addPlate(main, G.plates[i]);
      for(var j=0;j<G.texts.length;j++) addText(main, G.texts[j]);
      continue;
    }
    var pc=P.items.addComp("group_"+g, C.w, C.h, 1, C.dur, C.fps);
    if(G.still){ var st=pc.layers.add(P.importFile(new ImportOptions(new File(G.still)))); st.outPoint=C.dur; }
    for(var a=0;a<G.plates.length;a++) addPlate(pc, G.plates[a]);
    for(var b=0;b<G.texts.length;b++) addText(pc, G.texts[b]);
    var L=main.layers.add(pc), tr=L.property("ADBE Transform Group");
    tr.property("ADBE Anchor Point").setValue(G.anchor);
    var pos=tr.property("ADBE Position"), sc=tr.property("ADBE Scale"), op=tr.property("ADBE Opacity");
    for(var k=0;k<G.keys.length;k++){
      var K=G.keys[k], t=k/C.fps;
      if(K===null){ op.setValueAtTime(t,0); LOG.keys++; continue; }
      op.setValueAtTime(K.t,100); pos.setValueAtTime(K.t,[K.cx,K.cy]); sc.setValueAtTime(K.t,[100*K.s,100*K.s]);
      LOG.keys+=3;
    }
    // 키 사이를 보간하지 않고 프레임마다 그대로(원본 프레임 측정값)
    for(var q=1;q<=op.numKeys;q++) op.setInterpolationTypeAtKey(q, KeyframeInterpolationType.HOLD);
  }
  var rq=P.renderQueue.items.add(main);
  var om=rq.outputModule(1); om.applyTemplate("High Quality");
  om.file=new File(C.render_to);
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
