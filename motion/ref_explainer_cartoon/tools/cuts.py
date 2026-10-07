import numpy as np,sys,json
fps=30000/1001
out={}
for id in ['OR-55EGPOLY','jb0NxoZHuu8','mBhCwJK1xR4']:
    a=np.load(f'scenes/{id}_small.npy',mmap_mode='r')
    top=a[:,:76].astype(np.int16)
    d=np.abs(np.diff(top,axis=0)).mean(axis=(1,2,3))  # d[i]: frame i -> i+1
    # segments of activity
    act=d>1.5
    segs=[];i=0;n=len(d)
    while i<n:
        if act[i]:
            j=i
            while j+1<n and act[j+1]: j+=1
            tot=np.abs(top[j+1]-top[i]).mean()
            segs.append((i,j,float(d[i:j+1].max()),float(tot)))
            i=j+1
        else: i+=1
    # scene change = total change >= 20 (big recomposition)
    ev=[]
    for s,e,mx,tot in segs:
        L=e-s+1
        if tot<18: continue
        kind='hard' if L==1 else ('near-hard' if L<=2 else 'gradual')
        ev.append(dict(t=round(s/fps,2),len=L,max=round(mx,1),tot=round(tot,1),kind=kind))
    ts=[e['t'] for e in ev]
    gaps=np.diff([0]+ts)
    from collections import Counter
    c=Counter(e['kind'] for e in ev)
    gl=[e['len'] for e in ev if e['kind']=='gradual']
    print(id,'events',len(ev),dict(c),'mean shot %.2fs median %.2fs'%(np.mean(gaps),np.median(gaps)),'gradual len median',np.median(gl) if gl else None, 'pct',np.percentile(gl,[25,50,75]) if gl else None)
    # histogram of gradual lengths
    print('  gradual len hist',sorted(Counter(gl).items())[:25])
    out[id]=ev
json.dump(out,open('scenes/events.json','w'),ensure_ascii=False,indent=0)
