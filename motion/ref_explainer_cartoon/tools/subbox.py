from PIL import Image; import numpy as np, sys, glob
for f in sys.argv[1:]:
    a=np.asarray(Image.open(f).convert('RGB')).astype(int); H,W,_=a.shape
    # find dark box rows in bottom 20%: rows where central run of near-black pixels long
    dark=(a.sum(2)<60)
    rows=[y for y in range(int(H*0.8),H) if dark[y,W//4:3*W//4].mean()>0.5 or False]
    # better: locate box by column/row profile of dark pixels in bottom region
    sub=dark[int(H*0.8):]
    rp=sub.mean(1); ys=np.where(rp>0.2)[0]
    if len(ys)==0: print(f,'nobox'); continue
    y0,y1=ys.min()+int(H*0.8),ys.max()+int(H*0.8)
    band=dark[y0:y1+1]; cp=band.mean(0); xs=np.where(cp>0.6)[0]
    x0,x1=xs.min(),xs.max()
    box=a[y0:y1+1,x0:x1+1]
    white=(box.min(2)>200); wr=np.where(white.any(1))[0]; wc=np.where(white.any(0))[0]
    bg=np.median(box[~white].reshape(-1,3),0)
    print(f.split('/')[-1],'H',H,'box x',x0,x1,'w',x1-x0+1,'y',y0,y1,'h',y1-y0+1,'bottom margin',H-1-y1,'center x',(x0+x1)/2,'text rows',wr.min()+y0,wr.max()+y0,'text h',wr.max()-wr.min()+1,'pad x',wc.min(),x1-x0-wc.max(),'bg',bg, 'alpha-ish? bg std',box[~white].std())
