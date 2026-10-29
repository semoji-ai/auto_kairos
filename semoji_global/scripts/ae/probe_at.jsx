// 디버그: 컴프의 특정 시각에 보이는 레이어를 프리컴프까지 따라가며 나열.  job: {aep, comp, t, out, depth}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), OUT=[];
function walk(comp,t,d,path){
  if(d>C.depth) return;
  for(var i=1;i<=comp.numLayers;i++){
    var L=comp.layer(i);
    if(!L.enabled || t<L.inPoint || t>=L.outPoint) continue;
    var e={path:path, idx:i, name:L.name, d:d};
    if(L instanceof TextLayer){ try{ e.text=String(L.property("ADBE Text Properties").property("ADBE Text Document").valueAtTime(t,false).text);}catch(_){} }
    if(L.source){ e.src=L.source.name; e.src_id=L.source.id; e.type=(L.source instanceof CompItem)?"comp":"footage"; }
    OUT.push(e);
    if(L.source && L.source instanceof CompItem){
      var lt=t-L.startTime; try{ if(L.timeRemapEnabled) lt=L.property("ADBE Time Remapping").valueAtTime(t,false); else lt=(t-L.startTime)*(L.stretch/100>0?100/L.stretch:1);}catch(_){}
      walk(L.source, lt, d+1, path+"/"+L.source.name);
    }
  }
}
app.beginSuppressDialogs();
try{ var P=openProject(C.aep), comp=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp){comp=it;break;} }
  walk(comp, C.t, 0, C.comp); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ OUT.push({error:String(e)+" line "+e.line}); }
writeText(C.out, S(OUT));
app.endSuppressDialogs(false);
})();
