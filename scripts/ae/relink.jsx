// 누락 footage 재연결. 설정: relink_job.json
// {"jobs":[{"aep":절대경로,"save_as":절대경로,"map":{"원래 fullpath(\\는 /로)":"새 절대경로",...}}], "log":절대경로}
// 각 job: 열기 → footageMissing 항목을 map(원래 경로 → 파일명 순으로 매칭)으로 replace → save_as → 닫기.
// 결과(job별 relinked/still_missing 목록)를 log에 JSON으로 기록.
(function(){
var J="/Users/jleavens_macmini/LocalProjects/auto_kairos/adobe/cep/com.autokairos.pd/jsx/";
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
function W(p,s){var f=new File(p);f.encoding="UTF-8";f.open("w");f.write(s);f.close();}
$.evalFile(J+"json2.jsx");
function S(v){ // json2.jsx는 parse 전용이라 직렬화는 여기서
  if(v===null||v===undefined) return "null";
  var t=typeof v;
  if(t==="number"||t==="boolean") return String(v);
  if(t==="string") return '"'+v.replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\n/g,"\\n").replace(/\r/g,"\\r").replace(/\t/g,"\\t")+'"';
  if(v instanceof Array){ var a=[]; for(var i=0;i<v.length;i++) a.push(S(v[i])); return "["+a.join(",")+"]"; }
  var o=[]; for(var k in v) if(v.hasOwnProperty(k)) o.push(S(k)+":"+S(v[k])); return "{"+o.join(",")+"}";
}
var CFG=$.fileName.replace(/\.jsx$/,"_job.json");
var C=JSON.parse(R(CFG)), out=[];
var STILL=/\.(png|jpe?g|tiff?|tga|psd|exr|dpx|bmp|ai|eps|pdf)$/i;
function norm(s){return String(s).replace(/\\/g,"/");}
function base(s){var p=norm(s).split("/");return p[p.length-1].toLowerCase();}
app.beginSuppressDialogs();
for(var k=0;k<C.jobs.length;k++){
  var jb=C.jobs[k], res={aep:jb.aep, relinked:[], still_missing:[], error:null};
  try{
    try{ if(app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}
    app.open(new File(jb.aep)); var P=app.project;
    var byPath={}, byName={};
    for(var key in jb.map){ byPath[norm(key)]=jb.map[key]; var b=base(key); if(!byName[b]) byName[b]=jb.map[key]; else if(byName[b]!==jb.map[key]) byName[b]="__AMBIG__"; }
    for(var i=1;i<=P.numItems;i++){
      var it=P.item(i);
      if(!(it instanceof FootageItem) || !it.footageMissing) continue;
      var mp=""; try{ mp=it.mainSource.missingFootagePath; }catch(e){}
      var tgt=byPath[norm(mp)] || byName[base(mp||it.name)];
      if(!tgt || tgt==="__AMBIG__"){ res.still_missing.push({name:it.name, path:mp}); continue; }
      var f=new File(tgt);
      if(!f.exists){ res.still_missing.push({name:it.name, path:mp, tried:tgt}); continue; }
      try{
        var seq=false; try{ seq = STILL.test(tgt) && !it.mainSource.isStill; }catch(e){}
        if(seq) it.replaceWithSequence(f,false); else it.replace(f);
        res.relinked.push({name:it.name, from:mp, to:tgt, seq:seq});
      }catch(e){ res.still_missing.push({name:it.name, path:mp, tried:tgt, err:String(e)}); }
    }
    if(res.relinked.length) P.save(new File(jb.save_as));
    res.saved = res.relinked.length>0;
    P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
  }catch(e){ res.error=String(e); }
  out.push(res);
  W(C.log, S(out));
}
app.endSuppressDialogs(false);
})();
