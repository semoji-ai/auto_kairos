// 공용 유틸: 파일 읽기/쓰기, JSON 직렬화(json2.jsx는 parse 전용)
$.evalFile("/Users/jleavens_macmini/LocalProjects/auto_kairos/adobe/cep/com.autokairos.pd/jsx/json2.jsx");
function readText(p){var f=new File(p);f.encoding="UTF-8";f.open("r");var s=f.read();f.close();return s;}
function writeText(p,s){var f=new File(p);f.encoding="UTF-8";f.lineFeed="Unix";f.open("w");f.write(s);f.close();}
function S(v){
  if(v===null||v===undefined) return "null";
  var t=typeof v;
  if(t==="number") return isFinite(v)?String(v):"null";
  if(t==="boolean") return String(v);
  if(t==="string") return '"'+v.replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/\n/g,"\\n").replace(/\r/g,"\\r").replace(/\t/g,"\\t")+'"';
  if(v instanceof Array){ var a=[]; for(var i=0;i<v.length;i++) a.push(S(v[i])); return "["+a.join(",")+"]"; }
  var o=[]; for(var k in v) if(v.hasOwnProperty(k)) o.push(S(k)+":"+S(v[k])); return "{"+o.join(",")+"}";
}
function jobConfig(self){ return JSON.parse(readText(self.replace(/\.jsx$/,"_job.json"))); }
function openProject(p){
  try{ if(app.project) app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}
  app.open(new File(p)); return app.project;
}
