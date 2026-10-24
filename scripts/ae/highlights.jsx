// 형광펜(칠해 나가는 막대)을 번역 문장에 다시 맞춤.  job: highlights_job.json
//  mode "scan":  컴프마다 Scale 키가 있는 footage 레이어(막대 후보)와 __en_ 프리컴프 레이어(+안의 텍스트 레이어)를 기록
//  mode "apply": items[]마다 __en_ 컴프의 텍스트 레이어에서 [i0,i1) 구절의 x 범위(그 컴프 좌표)를 재고,
//                메인 좌표로 바꿔 막대 position x와 마지막 Scale X 키를 맞춤 → save_as
(function(){
var SELF=$.fileName;
$.evalFile(File(SELF).parent.fsName+"/lib.jsx");
var C=jobConfig(SELF), LOG={bars:[], texts:[], fitted:[], errors:[]};
function tr(L){ var t=L.property("ADBE Transform Group");
  return {anchor:t.property("ADBE Anchor Point").value, pos:t.property("ADBE Position").value, scale:t.property("ADBE Scale").value}; }
function keysOf(L){ var p=L.property("ADBE Transform Group").property("ADBE Scale"), k=[];
  for(var i=1;i<=p.numKeys;i++) k.push(["ADBE Scale", p.keyTime(i), p.keyValue(i)]); return k; }
function width(L, s){
  var sp=L.property("ADBE Text Properties").property("ADBE Text Document"), td=sp.value;
  td.text=s; sp.setValue(td); return L.sourceRectAtTime(0,false).width;
}
app.beginSuppressDialogs();
try{
  var P=openProject(C.aep), comps={};
  for(var i=1;i<=P.numItems;i++){ var it=P.item(i); if(it instanceof CompItem) comps[it.name]=it; }
  if(C.mode==="scan"){
    for(var name in comps){ if(!comps.hasOwnProperty(name)) continue; var cp=comps[name];
      for(var j=1;j<=cp.numLayers;j++){ var L=cp.layer(j); if(!L.source) continue;
        var t=tr(L);
        if(L.source instanceof FootageItem && L.property("ADBE Transform Group").property("ADBE Scale").numKeys>=2)
          LOG.bars.push({comp:name, idx:j, src:L.source.id, name:L.name, w:L.source.width, h:L.source.height, "in":L.inPoint, "out":L.outPoint,
                         anchor:t.anchor, pos:t.pos, scale:t.scale, keys:keysOf(L)});
        if(L.source instanceof CompItem && L.source.name.indexOf("__en_")===0){
          var sub=L.source, lines=[];
          for(var q=1;q<=sub.numLayers;q++){ var S2=sub.layer(q); if(!(S2 instanceof TextLayer)) continue;
            var st=tr(S2), r=S2.sourceRectAtTime(0,false);
            lines.push({key:S2.name, text:String(S2.property("ADBE Text Properties").property("ADBE Text Document").value.text),
                        anchor:st.anchor, pos:st.pos, scale:st.scale, left:r.left, width:r.width, top:r.top, height:r.height}); }
          LOG.texts.push({comp:name, idx:j, sub:sub.name, "in":L.inPoint, "out":L.outPoint, anchor:t.anchor, pos:t.pos, scale:t.scale, lines:lines});
        }
      }
    }
  } else {
    for(var k=0;k<C.items.length;k++){
      var J=C.items[k];
      try{
        var cp=comps[J.comp], sub=comps[J.sub], T=null, BL=cp.layer(J.bar_idx);
        for(var q=1;q<=sub.numLayers;q++) if(sub.layer(q).name===J.key) T=sub.layer(q);
        if(!T){ LOG.errors.push(J.key+": text layer not found"); continue; }
        var D=T.duplicate(); D.enabled=false;
        var full=width(D, J.text), pre=J.i0>0?width(D, J.text.substring(0,J.i0)+"|")-width(D,"|"):0, seg=width(D, J.text.substring(J.i0,J.i1));
        D.remove();
        var st=tr(T), r=T.sourceRectAtTime(0,false), sx=st.scale[0]/100;
        var left=st.pos[0]-(st.anchor[0]-r.left)*sx;                 // 그 컴프 좌표에서 줄 왼쪽 끝
        var u0=left+pre*sx-J.pad, u1=left+(pre+seg)*sx+J.pad;
        var Lt=J.layer_tr, x0=Lt.pos[0]+(u0-Lt.anchor[0])*Lt.scale[0]/100, x1=Lt.pos[0]+(u1-Lt.anchor[0])*Lt.scale[0]/100;
        var sxNew=100*(x1-x0)/BL.source.width, tg=BL.property("ADBE Transform Group"), sc=tg.property("ADBE Scale"), ps=tg.property("ADBE Position");
        var lk=BL.locked; BL.locked=false;
        var last=sc.numKeys, v=sc.keyValue(last); sc.setValueAtKey(last,[sxNew, v[1], v.length>2?v[2]:100]);
        var pv=ps.value; ps.setValue([x0+tg.property("ADBE Anchor Point").value[0]*sxNew/100, pv[1], pv.length>2?pv[2]:0]);
        BL.locked=lk;
        LOG.fitted.push({bar:J.comp+"#"+J.bar_idx, key:J.key, phrase:J.text.substring(J.i0,J.i1), x0:x0, x1:x1});
      }catch(e1){ LOG.errors.push(J.key+": "+String(e1)+" line "+e1.line); }
    }
    P.save(new File(C.save_as));
  }
  P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
}catch(e){ LOG.errors.push(String(e)+" line "+e.line); }
writeText(C.out, S(LOG));
app.endSuppressDialogs(false);
})();
