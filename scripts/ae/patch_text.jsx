// 화면 문자열 교체. comp_id+layer로 찾아 원문(ko)과 같은 소스텍스트(키프레임 포함)를 번역으로 바꾸고,
// 폰트 매핑, 원래보다 넓어지면 글자 크기를 줄여(최소 min_scale) 원래 폭에 맞춘다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={replaced:0, keys_replaced:0, shrunk:[], overflow:[], not_found:[], mismatch:[], errors:[]};
function norm(s){ return String(s).replace(/\r\n|\n/g,"\r"); }
function width(L,t){ try{ var r=L.sourceRectAtTime(t,false); return r.width; }catch(e){ return 0; } }
var UNMAPPED={};
function apply(td,txt){ td.text=txt; if(C.font_map[td.font]) td.font=C.font_map[td.font]; else UNMAPPED[td.font]=1; return td; }
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem) byId[it.id]=it; }
  for(var k=0;k<C.items.length;k++){
    var e=C.items[k], comp=byId[e.comp_id];
    if(!comp || e.layer>comp.numLayers || !(comp.layer(e.layer) instanceof TextLayer)){ LOG.not_found.push(e.id); continue; }
    var L=comp.layer(e.layer), wasLocked=L.locked; L.locked=false;
    var sp=L.property("ADBE Text Properties").property("ADBE Text Document");
    // 폭은 레이어가 보이는 구간의 중간에서 잰다(등장 애니메이션으로 시작 시점엔 글자가 덜 보일 수 있음)
    function midOf(a,b){ return a+(b-a)/2; }
    try{
      var targets=[];   // {t: 측정 시각, key: 키 번호 또는 0}
      if(sp.numKeys>0){
        for(var q=1;q<=sp.numKeys;q++){
          if(norm(sp.keyValue(q).text)!==norm(e.ko)) continue;
          var a=Math.max(sp.keyTime(q),L.inPoint), b=(q<sp.numKeys)?Math.min(sp.keyTime(q+1),L.outPoint):L.outPoint;
          targets.push({t:midOf(a,b), key:q});
        }
        if(!targets.length) LOG.mismatch.push(e.id);
      } else if(norm(sp.value.text)!==norm(e.ko)){ LOG.mismatch.push(e.id); }
      else targets.push({t:midOf(L.inPoint,L.outPoint), key:0});
      for(var n=0;n<targets.length;n++){
        var tg=targets[n], w0=width(L,tg.t);
        var td=tg.key?sp.keyValue(tg.key):sp.value; apply(td,e.text);
        if(tg.key){ sp.setValueAtKey(tg.key,td); LOG.keys_replaced++; } else { sp.setValue(td); LOG.replaced++; }
        var w1=width(L,tg.t);
        if(w0>0 && w1>w0*1.05){
          var s=Math.max(C.min_scale, w0/w1), td2=tg.key?sp.keyValue(tg.key):sp.value; td2.fontSize=td2.fontSize*s;
          if(tg.key) sp.setValueAtKey(tg.key,td2); else sp.setValue(td2);
          LOG.shrunk.push({id:e.id, scale:Math.round(s*100)/100});
          if(w1*s>w0*1.05) LOG.overflow.push({id:e.id, ratio:Math.round(w1*s/w0*100)/100});   // 하한에 걸려 여전히 넓음
        }
      }
    }catch(err){ LOG.errors.push(e.id+": "+String(err)); }
    L.locked=wasLocked;
  }
  for(var u in UNMAPPED) if(UNMAPPED.hasOwnProperty(u)) LOG.errors.push("폰트 대응표에 없음: "+u+" (profiles/<lang>.json fonts)");
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
