// 화면 문자열 교체. comp_id+layer로 찾아 원문(ko)과 같은 소스텍스트(키프레임 포함)를 번역으로 바꾸고,
// 폰트 매핑, 원래보다 넓어지면 글자 크기를 줄여(최소 min_scale) 원래 폭에 맞춘다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={replaced:0, keys_replaced:0, shrunk:[], not_found:[], mismatch:[], errors:[]};
function norm(s){ return String(s).replace(/\r\n|\n/g,"\r"); }
function width(L,t){ try{ var r=L.sourceRectAtTime(t,false); return r.width; }catch(e){ return 0; } }
function apply(td,txt){ td.text=txt; if(C.font_map[td.font]) td.font=C.font_map[td.font]; return td; }
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem) byId[it.id]=it; }
  for(var k=0;k<C.items.length;k++){
    var e=C.items[k], comp=byId[e.comp_id];
    if(!comp || e.layer>comp.numLayers || !(comp.layer(e.layer) instanceof TextLayer)){ LOG.not_found.push(e.id); continue; }
    var L=comp.layer(e.layer), wasLocked=L.locked; L.locked=false;
    var sp=L.property("ADBE Text Properties").property("ADBE Text Document");
    var t=L.inPoint+0.01, w0=width(L,t);
    try{
      if(sp.numKeys>0){
        for(var q=1;q<=sp.numKeys;q++){ var td=sp.keyValue(q);
          if(norm(td.text)===norm(e.ko)){ sp.setValueAtKey(q, apply(td,e.text)); LOG.keys_replaced++; } }
      } else {
        var td=sp.value;
        if(norm(td.text)!==norm(e.ko)){ LOG.mismatch.push(e.id); }
        else { sp.setValue(apply(td,e.text)); LOG.replaced++; }
      }
      var w1=width(L,t);
      if(w0>0 && w1>w0*1.05 && sp.numKeys===0){
        var s=Math.max(C.min_scale, w0/w1), td2=sp.value; td2.fontSize=td2.fontSize*s; sp.setValue(td2);
        LOG.shrunk.push({id:e.id, scale:Math.round(s*100)/100});
      }
    }catch(err){ LOG.errors.push(e.id+": "+String(err)); }
    L.locked=wasLocked;
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
