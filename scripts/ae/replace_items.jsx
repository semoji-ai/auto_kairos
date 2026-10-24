// 일러스트·이미지 footage를 "글자 없는 판 + 영어 텍스트 레이어" 프리컴프로 교체.
// footage마다 같은 크기 컴프 __en_<id>: 판 PNG(k배 → scale 100/k) + 텍스트 레이어(위치·각도·색, 폭 넘으면 축소, 강조 구간 색).
// 그 footage를 소스로 쓰는 모든 레이어를 교체하고 collapse(연속 래스터화)를 켜서 확대돼도 선명하게.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={comps:0, text_layers:0, replaced:0, shrunk:0, emph:0, emph_failed:[], name_mismatch:[], not_found:[], unused:[], errors:[]};
function rgb(c){ return [c[0]/255, c[1]/255, c[2]/255]; }
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={}, comps=[];
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); byId[it.id]=it; if(it instanceof CompItem) comps.push(it); }
  var folder=P.items.addFolder("__en_raster");
  var made={};
  for(var j=0;j<C.jobs.length;j++){
    var J=C.jobs[j], src=byId[J.id];
    if(!src || !(src instanceof FootageItem)){ LOG.not_found.push(J.id); continue; }
    if(src.name.indexOf(J.name)<0 && J.name.indexOf(src.name)<0) LOG.name_mismatch.push(J.id+": "+src.name+" vs "+J.name);
    try{
      var png=P.importFile(new ImportOptions(new File(J.png))); png.parentFolder=folder;
      var dur=Math.max(src.duration||0, 3600);
      var comp=P.items.addComp("__en_"+J.id, J.w, J.h, src.pixelAspect||1, dur, 30); comp.parentFolder=folder;
      var pl=comp.layers.add(png); pl.property("ADBE Transform Group").property("ADBE Scale").setValue([J.scale, J.scale]);
      pl.property("ADBE Transform Group").property("ADBE Position").setValue([J.w/2, J.h/2]);
      pl.outPoint=dur;
      for(var t=0;t<J.texts.length;t++){
        var T=J.texts[t], L=comp.layers.addText(T.text);
        var sp=L.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value;
        td.resetCharStyle(); td.resetParagraphStyle();
        td.font=T.font; td.fontSize=T.size; td.applyFill=true; td.fillColor=rgb(T.base);
        td.applyStroke=false;
        td.justification=ParagraphJustification.CENTER_JUSTIFY; td.tracking=0;
        sp.setValue(td);
        if(sp.value.font!==T.font) LOG.errors.push(T.key+": 폰트 대체됨 "+T.font+" → "+sp.value.font);   // 폰트 없으면 AE가 조용히 바꿈
        var r=L.sourceRectAtTime(0,false);
        if(r.width>T.wmax && r.width>0){
          td=sp.value; td.fontSize=T.size*T.wmax/r.width; sp.setValue(td); LOG.shrunk++;
          r=L.sourceRectAtTime(0,false);
        }
        if(T.emph.length){
          try{
            td=sp.value;
            for(var e=0;e<T.emph.length;e++) td.characterRange(T.emph[e][0], T.emph[e][1]).fillColor=rgb(T.emph_color);
            sp.setValue(td); LOG.emph++;
          }catch(ee){ LOG.emph_failed.push(T.key+": "+String(ee)); }
        }
        var tr=L.property("ADBE Transform Group");
        tr.property("ADBE Anchor Point").setValue([r.left+r.width/2, r.top+r.height/2]);
        tr.property("ADBE Position").setValue([T.cx, T.cy]);
        tr.property("ADBE Rotate Z").setValue(T.angle);
        L.outPoint=dur; L.name=T.key;
        // 외곽선은 아래쪽 복제 레이어에 따로: 한 레이어에 외곽선을 켜면 다음 글자의 외곽선이 앞 글자 획을 덮어
        // 붙은 손글씨가 깨짐(Let's → Le'ts). 외곽선 레이어는 글자 속까지 외곽선 색으로 채워 틈이 없게, 보이는 두께 = strokeWidth/2
        if(T.stroke){
          var SL=L.duplicate(); SL.moveAfter(L); SL.name=T.key+"_stroke";
          var ssp=SL.property("ADBE Text Properties").property("ADBE Text Document"), std=ssp.value;
          std.applyFill=true; std.fillColor=rgb(T.stroke);
          std.applyStroke=true; std.strokeColor=rgb(T.stroke); std.strokeWidth=Math.max(1,T.stroke_w*2); std.strokeOverFill=true;
          ssp.setValue(std);
        }
        LOG.text_layers++;
      }
      made[J.id]=comp; LOG.comps++;
    }catch(err){ LOG.errors.push(J.id+": "+String(err)+" line "+err.line); }
  }
  // 소스 교체: 원래 프로젝트의 모든 컴프에서 해당 footage를 쓰는 레이어
  var used={};
  for(var c=0;c<comps.length;c++){
    var cp=comps[c];
    for(var l=1;l<=cp.numLayers;l++){
      var ly=cp.layer(l);
      try{
        if(!(ly instanceof AVLayer) || !ly.source || !made[ly.source.id]) continue;
        var nc=made[ly.source.id], lk=ly.locked; ly.locked=false;
        ly.replaceSource(nc, false);
        try{ ly.collapseTransformation=true; }catch(_c){}
        ly.locked=lk; used[nc.id]=1; LOG.replaced++;
      }catch(err2){ LOG.errors.push(cp.name+"#"+l+": "+String(err2)); }
    }
  }
  for(var id in made) if(made.hasOwnProperty(id) && !used[made[id].id]) LOG.unused.push(id);
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
