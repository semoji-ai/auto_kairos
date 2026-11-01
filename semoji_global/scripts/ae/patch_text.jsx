// 화면 문자열 교체. comp_id+layer로 찾아 원문(ko)과 같은 소스텍스트(키프레임 포함)를 번역으로 바꾸고,
// 폰트 매핑, 원래보다 넓어지면 글자 크기를 줄여(최소 min_scale) 원래 폭에 맞춘다.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={replaced:0, keys_replaced:0, shrunk:[], overflow:[], not_found:[], mismatch:[], errors:[]};
function norm(s){ return String(s).replace(/\r\n|\n/g,"\r"); }
function width(L,t){ try{ var r=L.sourceRectAtTime(t,false); return r.width; }catch(e){ return 0; } }
var UNMAPPED={};
function apply(td,txt,font){ td.text=txt; if(font) td.font=font; else if(C.font_map[td.font]) td.font=C.font_map[td.font]; else UNMAPPED[td.font]=1; return td; }   // font: l10n strings의 글꼴 지정(대응표보다 우선)
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
        var td=tg.key?sp.keyValue(tg.key):sp.value; apply(td,e.text,e.font);
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
  // 이펙트 값 덮어쓰기(l10n의 _fx: 예) 숫자 카운터 끝값). ko = 원래 값(다르면 mismatch)
  LOG.fx=0;
  for(var f=0;f<(C.fx||[]).length;f++){
    var X=C.fx[f], fc=byId[X.comp_id], id="fx:"+X.comp_id+":"+X.layer+":"+X.prop;
    try{
      var FL=fc.layer(X.layer), FP=null, par=FL.property("ADBE Effect Parade");
      for(var z=1;z<=par.numProperties;z++) if(par.property(z).matchName===X.effect){ FP=par.property(z).property(X.prop); break; }
      if(!FP){ LOG.not_found.push(id); continue; }
      var cur=X.key?FP.keyValue(X.key):FP.value;
      if(Math.abs(cur-X.ko)>1e-6){ LOG.mismatch.push(id+" ("+cur+")"); continue; }
      if(X.key) FP.setValueAtKey(X.key,X.value); else FP.setValue(X.value);
      LOG.fx++;
    }catch(err){ LOG.errors.push(id+": "+String(err)); }
  }
  // 글자 레이어를 표현식 카운터로(l10n의 _expr: Numbers 이펙트 한계 30000을 넘는 수 등). disable_layer = 끌 레이어, disable_fx = 끌 이펙트
  LOG.expr=0;
  for(var x=0;x<(C.expr||[]).length;x++){
    var Q=C.expr[x], qc=byId[Q.comp_id], qid="expr:"+Q.comp_id+":"+Q.layer;
    try{
      var QL=qc.layer(Q.layer), qs=QL.property("ADBE Text Properties").property("ADBE Text Document"), qd=qs.value;
      if(Q.font) qd.font=Q.font; if(Q.size) qd.fontSize=Q.size; qd.justification=ParagraphJustification.CENTER_JUSTIFY; qs.setValue(qd);
      qs.expression=Q.expr;
      if(Q.pos){ var tr=QL.property("ADBE Transform Group"); QL.parent=null; tr.property("ADBE Anchor Point").setValue([0,0]); tr.property("ADBE Position").setValue(Q.pos); tr.property("ADBE Scale").setValue([100,100]); }
      if(Q.disable_layer) qc.layer(Q.disable_layer).enabled=false;   // 이펙트만 끄면 솔리드가 드러나 아래를 덮음
      if(Q.disable_fx){ var DL=qc.layer(Q.disable_fx.layer), dp=DL.property("ADBE Effect Parade");
        for(var z2=1;z2<=dp.numProperties;z2++) if(dp.property(z2).matchName===Q.disable_fx.effect) dp.property(z2).enabled=false; }
      LOG.expr++;
    }catch(err){ LOG.errors.push(qid+": "+String(err)); }
  }
  for(var u in UNMAPPED) if(UNMAPPED.hasOwnProperty(u)) LOG.errors.push("폰트 대응표에 없음: "+u+" (profiles/<lang>.json fonts)");
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
