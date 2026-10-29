// 컴프 그래프: 컴프마다 레이어(소스 id, in/out, startTime, stretch, enabled, 오디오/비디오, timeRemap) 목록.
// 설정 graph_job.json {aep, out}. 실제 렌더 도달 여부 계산은 python(scripts/reach.py)에서.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), res={aep:C.aep, comps:{}, items:{}, rq:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep);
  for(var i=1;i<=P.numItems;i++){
    var it=P.item(i);
    if(it instanceof CompItem){
      var Ls=[];
      for(var j=1;j<=it.numLayers;j++){
        var L=it.layer(j), src=null;
        try{ if(L.source) src=L.source.id; }catch(e){}
        var tr=false; try{ tr=L.timeRemapEnabled; }catch(e){}
        Ls.push({i:j, name:L.name, src:src, "in":L.inPoint, "out":L.outPoint, st:L.startTime, sx:L.stretch,
                 en:L.enabled, au:(function(){try{return L.hasAudio&&L.audioEnabled;}catch(e){return false;}})(),
                 vid:L.hasVideo, tr:tr, adj:(function(){try{return L.adjustmentLayer;}catch(e){return false;}})(),
                 matte:(function(){try{return L.isTrackMatte;}catch(e){return false;}})()});
      }
      res.comps[it.id]={name:it.name, dur:it.duration, fps:it.frameRate, wa:[it.workAreaStart, it.workAreaStart+it.workAreaDuration], layers:Ls};
    } else if(it instanceof FootageItem){
      var f=""; try{ f=it.mainSource.file?it.mainSource.file.fsName:""; }catch(x){}
      var mp=""; try{ mp=it.mainSource.missingFootagePath; }catch(x){}
      res.items[it.id]={name:it.name, file:f, missing:it.footageMissing, mpath:mp, solid:(function(){try{return it.mainSource instanceof SolidSource;}catch(x){return false;}})()};
    }
  }
  for(var r=1;r<=P.renderQueue.numItems;r++){ var q=P.renderQueue.item(r); res.rq.push({comp:q.comp.id, name:q.comp.name, status:String(q.status), start:q.timeSpanStart, dur:q.timeSpanDuration}); }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ res.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(res));
app.endSuppressDialogs(false);
})();
