// 어떤 footage id를 쓰는 컴프의 모든 레이어 위치·크기·앵커 나열. 설정: probe_comp_layers_job.json {"aep","src_id","out"}
(function(){
var SELF=$.fileName; $.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), out=[];
app.beginSuppressDialogs();
try{
var P=openProject(C.aep);
for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(!(it instanceof CompItem)) continue;
  var hit=false; for(var j=1;j<=it.numLayers;j++){ var s=it.layer(j).source; if(s && s.id===C.src_id) hit=true; }
  if(!hit) continue;
  out.push("COMP "+it.name+" "+it.width+"x"+it.height);
  for(var j=1;j<=it.numLayers;j++){ var L=it.layer(j), T=L.property("ADBE Transform Group");
    var t=(L.inPoint+L.outPoint)/2;
    try{ out.push(j+" | "+L.name+" | id="+(L.source?L.source.id:"")+" | src="+(L.source?L.source.width+"x"+L.source.height:"")+" | pos="+T.property("ADBE Position").valueAtTime(t,false)+" | scale="+T.property("ADBE Scale").valueAtTime(t,false)+" | anchor="+T.property("ADBE Anchor Point").valueAtTime(t,false)+" | parent="+(L.parent?L.parent.index:"")+" | en="+L.enabled); }catch(e2){ out.push(j+" | "+L.name+" | ERR "+e2); }
  }
}
}catch(e){ out.push("ERR "+e+" "+e.line); }
writeText(C.out, out.join("\n"));
try{ app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(e){}
app.endSuppressDialogs(false);
})();
