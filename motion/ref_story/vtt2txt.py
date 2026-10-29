"""VTT(수동/자동) -> 타임스탬프 원고 txt. 자동자막은 롤링 중복 제거."""
import re,sys,os,glob,json
TS=re.compile(r'(\d+):(\d+):(\d+\.\d+) --> (\d+):(\d+):(\d+\.\d+)')
def sec(h,m,s): return int(h)*3600+int(m)*60+float(s)
def parse(path):
    txt=open(path,encoding='utf-8').read()
    blocks=txt.split('\n\n'); cues=[]
    auto='<c>' in txt
    for b in blocks:
        lines=b.strip('\n').split('\n')
        for i,l in enumerate(lines):
            m=TS.search(l)
            if m:
                st=sec(*m.groups()[:3]); en=sec(*m.groups()[3:])
                body=lines[i+1:]
                if auto:
                    tagged=[x for x in body if '<c>' in x]
                    if not tagged: break
                    t=re.sub(r'<[^>]+>','',tagged[-1]).strip()
                else:
                    t=' '.join(x.strip() for x in body).strip()
                    t=re.sub(r'<[^>]+>','',t)
                if t: cues.append((st,en,t))
                break
    return cues,auto
def fmt(s): return f"{int(s//60):02d}:{s%60:04.1f}"
if __name__=='__main__':
    ch=sys.argv[1]
    for info in sorted(glob.glob(f'{ch}/raw/*.info.json')):
        vid=os.path.basename(info).split('.')[0]
        d=json.load(open(info))
        man=[s for s in (d.get('subtitles') or {}) if s=='ko']
        p=f'{ch}/raw/{vid}.ko.vtt' if man else f'{ch}/raw/{vid}.ko-orig.vtt'
        cues,auto=parse(p)
        with open(f'{ch}/transcripts/{vid}.txt','w') as o:
            o.write(f"# {d['title']}\n# https://youtu.be/{vid} | {d['duration']}s | views {d.get('view_count')} | subs={'auto' if auto else 'manual'}\n")
            for c in d.get('chapters') or []: o.write(f"# chapter {fmt(c['start_time'])} {c['title']}\n")
            o.write('\n')
            for st,en,t in cues: o.write(f"[{fmt(st)}] {t}\n")
        print(vid,len(cues),'auto' if auto else 'manual')
