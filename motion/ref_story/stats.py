import re,glob,sys,statistics as S,json,os
from collections import Counter
END=re.compile(r'(습니다|습니까|니다|니까|세요|에요|예요|어요|아요|해요|네요|군요|죠|까요|나요|가요|래요|데요|거든요|잖아요|요|다|까|냐|지|야|어|네|죠)$')
def load(p):
    L=[l for l in open(p) if l.startswith('[')]
    cues=[]
    for l in L:
        m=re.match(r'\[(\d+):(\d+\.\d)\] (.*)',l); cues.append((int(m[1])*60+float(m[2]),m[3].strip()))
    return cues
def sentences(text):
    toks=text.split(); out=[]; cur=[]
    for t in toks:
        cur.append(t); bare=re.sub(r'[^\w가-힣]','',t)
        punct=bool(re.search(r'[.?!…]$',t.rstrip(')"\'”')))
        if punct or re.search(r'(습니다|습니까|니다|니까|세요|에요|예요|어요|아요|해요|네요|군요|죠|까요|나요|거든요|잖아요|데요|는데요|래요)$',bare):
            out.append(' '.join(cur)); cur=[]
    if cur: out.append(' '.join(cur))
    return out
def cls(s):
    b=re.sub(r'[^\w가-힣]','',s.split()[-1]) if s.split() else ''
    if re.search(r'(습니다|습니까|니다|니까)$',b): return '합니다'
    if re.search(r'(요|죠)$',b): return '해요'
    return '기타/반말·연결'
rows={}
for p in sorted(glob.glob(sys.argv[1]+'/transcripts/*.txt')):
    vid=os.path.basename(p)[:-4]; cues=load(p)
    head=open(p).readline()
    dur=float(re.search(r'\| (\d+)s',open(p).read(300))[1])
    text=' '.join(c[1] for c in cues)
    chars=len(re.sub(r'\s','',text)); eoj=len(text.split())
    span=(cues[-1][0]-cues[0][0])/60
    sents=sentences(text); lens=[len(s.split()) for s in sents]
    C=Counter(cls(s) for s in sents)
    q=sum(1 for s in sents if s.rstrip().endswith('?') or re.search(r'(까|까요|나요|을까|ㄹ까|는지|냐)\??$',re.sub(r'[^\w가-힣?]','',s)))
    conj=Counter(re.findall(r'(그런데|하지만|그러나|근데|그럼에도|반면|그런데도|그래서|결국|사실)',text))
    nums=len(re.findall(r'\d[\d,.]*\s*(?:년|억|만|원|%|퍼센트|개|명|배|위|달러|km|미터|시간|분|초|살|세)',text))
    first=[c for c in cues if c[0]<=60]
    rows[vid]=dict(dur=dur,chars_per_min=round(chars/span),eoj_per_min=round(eoj/span),n_sent=len(sents),
      sent_eoj_mean=round(S.mean(lens),1),sent_eoj_median=S.median(lens),p90=sorted(lens)[int(len(lens)*.9)],
      style={k:round(v/len(sents)*100) for k,v in C.items()},q_per_min=round(q/span,2),q_total=q,
      conj=dict(conj),conj_contrast_per_min=round(sum(conj[k] for k in ['그런데','하지만','그러나','근데','그럼에도','반면','그런데도'])/span,2),
      nums_per_min=round(nums/span,2),
      i_we=len(re.findall(r'(저는|제가|저도|저희|저처럼|제 )',text)),you=len(re.findall(r'(여러분|당신|너희|너는|니가|네가)',text)))
json.dump(rows,open(sys.argv[1]+'/stats.json','w'),ensure_ascii=False,indent=1)
for k,v in rows.items(): print(k,v)
