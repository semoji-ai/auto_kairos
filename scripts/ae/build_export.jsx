// 렌더 없이 내보내기 준비만: footage마다 k배 컴프를 만들어 렌더 큐(TIFF+알파, 1프레임)에 넣고 저장.
// 실제 렌더는 aerender -project <save_as> (화면 잠김에서도 동작). 설정 build_export_job.json {aep, ids, k, max_px, out_dir, save_as, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={queued:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof FootageItem) byId[it.id]=it; }
  while(P.renderQueue.numItems>0) P.renderQueue.item(1).remove();
  for(var k=0;k<C.ids.length;k++){
    var it=byId[C.ids[k]];
    if(!it){ LOG.errors.push("no item "+C.ids[k]); continue; }
    try{
      var fn=(it.mainSource && it.mainSource.file)?it.mainSource.file.name:it.name;
      var isVec=/\.(ai|eps|pdf)$/i.test(fn);
      var kk=isVec?Math.min(C.k, C.max_px/Math.max(it.width,it.height)):1; if(kk<1) kk=1;
      var w=Math.max(4,Math.round(it.width*kk)), h=Math.max(4,Math.round(it.height*kk));
      var comp=P.items.addComp("__exp_"+it.id, w, h, 1, 1/29.97, 29.97);
      var L=comp.layers.add(it); L.startTime=0;
      if(kk!==1){ L.property("ADBE Transform Group").property("ADBE Scale").setValue([kk*100,kk*100]); L.collapseTransformation=true; }
      L.property("ADBE Transform Group").property("ADBE Position").setValue([w/2,h/2]);
      var rq=P.renderQueue.items.add(comp);
      rq.timeSpanStart=0; rq.timeSpanDuration=1/29.97;
      var om=rq.outputModule(1); om.applyTemplate("TIFF Sequence with Alpha");
      om.file=new File(C.out_dir+"/"+it.id+"_[#].tif");
      LOG.queued.push({id:it.id, name:it.name, w:it.width, h:it.height, k:kk});
    }catch(e){ LOG.errors.push(C.ids[k]+": "+String(e)); }
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
