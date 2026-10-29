// 디버그: 컴프의 이름이 match인 레이어의 blendingMode·불투명도·스케일·위치·in/out.  job: {aep, comp, match, out}
(function(){
var SELF=$.fileName; $.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), OUT=[];
app.beginSuppressDialogs();
try{ var P=openProject(C.aep), comp=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp) comp=it; }
  for(var j=1;j<=comp.numLayers;j++){ var L=comp.layer(j); if(L.name!==C.match) continue; var t=L.property("ADBE Transform Group");
    OUT.push({idx:j, name:L.name, blend:String(L.blendingMode), op:t.property("ADBE Opacity").value, opKeys:t.property("ADBE Opacity").numKeys, scale:t.property("ADBE Scale").value, pos:t.property("ADBE Position").value, "in":L.inPoint, "out":L.outPoint, src:L.source?L.source.name:"", effects:L.property("ADBE Effect Parade").numProperties}); }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ OUT.push({error:String(e)+" line "+e.line}); }
writeText(C.out, S(OUT)); app.endSuppressDialogs(false);
})();
