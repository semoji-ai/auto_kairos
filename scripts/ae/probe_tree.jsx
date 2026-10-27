// 컴프 트리 덤프(값 읽기 최소: 이름·소스·크기·켜짐·in/out). 설정: probe_tree_job.json {"aep","comp","out"}
(function(){
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var C=eval("("+R($.fileName.replace(/\.jsx$/,"_job.json"))+")"), out=[];
app.beginSuppressDialogs();
try{
app.open(new File(C.aep)); var P=app.project, root=null;
for(var i=1;i<=P.numItems;i++){var it=P.item(i); if(it instanceof CompItem && it.name===C.comp && !root) root=it;}
function dump(comp,ind,d){ out.push(ind+"COMP "+comp.name+" "+comp.width+"x"+comp.height+" dur="+comp.duration.toFixed(2));
  for(var j=1;j<=comp.numLayers;j++){ var L=comp.layer(j), s=L.source, info="";
    try{ if(s instanceof FootageItem) info=" src="+s.name+" "+s.width+"x"+s.height+(s.file?" file="+s.file.fsName:"")+(s.footageMissing?" MISSING":""); }catch(e){info=" src?";}
    try{ if(L instanceof TextLayer) info+=" TEXT="+L.property("ADBE Text Properties").property("ADBE Text Document").value.text; }catch(e){}
    var mt=""; try{ mt=" matte="+L.trackMatteType; }catch(e){}
    out.push(ind+"  "+j+" "+L.name+" en="+L.enabled+" in="+L.inPoint.toFixed(2)+" out="+L.outPoint.toFixed(2)+mt+" blend="+L.blendingMode+info);
    if(s instanceof CompItem && d<4) dump(s,ind+"    ",d+1); } }
if(root) dump(root,"",0); else out.push("no comp");
}catch(e){ out.push("ERR "+e+" line "+e.line); }
var f=new File(C.out);f.encoding="UTF-8";f.open("w");f.write(out.join("\r\n"));f.close();
try{app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(e){} app.endSuppressDialogs(false);
})();
