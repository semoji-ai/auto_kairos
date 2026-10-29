(function(){
var SELF=$.fileName; $.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), out=[];
function st(L){ return "in="+L.inPoint.toFixed(3)+" out="+L.outPoint.toFixed(3)+" st="+L.startTime.toFixed(3)+" srcDur="+L.source.duration.toFixed(3); }
app.beginSuppressDialogs();
try{
var P=openProject(C.aep), comp=null;
for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name==="MAIN_GAEUL") comp=it; }
var L=null; for(var j=1;j<=comp.numLayers;j++) if(comp.layer(j).name==="2 검은창") L=comp.layer(j);
out.push("0 "+st(L)+" locked="+L.locked);
L.locked=false;
L.startTime=0.2; out.push("1 "+st(L));
L.source.duration=44.65; out.push("2 dur44.65 "+st(L));
L.source.duration=1283.383; out.push("3 dur1283 "+st(L));
L.inPoint=35.736; out.push("4 in "+st(L));
L.outPoint=44.8; out.push("5 out "+st(L));
}catch(e){ out.push("ERR "+e+" "+e.line); }
writeText(C.out, out.join("\n"));
})();
