// 메인 컴프 이름을 고유하게 바꾸고 save_as. 설정 prep_main_job.json {aep, comp_id, new_name, check_ids:[footage id], save_as, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), res={missing_used:[], ok:0, errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), comp=null;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it.id==C.comp_id) comp=it; }
  if(!comp) throw new Error("comp id not found");
  comp.name=C.new_name; res.comp=comp.name; res.dur=comp.duration;
  var want={}; for(var k=0;k<C.check_ids.length;k++) want[C.check_ids[k]]=1;
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i);
    if(it instanceof FootageItem && want[it.id]){ if(it.footageMissing) res.missing_used.push(it.name); else res.ok++; } }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ res.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(res));
app.endSuppressDialogs(false);
})();
