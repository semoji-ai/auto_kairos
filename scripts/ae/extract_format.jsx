// 코스트코(B209) 중국어판 포맷 템플릿 추출: 챕터 판 컴프·자막바·자막바그림자·자막 글자 템플릿·챕터 효과음만 남긴 작은 aep.
// 설정: extract_format_job.json {"aep","main","chapter","sub","out_aep","out_dir","log"}
// 쓰인 그림·소리 파일은 out_dir/footage 로 복사해 다시 연결(코스트코 편 폴더를 지워도 템플릿이 살아 있게).
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={kept:[], footage:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), main=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem && it.name===C.main) main=it; }
  if(!main) throw new Error("main 없음 "+C.main);
  var chap=null, sub=null, bars=[], sound=null;
  for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j);
    if(L.source && L.source.name===C.chapter && !chap) chap=L.source;
    if(L.name==="자막바"||L.name==="자막바그림자") bars.push(L);
    if(L.source instanceof CompItem && L.source.name===C.sub) sub=L;
    if(L.source && L.source.name && L.source.name.indexOf("리뉴얼 또롱")===0 && !sound) sound=L.source; }
  if(!chap) throw new Error("챕터 컴프 없음 "+C.chapter);
  var fmt=P.items.addComp("COSTCO_FMT", main.width, main.height, main.pixelAspect, 10, main.frameRate);
  for(var b=bars.length-1;b>=0;b--){ bars[b].copyToComp(fmt); }
  var tmpl=null; if(sub){ for(var q=1;q<=sub.source.numLayers;q++) if(sub.source.layer(q) instanceof TextLayer){ tmpl=sub.source.layer(q); break; } }
  if(tmpl){ var SC=P.items.addComp("SUB_TMPL", sub.source.width, sub.source.height, sub.source.pixelAspect, 10, sub.source.frameRate); tmpl.copyToComp(SC);
    var sl=fmt.layers.add(SC); sl.name="SUB_TMPL";
    var t0=sub.property("ADBE Transform Group"), t1=sl.property("ADBE Transform Group");
    t1.property("ADBE Anchor Point").setValue(t0.property("ADBE Anchor Point").value); t1.property("ADBE Position").setValue(t0.property("ADBE Position").value); t1.property("ADBE Scale").setValue(t0.property("ADBE Scale").value); }
  else LOG.errors.push("자막 템플릿 없음");
  var cl=fmt.layers.add(chap); cl.name="CHAPTER";
  if(sound){ var sd=fmt.layers.add(sound); sd.name="CHAPTER_SOUND"; }
  for(var z=1;z<=fmt.numLayers;z++) LOG.kept.push(fmt.layer(z).name);
  P.reduceProject([fmt]);
  // 쓰인 파일 복사 + 다시 연결. 레이어별로 불러온 .ai("레이어/파일.ai")는 replace()하면 레이어 선택이 풀려 전체 그림이 됨
  // → 복사본을 '컴포지션으로' 다시 불러와 같은 이름("레이어/파일.ai") 항목으로 레이어 소스를 바꿔 끼움
  var fd=new Folder(C.out_dir+"/footage"); if(!fd.exists) fd.create();
  var olds=[]; for(var k=1;k<=P.numItems;k++){ var F=P.item(k); if(F instanceof FootageItem && F.file) olds.push(F); }
  var imported={};
  for(var k=0;k<olds.length;k++){ var F=olds[k], FN=""; try{ FN=F.name;
    var dst=new File(fd.fsName+"/"+F.file.name); if(!dst.exists) F.file.copy(dst);
    LOG.footage.push(F.name+" <- "+F.file.fsName);
    if(F.name.indexOf("/")>0){
      // 레이어별 .ai → 같은 크기 투명 PNG로 구워서 교체(크기 같으니 위치·배율 그대로). 1배(원래 픽셀 크기)
      var K=1, tc=P.items.addComp("_bake", F.width*K, F.height*K, 1, 1, 30), tl=tc.layers.add(F);
      tl.property("ADBE Transform Group").property("ADBE Scale").setValue([100*K,100*K]); tl.property("ADBE Transform Group").property("ADBE Position").setValue([F.width*K/2,F.height*K/2]);
      var png=new File(fd.fsName+"/"+F.name.split("/")[0]+".png");
      tc.saveFrameToPng(0, png);
      for(var w=0;w<50 && !png.exists;w++) $.sleep(100);
      if(!png.exists){ LOG.errors.push("png 굽기 실패 "+F.name); continue; }
      var NEW=P.importFile(new ImportOptions(png)); NEW.mainSource.alphaMode=AlphaMode.PREMULTIPLIED; NEW.mainSource.premulColor=[0,0,0];   // saveFrameToPng는 검정 미리곱 알파
      var users=F.usedIn;
      for(var u=0;u<users.length;u++){ var cp=users[u]; if(cp===tc) continue; for(var l=1;l<=cp.numLayers;l++){ var LL=cp.layer(l); if(LL.source===F){
        LL.replaceSource(NEW,false);   // 같은 픽셀 크기라 위치·배율 그대로
      } } }
      tc.remove();
      LOG.footage.push("  -> png "+png.name+" "+NEW.width+"x"+NEW.height);
    } else F.replace(dst);
  }catch(e){ LOG.errors.push("footage "+FN+": "+e.toString()+" line "+e.line); } }
  P.reduceProject([fmt]);
  P.save(new File(C.out_aep)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.log, S(LOG));
app.endSuppressDialogs(false);
})();
