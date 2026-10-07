#!/usr/bin/env python3
"""YouTube auto-caption VTT (word timestamps) -> words.json + sentence transcript txt.
usage: vtt2txt.py <vtt> <out_txt>"""
import re, sys, json
def ts(s):
    h,m,r=s.split(':'); return int(h)*3600+int(m)*60+float(r)
vtt,out=sys.argv[1],sys.argv[2]
words=[]
cue_start=None
for line in open(vtt,encoding='utf-8'):
    line=line.rstrip('\n')
    m=re.match(r'(\d\d:\d\d:\d\d\.\d+) --> ',line)
    if m: cue_start=ts(m.group(1)); continue
    if '<c>' in line:
        first=re.match(r'^([^<]*)',line).group(1).strip()
        if first: words.append((cue_start,first))
        for t,w in re.findall(r'<(\d\d:\d\d:\d\d\.\d+)><c>\s*([^<]*)</c>',line):
            w=w.strip()
            if w: words.append((ts(t),w))
# manual subs (no <c>) fallback
if not words:
    print('no word-level cues', file=sys.stderr)
# sentence split: punctuation, or long pause >1.2s after a verb-final ending
sents=[];cur=[];start=None;prev_t=None
END=re.compile(r'(다|요|죠|까|니다|네|지|야|어|아|음|임|함|듯|ㄷㄷ)$')
for i,(t,w) in enumerate(words):
    nxt=words[i+1][0] if i+1<len(words) else t+5
    if start is None: start=t
    cur.append(w)
    gap=nxt-t
    if re.search(r'[.?!]$',w) or (gap>1.6 and END.search(w)) or len(cur)>=45:
        sents.append((start,' '.join(cur))); cur=[]; start=None
if cur: sents.append((start,' '.join(cur)))
with open(out,'w',encoding='utf-8') as f:
    for t,s in sents:
        f.write(f"[{int(t//60):02d}:{t%60:05.2f}] {s}\n")
json.dump(words,open(out.replace('.txt','.words.json'),'w'),ensure_ascii=False)
print(out,len(words),'words',len(sents),'sents')
