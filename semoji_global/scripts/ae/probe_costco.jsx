// 코스트코(B209) 중국어판 포맷 요소 덤프: 챕터 컴프(재귀 텍스트), 본편 자막바·자막바그림자, #자막 템플릿. 설정: probe_costco_job.json {"aep","main","out"}
(function(){
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
var C=eval("("+R($.fileName.replace(/\.jsx$/,"_job.json"))+")"), out=[];
app.beginSuppressDialogs();
app.open(new File(C.aep)); var P=app.project, main=null;
for(var i=1;i<=P.numItems;i++){var it=P.item(i); if(it instanceof CompItem && it.name===C.main) main=it;}
function tx(L){ var sp=L.property("ADBE Text Properties").property("ADBE Text Document"); if(sp.expressionEnabled) return " TEXTEXPR("+sp.expression.slice(0,80)+")"; var td=sp.value, r="";
  function g(f){ try{ return f(); }catch(e){ return "?"; } }
  return " TEXT="+g(function(){return td.text.replace(/\r/g,"|");})+" font="+g(function(){return td.font;})+" size="+g(function(){return td.fontSize;})+" fill="+g(function(){return td.applyFill?td.fillColor:"-";})+" stroke="+g(function(){return td.applyStroke?td.strokeColor+"/"+td.strokeWidth:"-";})+" track="+g(function(){return td.tracking;})+" just="+g(function(){return td.justification;}); }
function tx_old(L){ var td=null;
  return " TEXT="+td.text.replace(/\r/g,"|")+" font="+td.font+" size="+td.fontSize+" fill="+(td.applyFill?td.fillColor:"-")+" stroke="+(td.applyStroke?td.strokeColor+"/"+td.strokeWidth:"-")+" track="+td.tracking+" just="+td.justification; }
function tr(L){ try{ return tr0(L); }catch(e){ return " tr?"+e; } }
function V(p){ if(p.expressionEnabled) return "EXPR("+p.expression.replace(/[\r\n]+/g," ").slice(0,80)+")"; return p.value; }
function tr0(L){ var g=L.property("ADBE Transform Group"); return " pos="+V(g.property("ADBE Position"))+" anc="+V(g.property("ADBE Anchor Point"))+" sc="+V(g.property("ADBE Scale"))+" op="+V(g.property("ADBE Opacity"))+" posKeys="+g.property("ADBE Position").numKeys+" scKeys="+g.property("ADBE Scale").numKeys; }
function dump(comp,ind,depth){ out.push(ind+"COMP "+comp.name+" id="+comp.id+" "+comp.width+"x"+comp.height+" dur="+comp.duration);
  for(var j=1;j<=comp.numLayers;j++){ var L=comp.layer(j), s="";
    try{ if(L instanceof TextLayer) s=tx(L); }catch(e){}
    var fx=L.property("ADBE Effect Parade"), fxs=[]; if(fx) for(var k=1;k<=fx.numProperties;k++) fxs.push(fx.property(k).matchName);
    out.push(ind+"  "+j+" "+L.name+" ["+(L.source?L.source.name:(L instanceof ShapeLayer?"shape":""))+"] in="+L.inPoint.toFixed(2)+" out="+L.outPoint.toFixed(2)+tr(L)+s+" fx="+fxs.join(","));
    if(L.source instanceof CompItem && depth<3) dump(L.source,ind+"    ",depth+1); } }
for(var j=1;j<=main.numLayers;j++){ var L=main.layer(j);
  if(L.name.indexOf("챕터2")===0 || L.name==="자막바" || L.name==="자막바그림자" || L.name==="세모지 로고"){ out.push("MAIN "+j+" "+L.name+tr(L)+" in="+L.inPoint.toFixed(2)+" out="+L.outPoint.toFixed(2));
    if(L.source instanceof CompItem) dump(L.source,"  ",0);
    if(L instanceof ShapeLayer){ var g=L.property("ADBE Root Vectors Group"); for(var a=1;a<=g.numProperties;a++){ var gg=g.property(a); out.push("   shape "+gg.name);
      var v=gg.property("ADBE Vectors Group"); if(v) for(var b=1;b<=v.numProperties;b++){ var p=v.property(b); var d=p.name;
        try{ if(p.matchName==="ADBE Vector Shape - Rect") d+=" size="+p.property("ADBE Vector Rect Size").value+" pos="+p.property("ADBE Vector Rect Position").value+" r="+p.property("ADBE Vector Rect Roundness").value;
          if(p.matchName==="ADBE Vector Graphic - Fill") d+=" fill="+p.property("ADBE Vector Fill Color").value+" op="+p.property("ADBE Vector Fill Opacity").value;
          if(p.matchName==="ADBE Vector Graphic - Stroke") d+=" stroke="+p.property("ADBE Vector Stroke Color").value+" w="+p.property("ADBE Vector Stroke Width").value; }catch(e){}
        out.push("     "+d); } } } }
  if(L.source instanceof CompItem && L.source.name==="#자막"){ var sc=L.source; out.push("SUB layer "+j+tr(L)); for(var q=1;q<=Math.min(2,sc.numLayers);q++){ var T=sc.layer(q); out.push("  tmpl "+T.name+tr(T)+(T instanceof TextLayer?tx(T):"")); } } }
var f=new File(C.out);f.encoding="UTF-8";f.open("w");f.write(out.join("\r\n"));f.close();
P.close(CloseOptions.DO_NOT_SAVE_CHANGES); app.endSuppressDialogs(false);
})();
