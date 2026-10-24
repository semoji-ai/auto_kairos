// 디버그: 지정 footage id들을 소스로 쓰는 모든 레이어의 변형값·키프레임(시각·값)·마스크·이펙트를 나열.  job: {aep, ids, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), OUT=[];
function val(v){ return (v instanceof Array)? v : [v]; }
function dump(L, path){
  var tr=L.property("ADBE Transform Group"), r={comp:path, idx:L.index, name:L.name, src:L.source.id, "in":L.inPoint, "out":L.outPoint,
    st:L.startTime, anchor:tr.property("ADBE Anchor Point").value, pos:tr.property("ADBE Position").value,
    scale:tr.property("ADBE Scale").value, rot:tr.property("ADBE Rotate Z").value, keys:[], masks:L.property("ADBE Mask Parade").numProperties,
    effects:[]};
  var props=["ADBE Anchor Point","ADBE Position","ADBE Scale","ADBE Opacity"];
  for(var i=0;i<props.length;i++){ var p=tr.property(props[i]); for(var k=1;k<=p.numKeys;k++) r.keys.push([props[i], p.keyTime(k), val(p.keyValue(k))]); }
  var fx=L.property("ADBE Effect Parade"); for(var e=1;e<=fx.numProperties;e++) r.effects.push(fx.property(e).name);
  var mp=L.property("ADBE Mask Parade");
  for(var m=1;m<=mp.numProperties;m++){ var sh=mp.property(m).property("ADBE Mask Shape"); r.keys.push(["mask"+m, sh.numKeys, sh.value.vertices]); }
  OUT.push(r);
}
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), want={};
  for(var i=0;i<C.ids.length;i++) want[C.ids[i]]=1;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(!(it instanceof CompItem)) continue;
    for(var j=1;j<=it.numLayers;j++){ var L=it.layer(j); if(L.source && want[L.source.id]) dump(L, it.name); } }
}catch(e){ OUT.push({error:String(e)+" line "+e.line}); }
writeText(C.out, S(OUT));
app.endSuppressDialogs(false);
})();
