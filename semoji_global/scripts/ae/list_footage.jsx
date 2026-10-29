(function(){
var J="/Users/jleavens_macmini/LocalProjects/auto_kairos/adobe/cep/com.autokairos.pd/jsx/";
function R(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
$.evalFile(J+"json2.jsx");
var C=JSON.parse(R($.fileName.replace(/\.jsx$/,"_job.json"))), lines=[];
app.beginSuppressDialogs();
try{ if(app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}
app.open(new File(C.aep)); var P=app.project;
for(var i=1;i<=P.numItems;i++){var it=P.item(i); if(!(it instanceof FootageItem)) continue;
  var f="",m=""; try{f=it.mainSource.file?it.mainSource.file.fsName:"";}catch(e){} try{m=it.mainSource.missingFootagePath;}catch(e){}
  lines.push((it.footageMissing?"MISS":"OK")+"\t"+f+"\t"+m);}
P.close(CloseOptions.DO_NOT_SAVE_CHANGES);
var g=new File(C.out); g.encoding="UTF-8"; g.open("w"); g.write(lines.join("\n")); g.close();
})();
