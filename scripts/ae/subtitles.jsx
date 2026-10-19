// 파트 컴프 바로 아래 '#자막' 프리컴프를 영어 자막으로 다시 채운다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={parts:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep);
  for(var k=0;k<C.parts.length;k++){
    var part=C.parts[k], main=null, sub=null;
    for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===part.comp) main=it; }
    for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j); if(L.source instanceof CompItem && L.source.name.indexOf("#자막")===0){ sub=L.source; L.enabled=true; } }
    if(!sub){ LOG.errors.push("no #자막 under "+part.comp); continue; }
    var tmpl=null, olds=[];
    for(var j=1;j<=sub.numLayers;j++){ var L=sub.layer(j); if(L instanceof TextLayer){ olds.push(L); if(!tmpl) tmpl=L; } }
    if(!tmpl){ LOG.errors.push("no text template in "+sub.name); continue; }
    for(var j=0;j<olds.length;j++) olds[j].locked=false;
    var made=0;
    for(var c=0;c<part.cues.length;c++){
      var q=part.cues[c], N=tmpl.duplicate();
      var sp=N.property("ADBE Text Properties").property("ADBE Text Document");
      while(sp.numKeys>0) sp.removeKey(1);
      var td=sp.value; td.text=q.text; sp.setValue(td);
      N.startTime=0; N.inPoint=q["in"]; N.outPoint=q["out"]; if(Math.abs(N.inPoint-q["in"])>1e-3) N.inPoint=q["in"];
      N.name="EN "+(c+1); N.enabled=true; made++;
    }
    for(var j=0;j<olds.length;j++) olds[j].remove();
    LOG.parts.push({comp:part.comp, sub:sub.name, created:made, deleted:olds.length});
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
