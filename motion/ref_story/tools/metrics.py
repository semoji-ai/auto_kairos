#!/usr/bin/env python3
"""Script metrics per transcript. usage: metrics.py <channel_dir> [--srt]  (reads transcripts/*.txt + *.words.json, subs/*.info.json)"""
import re, sys, json, glob, os, statistics as st
ch=sys.argv[1]
def load_txt(p):
    out=[]
    for l in open(p,encoding='utf-8'):
        m=re.match(r'\[(\d+):([\d.]+)\] (.*)',l.strip())
        if m: out.append((int(m.group(1))*60+float(m.group(2)),m.group(3)))
    return out
def cls_end(s):
    s=re.sub(r'\[음악\]|&gt;&gt;','',s).strip().rstrip('.?!~ ').strip()
    if not s: return None
    if re.search(r'(니다|니까|십시오|습니까)$',s): return '합니다'
    if re.search(r'(요|죠)$',s): return '해요'
    if re.search(r'(다|냐|니|거|야|어|아|지|음|임|함|네|듯|ㄷㄷ|라|자|게|고|는데|는|데|까)$',s): return '반말·평서'
    return '명사·기타'
CONTRAST=['그런데','근데','하지만','그러나','다만','반면','그럼에도','그래도','오히려','사실']
SIG=['엥?','다는 거','하실 수도 있는데','로다가','왜냐','오지게','국룰','각이','이쯤 되면','예.','아니요','자,','뭐 ','물론','실제로','대체','과연','여러분','우리','저희','제가','저는']
rows=[]
for tp in sorted(glob.glob(f'{ch}/transcripts/*.txt')):
    vid=os.path.basename(tp)[:-4]
    if vid.endswith('.whisper'): continue
    info=json.load(open(f'{ch}/subs/{vid}.info.json'))
    words=json.load(open(tp.replace('.txt','.words.json')))
    sp=os.path.exists(tp.replace('.txt','.whisper.txt'))
    sents=load_txt(tp.replace('.txt','.whisper.txt') if sp else tp)
    t0,t1=words[0][0],words[-1][0]
    mins=(t1-t0)/60
    text=' '.join(w for _,w in words)
    text=re.sub(r'\[음악\]','',text)
    chars=len(re.sub(r'\s','',text)); eoj=len(text.split())
    lens=[len(re.sub(r'\[음악\]','',s).split()) for _,s in sents]
    ends={}
    for _,s in sents:
        c=cls_end(s)
        if c: ends[c]=ends.get(c,0)+1
    nE=sum(ends.values())
    q=sum(1 for _,s in sents if s.strip().endswith('?') or re.search(r'(까요|냐|나요|는가)[.?]?$',s.strip()))
    contrast={k:len(re.findall(k,text)) for k in CONTRAST}
    sig={k:text.count(k) for k in SIG}
    nums=len(re.findall(r'\d[\d,.]*|(?:[일이삼사오육칠팔구십백천만억]+(?:만|억|천|백)?(?:\s)?(?:명|톤|척|년|배|%|원|개|kg|m|칼로리))',text))
    gaps=[(round(words[i][0]),round(words[i+1][0]-words[i][0],1)) for i in range(len(words)-1) if words[i+1][0]-words[i][0]>3.0]
    rows.append(dict(id=vid,title=info['title'],dur=info['duration'],speech_span=round(t1-t0),chars_pm=round(chars/mins),eoj_pm=round(eoj/mins),
      n_sent=len(sents),sent_mean=round(st.mean(lens),1),sent_median=st.median(lens),p10=sorted(lens)[len(lens)//10],p90=sorted(lens)[len(lens)*9//10],
      short_le4=round(100*sum(1 for x in lens if x<=4)/len(lens)),long_ge20=round(100*sum(1 for x in lens if x>=20)/len(lens)),
      ends={k:round(100*v/nE) for k,v in ends.items()},questions=q,q_pm=round(q/mins,2),contrast=contrast,contrast_pm=round(sum(contrast[k] for k in ['그런데','근데','하지만','그러나','다만','반면'])/mins,2),
      sig=sig,nums=nums,nums_pm=round(nums/mins,1),gaps=gaps,sent_src='whisper' if sp else 'yt-auto'))
json.dump(rows,open(f'{ch}/metrics.json','w'),ensure_ascii=False,indent=1)
for r in rows:
    print(r['id'],r['dur'],r['speech_span'],'cpm',r['chars_pm'],'epm',r['eoj_pm'],'sent',r['n_sent'],r['sent_mean'],r['sent_median'],r['p10'],r['p90'],'short',r['short_le4'],'long',r['long_ge20'],r['ends'],'q',r['questions'],r['q_pm'],'con',r['contrast_pm'],r['contrast'],'num/m',r['nums_pm'],r['sent_src'])
    print('   sig',{k:v for k,v in r['sig'].items() if v}); print('   gaps',r['gaps'])
