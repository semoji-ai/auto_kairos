(function(){
var SELF=$.fileName; $.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), out=[];
app.beginSuppressDialogs();
try{
var P=openProject(C.aep), comp=null;
for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp) comp=it; }
var L=comp.layer(C.layer);
out.push("layer "+L.name+" tr="+L.timeRemapEnabled+" src="+(L.source?L.source.name:"")+" collapse="+L.collapseTransformation);
function walk(g,path){ for(var i=1;i<=g.numProperties;i++){ var p=g.property(i);
  if(p.propertyType===PropertyType.PROPERTY){ if(p.numKeys>0){ var r="";
     try{ p.setValueAtTime(p.keyTime(1)+0.0, p.keyValue(1)); r="ok"; }catch(e){ r=String(e).slice(0,70); }
     out.push(path+"/"+p.matchName+" ("+p.name+") keys="+p.numKeys+" -> "+r); } }
  else walk(p,path+"/"+p.matchName); } }
walk(L,"");
}catch(e){ out.push("ERR "+e+" "+e.line); }
writeText(C.out, out.join("\n"));
})();
