(function(){var out=[];function t(p){try{var it=app.project.importFile(new ImportOptions(new File(p)));out.push('OK '+p);}catch(e){out.push('ERR '+p+' '+String(e).slice(0,60));}}
app.beginSuppressDialogs();try{app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(_e){}app.newProject();
t("/private/tmp/claude-501/-Users-jleavens-macmini/7cf44c15-9613-44eb-8454-4637dec8240a/scratchpad/\ub85c\uceec\ud55c\uae00_c/g1.png");
t("/private/tmp/claude-501/-Users-jleavens-macmini/7cf44c15-9613-44eb-8454-4637dec8240a/scratchpad/\u1105\u1169\u110f\u1165\u11af\u1112\u1161\u11ab\u1100\u1173\u11af_d/g1.png");
var g=new File('/Users/jleavens_macmini/Projects/semoji_global/reports/t_import.txt');g.encoding='UTF-8';g.open('w');g.write(out.join('\n'));g.close();})();