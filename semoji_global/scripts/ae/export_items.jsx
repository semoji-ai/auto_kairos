// footage 아이템을 k배 PNG로 저장(벡터는 연속 래스터화). 설정 export_items_job.json {aep, ids:[item id], k, out_dir, out}
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={saved:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof FootageItem) byId[it.id]=it; }
  var tmp=P.items.addComp("__export", 100, 100, 1, 1, 29.97);
  for(var k=0;k<C.ids.length;k++){
    var it=byId[C.ids[k]];
    if(!it){ LOG.errors.push("no item "+C.ids[k]); continue; }
    try{
      var k=C.k||1, isVec=/\.(ai|eps|pdf)$/i.test(it.name.split("/").pop()) || (it.mainSource && it.mainSource.file && /\.(ai|eps|pdf)$/i.test(it.mainSource.file.name));
      var kk=isVec?k:1;   // 래스터 이미지는 원래 해상도 그대로
      tmp.width=Math.min(30000,Math.round(it.width*kk)); tmp.height=Math.min(30000,Math.round(it.height*kk));
      while(tmp.numLayers>0) tmp.layer(1).remove();
      var L=tmp.layers.add(it); L.startTime=0;
      if(kk!==1){ L.property("ADBE Transform Group").property("ADBE Scale").setValue([kk*100,kk*100]); L.collapseTransformation=true;
                  L.property("ADBE Transform Group").property("ADBE Position").setValue([tmp.width/2,tmp.height/2]); }
      var f=new File(C.out_dir+"/"+it.id+".png");
      tmp.saveFrameToPng(0, f);
      LOG.saved.push({id:it.id, name:it.name, w:it.width, h:it.height, k:kk, file:f.fsName});
    }catch(e){ LOG.errors.push(C.ids[k]+": "+String(e)); }
  }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
