// 코스트코(B209) 중국어판 포맷 적용(format_costco.py가 만든 job). 템플릿 aep를 불러와 본편에 자막바·자막 템플릿·챕터 판·챕터 소리를 넣고
// 목차·기존 자막바·원래 장 제목 글자를 끄고, AE 안 장 효과음을 음소거.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={hidden:[], muted:[], chapters:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), main=P.itemByID(C.main_id);
  if(!main) throw new Error("main 없음 "+C.main_id);
  // 레이어 참조를 먼저 잡아 둠(새 레이어를 넣으면 번호가 밀림)
  var hide=[], mute=[], chap=[], subL=null, logoL=null;
  for(var i=0;i<C.hide.length;i++) hide.push(main.layer(C.hide[i]));
  for(var i=0;i<C.mute.length;i++) mute.push(main.layer(C.mute[i]));
  for(var i=0;i<C.chapters.length;i++) chap.push(main.layer(C.chapters[i].layer));
  for(var j=1;j<=main.numLayers;j++){ var M=main.layer(j), sn=(M.source&&M.source.name)||"";
    if(M.source instanceof CompItem && sn===C.sub_name) subL=M;
    if(sn.indexOf("세모지로고")===0) logoL=M; }
  if(!subL) throw new Error("자막 컴프 레이어 없음 "+C.sub_name);
  // 템플릿 불러오기
  var before={}; for(var k=1;k<=P.numItems;k++) before[P.item(k).id]=1;
  try{ P.importFile(new ImportOptions(new File(C.fmt))); }catch(e){ LOG.warnings=(LOG.warnings||[]).concat(["import: "+String(e).replace(/[^\u0020-\uFFFF]/g,"?")]); }   // 이름 속 이상 문자 경고는 무시(불러오기는 됨)
  var fmt=null; for(var k=1;k<=P.numItems;k++){ var it=P.item(k); if(!before[it.id] && it instanceof CompItem && it.name==="COSTCO_FMT") fmt=it; }
  if(!fmt) throw new Error("COSTCO_FMT 없음");
  var fl={}; for(var k=1;k<=fmt.numLayers;k++) fl[fmt.layer(k).name]=fmt.layer(k);
  // 1) 끄기·음소거
  for(var i=0;i<hide.length;i++){ hide[i].locked=false; hide[i].enabled=false; LOG.hidden.push(hide[i].name); }
  for(var i=0;i<chap.length;i++){ chap[i].locked=false; chap[i].enabled=false; LOG.hidden.push(chap[i].name); }
  for(var i=0;i<mute.length;i++){ mute[i].locked=false; try{ mute[i].audioEnabled=false; }catch(e){} mute[i].enabled=false; LOG.muted.push(mute[i].name); }
  // 2) 챕터 판 + 소리(로고 바로 아래 = 본편 그림 위)
  var chComp=fl["CHAPTER"].source, snd=fl["CHAPTER_SOUND"]?fl["CHAPTER_SOUND"].source:null;
  for(var i=0;i<C.chapters.length;i++){ var c=C.chapters[i];
    var D=chComp.duplicate(); D.name="CN_CHAPTER_"+c.num;
    for(var t=1;t<=D.numLayers;t++){ var T=D.layer(t); if(!(T instanceof TextLayer)) continue;
      var sp=T.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value, s=String(td.text);
      if(/^\d+$/.test(s)) td.text=String(c.num); else if(s.indexOf("章")>=0) td.text="第"+c.num+"章"; else td.text=c.title;
      sp.setValue(td); }
    var CL=main.layers.add(D); CL.startTime=c["in"]; var span=c.out-c["in"];
    if(span>D.duration+1e-3){ CL.stretch=span/D.duration*100; CL.startTime=c["in"]; }
    CL.inPoint=c["in"]; CL.outPoint=c["in"]+Math.max(span,0.01);
    if(logoL) CL.moveAfter(logoL);
    LOG.chapters.push({num:c.num, title:c.title, "in":CL.inPoint, out:CL.outPoint});
    if(snd){ var SL=main.layers.add(snd); SL.startTime=c["in"]; SL.moveToEnd(); }
  }
  // 3) 자막바(자막 컴프 바로 아래) + 자막 글자 템플릿(자막 컴프 맨 위)
  var shadow=null, bar=null;
  function byName(n){ for(var z=1;z<=main.numLayers;z++) if(main.layer(z).name===n) return main.layer(z); return null; }
  fl["자막바그림자"].copyToComp(main); shadow=byName("자막바그림자");
  fl["자막바"].copyToComp(main); bar=byName("자막바");
  if(!bar||!shadow) throw new Error("자막바 복사 실패");
  bar.locked=false; shadow.locked=false;
  // 코스트코 편에서 복사한 자막바에는 그 편 자막 구간 불투명도 키가 따라옴(0초 값=0) → 키 지우고 원래 값(100)으로. 구간 키는 subtitles.jsx가 다시 넣음
  var BB=[bar,shadow]; for(var b2=0;b2<BB.length;b2++){ var op=BB[b2].property("ADBE Transform Group").property("ADBE Opacity"); while(op.numKeys>0) op.removeKey(1); op.setValue(100); }
  var bl=[bar,shadow];
  for(var b=0;b<bl.length;b++){ bl[b].startTime=0; bl[b].inPoint=0; bl[b].outPoint=main.duration; }
  bar.moveAfter(subL); shadow.moveAfter(bar);
  var ST=fl["SUB_TMPL"], tsrc=null; for(var q=1;q<=ST.source.numLayers;q++) if(ST.source.layer(q) instanceof TextLayer){ tsrc=ST.source.layer(q); break; }
  if(!tsrc) throw new Error("자막 템플릿 글자 없음");
  tsrc.copyToComp(subL.source);   // 맨 위 = subtitles.jsx가 쓰는 첫 글자 레이어
  var t0=ST.property("ADBE Transform Group"), t1=subL.property("ADBE Transform Group"); subL.locked=false;
  t1.property("ADBE Anchor Point").setValue(t0.property("ADBE Anchor Point").value);
  t1.property("ADBE Position").setValue(t0.property("ADBE Position").value);
  t1.property("ADBE Scale").setValue(t0.property("ADBE Scale").value);
  if(subL.source.width!==ST.source.width || subL.source.height!==ST.source.height) LOG.errors.push("자막 컴프 크기 다름 "+subL.source.width+"x"+subL.source.height+" vs "+ST.source.width+"x"+ST.source.height);
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
