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
    var SN=C.sub_name||"#자막", subL=null;   // '#자막'과 '#자막바'처럼 접두어가 겹치면 이름이 정확히 같은 것 우선
    for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j); if(L.source instanceof CompItem && L.source.name===SN) subL=L; }
    if(!subL) for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j); if(L.source instanceof CompItem && L.source.name.indexOf(SN)===0) subL=L; }
    if(subL && part.sub_st!==undefined){   // 같은 자막 컴프를 여러 레이어가 나눠 쓰면: 시작 시각이 맞는 하나를 파트 전체로 늘리고 나머지는 끔
      var same=[]; for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j); if(L.source instanceof CompItem && (L.source===subL.source || L.source.name.replace(/ \d+$/,"")===subL.source.name.replace(/ \d+$/,""))) same.push(L); }   // localize가 레이어마다 컴프를 복제했을 수 있음(이름은 같음)
      for(var j=0;j<same.length;j++) same[j].locked=false;
      if(same.length>1){ var best=same[0];
        for(var j=0;j<same.length;j++) if(Math.abs(same[j].startTime-part.sub_st)<Math.abs(best.startTime-part.sub_st)) best=same[j];
        for(var j=0;j<same.length;j++) if(same[j]!==best) same[j].enabled=false;
        subL=best; subL.inPoint=Math.max(0,subL.startTime); subL.outPoint=main.duration; }
    }
    if(subL){ sub=subL.source; subL.enabled=true; }
    if(!sub){ LOG.errors.push("no "+SN+" under "+part.comp); continue; }
    var tmpl=null, olds=[];
    for(var j=1;j<=sub.numLayers;j++){ var L=sub.layer(j); if(L instanceof TextLayer){ olds.push(L); if(!tmpl) tmpl=L; } }
    if(!tmpl){ LOG.errors.push("no text template in "+sub.name); continue; }
    for(var j=0;j<olds.length;j++) olds[j].locked=false;
    var made=0;
    for(var c=0;c<part.cues.length;c++){
      var q=part.cues[c], N=tmpl.duplicate();
      var sp=N.property("ADBE Text Properties").property("ADBE Text Document");
      while(sp.numKeys>0) sp.removeKey(1);
      var td=sp.value; td.text=q.text; if(C.font) td.font=C.font;
      td.justification=ParagraphJustification.CENTER_JUSTIFY; sp.setValue(td);
      // 원본 템플릿은 왼쪽 정렬 + 한국어 문장 폭에 맞춘 고정 앵커 → 번역문 길이가 달라지면 한쪽으로 쏠림.
      // 가운데 정렬 점 텍스트는 원점(x=0)이 가운데이므로 앵커 x=0, 위치 x는 템플릿 그대로(자막바 가운데)
      var tg=N.property("ADBE Transform Group"), ap=tg.property("ADBE Anchor Point"), av=ap.value;
      if(ap.numKeys===0) ap.setValue([0, av[1], av.length>2?av[2]:0]);
      if(C.font && c===0 && sp.value.font!==C.font) LOG.errors.push("자막 폰트 대체됨 "+C.font+" → "+sp.value.font);
      N.startTime=0; N.inPoint=q["in"]; N.outPoint=q["out"]; if(Math.abs(N.inPoint-q["in"])>1e-3) N.inPoint=q["in"];
      N.name="EN "+(c+1); N.enabled=true; made++;
    }
    for(var j=0;j<olds.length;j++) olds[j].remove();
    // 자막 바: 자막 구간에만 보이게 불투명도 키(3프레임 페이드), 원래 불투명도 값은 유지
    var fr=3/main.frameRate, bars=0;
    for(var j=1;j<=main.numLayers;j++){
      var BL=main.layer(j), isBar=false;
      for(var b=0;b<C.bar_layers.length;b++) if(BL.name===C.bar_layers[b]) isBar=true;
      if(!isBar) continue;
      var wasLocked=BL.locked; BL.locked=false;
      var op=BL.property("ADBE Transform Group").property("ADBE Opacity"), v0=op.value;
      while(op.numKeys>0) op.removeKey(1);
      op.setValueAtTime(0,0);
      for(var q=0;q<part.bar.length;q++){
        var a=part.bar[q][0], e=part.bar[q][1];
        op.setValueAtTime(Math.max(0,a-fr),0); op.setValueAtTime(a,v0);
        op.setValueAtTime(e,v0); op.setValueAtTime(e+fr,0);
      }
      BL.locked=wasLocked; bars++;
    }
    if(bars===0) LOG.errors.push("no subtitle bar layer in "+part.comp);
    LOG.parts.push({comp:part.comp, sub:sub.name, created:made, deleted:olds.length, bar_layers:bars, bar_spans:part.bar.length});
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
