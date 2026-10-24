// 디버그: 파트 컴프 '#자막' 첫 텍스트 레이어의 정렬·위치·앵커·상자와 자막바 위치를 기록.  job: {aep, comp, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), OUT={};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), main=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp) main=it; }
  for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j);
    if(L.name==="자막바"){ var r=L.sourceRectAtTime(L.inPoint+1,false), t=L.property("ADBE Transform Group");
      OUT.bar={rect:[r.left,r.top,r.width,r.height], pos:t.property("ADBE Position").value, anchor:t.property("ADBE Anchor Point").value, scale:t.property("ADBE Scale").value}; }
    if(L.source instanceof CompItem && L.source.name.indexOf("#자막")===0){
      OUT.sub_layer={pos:L.property("ADBE Transform Group").property("ADBE Position").value, anchor:L.property("ADBE Transform Group").property("ADBE Anchor Point").value, w:L.source.width};
      var S2=L.source;
      for(var q=1;q<=S2.numLayers;q++){ var T=S2.layer(q); if(!(T instanceof TextLayer)) continue;
        var td=T.property("ADBE Text Properties").property("ADBE Text Document").value, tr=T.property("ADBE Transform Group"), rr=T.sourceRectAtTime(T.inPoint+0.1,false);
        OUT.text={name:T.name, just:String(td.justification), box:td.boxText, pos:tr.property("ADBE Position").value, anchor:tr.property("ADBE Anchor Point").value, rect:[rr.left,rr.top,rr.width,rr.height], font:td.font, size:td.fontSize};
        break; }
    }
  }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ OUT.error=String(e)+" line "+e.line; }
writeText(C.out, S(OUT));
app.endSuppressDialogs(false);
})();
