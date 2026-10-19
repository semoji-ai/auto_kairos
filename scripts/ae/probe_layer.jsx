(function(){
var SELF=$.fileName; $.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), out=[];
app.beginSuppressDialogs();
try{
var P=openProject(C.aep), comp=null;
for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.comp) comp=it; }
for(var j=1;j<=comp.numLayers;j++){ var L=comp.layer(j); if(L.name.indexOf(C.match)<0) continue;
  out.push("hasVideo="+L.hasVideo+" hasAudio="+L.hasAudio+" audioEnabled="+L.audioEnabled+" isFootage="+(L.source instanceof FootageItem)+" still="+(L.source&&L.source.mainSource?L.source.mainSource.isStill:"")); out.push(L.name+" in="+L.inPoint.toFixed(3)+" out="+L.outPoint.toFixed(3)+" st="+L.startTime.toFixed(3)+" sx="+L.stretch+" srcDur="+(L.source?L.source.duration.toFixed(3):"")+" src="+(L.source?L.source.name:"")+" usedIn="+(L.source&&L.source.usedIn?L.source.usedIn.length:""));
  break; }
}catch(e){ out.push("ERR "+e+" "+e.line); }
writeText(C.out, out.join("\n"));
})();
