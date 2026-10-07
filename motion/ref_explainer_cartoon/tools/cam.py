import numpy as np,subprocess,sys
from PIL import Image
W,H=480,270; fps=30000/1001
def grab(v,t0,dur):
    p=subprocess.run(['ffmpeg','-v','error','-ss',str(t0),'-i',v,'-t',str(dur),'-vf',f'scale={W}:{H}','-f','rawvideo','-pix_fmt','gray','-'],capture_output=True)
    return np.frombuffer(p.stdout,np.uint8).reshape(-1,H,W).astype(np.float32)
def pc(a,b):
    wdw=np.outer(np.hanning(a.shape[0]),np.hanning(a.shape[1]))
    A=np.fft.fft2(a*wdw);B=np.fft.fft2(b*wdw);R=A*np.conj(B);R/=np.abs(R)+1e-9
    r=np.fft.ifft2(R).real; y,x=np.unravel_index(r.argmax(),r.shape)
    if y>a.shape[0]/2:y-=a.shape[0]
    if x>a.shape[1]/2:x-=a.shape[1]
    return x,y,r.max()
def scaled(img,s):
    im=Image.fromarray(img); w,h=im.size
    nw,nh=w/s,h/s; box=((w-nw)/2,(h-nh)/2,(w+nw)/2,(h+nh)/2)
    return np.asarray(im.transform((w,h),Image.EXTENT,box,Image.BILINEAR)).astype(np.float32)
def est(a,b):
    crop=lambda x:x[20:H-60,20:W-20]  # exclude subtitles
    best=None
    for s in np.arange(0.96,1.06,0.002):
        bs=scaled(b,1/s) if s!=1 else b   # undo zoom of b
        dx,dy,_=pc(crop(a),crop(bs))
        bb=np.roll(np.roll(bs,-dy,0),-dx,1) if False else bs
        err=np.abs(crop(a)[10:-10,10:-10]-np.roll(np.roll(crop(bs),dy,0),dx,1)[10:-10,10:-10]).mean()
        if best is None or err<best[0]: best=(err,s,dx,dy)
    return best
v,t0,dur,step=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),int(sys.argv[4])
fr=grab(v,t0,dur)
for i in range(0,len(fr)-step,step):
    e,s,dx,dy=est(fr[i],fr[i+step])
    print(f't={t0+i/fps:.2f} scale/{step}f={s:.3f} (per f {(s**(1/step)-1)*100:+.3f}%) shift=({dx*4},{dy*4})px@1920/{step}f err={e:.1f}')
