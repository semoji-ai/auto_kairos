// 언어별 삽입 구간 조립: build/<lang>/inserts_plan.json의 장면들을 AE 컴프 INSERT_<name>으로 만들고
// (배경·이미지·뱃지·글자·막대 등 + 등장 애니메이션), 본편의 자막바·채널 로고·자막 글자 스타일을 복사해 자막을 얹는다.
// job: build_inserts_job.json {aep, save_as, out, fonts, plan, fps}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={comps:[], layers:0, cues:0, errors:[]};
var W=1920, H=1080, FPS=C.fps;
function rgb(c){ return [c[0]/255, c[1]/255, c[2]/255]; }
function ease(p){ for(var k=1;k<=p.numKeys;k++){ try{ p.setInterpolationTypeAtKey(k, KeyframeInterpolationType.BEZIER);
  var n=(p.value instanceof Array)?p.value.length:1, e=[]; for(var i=0;i<(p.propertyValueType===PropertyValueType.TwoD_SPATIAL||p.propertyValueType===PropertyValueType.ThreeD_SPATIAL?1:n);i++) e.push(new KeyframeEase(0,70));
  p.setTemporalEaseAtKey(k,e,e);}catch(_){} } }
var IMPORTED={}, PROJ=null, FOLDER=null;
function footage(path){ if(IMPORTED[path]) return IMPORTED[path];
  var f=PROJ.importFile(new ImportOptions(new File(path))); f.parentFolder=FOLDER; IMPORTED[path]=f; return f; }
function animate(L, kind, t, x, y, rot){
  var tr=L.property("ADBE Transform Group"), sc=tr.property("ADBE Scale"), op=tr.property("ADBE Opacity"), pos=tr.property("ADBE Position");
  var s0=sc.value[0], base=[x,y];
  if(rot) tr.property("ADBE Rotate Z").setValue(rot);
  if(kind==="none"||!kind){ pos.setValue(base); return; }
  pos.setValue(base);
  op.setValueAtTime(Math.max(0,t-0.01),0); op.setValueAtTime(t,0);
  if(kind==="fade"){ op.setValueAtTime(t+0.3,100); }
  else if(kind==="pop"){ op.setValueAtTime(t+0.08,100); sc.setValueAtTime(t,[0,0]); sc.setValueAtTime(t+0.18,[s0*1.1,s0*1.1]); sc.setValueAtTime(t+0.3,[s0,s0]); ease(sc); }
  else if(kind==="slam"){ op.setValueAtTime(t+0.05,100); sc.setValueAtTime(t,[s0*1.7,s0*1.7]); sc.setValueAtTime(t+0.16,[s0*0.94,s0*0.94]); sc.setValueAtTime(t+0.28,[s0,s0]); ease(sc); }
  else { var d={slide_up:[0,220], slide_right:[-360,0], slide_left:[360,0]}[kind]||[0,0];
    op.setValueAtTime(t+0.2,100); pos.setValueAtTime(t,[x+d[0],y+d[1]]); pos.setValueAtTime(t+0.4,base); ease(pos); }
}
function addText(comp, text, font, size, color, stroke, stroke_w){
  var L=comp.layers.addText(text), sp=L.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value;
  td.resetCharStyle(); td.resetParagraphStyle(); td.font=font; td.fontSize=size; td.applyFill=true; td.fillColor=rgb(color);
  if(stroke){ td.applyStroke=true; td.strokeColor=rgb(stroke); td.strokeWidth=stroke_w||6; td.strokeOverFill=false; } else td.applyStroke=false;
  td.justification=ParagraphJustification.CENTER_JUSTIFY; sp.setValue(td);
  if(sp.value.font!==font) LOG.errors.push("폰트 대체됨 "+font+" → "+sp.value.font);
  var r=L.sourceRectAtTime(0,false); L.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([r.left+r.width/2, r.top+r.height/2]);
  return {layer:L, w:r.width, h:r.height};
}
function rectShape(comp, w, h, color, radius, name){
  var L=comp.layers.addShape(); L.name=name||"rect";
  var g=L.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group"), v=g.property("ADBE Vectors Group");
  var r=v.addProperty("ADBE Vector Shape - Rect"); r.property("ADBE Vector Rect Size").setValue([w,h]); r.property("ADBE Vector Rect Roundness").setValue(radius||0);
  v.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(rgb(color));
  return L;
}
function fadeChildren(layers, kind, t){   // null의 불투명도는 자식에 안 먹음 → 자식마다 같은 등장 시각에 불투명도 키
  if(!kind || kind==="none") return;
  var d=(kind==="fade")?0.3:(kind==="slam"?0.05:(kind==="pop"?0.08:0.2));
  for(var i=0;i<layers.length;i++){ var op=layers[i].property("ADBE Transform Group").property("ADBE Opacity");
    op.setValueAtTime(Math.max(0,t-0.01),0); op.setValueAtTime(t,0); op.setValueAtTime(t+d,100); }
}
// 규칙(도장·팝 등 스케일 등장 효과): 스케일 키로 등장하는 것은 "실제로 그려지는 레이어"마다 첫 스케일 키 시각에
// 불투명도 0→100 키가 있어야 한다. null·부모는 자식의 불투명도를 바꾸지 못하므로 부모에만 넣으면 처음부터 보인다.
// checkReveal이 장면마다 이 규칙을 검사해 어기면 오류로 멈춘다.
function firstScaleKey(L){ for(var p=L;p;p=p.parent){ var sc=p.property("ADBE Transform Group").property("ADBE Scale"); if(sc.numKeys>0) return sc.keyTime(1); } return null; }
function checkReveal(comp, sid){
  for(var i=1;i<=comp.numLayers;i++){ var L=comp.layer(i); if(L.nullLayer) continue;
    var t=firstScaleKey(L); if(t===null) continue;
    var op=L.property("ADBE Transform Group").property("ADBE Opacity");
    if(op.numKeys===0 || op.keyValue(1)>0.5 || op.keyTime(1)>t+0.02)
      LOG.errors.push(sid+": '"+L.name+"' 스케일 등장(t="+t.toFixed(2)+")인데 자기 불투명도 0 키가 없음 — 처음부터 보임");
  }
}
function grouped(comp, layers, name){   // 여러 레이어를 한 null에 붙여 함께 움직임
  var N=comp.layers.addNull(); N.name=name||"grp"; N.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]);
  N.property("ADBE Transform Group").property("ADBE Anchor Point").setValue([0,0]);
  for(var i=0;i<layers.length;i++) layers[i].parent=N;
  return N;
}
function buildScene(sc, fonts){
  var comp=PROJ.items.addComp("SCENE_"+sc.id, W, H, 1, sc.dur, FPS); comp.parentFolder=FOLDER;
  var na=sc.narr_at-sc.start, nd=sc.narr_dur;
  for(var i=0;i<sc.layers.length;i++){
    var S=sc.layers[i], t=na+(S.at||0)*nd, L;
    try{
      if(S.type==="bg"){ L=comp.layers.add(footage(S.src)); var sx=Math.max(W/L.source.width,H/L.source.height)*100;
        L.property("ADBE Transform Group").property("ADBE Scale").setValue([sx,sx]); L.property("ADBE Transform Group").property("ADBE Position").setValue([W/2,H/2]);
        L.moveToEnd();
        if(S.dim){ var D=comp.layers.addSolid([0,0,0],"dim",W,H,1,sc.dur); D.property("ADBE Transform Group").property("ADBE Opacity").setValue(S.dim*100); D.moveBefore(L); }
      } else if(S.type==="split"){
        var A=comp.layers.addSolid(rgb(S.left),"left",W/2,H,1,sc.dur); A.property("ADBE Transform Group").property("ADBE Position").setValue([W/4,H/2]); A.moveToEnd();
        var B=comp.layers.addSolid(rgb(S.right),"right",W/2,H,1,sc.dur); B.property("ADBE Transform Group").property("ADBE Position").setValue([3*W/4,H/2]); B.moveToEnd();
      } else if(S.type==="image"){
        var n=S.repeat?S.repeat.n:1;
        for(var k=0;k<n;k++){
          L=comp.layers.add(footage(S.src)); var s=100*S.w/L.source.width; L.property("ADBE Transform Group").property("ADBE Scale").setValue([s,s]);
          var ox=0, oy=0;
          if(S.repeat){ if(S.repeat.grid){ ox=(k%S.repeat.grid[0])*S.repeat.grid[1]; oy=Math.floor(k/S.repeat.grid[0])*S.repeat.grid[2]; } else { ox=k*S.repeat.dx; oy=k*S.repeat.dy; } }
          animate(L, S.anim, t+(S.repeat?k*S.repeat.stagger*nd:0), S.x+ox, S.y+oy, S.rot);
          LOG.layers++;
        }
        continue;
      } else if(S.type==="text"){
        var T=addText(comp, S.text, fonts[S.font]||S.font, S.size, S.color, S.stroke, S.stroke_w); animate(T.layer, S.anim, t, S.x, S.y, S.rot);
      } else if(S.type==="badge"){
        var T2=addText(comp, S.text, fonts.label, S.size, S.color), pad=S.size*0.45;
        var R=rectShape(comp, T2.w+pad*2, T2.h+pad*1.1, S.bg, S.size*0.25, "badge_bg"); R.moveAfter(T2.layer);
        T2.layer.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]); R.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]);
        var G=grouped(comp,[T2.layer,R],"badge"); animate(G, S.anim, t, S.x, S.y, S.rot); fadeChildren([T2.layer,R], S.anim, t);
      } else if(S.type==="phone"){
        var P1=rectShape(comp, S.w, S.h, [40,40,40], 60, "phone"), P2=rectShape(comp, S.w-36, S.h-110, [255,255,255], 28, "screen");
        P1.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]); P2.property("ADBE Transform Group").property("ADBE Position").setValue([0,0]);
        P2.moveBefore(P1); var G2=grouped(comp,[P1,P2],"phone"); animate(G2, S.anim, t, S.x, S.y); fadeChildren([P1,P2], S.anim, t);
      } else if(S.type==="bar"){
        var R2=rectShape(comp, S.w, S.h, S.color, 8, "bar"); var tr=R2.property("ADBE Transform Group");
        tr.property("ADBE Anchor Point").setValue([0, S.h/2]); tr.property("ADBE Position").setValue([S.x, S.base_y]);
        var scp=tr.property("ADBE Scale"); scp.setValueAtTime(t,[100,0]); scp.setValueAtTime(t+0.5,[100,100]); ease(scp); fadeChildren([R2], "pop", t);
        var TL=addText(comp, S.label, fonts.label, 54, [40,40,40]); animate(TL.layer, "fade", t, S.x, S.base_y+60);
      } else if(S.type==="cover"){
        var E=comp.layers.addShape(); E.name="cover"; var g=E.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group"), v=g.property("ADBE Vectors Group");
        v.addProperty("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size").setValue([S.r*2,S.r*2]);
        v.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(rgb(S.color));
        E.property("ADBE Transform Group").property("ADBE Position").setValue([S.x,S.y]);
        if(S.text){ var TC=addText(comp, S.text, fonts.label, S.size, S.text_color); TC.layer.property("ADBE Transform Group").property("ADBE Position").setValue([S.x,S.y]); }
      }
      LOG.layers++;
    }catch(e){ LOG.errors.push(sc.id+" layer "+i+" ("+S.type+"): "+String(e)+" line "+e.line); }
  }
  checkReveal(comp, sc.id);
  return comp;
}
app.beginSuppressDialogs();
try{
  PROJ=openProject(C.aep);
  FOLDER=PROJ.items.addFolder("__inserts");
  var main=null, sub=null;
  for(var i=1;i<=PROJ.numItems;i++){ var it=PROJ.item(i); if(it instanceof CompItem && it.name==="MAIN_KO") main=it; }
  for(var name in C.plan){ if(!C.plan.hasOwnProperty(name)) continue;
    var P=C.plan[name], ins=PROJ.items.addComp("INSERT_"+name, W, H, 1, P.dur, FPS); ins.parentFolder=FOLDER;
    for(var s=0;s<P.scenes.length;s++){ var sc=P.scenes[s], SC=buildScene(sc, C.fonts), L=ins.layers.add(SC); L.startTime=sc.start; L.moveToEnd(); }
    // 본편에서 채널 로고·자막바·자막 글자 스타일 복사
    var bars=[], tmpl=null, logo=null, tex=null;
    var SN=C.sub_name||"#자막", BN=C.bar_layers||["자막바","자막바그림자"], subL=null;   // 편마다 이름이 다름(B053: '자막', 로고 '세모지로고만).png')
    for(var j=1;j<=main.numLayers;j++){ var M=main.layer(j), srcName=(M.source&&M.source.name)||"";
      for(var b=0;b<BN.length;b++) if(M.name===BN[b]) bars.push(M);
      if(!logo && (M.name==="세모지 로고" || srcName.indexOf("세모지로고")===0)) logo=M;
      if(M.name==="텍스쳐" || (C.texture && srcName===C.texture)) tex=M;   // KFC 편은 이름이 63517.jpg
      if(M.source instanceof CompItem && (M.source.name===SN || (!subL && M.source.name.indexOf(SN)===0 && M.source.name.indexOf("자막바")<0))) subL=M; }
    if(subL) for(var q=1;q<=subL.source.numLayers;q++) if(subL.source.layer(q) instanceof TextLayer){ tmpl=subL.source.layer(q); break; }
    var copied=function(L){ var before=ins.numLayers; L.copyToComp(ins);
      var c=null; for(var z=1;z<=ins.numLayers;z++){ if(ins.layer(z).name===L.name){ c=ins.layer(z); break; } }
      if(!c){ LOG.errors.push("복사 실패: "+L.name+" ("+before+"→"+ins.numLayers+")"); return null; }
      c.locked=false; c.startTime=0; c.inPoint=0; c.outPoint=P.dur; c.moveToBeginning(); return c; };   // 장면 위로
    if(logo){ var LL=copied(logo); }
    // 자막바: 자막이 있을 때만 보이게(본편 subtitles.jsx와 같은 규칙, 3프레임 페이드)
    var fr=3/FPS;
    for(var b=bars.length-1;b>=0;b--){ var BL=copied(bars[b]); if(!BL) continue; var op=BL.property("ADBE Transform Group").property("ADBE Opacity");
      while(op.numKeys>0) op.removeKey(1); op.setValueAtTime(0,0);
      for(var q=0;q<P.bar.length;q++){ var a0=P.bar[q][0], e0=P.bar[q][1];
        op.setValueAtTime(Math.max(0,a0-fr),0); op.setValueAtTime(a0,100); op.setValueAtTime(e0,100); op.setValueAtTime(e0+fr,0); } }
    var TX=tex?copied(tex):null; if(!TX) LOG.errors.push("본편 '텍스쳐' 레이어 없음");   // 종이 텍스처(본편처럼 맨 위)
    if(!tmpl){ LOG.errors.push("자막 글자 템플릿 없음"); }
    else { var TT=copied(tmpl); if(!TT) throw new Error("자막 템플릿 복사 실패");
      for(var c=0;c<P.cues.length;c++){ var Q=P.cues[c], N=TT.duplicate(); var sp=N.property("ADBE Text Properties").property("ADBE Text Document");
        while(sp.numKeys>0) sp.removeKey(1); var td=sp.value; td.text=Q.text; sp.setValue(td);
        N.startTime=0; N.inPoint=Q["in"]; N.outPoint=Q["out"]; N.name="SUB "+(c+1); LOG.cues++; }
      TT.remove(); }
    if(TX) TX.moveToBeginning();
    LOG.comps.push({name:"INSERT_"+name, dur:P.dur, scenes:P.scenes.length});
  }
  PROJ.save(new File(C.save_as)); PROJ.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
