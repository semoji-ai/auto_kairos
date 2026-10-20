// 디버그: 컴프의 이름에 match가 들어간 레이어마다 in/out과 익스프레션·키가 있는 속성을 나열.  job: {aep, comp, match, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), OUT=[];
function walk(g, path, L){
  for(var i=1;i<=g.numProperties;i++){
    var p=g.property(i);
    if(p.propertyType===PropertyType.PROPERTY){
      var e=""; try{ if(p.canSetExpression && p.expressionEnabled) e=p.expression; }catch(_){}
      var nk=0; try{ nk=p.numKeys; }catch(_){}
      if(e || nk>0) OUT.push({layer:L.name, prop:path+"/"+p.name, expr:e, keys:nk});
    } else walk(p, path+"/"+p.name, L);
  }
}
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), comp=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp) comp=it; }
  for(var j=1;j<=comp.numLayers;j++){
    var L=comp.layer(j); if(L.name.indexOf(C.match)<0) continue;
    OUT.push({layer:L.name, idx:j, "in":L.inPoint, "out":L.outPoint, enabled:L.enabled, type:L.matchName});
    walk(L, "", L);
  }
}catch(e){ OUT.push({error:String(e)+" line "+e.line}); }
writeText(C.out, S(OUT));
app.endSuppressDialogs(false);
})();
