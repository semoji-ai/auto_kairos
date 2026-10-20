// 감정 영상 영어판: 원본 글자 덩어리 트랙마다 텍스트 레이어(위치·크기·불투명도 키프레임, 고정 기울기)를 만들어
// 알파 포함 mov로 렌더 큐에 넣고 저장(렌더는 aerender). job: build_emotion_en_job.json
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={layers:0, keys:0, errors:[]};
function rgb(c){ return [c[0]/255, c[1]/255, c[2]/255]; }
app.beginSuppressDialogs();
try{
  try{ if(app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}
  var P=app.newProject();
  var comp=P.items.addComp("emotion_en", C.w, C.h, 1, C.dur, C.fps);
  for(var k=0;k<C.tracks.length;k++){
    var T=C.tracks[k], L=comp.layers.addText(C.text);
    var sp=L.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value;
    td.resetCharStyle(); td.resetParagraphStyle();
    td.font=C.font; td.fontSize=100; td.applyFill=true; td.fillColor=rgb(T.fill);
    td.applyStroke=true; td.strokeColor=rgb(T.stroke); td.strokeWidth=Math.max(1,T.stroke_w*2); td.strokeOverFill=false;
    td.justification=ParagraphJustification.CENTER_JUSTIFY;
    sp.setValue(td);
    if(sp.value.font!==C.font) LOG.errors.push("폰트 대체됨 "+C.font+" → "+sp.value.font);
    var r=L.sourceRectAtTime(0,false);
    var base=100*T.h_ref/r.height;
    var tr=L.property("ADBE Transform Group");
    tr.property("ADBE Anchor Point").setValue([r.left+r.width/2, r.top+r.height/2]);
    tr.property("ADBE Rotate Z").setValue(T.rot);
    var pos=tr.property("ADBE Position"), sc=tr.property("ADBE Scale"), op=tr.property("ADBE Opacity");
    for(var i=0;i<T.keys.length;i++){
      var K=T.keys[i], t=i/C.fps;
      if(K===null){ op.setValueAtTime(t,0); LOG.keys++; continue; }
      pos.setValueAtTime(K.t,[K.cx,K.cy]);
      sc.setValueAtTime(K.t,[base*K.scale, base*K.scale]);
      op.setValueAtTime(K.t,100*K.alpha);
      LOG.keys+=3;
    }
    L.name="laugh_"+k; LOG.layers++;
  }
  var rq=P.renderQueue.items.add(comp);
  var om=rq.outputModule(1); om.applyTemplate("High Quality with Alpha");
  om.file=new File(C.render_to);
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
