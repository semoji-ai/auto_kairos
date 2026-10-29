// 텍스트 레이어 폰트 일괄 교체(소스텍스트 키프레임 포함). 설정 fontmap_job.json {aep, save_as, map:{기존 PS이름:새 PS이름}, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), res={changed:0, keys:0, failed:[], left:{}, errors:[]};
app.beginSuppressDialogs();
function fix(td){ var f=td.font; if(C.map[f]){ td.font=C.map[f]; return true;} res.left[f]=(res.left[f]||0)+1; return false; }
try{
  var P=openProject(C.aep);
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(!(it instanceof CompItem)) continue;
    for(var j=1;j<=it.numLayers;j++){ var L=it.layer(j); if(!(L instanceof TextLayer)) continue;
      var sp=L.property("ADBE Text Properties").property("ADBE Text Document");
      try{
        if(sp.numKeys>0){ for(var k=1;k<=sp.numKeys;k++){ var td=sp.keyValue(k); if(fix(td)){ sp.setValueAtKey(k,td); res.keys++; } } }
        else { var td=sp.value; if(fix(td)){ sp.setValue(td); res.changed++; } }
      }catch(e){ res.failed.push(it.name+"/"+L.name+": "+String(e)); }
    } }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ res.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(res));
app.endSuppressDialogs(false);
})();
