// 이름에 KEY가 들어간 레이어의 이펙트 matchName 나열. 설정: probe_fx_job.json {"aep","key","out"}
(function(){
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var C=eval("("+R($.fileName.replace(/\.jsx$/,"_job.json"))+")"), out=[];
app.beginSuppressDialogs();
app.open(new File(C.aep)); var P=app.project;
for(var i=1;i<=P.numItems;i++){var it=P.item(i); if(!(it instanceof CompItem)) continue;
  for(var j=1;j<=it.numLayers;j++){var L=it.layer(j); var sn=""; try{sn=L.source?L.source.name:"";}catch(e){} if(L.name.indexOf(C.key)<0 && sn.indexOf(C.key)<0) continue;
    var fx=L.property("ADBE Effect Parade"), a=[];
    if(fx) for(var k=1;k<=fx.numProperties;k++) a.push(fx.property(k).matchName+"|"+fx.property(k).name);
    out.push(it.name+" :: "+L.name+" blend="+L.blendingMode+" fx="+a.join(","));}}
var f=new File(C.out);f.encoding="UTF-8";f.open("w");f.write(out.join("\n"));f.close();
P.close(CloseOptions.DO_NOT_SAVE_CHANGES); app.endSuppressDialogs(false);
})();
