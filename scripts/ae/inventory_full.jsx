// 편 전체 인벤토리. 설정 inventory_full_job.json {aep, out}
// 출력: comps(이름·길이·fps·레이어 수·부모 사용처), texts(모든 텍스트 레이어: 컴프·레이어·문자열/키프레임·폰트·크기·in/out),
//       footage(파일 경로·누락 여부·사용 횟수), missing_fonts
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), P, res={aep:C.aep, comps:[], texts:[], footage:[], errors:[]};
app.beginSuppressDialogs();
try{
  P=openProject(C.aep);
  for(var i=1;i<=P.numItems;i++){
    var it=P.item(i);
    if(it instanceof CompItem){
      var users=[]; try{ for(var u=0;u<it.usedIn.length;u++) users.push(it.usedIn[u].name); }catch(e){}
      res.comps.push({id:it.id, name:it.name, dur:it.duration, fps:it.frameRate, w:it.width, h:it.height, layers:it.numLayers, used_in:users});
      for(var j=1;j<=it.numLayers;j++){
        var L=it.layer(j);
        if(!(L instanceof TextLayer)) continue;
        var sp=L.property("ADBE Text Properties").property("ADBE Text Document");
        var e={comp:it.name, comp_id:it.id, layer:j, name:L.name, enabled:L.enabled, "in":L.inPoint, "out":L.outPoint,
               keys:[], text:"", font:"", size:0, expr:sp.expressionEnabled?sp.expression:""};
        try{ var td=sp.value; e.text=td.text; e.font=td.font; e.size=td.fontSize; e.box=td.boxText; }catch(x){}
        for(var k=1;k<=sp.numKeys;k++) e.keys.push({t:sp.keyTime(k), text:sp.keyValue(k).text});
        res.texts.push(e);
      }
    } else if(it instanceof FootageItem){
      var f=""; try{ f=it.mainSource.file?it.mainSource.file.fsName:""; }catch(x){}
      res.footage.push({id:it.id, name:it.name, file:f, missing:it.footageMissing, uses:it.usedIn.length,
                        still:(function(){try{return it.mainSource.isStill;}catch(x){return null;}})(), w:it.width, h:it.height});
    }
  }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ res.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(res));
app.endSuppressDialogs(false);
})();
