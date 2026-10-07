# usage: sheet.py video out_prefix start dur fps [cols rows width]
import sys,subprocess,os,glob,tempfile
from PIL import Image,ImageDraw,ImageFont
v,out,st,du,fps=sys.argv[1:6]; cols=int(sys.argv[6]) if len(sys.argv)>6 else 6; rows=int(sys.argv[7]) if len(sys.argv)>7 else 5; w=int(sys.argv[8]) if len(sys.argv)>8 else 320
td=tempfile.mkdtemp()
N=max(1,round((30000/1001)/eval(fps)))
subprocess.run(['ffmpeg','-v','error','-ss',st,'-i',v,'-t',du,'-vf',f"select='not(mod(n\\,{N}))',scale={w}:-2",'-vsync','vfr',f'{td}/%05d.jpg'],check=True)
fs=sorted(glob.glob(td+'/*.jpg')); st=float(st); fr=(30000/1001)/N
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',14)
n=cols*rows
for k in range(0,len(fs),n):
    ims=[Image.open(f) for f in fs[k:k+n]]; h=ims[0].height
    S=Image.new('RGB',(cols*w,rows*h),'gray')
    for i,im in enumerate(ims):
        idx=k+i; t=st+idx/fr
        d=ImageDraw.Draw(im); lab=f'{t:.2f}s' if fr<=2 else f'{t:.2f} f{idx}'
        d.rectangle([0,0,len(lab)*8+6,17],fill='black'); d.text((3,1),lab,fill='yellow',font=font)
        S.paste(im,((i%cols)*w,(i//cols)*h))
    S.save(f'{out}_{k//n}.jpg',quality=85)
print(len(fs),'frames')
