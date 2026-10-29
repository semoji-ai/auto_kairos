#!/usr/bin/env python3
# usage: beatsheet.py video out.jpg t1 t2 ... (seconds; frame taken at t+offset 1.2s) [cols=5]
import sys,subprocess,tempfile,os
from PIL import Image,ImageDraw,ImageFont
v,out=sys.argv[1],sys.argv[2]; ts=[float(x) for x in sys.argv[3:]]
td=tempfile.mkdtemp(); w=384; cols=5
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16)
ims=[]
for i,t in enumerate(ts):
    p=f'{td}/{i:03d}.jpg'
    subprocess.run(['ffmpeg','-v','error','-ss',str(t),'-i',v,'-frames:v','1','-vf',f'scale={w}:-2','-y',p],check=True)
    im=Image.open(p); d=ImageDraw.Draw(im); lab=f'#{i+1} {int(t//60)}:{t%60:04.1f}'
    d.rectangle([0,0,len(lab)*9+6,20],fill='black'); d.text((3,1),lab,fill='yellow',font=font); ims.append(im)
h=ims[0].height; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(cols*w,rows*h),'gray')
for i,im in enumerate(ims): S.paste(im,((i%cols)*w,(i//cols)*h))
S.save(out,quality=82); print(out,len(ims))
