// 공용 에셋 교체: job.items의 footage id를 새 파일로 replace, 교체 후 크기·길이가 원본과 다르면 mismatch.
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={replaced:[], missing:[], mismatch:[], errors:[]};
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), byId={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof FootageItem) byId[it.id]=it; }
  for(var k=0;k<C.items.length;k++){
    var J=C.items[k], f=byId[J.id];
    if(!f){ LOG.missing.push(J.id); continue; }
    try{
      var w0=f.width, h0=f.height, d0=f.duration;
      f.replace(new File(J.path));
      if(f.width!==w0 || f.height!==h0 || Math.abs(f.duration-d0)>0.05) LOG.mismatch.push(J.id+" "+J.name+": "+w0+"x"+h0+"/"+d0+" → "+f.width+"x"+f.height+"/"+f.duration);
      else LOG.replaced.push(J.id+" "+J.name);
    }catch(e1){ LOG.errors.push(J.id+": "+String(e1)); }
  }
  P.save(new File(C.save_as)); P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
