// 타임 워프 엔진. 설정 localize_job.json (scripts/timewarp.py가 생성)
// 파트 컴프마다 앵커 [[old,new],...]로 레이어 in/out·startTime·stretch·키프레임을 옮기고, 프리컴프는 재귀(여러 번 쓰이면 복제).
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={parts:[], warnings:[], errors:[]}, ST=null;
var FR=1/29.97;

function Map(a){ this.a=a; }
Map.prototype.f=function(t){ var a=this.a,n=a.length;
  if(t<=a[0][0]) return a[0][1]+(t-a[0][0]);
  if(t>=a[n-1][0]) return a[n-1][1]+(t-a[n-1][0]);
  var lo=0,hi=n-1; while(hi-lo>1){ var m=(lo+hi)>>1; if(a[m][0]<=t) lo=m; else hi=m; }
  return a[lo][1]+(a[hi][1]-a[lo][1])*(t-a[lo][0])/(a[hi][0]-a[lo][0]); };
Map.prototype.child=function(stOld,stNew,sx){ var b=[]; for(var i=0;i<this.a.length;i++) b.push([(this.a[i][0]-stOld)/sx,(this.a[i][1]-stNew)/sx]); return new Map(b); };

function isSpatial(p){ return p.propertyValueType===PropertyValueType.TwoD_SPATIAL||p.propertyValueType===PropertyValueType.ThreeD_SPATIAL; }

// 1) 키프레임 기록(레이어 시간 변경 전)
function recordKeys(group, out){
  for(var i=1;i<=group.numProperties;i++){
    var p=group.property(i);
    if(p.matchName==="ADBE Marker") continue;
    if(p.propertyType===PropertyType.PROPERTY){
      if(p.numKeys>0){
        // 숨겨진 속성(프리셋 내부 등)은 키를 다시 쓸 수 없다 → 지우기 전에 확인하고 건너뜀
        try{ p.setValueAtKey(1, p.keyValue(1)); }catch(e){ LOG.warnings.push("keys not writable, left as-is: "+p.name+" ("+String(e).slice(0,60)+")"); continue; }
        var K=[], sp=isSpatial(p);
        for(var k=1;k<=p.numKeys;k++){
          var o={t:p.keyTime(k), v:p.keyValue(k), ii:p.keyInInterpolationType(k), oi:p.keyOutInterpolationType(k)};
          try{ o.ie=p.keyInTemporalEase(k); o.oe=p.keyOutTemporalEase(k); o.tc=p.keyTemporalContinuous(k); o.ta=p.keyTemporalAutoBezier(k);}catch(e){}
          if(sp){ try{ o.ist=p.keyInSpatialTangent(k); o.ost=p.keyOutSpatialTangent(k); o.sc=p.keySpatialContinuous(k); o.sa=p.keySpatialAutoBezier(k); o.rv=p.keyRoving(k);}catch(e){} }
          K.push(o);
        }
        out.push({p:p, K:K, sp:sp});
      }
    } else { recordKeys(p, out); }
  }
}
// 2) 키프레임 재생성(절대 컴프 시간 = map(원래 시각)).
// 키가 0개가 되는 순간이 없도록 새 키를 먼저 만들고 옛 키를 지운다(Time Remap은 키가 0개면 꺼져서 숨겨짐).
function rewriteKeys(rec, map){
  var p=rec.p, K=rec.K, keep=[];
  for(var i=0;i<K.length;i++){ K[i].nt=map.f(K[i].t); }
  // 변환으로 실제로 접힌 키(새 간격이 원래 간격의 절반 미만이면서 1/4프레임 미만)만 앞 키를 버린다
  for(var i=0;i<K.length;i++){
    if(i+1<K.length){ var dn=K[i+1].nt-K[i].nt, d0=K[i+1].t-K[i].t; if(dn<1e-5 || (dn<FR/4 && dn<d0*0.5)) continue; }
    keep.push(K[i]); }
  // AE가 키 시각을 프레임 격자로 맞출 수 있으므로 addKey가 만든 실제 시각(at)을 기록해 그 키만 남긴다
  for(var i=0;i<keep.length;i++){ var ix=p.addKey(keep[i].nt); p.setValueAtKey(ix, keep[i].v); keep[i].at=p.keyTime(ix); }
  for(var k=p.numKeys;k>=1;k--){
    var t=p.keyTime(k), ok=false;
    for(var i=0;i<keep.length;i++) if(Math.abs(keep[i].at-t)<1e-6){ ok=true; break; }
    if(!ok) p.removeKey(k);
  }
  for(var i=0;i<keep.length;i++){
    var o=keep[i], idx=p.nearestKeyIndex(o.at);
    try{ p.setInterpolationTypeAtKey(idx,o.ii,o.oi);}catch(e){}
    try{ if(o.ie) p.setTemporalEaseAtKey(idx,o.ie,o.oe);}catch(e){}
    try{ if(o.tc!==undefined){ p.setTemporalContinuousAtKey(idx,o.tc); p.setTemporalAutoBezierAtKey(idx,o.ta);} }catch(e){}
    if(rec.sp){ try{ p.setSpatialTangentsAtKey(idx,o.ist,o.ost); p.setSpatialContinuousAtKey(idx,o.sc); p.setSpatialAutoBezierAtKey(idx,o.sa); p.setRovingAtKey(idx,o.rv);}catch(e){} }
  }
  if(p.numKeys!==keep.length) LOG.warnings.push("key count mismatch "+p.name+" "+p.numKeys+"/"+keep.length);
  return keep.length;
}
function setInOut(L,a,b){ if(a>=L.outPoint){ L.outPoint=b; L.inPoint=a; } else { L.inPoint=a; L.outPoint=b; } }
function srcName(L){ try{ return L.source?L.source.name:""; }catch(e){ return ""; } }
function muted(L){ var n=srcName(L); for(var i=0;i<C.mute_sources.length;i++) if(n===C.mute_sources[i]) return true; return false; }
function usesIn(parent, item){ var c=0; for(var j=1;j<=parent.numLayers;j++){ try{ if(parent.layer(j).source===item) c++; }catch(e){} } return c; }
function hidden(L){ return C.hide_comp_prefix && (L.source instanceof CompItem) && String(L.source.name).indexOf(C.hide_comp_prefix)===0; }

function warpComp(comp, map, depth){
  if(depth>25){ LOG.warnings.push("depth>25 "+comp.name); return; }
  // 프리컴프는 stNew=map(ost)로 잡으므로 자식 시간 0 → 0 이 유지된다
  var oldDur=comp.duration, newDur=Math.max(map.f(oldDur), FR);
  if(Math.abs(map.f(0))>FR) LOG.warnings.push("child start shifted "+map.f(0).toFixed(3)+" in "+comp.name);
  if(newDur>comp.duration) comp.duration=newDur;
  var relock=[];  // 잠긴 레이어는 풀고 처리한 뒤 다시 잠근다
  for(var j=1;j<=comp.numLayers;j++){ if(comp.layer(j).locked){ comp.layer(j).locked=false; relock.push(j); } }
  for(var j=1;j<=comp.numLayers;j++){
    var L=comp.layer(j);
    try{
      var oin=L.inPoint, oout=L.outPoint, ost=L.startTime, sx=L.stretch/100;
      var nin=map.f(oin), nout=map.f(oout);
      if(muted(L)){ L.audioEnabled=false; }
      if(hidden(L)){ L.enabled=false; L.audioEnabled=false; continue; }
      var recs=[]; recordKeys(L, recs);
      if(nout-nin<FR){ L.enabled=false; try{L.audioEnabled=false;}catch(e){} continue; }
      if(sx<0){ LOG.warnings.push("reversed layer skipped "+comp.name+"/"+L.name); continue; }
      var stNew;
      if(L.source instanceof CompItem && !L.timeRemapEnabled){
        var child=L.source;
        if(child.usedIn.length>1 || usesIn(comp, child)>1 || ST.done[child.id]){ child=child.duplicate(); L.replaceSource(child,false); ST.dups++; }
        stNew=map.f(ost);
        L.startTime=stNew; setInOut(L,nin,nout);
        ST.done[child.id]=true;
        warpComp(child, map.child(ost, stNew, sx), depth+1);
      } else if(L.source instanceof FootageItem && L.hasVideo && !L.source.mainSource.isStill && !L.timeRemapEnabled){
        var r=(nout-nin)/(oout-oin), u=(oin-ost)/sx;
        if(r>=0.8 && r<=1.25){ L.stretch=L.stretch*r; stNew=nin-u*sx*r; L.startTime=stNew; setInOut(L,nin,nout); }
        else if(r<0.8){ L.stretch=L.stretch*0.8; stNew=nin-u*sx*0.8; L.startTime=stNew; setInOut(L,nin,nout); LOG.warnings.push("clip squeezed+trimmed r="+r.toFixed(2)+" "+comp.name+"/"+L.name); }
        else {
          stNew=nin-(oin-ost); L.startTime=stNew;
          var natEnd=stNew+L.source.duration*sx;
          if(nout<=natEnd+1e-6){ setInOut(L,nin,nout); }
          else { L.timeRemapEnabled=true; setInOut(L,nin,nout);
                 var tr=L.property("ADBE Time Remapping"); var lastSrc=L.source.duration-FR;
                 tr.setValueAtTime(natEnd-FR,lastSrc); tr.setValueAtTime(nout,lastSrc); ST.holds++; }
        }
      } else if(!L.hasVideo && L.hasAudio){
        stNew=ost+(nin-oin); L.startTime=stNew; setInOut(L,nin,nin+(oout-oin));
      } else {
        stNew=nin-(oin-ost); L.startTime=stNew; setInOut(L,nin,nout);
      }
      for(var q=0;q<recs.length;q++) ST.keys+=rewriteKeys(recs[q], map);
      ST.layers++;
    }catch(e){ LOG.errors.push(comp.name+"/"+L.name+": "+String(e)+" line "+e.line); }
  }
  for(var q=0;q<relock.length;q++){ try{ comp.layer(relock[q]).locked=true; }catch(e){} }
  comp.duration=newDur;
  try{ comp.workAreaStart=0; comp.workAreaDuration=newDur; }catch(e){}
}

app.beginSuppressDialogs();
try{
  var P=openProject(C.aep);
  for(var k=0;k<C.parts.length;k++){
    var part=C.parts[k], comp=null;
    for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===part.comp) comp=it; }
    if(!comp){ LOG.errors.push("comp not found "+part.comp); continue; }
    ST={layers:0, keys:0, dups:0, holds:0, done:{}};
    warpComp(comp, new Map(part.anchors), 0);
    LOG.parts.push({comp:part.comp, layers:ST.layers, keys:ST.keys, dups:ST.dups, holds:ST.holds, dur_new:comp.duration, dur_expected:part.dur_new});
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
