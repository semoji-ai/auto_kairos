// 한 레이어의 이펙트(속성값·키 포함)와 소스 텍스트 표현식 덤프. 설정: probe_layer_job.json {"aep","comp_id","layer","out"}
(function(){
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var C=eval("("+R($.fileName.replace(/\.jsx$/,"_job.json"))+")"), out=[];
app.beginSuppressDialogs();
app.open(new File(C.aep)); var P=app.project, comp=P.itemByID(C.comp_id), L=comp.layer(C.layer);
out.push("name="+L.name);
if(L instanceof TextLayer){var st=L.property("ADBE Text Properties").property("ADBE Text Document"); out.push("expr="+st.expression+" | text="+st.value.text+" | keys="+st.numKeys);}
function dump(g,ind){ for(var k=1;k<=g.numProperties;k++){var p=g.property(k);
  if(p.propertyType===PropertyType.PROPERTY){ var v=""; try{v=String(p.value);}catch(e){} var ks=[]; try{for(var q=1;q<=p.numKeys;q++) ks.push(p.keyTime(q).toFixed(2)+"="+String(p.keyValue(q)));}catch(e){}
    out.push(ind+p.matchName+"|"+p.name+"="+v+(p.expressionEnabled?" EXPR:"+p.expression:"")+(ks.length?" KEYS:"+ks.join(";"):""));}
  else { out.push(ind+"["+p.matchName+"|"+p.name+"]"); dump(p,ind+"  "); } } }
var fx=L.property("ADBE Effect Parade"); if(fx) dump(fx,"");
var f=new File(C.out);f.encoding="UTF-8";f.open("w");f.write(out.join("\r\n"));f.close();
P.close(CloseOptions.DO_NOT_SAVE_CHANGES); app.endSuppressDialogs(false);
})();
